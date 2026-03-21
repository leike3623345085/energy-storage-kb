#!/usr/bin/env python3
"""
Harness Quick Start - 快速集成示例
展示如何使用 Harness Engineering 架构优化现有工作流
"""

import sys
from pathlib import Path

# 添加 harness 到路径
sys.path.insert(0, str(Path(__file__).parent / 'harness'))

from agent_runner import AgentRunner
from guardrails import GuardrailsSystem
from feedback_loop import FeedbackLoop


def example_1_basic_guardrails():
    """示例1：基础护栏检查"""
    print("=" * 60)
    print("示例1: 基础护栏检查 (Guardrails)")
    print("=" * 60)
    
    guardrails = GuardrailsSystem()
    data_dir = Path('/root/.openclaw/workspace/energy_storage/data')
    
    # 执行飞行前检查
    passed, results = guardrails.pre_flight_check(data_dir)
    
    print(f"\n检查结果: {'通过 ✓' if passed else '未通过 ✗'}")
    for r in results:
        status = "✓" if r.passed else "✗"
        print(f"  [{status}] {r.code}: {r.message}")
    
    return passed


def example_2_feedback_loop():
    """示例2：反馈循环"""
    print("\n" + "=" * 60)
    print("示例2: 反馈循环 (Feedback Loop)")
    print("=" * 60)
    
    feedback = FeedbackLoop()
    
    # 模拟一个错误
    result = feedback.process_error(
        code="E001",
        message="爬虫数据不足: 5 < 20",
        context={'date': '2026-03-21', 'attempt': 1}
    )
    
    print(f"\n错误处理结果:")
    print(f"  错误类型: {result['error_type']}")
    print(f"  自动修复: {'是 ✓' if result['auto_fixed'] else '否 ✗'}")
    print(f"  修复动作: {result.get('fix_action', 'N/A')}")
    print(f"  修复结果: {result.get('fix_result', 'N/A')}")
    
    # 显示错误统计
    stats = feedback.get_error_stats()
    print(f"\n错误统计:")
    for error_type, count in stats.items():
        print(f"  {error_type}: {count} 次")


def example_3_full_workflow():
    """示例3：完整工作流"""
    print("\n" + "=" * 60)
    print("示例3: 完整工作流 (Agent Runner)")
    print("=" * 60)
    
    runner = AgentRunner()
    
    # 显示系统健康
    health = runner.get_system_health()
    print(f"\n系统健康状态:")
    print(f"  护栏系统: {health['guardrails']}")
    print(f"  反馈循环: {health['feedback_loop']}")
    print(f"  渐进式披露: {health['progressive_disclosure']}")
    print(f"  学习到的模式: {health['learned_patterns']} 个")
    
    # 运行日报工作流
    print(f"\n执行日报工作流...")
    result = runner.run_daily_report()
    
    print(f"\n执行结果:")
    print(f"  成功: {'是 ✓' if result.success else '否 ✗'}")
    print(f"  耗时: {result.duration_seconds:.2f} 秒")
    print(f"  完成步骤: {' -> '.join(result.steps_completed)}")
    
    if result.errors:
        print(f"  错误: {len(result.errors)} 个")
        for e in result.errors:
            print(f"    - [{e.get('code')}] {e.get('error')}")


def example_4_integrate_existing():
    """示例4：集成到现有系统"""
    print("\n" + "=" * 60)
    print("示例4: 集成到现有系统")
    print("=" * 60)
    
    code = '''
# 在现有的日报生成脚本中使用 Harness

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'harness'))

from agent_runner import AgentRunner

def generate_daily_report_with_harness():
    runner = AgentRunner()
    
    # 运行完整工作流
    result = runner.run_daily_report()
    
    if result.success:
        print(f"日报生成成功，耗时: {result.duration_seconds}s")
        return True
    else:
        print(f"日报生成失败: {result.errors}")
        return False

# 替换原有的直接调用
# 原有: generate_report()
# 新: generate_daily_report_with_harness()
'''
    print(code)


def main():
    """运行所有示例"""
    print("\n" + "=" * 60)
    print("Harness Engineering 快速入门")
    print("储能监控系统 AI 工作流优化")
    print("=" * 60)
    
    try:
        example_1_basic_guardrails()
    except Exception as e:
        print(f"示例1出错: {e}")
    
    try:
        example_2_feedback_loop()
    except Exception as e:
        print(f"示例2出错: {e}")
    
    try:
        example_3_full_workflow()
    except Exception as e:
        print(f"示例3出错: {e}")
    
    example_4_integrate_existing()
    
    print("\n" + "=" * 60)
    print("快速入门完成！")
    print("=" * 60)
    print("\n下一步:")
    print("  1. 查看完整文档: harness/README.md")
    print("  2. 修改配置: harness/harness_config.yaml")
    print("  3. 集成到现有脚本: 参考示例4")
    print("  4. 运行测试: python3 harness_quick_start.py")


if __name__ == '__main__':
    main()
