#!/usr/bin/env python3
"""
Agent Runner - Agent执行器
基于 Harness Engineering 的 Agent 任务执行总控
"""

import yaml
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass

# 导入 Harness 组件
from guardrails import GuardrailsSystem, ValidationResult
from feedback_loop import FeedbackLoop
from progressive_context import ProgressiveDisclosure, Context
from drift_detector import DriftDetector, DriftCheckResult


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('AgentRunner')


@dataclass
class TaskResult:
    """任务执行结果"""
    success: bool
    task_type: str
    started_at: str
    completed_at: str
    duration_seconds: float
    steps_completed: List[str]
    errors: List[Dict]
    output: Optional[str] = None


class AgentRunner:
    """
    Harness Engineering Agent 执行器
    
    基于 OpenAI Harness Engineering 架构，提供：
    - 飞行前检查（Guardrails）
    - 渐进式上下文加载
    - 任务执行
    - 反馈循环
    - 强制漂移检测（不可跳过）
    """
    
    def __init__(self, workspace_dir: Optional[Path] = None):
        if workspace_dir is None:
            workspace_dir = Path('/root/.openclaw/workspace/energy_storage')
        
        self.workspace_dir = workspace_dir
        self.data_dir = workspace_dir / 'data'
        self.harness_dir = workspace_dir / 'harness'
        self.config_path = self.harness_dir / 'harness_config.yaml'
        
        # 初始化 Harness 组件
        self.guardrails = GuardrailsSystem(self.config_path)
        self.feedback = FeedbackLoop(self.config_path)
        self.context_loader = ProgressiveDisclosure(self.config_path, self.data_dir)
        self.drift_detector = DriftDetector(self.config_path)
        
        # 加载配置
        with open(self.config_path) as f:
            self.config = yaml.safe_load(f)
        
        # 审计追踪：记录所有漂移检测
        self.drift_audit_log: List[Dict] = []
        
        logger.info("AgentRunner initialized with Harness Engineering (Drift Detection enabled)")
    
    def execute_workflow(self, workflow_name: str, **params) -> TaskResult:
        """
        执行预定义的工作流 - 带强制漂移检测
        
        保证：每个 agent_executor 步骤后必定执行漂移检测
        """
        started_at = datetime.now()
        steps_completed = []
        errors = []
        
        logger.info(f"Starting workflow: {workflow_name}")
        
        try:
            # 获取工作流定义
            workflows = self.config.get('workflows', {})
            workflow = workflows.get(workflow_name)
            
            if not workflow:
                raise ValueError(f"Unknown workflow: {workflow_name}")
            
            steps = workflow.get('steps', [])
            
            # 按顺序执行步骤
            for step in steps:
                step_name = step.get('step')
                component = step.get('component')
                description = step.get('description')
                
                logger.info(f"Executing step: {step_name} ({component}) - {description}")
                
                # 根据组件类型执行
                if component == 'guardrails':
                    result = self._execute_guardrail_step(step_name, **params)
                    
                elif component == 'progressive_disclosure':
                    result = self._execute_context_step(step_name, workflow_name, **params)
                    
                elif component == 'feedback_loop':
                    result = self._execute_feedback_step(step_name, **params)
                    
                elif component == 'agent_executor':
                    # ===== Agent 执行 + 强制漂移检测 =====
                    result = self._execute_agent_with_mandatory_drift_check(
                        step=step,
                        step_name=step_name,
                        workflow_name=workflow_name,
                        **params
                    )
                    
                elif component == 'delivery':
                    result = self._execute_delivery_step(step_name, **params)
                    
                else:
                    result = {'status': 'skipped', 'reason': 'unknown_component'}
                
                # 检查步骤结果
                if isinstance(result, dict) and not result.get('passed', True):
                    error_info = {
                        'step': step_name,
                        'component': component,
                        'error': result.get('message', 'Step failed'),
                        'code': result.get('code', 'UNKNOWN')
                    }
                    errors.append(error_info)
                    
                    # 触发反馈循环
                    self.feedback.process_error(
                        code=error_info['code'],
                        message=error_info['error'],
                        context={'step': step_name, 'workflow': workflow_name}
                    )
                    
                    # 如果配置了失败停止，则中断
                    if step.get('fail_fast', True):
                        logger.error(f"Step {step_name} failed, stopping workflow")
                        break
                
                steps_completed.append(step_name)
                
                # 检查超时
                timeout_check = self.guardrails.check_timeout(started_at)
                if not timeout_check.passed:
                    logger.error(f"Workflow timeout: {timeout_check.message}")
                    errors.append({
                        'step': 'timeout_check',
                        'error': timeout_check.message,
                        'code': 'E005'
                    })
                    break
            
            completed_at = datetime.now()
            duration = (completed_at - started_at).total_seconds()
            
            return TaskResult(
                success=len(errors) == 0,
                task_type=workflow_name,
                started_at=started_at.isoformat(),
                completed_at=completed_at.isoformat(),
                duration_seconds=duration,
                steps_completed=steps_completed,
                errors=errors
            )
            
        except Exception as e:
            logger.exception("Workflow execution failed")
            completed_at = datetime.now()
            duration = (completed_at - started_at).total_seconds()
            
            return TaskResult(
                success=False,
                task_type=workflow_name,
                started_at=started_at.isoformat(),
                completed_at=completed_at.isoformat(),
                duration_seconds=duration,
                steps_completed=steps_completed,
                errors=[{'step': 'exception', 'error': str(e)}]
            )
    
    def _execute_agent_with_mandatory_drift_check(
        self,
        step: Dict,
        step_name: str,
        workflow_name: str,
        **params
    ) -> Dict:
        """
        执行 Agent 步骤 + 强制漂移检测
        
        保证机制：
        1. 即使 Agent 执行异常，也会执行漂移检测
        2. 漂移检测无法被配置禁用
        3. 检测结果必定记录到审计日志
        """
        drift_check_executed = False
        drift_result = None
        agent_result = None
        
        try:
            # 1. 执行 Agent
            agent_result = self._execute_agent_step(step_name, **params)
            
        except Exception as e:
            logger.error(f"Agent execution failed: {e}")
            agent_result = {
                'passed': False,
                'error': str(e),
                'output': f"执行异常: {e}"
            }
        
        # ===== 强制漂移检测（以下代码无法被跳过） =====
        try:
            # 强制启用检测器（即使被禁用）
            if not self.drift_detector.enabled:
                logger.warning("[强制审查] 漂移检测器被禁用，强制启用")
                self.drift_detector.enabled = True
            
            # 执行漂移检测
            description = step.get('description', '未知任务')
            output = agent_result.get('output', str(agent_result))
            
            drift_config = self.config.get('drift_detection', {})
            keyword_library = drift_config.get('keyword_library', {})
            expected_keywords = keyword_library.get(workflow_name, {}).get('required', [])
            
            drift_result = self.drift_detector.check(
                task_description=description,
                actual_result=str(output),
                expected_keywords=expected_keywords if expected_keywords else None,
                check_types=["keyword", "semantic", "format"]
            )
            drift_check_executed = True
            
            # 记录到审计日志
            audit_record = {
                'timestamp': datetime.now().isoformat(),
                'workflow': workflow_name,
                'step': step_name,
                'task': description,
                'drift_detected': drift_result.is_drift,
                'confidence': drift_result.confidence,
                'check_type': drift_result.check_type,
                'verified': True
            }
            self.drift_audit_log.append(audit_record)
            
            # 强制处理检测结果
            if drift_result.is_drift:
                logger.warning(
                    f"[强制审查] 步骤 {step_name} 检测到漂移: "
                    f"{drift_result.reason} (置信度: {drift_result.confidence:.2f})"
                )
                
                agent_result['drift_detected'] = True
                agent_result['drift_info'] = drift_result.to_dict()
                
                # 根据置信度处理
                agent_result = self._enforce_drift_handling(
                    step_name=step_name,
                    result=agent_result,
                    drift_result=drift_result,
                    workflow_name=workflow_name
                )
            else:
                agent_result['drift_detected'] = False
                agent_result['drift_info'] = drift_result.to_dict()
                logger.info(
                    f"[强制审查] 步骤 {step_name} 检测通过 (置信度: {drift_result.confidence:.2f})"
                )
                
        except Exception as e:
            logger.error(f"[强制审查] 漂移检测执行失败: {e}")
            # 检测失败也记录下来
            self.drift_audit_log.append({
                'timestamp': datetime.now().isoformat(),
                'workflow': workflow_name,
                'step': step_name,
                'error': str(e),
                'check_executed': False
            })
        
        # 验证检测确实执行了
        if not drift_check_executed:
            logger.critical(
                f"[严重错误] 步骤 {step_name} 的漂移检测未执行！"
                "这是不应该发生的情况。"
            )
        
        return agent_result
    
    def _execute_guardrail_step(self, step_name: str, **params) -> Dict:
        """执行护栏步骤"""
        if step_name == 'pre_flight_check':
            passed, results = self.guardrails.pre_flight_check(self.data_dir)
            return {
                'passed': passed,
                'code': 'E001' if not passed else 'OK',
                'message': '; '.join([r.message for r in results if not r.passed]),
                'details': [r.__dict__ for r in results]
            }
        elif step_name == 'validate_output':
            content = params.get('report_content', '')
            result = self.guardrails.validate_output(content)
            return {
                'passed': result.passed,
                'code': result.code,
                'message': result.message,
                'details': result.details
            }
        return {'passed': True}
    
    def _execute_context_step(self, step_name: str, workflow_name: str, **params) -> Dict:
        """执行上下文加载步骤"""
        context = self.context_loader.load_context(workflow_name, **params)
        return {
            'passed': True,
            'context_level': context.level.value,
            'summary': self.context_loader.get_context_summary(context),
            'sources': context.sources
        }
    
    def _execute_feedback_step(self, step_name: str, **params) -> Dict:
        """执行反馈步骤"""
        return {
            'passed': True,
            'action': 'recorded',
            'timestamp': datetime.now().isoformat()
        }
    
    def _execute_agent_step(self, step_name: str, **params) -> Dict:
        """执行 Agent 生成步骤"""
        logger.info(f"Agent executing: {step_name}")
        return {
            'passed': True,
            'status': 'generated',
            'output_size': 0
        }
    
    def _enforce_drift_handling(
        self,
        step_name: str,
        result: Dict,
        drift_result: DriftCheckResult,
        workflow_name: str
    ) -> Dict:
        """强制处理漂移结果"""
        drift_config = self.config.get('drift_detection', {})
        mandatory_config = drift_config.get('mandatory', {})
        
        confidence = drift_result.confidence
        
        if confidence > 0.8:
            # 高置信度漂移：强制阻断
            logger.error(f"[强制审查] 高置信度漂移: {drift_result.reason}")
            
            self.feedback.process_error(
                code='E008',
                message=f"高置信度漂移: {drift_result.reason}",
                context={
                    'step': step_name,
                    'workflow': workflow_name,
                    'drift_type': drift_result.check_type,
                    'confidence': confidence,
                    'action': 'block'
                }
            )
            
            if mandatory_config.get('block_on_drift', True):
                result['passed'] = False
                result['blocked_by_drift'] = True
                result['error'] = f"任务被漂移检测阻断: {drift_result.reason}"
                
        elif confidence > 0.6:
            # 中等置信度：标记修复
            logger.warning(f"[强制审查] 中等置信度漂移: {drift_result.reason}")
            
            self.feedback.process_error(
                code='E008-M',
                message=f"中等置信度漂移: {drift_result.reason}",
                context={
                    'step': step_name,
                    'workflow': workflow_name,
                    'drift_type': drift_result.check_type,
                    'confidence': confidence,
                    'action': 'retry'
                }
            )
            
            result['needs_correction'] = True
            result['drift_suggestion'] = drift_result.suggestion
            
        else:
            # 低置信度：记录警告
            logger.info(f"[强制审查] 低置信度漂移: {drift_result.reason}")
            result['drift_warning'] = drift_result.reason
        
        return result
    
    def _execute_delivery_step(self, step_name: str, **params) -> Dict:
        """执行交付步骤"""
        logger.info(f"Delivering: {step_name}")
        return {
            'passed': True,
            'status': 'delivered'
        }
    
    def verify_all_drift_checks_completed(self) -> bool:
        """
        验证所有漂移检测是否都已完成
        
        返回: True 如果所有检测都执行了，否则 False
        """
        incomplete = [
            record for record in self.drift_audit_log
            if not record.get('verified', False)
        ]
        
        if incomplete:
            logger.error(f"[验证失败] 发现 {len(incomplete)} 个未完成漂移检测的记录")
            return False
        
        logger.info("[验证通过] 所有漂移检测都已完成")
        return True
    
    def run_daily_report(self) -> TaskResult:
        """快捷方法：运行日报工作流"""
        return self.execute_workflow('daily_report')
    
    def run_crawler_monitor(self) -> TaskResult:
        """快捷方法：运行爬虫监控"""
        return self.execute_workflow('crawler_monitor')
    
    def run_self_healing(self) -> TaskResult:
        """快捷方法：运行自愈系统"""
        return self.execute_workflow('self_healing')
    
    def get_system_health(self) -> Dict:
        """获取系统健康状态"""
        return {
            'timestamp': datetime.now().isoformat(),
            'guardrails': 'active',
            'feedback_loop': 'active',
            'progressive_disclosure': 'active',
            'drift_detection': 'active',
            'drift_stats': self.drift_detector.get_stats(),
            'drift_audit_count': len(self.drift_audit_log),
            'error_stats': self.feedback.get_error_stats(),
            'learned_patterns': len(self.feedback.rule_updater.get_learned_patterns())
        }


def main():
    """测试 Agent Runner"""
    runner = AgentRunner()
    
    print("=" * 50)
    print("Harness Engineering Agent Runner")
    print("=" * 50)
    
    # 显示系统健康状态
    health = runner.get_system_health()
    print("\n[系统健康状态]")
    print(json.dumps(health, indent=2, ensure_ascii=False))
    
    # 测试日报工作流
    print("\n[测试日报工作流]")
    result = runner.run_daily_report()
    print(f"Success: {result.success}")
    print(f"Duration: {result.duration_seconds:.2f}s")
    print(f"Steps: {' -> '.join(result.steps_completed)}")
    if result.errors:
        print(f"Errors: {result.errors}")
    
    # 验证所有漂移检测都执行了
    print("\n[验证漂移检测执行状态]")
    all_completed = runner.verify_all_drift_checks_completed()
    print(f"所有检测已完成: {'✅ 是' if all_completed else '❌ 否'}")


if __name__ == '__main__':
    main()
