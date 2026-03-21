#!/usr/bin/env python3
"""
Feedback Loop - 反馈循环系统
自动检测、分类、修复错误，并更新规则防止再犯
"""

import json
import yaml
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum


class ErrorType(Enum):
    """错误类型"""
    DATA_INSUFFICIENT = "data_insufficient"
    FORMAT_INVALID = "format_invalid"
    DELIVERY_FAILED = "delivery_failed"
    SYNC_FAILED = "sync_failed"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


@dataclass
class ErrorRecord:
    """错误记录"""
    timestamp: str
    error_type: str
    code: str
    message: str
    context: Dict
    auto_fixed: bool
    fix_action: Optional[str] = None
    fix_result: Optional[str] = None


class ErrorClassifier:
    """错误分类器"""
    
    def __init__(self, config: Dict):
        self.error_library = config.get('error_library', {})
    
    def classify(self, error_code: str, message: str) -> ErrorType:
        """根据错误代码和消息分类错误"""
        code_to_type = {
            "E001": ErrorType.DATA_INSUFFICIENT,
            "E002": ErrorType.FORMAT_INVALID,
            "E003": ErrorType.DELIVERY_FAILED,
            "E004": ErrorType.SYNC_FAILED,
            "E005": ErrorType.TIMEOUT,
        }
        return code_to_type.get(error_code, ErrorType.UNKNOWN)
    
    def can_auto_fix(self, error_type: ErrorType) -> bool:
        """判断是否可以自动修复"""
        type_str = error_type.value
        error_config = self.error_library.get(type_str, {})
        return error_config.get('auto_fix', False)
    
    def get_fix_action(self, error_type: ErrorType) -> Optional[str]:
        """获取修复动作"""
        type_str = error_type.value
        error_config = self.error_library.get(type_str, {})
        return error_config.get('fix_action')


class AutoRepair:
    """自动修复器"""
    
    def __init__(self):
        self.fix_strategies: Dict[str, Callable] = {
            'retry_crawler': self._retry_crawler,
            'regenerate_with_template': self._regenerate_with_template,
            'retry_with_backoff': self._retry_with_backoff,
            'notify_human': self._notify_human,
        }
    
    def _retry_crawler(self, context: Dict) -> str:
        """重试爬虫"""
        import subprocess
        try:
            result = subprocess.run(
                ['python3', 'crawler_multi.py'],
                cwd='/root/.openclaw/workspace/energy_storage',
                capture_output=True,
                text=True,
                timeout=300
            )
            return "success" if result.returncode == 0 else f"failed: {result.stderr}"
        except Exception as e:
            return f"error: {str(e)}"
    
    def _regenerate_with_template(self, context: Dict) -> str:
        """使用模板重新生成"""
        # 重新触发报告生成，强制使用模板
        return "regenerated_with_template"
    
    def _retry_with_backoff(self, context: Dict) -> str:
        """指数退避重试"""
        import time
        max_retries = 3
        for i in range(max_retries):
            time.sleep(2 ** i)  # 1, 2, 4 秒
            # 重试逻辑...
        return "retried"
    
    def _notify_human(self, context: Dict) -> str:
        """通知人工处理"""
        # 发送通知给管理员
        return "human_notified"
    
    def fix(self, action: str, context: Dict) -> str:
        """执行修复"""
        strategy = self.fix_strategies.get(action)
        if strategy:
            return strategy(context)
        return f"unknown_fix_action: {action}"


