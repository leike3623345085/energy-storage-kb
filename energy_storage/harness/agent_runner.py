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
        
        # 加载配置
        with open(self.config_path) as f:
            self.config = yaml.safe_load(f)
        
        logger.info("AgentRunner initialized with Harness Engineering")
    
    def execute_workflow(self, workflow_name: str, **params) -> TaskResult:
        """
        执行预定义的工作流
        
        Args:
            workflow_name: 工作流名称 (daily_report, crawler_monitor, self_healing)
            **params: 工作流参数
            
        Returns:
            TaskResult 对象
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
                    result = self._execute_agent_step(step_name, **params)
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
        # 记录执行结果
        return {
            'passed': True,
            'action': 'recorded',
            'timestamp': datetime.now().isoformat()
        }
    
    def _execute_agent_step(self, step_name: str, **params) -> Dict:
        """执行 Agent 生成步骤（占位，实际调用 AI 生成）"""
        logger.info(f"Agent executing: {step_name}")
        # 这里会调用实际的 AI 生成逻辑
        return {
            'passed': True,
            'status': 'generated',
            'output_size': 0
        }
    
    def _execute_delivery_step(self, step_name: str, **params) -> Dict:
        """执行交付步骤"""
        logger.info(f"Delivering: {step_name}")
        # 这里会调用邮件发送等逻辑
        return {
            'passed': True,
            'status': 'delivered'
        }
    
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


if __name__ == '__main__':
    main()
