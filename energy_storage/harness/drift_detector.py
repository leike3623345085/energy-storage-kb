#!/usr/bin/env python3
"""
Drift Detector - 漂移检测模块

检测 Agent 执行结果是否偏离预期目标
基于 HARNESS Engineering 第5步：结果校验与漂移检测
"""

import json
import logging
from difflib import SequenceMatcher
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict

logger = logging.getLogger('DriftDetector')


@dataclass
class DriftCheckResult:
    """漂移检测结果"""
    is_drift: bool
    confidence: float  # 0-1，越高表示越确定漂移
    reason: str
    suggestion: Optional[str] = None
    check_type: str = "semantic"  # semantic | keyword | format
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict:
        return asdict(self)


class DriftDetector:
    """
    漂移检测器
    
    检测维度：
    1. 关键词缺失检测 - 检查预期关键词是否出现在结果中
    2. 语义偏离检测 - 检查结果与任务目标的相关性
    3. 格式合规检测 - 检查输出格式是否符合预期
    """
    
    def __init__(self, config_path: Optional[Path] = None, threshold: float = 0.6):
        """
        Args:
            config_path: 配置文件路径
            threshold: 漂移检测阈值，低于此值判定为漂移
        """
        self.threshold = threshold
        self.config_path = config_path
        self.check_history: List[Dict] = []
        
        # 加载配置
        if config_path and config_path.exists():
            import yaml
            with open(config_path) as f:
                config = yaml.safe_load(f)
                drift_config = config.get('drift_detection', {})
                self.threshold = drift_config.get('threshold', threshold)
                self.enabled = drift_config.get('enabled', True)
        else:
            self.enabled = True
        
        logger.info(f"DriftDetector initialized (threshold={self.threshold}, enabled={self.enabled})")
    
    def check(
        self,
        task_description: str,
        actual_result: str,
        expected_keywords: Optional[List[str]] = None,
        expected_format: Optional[str] = None,
        check_types: Optional[List[str]] = None
    ) -> DriftCheckResult:
        """
        执行漂移检测
        
        Args:
            task_description: 原始任务描述
            actual_result: 实际执行结果
            expected_keywords: 预期应包含的关键词列表
            expected_format: 预期的输出格式 (json|markdown|table|text)
            check_types: 检测类型列表 [keyword, semantic, format]
        
        Returns:
            DriftCheckResult 对象
        """
        if not self.enabled:
            return DriftCheckResult(
                is_drift=False,
                confidence=1.0,
                reason="漂移检测已禁用",
                check_type="disabled"
            )
        
        if check_types is None:
            # 如果没有指定关键词，只做格式检测（如果有格式要求）
            if expected_keywords:
                check_types = ["keyword", "semantic"]
            elif expected_format:
                check_types = ["format"]
            else:
                check_types = ["semantic"]
        
        # 执行各种检测
        results = []
        
        if "keyword" in check_types and expected_keywords:
            results.append(self._check_keywords(actual_result, expected_keywords))
        
        if "semantic" in check_types:
            results.append(self._check_semantic(task_description, actual_result))
        
        if "format" in check_types and expected_format:
            results.append(self._check_format(actual_result, expected_format))
        
        # 综合判断
        if not results:
            return DriftCheckResult(
                is_drift=False,
                confidence=1.0,
                reason="未执行任何检测",
                check_type="none"
            )
        
        # 如果有任何一项检测到漂移，则判定为漂移
        drift_results = [r for r in results if r['is_drift']]
        
        if drift_results:
            # 取置信度最高的漂移结果
            worst = max(drift_results, key=lambda x: x['confidence'])
            result = DriftCheckResult(
                is_drift=True,
                confidence=worst['confidence'],
                reason=worst['reason'],
                suggestion=worst.get('suggestion'),
                check_type=worst['type']
            )
        else:
            # 所有检测都通过
            avg_confidence = sum(r['confidence'] for r in results) / len(results)
            result = DriftCheckResult(
                is_drift=False,
                confidence=avg_confidence,
                reason="所有检测通过，未发现漂移",
                check_type="combined"
            )
        
        # 记录历史
        self._record_check(task_description, actual_result, result)
        
        return result
    
    def _check_keywords(
        self,
        actual_result: str,
        expected_keywords: List[str]
    ) -> Dict:
        """关键词缺失检测"""
        actual_lower = actual_result.lower()
        missing = []
        
        for keyword in expected_keywords:
            if keyword.lower() not in actual_lower:
                missing.append(keyword)
        
        if missing:
            confidence = len(missing) / len(expected_keywords)
            return {
                'is_drift': True,
                'confidence': confidence,
                'reason': f"缺少预期关键词: {', '.join(missing)}",
                'suggestion': f"补充以下内容: {missing}",
                'type': 'keyword',
                'details': {'missing': missing, 'expected': expected_keywords}
            }
        
        return {
            'is_drift': False,
            'confidence': 1.0,
            'reason': "所有关键词都存在",
            'type': 'keyword'
        }
    
    def _check_semantic(
        self,
        task_description: str,
        actual_result: str
    ) -> Dict:
        """语义偏离检测（改进版）"""
        # 提取关键词
        task_keywords = self._extract_keywords(task_description)
        result_keywords = self._extract_keywords(actual_result)
        
        # 计算任务关键词在结果中的覆盖率
        if task_keywords and result_keywords:
            # 计算交集
            intersection = set(task_keywords) & set(result_keywords)
            coverage = len(intersection) / len(set(task_keywords)) if task_keywords else 0
        else:
            coverage = 0.0
        
        # 如果没有足够的关键词，降低阈值要求
        effective_threshold = self.threshold
        task_kw_count = len(set(task_keywords))
        
        # 对于短任务描述，大幅降低阈值
        if task_kw_count <= 10:
            effective_threshold = 0.15  # 短任务只需要15%覆盖率
        elif task_kw_count <= 20:
            effective_threshold = 0.25
        elif len(result_keywords) < 10:
            effective_threshold = 0.25
        
        if coverage < effective_threshold:
            return {
                'is_drift': True,
                'confidence': 1 - coverage,
                'reason': f"结果与任务目标偏离（关键词覆盖率: {coverage:.2f}，阈值: {effective_threshold:.2f}）",
                'suggestion': "检查是否偏离了原始任务目标，考虑重新执行任务",
                'type': 'semantic',
                'details': {
                    'task_keywords': task_keywords[:10],
                    'result_keywords_count': len(result_keywords),
                    'intersection': list(intersection) if task_keywords and result_keywords else [],
                    'coverage': coverage
                }
            }
        
        return {
            'is_drift': False,
            'confidence': coverage,
            'reason': f"语义相关度良好（覆盖率: {coverage:.2f}）",
            'type': 'semantic',
            'details': {
                'task_keywords': task_keywords[:10],
                'result_keywords_count': len(result_keywords),
                'coverage': coverage
            }
        }
    
    def _check_format(
        self,
        actual_result: str,
        expected_format: str
    ) -> Dict:
        """格式合规检测"""
        format_indicators = {
            'json': lambda x: x.strip().startswith('{') or x.strip().startswith('['),
            'markdown': lambda x: '#' in x or '##' in x or '*' in x,
            'table': lambda x: '|' in x and '---' in x,
            'text': lambda x: True  # 纯文本总是合规
        }
        
        checker = format_indicators.get(expected_format, format_indicators['text'])
        
        if not checker(actual_result):
            return {
                'is_drift': True,
                'confidence': 0.8,
                'reason': f"输出格式不符合预期: {expected_format}",
                'suggestion': f"请将输出格式化为: {expected_format}",
                'type': 'format'
            }
        
        return {
            'is_drift': False,
            'confidence': 1.0,
            'reason': f"格式符合预期: {expected_format}",
            'type': 'format'
        }
    
    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词（字符级匹配改进版）"""
        import re
        
        # 方法1: 提取中文词汇（长度>=2的中文字符串）
        chinese_words = re.findall(r'[\u4e00-\u9fa5]{2,}', text)
        
        # 方法2: 额外提取所有可能的双字组合（提高匹配率）
        chinese_chars = re.findall(r'[\u4e00-\u9fa5]', text)
        bigrams = []
        for i in range(len(chinese_chars) - 1):
            bigrams.append(chinese_chars[i] + chinese_chars[i+1])
        
        # 提取英文单词
        english_words = re.findall(r'[a-zA-Z_]{3,}', text)
        
        # 合并所有关键词
        all_words = chinese_words + bigrams + english_words
        
        # 返回唯一的关键词列表
        return list(set(all_words))
    
    def _record_check(
        self,
        task_description: str,
        actual_result: str,
        result: DriftCheckResult
    ):
        """记录检测历史"""
        record = {
            'timestamp': result.timestamp,
            'task_hash': hash(task_description) % 10000,
            'result_hash': hash(actual_result) % 10000,
            'is_drift': result.is_drift,
            'confidence': result.confidence,
            'reason': result.reason,
            'check_type': result.check_type
        }
        
        self.check_history.append(record)
        
        # 保留最近100条记录
        if len(self.check_history) > 100:
            self.check_history = self.check_history[-100:]
    
    def get_stats(self) -> Dict:
        """获取漂移检测统计"""
        if not self.check_history:
            return {'total_checks': 0, 'drift_rate': 0.0}
        
        total = len(self.check_history)
        drift_count = sum(1 for r in self.check_history if r['is_drift'])
        
        return {
            'total_checks': total,
            'drift_count': drift_count,
            'drift_rate': drift_count / total if total > 0 else 0.0,
            'recent_24h': len([
                r for r in self.check_history
                if (datetime.now() - datetime.fromisoformat(r['timestamp'])).days < 1
            ])
        }
    
    def get_correction_strategy(self, result: DriftCheckResult) -> Dict:
        """
        获取修正策略
        
        根据漂移类型返回相应的修正建议
        """
        strategies = {
            'keyword': {
                'action': 'retry_with_enhanced_prompt',
                'prompt_addition': '请确保包含以下关键信息: {missing_keywords}',
                'auto_retry': True
            },
            'semantic': {
                'action': 'clarify_task',
                'prompt_addition': '请重新审视任务目标，确保输出与任务相关',
                'auto_retry': False,
                'escalate_to_user': True
            },
            'format': {
                'action': 'reformat_output',
                'prompt_addition': '请以 {expected_format} 格式重新输出',
                'auto_retry': True
            }
        }
        
        return strategies.get(result.check_type, {
            'action': 'manual_review',
            'auto_retry': False,
            'escalate_to_user': True
        })


# 快捷使用函数
def check_drift(
    task: str,
    result: str,
    expected_keywords: Optional[List[str]] = None,
    threshold: float = 0.6
) -> DriftCheckResult:
    """快速漂移检测"""
    detector = DriftDetector(threshold=threshold)
    return detector.check(task, result, expected_keywords=expected_keywords)


if __name__ == '__main__':
    # 测试漂移检测
    logging.basicConfig(level=logging.INFO)
    
    detector = DriftDetector()
    
    # 测试案例1: 正常情况
    result = detector.check(
        task_description="爬取储能行业新闻",
        actual_result="今日储能行业新闻：1. 宁德时代发布新技术 2. 储能电站并网成功",
        expected_keywords=["储能", "新闻"]
    )
    print(f"\n[测试1] 正常情况:")
    print(f"  漂移: {result.is_drift}, 置信度: {result.confidence:.2f}")
    print(f"  原因: {result.reason}")
    
    # 测试案例2: 关键词缺失
    result = detector.check(
        task_description="爬取储能行业新闻",
        actual_result="今日新能源汽车销量创新高",
        expected_keywords=["储能", "新闻"]
    )
    print(f"\n[测试2] 关键词缺失:")
    print(f"  漂移: {result.is_drift}, 置信度: {result.confidence:.2f}")
    print(f"  原因: {result.reason}")
    print(f"  建议: {result.suggestion}")
    
    # 统计信息
    print(f"\n[统计]")
    print(json.dumps(detector.get_stats(), indent=2, ensure_ascii=False))
