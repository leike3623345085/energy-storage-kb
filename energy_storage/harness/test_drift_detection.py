#!/usr/bin/env python3
"""
漂移检测集成示例
演示如何在实际工作流中使用漂移检测
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace/energy_storage/harness')

from drift_detector import DriftDetector, check_drift
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# 初始化漂移检测器
detector = DriftDetector(threshold=0.5)

print("=" * 60)
print("漂移检测集成测试")
print("=" * 60)

# 测试场景1: 日报生成任务 - 正常情况
print("\n[场景1] 日报生成 - 正常输出")
result = detector.check(
    task_description="生成储能行业日报",
    actual_result="""
# 储能行业日报 2026-03-29

## 市场动态
- 宁德时代发布新一代储能电池
- 某储能电站正式并网运营

## 技术进展
- 固态电池技术取得突破
- 液流电池成本下降15%

## 政策动态
- 国家发改委发布储能补贴政策
- 某省出台储能电站并网标准

## 行情数据
- 宁德时代股价: 185.50 (+2.3%)
- 储能板块指数: 1250.80 (+1.8%)
""",
    expected_keywords=["储能", "市场", "技术", "政策", "行情"]
)
print(f"✓ 漂移: {result.is_drift} | 置信度: {result.confidence:.2f}")
print(f"✓ 检测类型: {result.check_type}")
if result.is_drift:
    print(f"⚠ 原因: {result.reason}")
    print(f"⚠ 建议: {result.suggestion}")

# 测试场景2: 日报生成任务 - 漂移情况（内容不足）
print("\n[场景2] 日报生成 - 内容偏离")
result = detector.check(
    task_description="生成储能行业日报",
    actual_result="今天天气很好，适合出去散步。储能行业的新闻暂时没有收集到。",
    expected_keywords=["储能", "市场", "技术", "政策"]
)
print(f"✓ 漂移: {result.is_drift} | 置信度: {result.confidence:.2f}")
print(f"✓ 检测类型: {result.check_type}")
if result.is_drift:
    print(f"⚠ 原因: {result.reason}")
    print(f"⚠ 建议: {result.suggestion}")

# 测试场景3: 爬虫任务 - 正常情况
print("\n[场景3] 爬虫任务 - 正常输出")
result = detector.check(
    task_description="爬取储能行业新闻",
    actual_result="爬取完成！成功获取25条新闻，其中新增18条，更新7条。",
    expected_keywords=["爬取", "成功", "条"]
)
print(f"✓ 漂移: {result.is_drift} | 置信度: {result.confidence:.2f}")
print(f"✓ 检测类型: {result.check_type}")
if result.is_drift:
    print(f"⚠ 原因: {result.reason}")

# 测试场景4: 格式检测
print("\n[场景4] 格式检测 - Markdown格式")
result = detector.check(
    task_description="生成Markdown格式报告",
    actual_result="""
# 标题
## 子标题
正文内容
- 列表项1
- 列表项2
""",
    expected_format="markdown",
    check_types=["format"]
)
print(f"✓ 漂移: {result.is_drift} | 置信度: {result.confidence:.2f}")
print(f"✓ 检测类型: {result.check_type}")

# 测试场景5: 格式检测 - 格式错误
print("\n[场景5] 格式检测 - JSON格式要求但实际是普通文本")
result = detector.check(
    task_description="生成JSON格式数据",
    actual_result="这是普通文本内容，不是JSON格式",
    expected_format="json",
    check_types=["format"]
)
print(f"✓ 漂移: {result.is_drift} | 置信度: {result.confidence:.2f}")
print(f"✓ 检测类型: {result.check_type}")
if result.is_drift:
    print(f"⚠ 原因: {result.reason}")
    print(f"⚠ 建议: {result.suggestion}")

# 显示统计信息
print("\n" + "=" * 60)
print("漂移检测统计")
print("=" * 60)
stats = detector.get_stats()
print(f"总检测次数: {stats['total_checks']}")
print(f"漂移次数: {stats['drift_count']}")
print(f"漂移率: {stats['drift_rate']*100:.1f}%")

print("\n✅ 漂移检测模块测试完成")
print("\n使用说明:")
print("1. 在 agent_runner.py 中已集成漂移检测")
print("2. 在 harness_config.yaml 中可配置检测参数")
print("3. 支持关键词检测、语义偏离检测、格式检测")
print("4. 漂移检测触发后会自动记录并通知反馈循环")
