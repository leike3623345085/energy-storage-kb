#!/usr/bin/env python3
"""
Guardrails - 确定性约束检查模块
护栏系统：硬性规则，Agent 不可违背
"""

import json
import yaml
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """验证结果"""
    passed: bool
    code: str
    message: str
    details: Optional[Dict] = None


class DataQualityGuardrail:
    """数据质量护栏"""
    
    def __init__(self, config: Dict):
        self.min_crawler_items = config.get('min_crawler_items', 20)
        self.min_news_items = config.get('min_news_items', 10)
        self.stock_data_required = config.get('stock_data_required', True)
        
    def check(self, data_dir: Path) -> ValidationResult:
        """检查数据质量"""
        today = datetime.now().strftime('%Y%m%d')
        
        # 检查爬虫数据
        crawler_files = list((data_dir / 'crawler').glob(f'*{today}*.json'))
        crawler_count = 0
        for f in crawler_files:
            try:
                with open(f) as fp:
                    crawler_count += len(json.load(fp))
            except:
                pass
        
        if crawler_count < self.min_crawler_items:
            return ValidationResult(
                passed=False,
                code="E001",
                message=f"爬虫数据不足: {crawler_count} < {self.min_crawler_items}",
                details={'current': crawler_count, 'required': self.min_crawler_items}
            )
        
        # 检查搜索数据
        news_files = list((data_dir / 'news').glob(f'*{today}*.json'))
        news_count = 0
        for f in news_files:
            try:
                with open(f) as fp:
                    news_count += len(json.load(fp))
            except:
                pass
        
        if news_count < self.min_news_items:
            return ValidationResult(
                passed=False,
                code="E001",
                message=f"新闻数据不足: {news_count} < {self.min_news_items}",
                details={'current': news_count, 'required': self.min_news_items}
            )
        
        return ValidationResult(
            passed=True,
            code="OK",
            message="数据质量检查通过",
            details={'crawler': crawler_count, 'news': news_count}
        )


class FormatGuardrail:
    """格式验证护栏"""
    
    def __init__(self, config: Dict):
        self.required_sections = config.get('required_sections', [
            "市场动态", "技术进展", "政策动态", "行情数据"
        ])
    
    def check(self, report_content: str) -> ValidationResult:
        """检查报告格式"""
        missing_sections = []
        for section in self.required_sections:
            if section not in report_content:
                missing_sections.append(section)
        
        if missing_sections:
            return ValidationResult(
                passed=False,
                code="E002",
                message=f"报告缺少必要章节: {', '.join(missing_sections)}",
                details={'missing': missing_sections}
            )
        
        return ValidationResult(
            passed=True,
            code="OK",
            message="格式验证通过"
        )


class SafetyGuardrail:
    """安全护栏"""
    
    def __init__(self, config: Dict):
        self.max_retries = config.get('max_retries', 3)
        self.timeout_seconds = config.get('timeout_seconds', 300)
    
    def check_execution_time(self, start_time: datetime) -> ValidationResult:
        """检查执行时间"""
        elapsed = (datetime.now() - start_time).total_seconds()
        if elapsed > self.timeout_seconds:
            return ValidationResult(
                passed=False,
                code="E005",
                message=f"执行超时: {elapsed}s > {self.timeout_seconds}s",
                details={'elapsed': elapsed, 'limit': self.timeout_seconds}
            )
        return ValidationResult(
            passed=True,
            code="OK",
            message="执行时间正常"
        )


class GuardrailsSystem:
    """护栏系统总控"""
    
    def __init__(self, config_path: Optional[Path] = None):
        if config_path is None:
            config_path = Path(__file__).parent / 'harness_config.yaml'
        
        with open(config_path) as f:
            self.config = yaml.safe_load(f)
        
        constraints = self.config.get('components', {}).get('deterministic_constraints', {})
        
        self.data_quality = DataQualityGuardrail(constraints.get('rules', {}).get('data_quality', {}))
        self.format_check = FormatGuardrail(constraints.get('rules', {}).get('format_validation', {}))
        self.safety = SafetyGuardrail(constraints.get('rules', {}).get('safety', {}))
    
    def pre_flight_check(self, data_dir: Path) -> Tuple[bool, List[ValidationResult]]:
        """
        飞行前检查 - 在执行任务前的全面检查
        
        Returns:
            (是否通过, 检查结果列表)
        """
        results = []
        
        # 数据质量检查
        result = self.data_quality.check(data_dir)
        results.append(result)
        
        # 可以添加更多检查...
        
        all_passed = all(r.passed for r in results)
        return all_passed, results
    
    def validate_output(self, report_content: str) -> ValidationResult:
        """验证输出内容"""
        return self.format_check.check(report_content)
    
    def check_timeout(self, start_time: datetime) -> ValidationResult:
        """检查是否超时"""
        return self.safety.check_execution_time(start_time)


def main():
    """测试护栏系统"""
    guardrails = GuardrailsSystem()
    
    data_dir = Path('/root/.openclaw/workspace/energy_storage/data')
    passed, results = guardrails.pre_flight_check(data_dir)
    
    print(f"Pre-flight check: {'PASS' if passed else 'FAIL'}")
    for r in results:
        status = "✓" if r.passed else "✗"
        print(f"  {status} [{r.code}] {r.message}")


if __name__ == '__main__':
    main()
