#!/usr/bin/env python3
"""
变更检测与自动触发器
在关键操作前自动检查是否有未记录的变更
"""

import subprocess
import json
from datetime import datetime
from pathlib import Path

CHANGE_RECORDS_FILE = Path(__file__).parent / "data" / "change_records.jsonl"
WATCHED_FILES = [
    "generate_report_harness_v3.py",
    "crawler_multi.py", 
    "send_email.py",
    "wechat_bot.py",
    "config.py",
    "sources_config.py"
]

def get_git_status():
    """获取git状态"""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            cwd="/root/.openclaw/workspace"
        )
        return result.stdout.strip()
    except:
        return ""

def get_recent_commits(hours=24):
    """获取最近N小时的提交"""
    try:
        result = subprocess.run(
            ["git", "log", f"--since={hours}.hours", "--name-only", "--oneline"],
            capture_output=True,
            text=True,
            cwd="/root/.openclaw/workspace"
        )
        return result.stdout
    except:
        return ""

def check_watched_files_changed():
    """检查受监控文件是否有变更"""
    status = get_git_status()
    recent = get_recent_commits(24)
    
    changed_files = []
    for file in WATCHED_FILES:
        if file in status or file in recent:
            changed_files.append(file)
    
    return changed_files

def check_recent_changes(hours=24):
    """检查最近N小时内是否有已完成的变更记录覆盖当前文件变更"""
    if not CHANGE_RECORDS_FILE.exists():
        return None
    
    recent_records = []
    with open(CHANGE_RECORDS_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                record = json.loads(line.strip())
                # 检查是否24小时内（无论状态）
                change_time = datetime.fromisoformat(record["timestamp"])
                if (datetime.now() - change_time).total_seconds() < hours * 3600:
                    recent_records.append(record)
            except:
                continue
    
    return recent_records

def auto_check():
    """自动检查变更"""
    print("🔍 变更自动检查...")
    
    # 检查是否有文件变更
    changed_files = check_watched_files_changed()
    
    if not changed_files:
        print("  ✅ 无受监控文件变更")
        return True
    
    print(f"  ⚠️  检测到 {len(changed_files)} 个受监控文件有变更:")
    for f in changed_files:
        print(f"     - {f}")
    
    # 检查是否有对应的变更记录
    recent = check_recent_changes()
    
    if recent:
        print(f"  ✅ 找到 {len(recent)} 个最近24小时内的变更记录:")
        for r in recent:
            status_emoji = "🔄" if r.get("status") in ["planned", "in_progress"] else "✅"
            print(f"     {status_emoji} {r['id']}: {r['title']} [{r.get('status', 'unknown')}]")
        return True
    else:
        print("  ❌ 未找到对应的变更记录！")
        print("\n  ⚠️  根据变更管理原则，请先创建变更记录:")
        print(f"     python3 change_manager.py --create --title \"XXX升级\"")
        print("\n  或在变更记录中标记相关文件:")
        print(f"     受影响文件: {', '.join(changed_files)}")
        return False

def pre_exec_check():
    """
    关键脚本执行前的检查
    如果检测到未记录的变更，询问是否继续
    """
    changed_files = check_watched_files_changed()
    
    if not changed_files:
        return True  # 无变更，直接继续
    
    pending = check_pending_changes()
    
    if pending:
        # 有变更记录，检查是否已完成
        for p in pending:
            if p.get("status") == "in_progress":
                print(f"⚠️  变更 {p['id']} 仍在进行中，确认已完成所有检查？")
                return True  # 允许继续，但已提醒
        return True
    else:
        print("=" * 70)
        print("🛑 变更管理警告")
        print("=" * 70)
        print(f"\n检测到以下关键文件有变更但未记录:")
        for f in changed_files:
            print(f"  - {f}")
        print(f"\n根据变更管理四项原则，请先创建变更记录:")
        print(f"  python3 change_manager.py --create --title \"描述变更内容\"")
        print(f"\n或添加 --force 参数跳过检查（不推荐）")
        print("=" * 70)
        return False


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--check":
        # 纯检查模式，用于定时任务
        if auto_check():
            sys.exit(0)
        else:
            sys.exit(1)
    else:
        # 执行前检查模式
        if not pre_exec_check():
            sys.exit(1)
        sys.exit(0)
