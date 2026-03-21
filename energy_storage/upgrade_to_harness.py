#!/usr/bin/env python3
"""
储能监控系统 - 定时任务升级脚本
自动将现有定时任务升级到 Harness Engineering 架构
"""

import json
import subprocess
from pathlib import Path
from datetime import datetime

WORKSPACE = Path("/root/.openclaw/workspace/energy_storage")
HARNESS_DIR = WORKSPACE / "harness"

# 新的定时任务配置
NEW_CRON_JOBS = [
    {
        "name": "储能日报生成 (Harness)",
        "schedule": {"kind": "cron", "expr": "5 18 * * *", "tz": "Asia/Shanghai"},
        "payload": {
            "kind": "agentTurn",
            "message": "【重要：必须使用 exec 工具实际执行命令】\n\n执行储能日报生成任务（Harness Engineering 架构）：\n\n```\ncd /root/.openclaw/workspace/energy_storage && python3 generate_report_harness.py\n```\n\n执行完成后，检查输出中的 Harness 步骤是否全部通过。"
        },
        "sessionTarget": "isolated",
        "enabled": True,
        "delivery": {"mode": "announce", "to": "main"}
    },
    {
        "name": "储能深度分析 (Harness)",
        "schedule": {"kind": "cron", "expr": "10 18 * * *", "tz": "Asia/Shanghai"},
        "payload": {
            "kind": "agentTurn",
            "message": "【重要：必须使用 exec 工具实际执行命令】\n\n执行储能深度分析任务（Harness Engineering 架构）：\n\n```\ncd /root/.openclaw/workspace/energy_storage && python3 generate_report_harness.py --date $(date +%Y-%m-%d)\n```\n\n生成深度分析报告。"
        },
        "sessionTarget": "isolated",
        "enabled": True,
        "delivery": {"mode": "announce", "to": "main"}
    },
    {
        "name": "储能系统巡检 (Harness)",
        "schedule": {"kind": "cron", "expr": "0 */6 * * *", "tz": "Asia/Shanghai"},
        "payload": {
            "kind": "agentTurn",
            "message": "【重要：必须使用 exec 工具实际执行命令】\n\n执行储能系统巡检（Harness Engineering 架构）：\n\n```\ncd /root/.openclaw/workspace/energy_storage && python3 self_healing_harness.py\n```\n\n使用 Harness 自愈系统检查日报、深度分析、数据状态。"
        },
        "sessionTarget": "isolated",
        "enabled": True,
        "delivery": {"mode": "none"}
    },
    {
        "name": "储能数据同步飞书",
        "schedule": {"kind": "cron", "expr": "*/5 * * * *", "tz": "Asia/Shanghai"},
        "payload": {
            "kind": "agentTurn",
            "message": "【重要：必须使用 exec 工具实际执行命令】\n\n执行飞书数据同步：\n\n```\ncd /root/.openclaw/workspace/energy_storage && timeout 120 python3 sync_batch.py\n```"
        },
        "sessionTarget": "isolated",
        "enabled": True,
        "delivery": {"mode": "none"}
    },
    {
        "name": "储能报告同步IMA",
        "schedule": {"kind": "cron", "expr": "*/2 * * * *", "tz": "Asia/Shanghai"},
        "payload": {
            "kind": "agentTurn",
            "message": "【重要：必须使用 exec 工具实际执行命令】\n\n执行 IMA 报告同步：\n\n```\ncd /root/.openclaw/workspace/energy_storage && timeout 60 python3 sync_ima.py\n```"
        },
        "sessionTarget": "isolated",
        "enabled": True,
        "delivery": {"mode": "none"}
    }
]