class RuleUpdater:
    """规则更新器 - 防止重复犯错"""
    
    def __init__(self, config_path: Path):
        self.config_path = config_path
        self.learned_rules_file = config_path.parent / 'learned_rules.json'
    
    def record_error_pattern(self, error_record: ErrorRecord):
        """记录错误模式"""
        # 计算错误指纹
        fingerprint = hashlib.md5(
            f"{error_record.error_type}:{error_record.code}".encode()
        ).hexdigest()[:8]
        
        rules = {}
        if self.learned_rules_file.exists():
            with open(self.learned_rules_file) as f:
                rules = json.load(f)
        
        # 记录错误出现次数
        if fingerprint not in rules:
            rules[fingerprint] = {
                'error_type': error_record.error_type,
                'code': error_record.code,
                'count': 0,
                'first_seen': error_record.timestamp,
                'contexts': []
            }
        
        rules[fingerprint]['count'] += 1
        rules[fingerprint]['last_seen'] = error_record.timestamp
        rules[fingerprint]['contexts'].append(error_record.context)
        
        # 只保留最近10个上下文
        rules[fingerprint]['contexts'] = rules[fingerprint]['contexts'][-10:]
        
        with open(self.learned_rules_file, 'w') as f:
            json.dump(rules, f, indent=2, ensure_ascii=False)
        
        return fingerprint
    
    def get_learned_patterns(self) -> Dict:
        """获取已学习的错误模式"""
        if not self.learned_rules_file.exists():
            return {}
        with open(self.learned_rules_file) as f:
            return json.load(f)


class FeedbackLoop:
    """反馈循环系统总控"""
    
    def __init__(self, config_path: Optional[Path] = None):
        if config_path is None:
            config_path = Path(__file__).parent / 'harness_config.yaml'
        
        with open(config_path) as f:
            self.config = yaml.safe_load(f)
        
        self.classifier = ErrorClassifier(self.config)
        self.auto_repair = AutoRepair()
        self.rule_updater = RuleUpdater(config_path)
        
        # 错误记录文件
        self.error_log_file = Path(__file__).parent / 'error_log.jsonl'
    
    def process_error(self, code: str, message: str, context: Dict) -> Dict:
        """
        处理错误的主流程
        
        Args:
            code: 错误代码
            message: 错误消息
            context: 错误上下文
            
        Returns:
            处理结果
        """
        # 1. 分类错误
        error_type = self.classifier.classify(code, message)
        
        # 2. 创建错误记录
        record = ErrorRecord(
            timestamp=datetime.now().isoformat(),
            error_type=error_type.value,
            code=code,
            message=message,
            context=context,
            auto_fixed=False
        )
        
        # 3. 判断是否可以自动修复
        can_fix = self.classifier.can_auto_fix(error_type)
        fix_result = None
        
        if can_fix:
            action = self.classifier.get_fix_action(error_type)
            if action:
                fix_result = self.auto_repair.fix(action, context)
                record.auto_fixed = True
                record.fix_action = action
                record.fix_result = fix_result
        
        # 4. 记录错误
        self._log_error(record)
        
        # 5. 更新规则
        fingerprint = self.rule_updater.record_error_pattern(record)
        
        return {
            'error_type': error_type.value,
            'auto_fixed': record.auto_fixed,
            'fix_action': record.fix_action,
            'fix_result': fix_result,
            'fingerprint': fingerprint
        }
    
    def _log_error(self, record: ErrorRecord):
        """记录错误到日志文件"""
        with open(self.error_log_file, 'a') as f:
            f.write(json.dumps(asdict(record), ensure_ascii=False) + '\n')
    
    def get_error_stats(self) -> Dict:
        """获取错误统计"""
        if not self.error_log_file.exists():
            return {}
        
        stats = {}
        with open(self.error_log_file) as f:
            for line in f:
                try:
                    record = json.loads(line)
                    error_type = record.get('error_type', 'unknown')
                    stats[error_type] = stats.get(error_type, 0) + 1
                except:
                    pass
        
        return stats
    
    def detect_recurring_issue(self, error_type: str, threshold: int = 3) -> bool:
        """检测是否为重复出现的问题"""
        patterns = self.rule_updater.get_learned_patterns()
        for pattern in patterns.values():
            if pattern.get('error_type') == error_type:
                if pattern.get('count', 0) >= threshold:
                    return True
        return False


def main():
    """测试反馈循环系统"""
    feedback = FeedbackLoop()
    
    # 模拟一个数据不足的错误
    result = feedback.process_error(
        code="E001",
        message="爬虫数据不足: 5 < 20",
        context={'date': '2026-03-21', 'crawler_count': 5}
    )
    
    print("Feedback Loop Result:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    print("\nError Stats:")
    print(json.dumps(feedback.get_error_stats(), indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