def test_harness_components():
    """测试 Harness 组件"""
    print("=" * 60)
    print("测试 Harness 组件")
    print("=" * 60)
    
    import sys
    sys.path.insert(0, str(HARNESS_DIR))
    
    try:
        from agent_runner import AgentRunner
        from guardrails import GuardrailsSystem
        from feedback_loop import FeedbackLoop
        from progressive_context import ProgressiveDisclosure
        
        # 测试 AgentRunner
        print("\n[1/4] 测试 AgentRunner...")
        runner = AgentRunner()
        health = runner.get_system_health()
        print(f"  ✓ AgentRunner 正常 (学习模式: {health['learned_patterns']} 个)")
        
        # 测试 Guardrails
        print("[2/4] 测试 Guardrails...")
        guardrails = GuardrailsSystem()
        print("  ✓ Guardrails 正常")
        
        # 测试 FeedbackLoop
        print("[3/4] 测试 FeedbackLoop...")
        feedback = FeedbackLoop()
        stats = feedback.get_error_stats()
        print(f"  ✓ FeedbackLoop 正常")
        
        # 测试 ProgressiveDisclosure
        print("[4/4] 测试 ProgressiveDisclosure...")
        pd = ProgressiveDisclosure()
        print("  ✓ ProgressiveDisclosure 正常")
        
        print("\n✅ 所有 Harness 组件测试通过")
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def update_cron_jobs():
    """更新定时任务"""
    print("\n" + "=" * 60)
    print("更新定时任务")
    print("=" * 60)
    
    try:
        # 获取现有任务
        result = subprocess.run(
            ["openclaw", "cron", "list"],
            capture_output=True,
            text=True,
            timeout=30
        )
        print("现有定时任务列表已获取")
        
        # 删除旧的储能相关任务
        print("\n删除旧的储能定时任务...")
        # 注意：这里只是示例，实际执行需要谨慎
        print("  (保留现有任务，添加新的 Harness 任务)")
        
        # 添加新的 Harness 任务
        print("\n添加新的 Harness 定时任务...")
        for i, job in enumerate(NEW_CRON_JOBS, 1):
            print(f"  [{i}/{len(NEW_CRON_JOBS)}] {job['name']}")
            
            # 创建任务
            result = subprocess.run(
                ["openclaw", "cron", "add"],
                input=json.dumps({"job": job}),
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                print(f"    ✓ 已创建")
            else:
                print(f"    ⚠️ 创建失败: {result.stderr}")
        
        print("\n✅ 定时任务更新完成")
        return True
        
    except Exception as e:
        print(f"\n❌ 更新失败: {e}")
        return False


def create_backup():
    """创建备份"""
    print("\n" + "=" * 60)
    print("创建备份")
    print("=" * 60)
    
    backup_dir = WORKSPACE / "backups" / datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    # 备份现有脚本
    files_to_backup = [
        "generate_report.py",
        "self_healing_fast.py",
        "send_email.py"
    ]
    
    for filename in files_to_backup:
        src = WORKSPACE / filename
        if src.exists():
            import shutil
            shutil.copy2(src, backup_dir / filename)
            print(f"  ✓ 已备份: {filename}")
    
    print(f"\n✅ 备份已保存到: {backup_dir}")
    return backup_dir


def main():
    """主函数"""
    print("=" * 60)
    print("储能监控系统 - Harness Engineering 升级")
    print("=" * 60)
    
    # 1. 测试 Harness 组件
    if not test_harness_components():
        print("\n❌ Harness 组件测试失败，升级中止")
        return 1
    
    # 2. 创建备份
    backup_dir = create_backup()
    
    # 3. 更新定时任务
    # update_cron_jobs()  # 暂不自动更新，避免影响现有任务
    
    print("\n" + "=" * 60)
    print("升级准备完成")
    print("=" * 60)
    print("\n下一步操作:")
    print("  1. 手动测试新脚本:")
    print("     python3 generate_report_harness.py")
    print("     python3 self_healing_harness.py")
    print("\n  2. 测试通过后，更新定时任务配置")
    print("\n  3. 如需回滚，备份在:")
    print(f"     {backup_dir}")
    
    return 0


if __name__ == "__main__":
    exit(main())
