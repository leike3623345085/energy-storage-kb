#!/usr/bin/env python3
"""
储能爬虫自动回滚系统
全自动闭环 - 回退环节
"""
import json
import shutil
from datetime import datetime
from pathlib import Path

WORKSPACE = Path("/root/.openclaw/workspace/energy_storage")
BACKUP_DIR = WORKSPACE / "backups"
LOG_FILE = WORKSPACE / "logs/rollback.log"

# 关键文件列表
CRITICAL_FILES = [
    "crawler_multi_v2.py",
    "run_crawler_safe.py",
    "validation_suite.py"
]

def ensure_dirs():
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    (WORKSPACE / "logs").mkdir(parents=True, exist_ok=True)

def create_backup(version_tag=None):
    """创建备份"""
    ensure_dirs()
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    version_tag = version_tag or f"auto_{timestamp}"
    backup_path = BACKUP_DIR / version_tag
    backup_path.mkdir(exist_ok=True)
    
    # 备份关键文件
    backed_files = []
    for filename in CRITICAL_FILES:
        src = WORKSPACE / filename
        if src.exists():
            dst = backup_path / filename
            shutil.copy2(src, dst)
            backed_files.append(filename)
    
    # 保存元数据
    metadata = {
        "version_tag": version_tag,
        "timestamp": timestamp,
        "files": backed_files,
        "reason": "auto_backup_before_deploy"
    }
    
    with open(backup_path / "metadata.json", 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    
    # 清理旧备份（保留最近10个）
    clean_old_backups(keep=10)
    
    print(f"✅ 备份创建: {version_tag}")
    return version_tag

def clean_old_backups(keep=10):
    """清理旧备份"""
    backups = sorted(BACKUP_DIR.glob("auto_*"), key=lambda x: x.stat().st_mtime, reverse=True)
    for old_backup in backups[keep:]:
        shutil.rmtree(old_backup)
        print(f"🗑️ 清理旧备份: {old_backup.name}")

def rollback(version_tag=None):
    """
    回滚到指定版本
    如果不指定，回滚到最新稳定版本
    """
    ensure_dirs()
    
    if version_tag is None:
        # 找到最新备份
        backups = sorted(BACKUP_DIR.glob("auto_*"), key=lambda x: x.stat().st_mtime, reverse=True)
        if not backups:
            return {"success": False, "error": "没有可用备份"}
        backup_path = backups[0]
        version_tag = backup_path.name
    else:
        backup_path = BACKUP_DIR / version_tag
        if not backup_path.exists():
            return {"success": False, "error": f"备份不存在: {version_tag}"}
    
    # 先创建当前状态的备份（方便后悔）
    current_backup = create_backup(f"pre_rollback_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    
    # 执行回滚
    restored_files = []
    for filename in CRITICAL_FILES:
        src = backup_path / filename
        if src.exists():
            dst = WORKSPACE / filename
            shutil.copy2(src, dst)
            restored_files.append(filename)
    
    # 记录回滚日志
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "action": "rollback",
        "from_backup": version_tag,
        "current_backed_up": current_backup,
        "restored_files": restored_files
    }
    
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    
    print(f"✅ 回滚完成: {version_tag}")
    print(f"   已恢复: {', '.join(restored_files)}")
    print(f"   当前状态已备份: {current_backup}")
    
    return {
        "success": True,
        "version": version_tag,
        "restored_files": restored_files,
        "current_backed_up": current_backup
    }

def get_backup_list():
    """获取备份列表"""
    ensure_dirs()
    backups = []
    
    for backup_dir in sorted(BACKUP_DIR.glob("*"), key=lambda x: x.stat().st_mtime, reverse=True):
        metadata_file = backup_dir / "metadata.json"
        if metadata_file.exists():
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            backups.append(metadata)
    
    return backups

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "backup":
            create_backup()
        elif sys.argv[1] == "rollback":
            version = sys.argv[2] if len(sys.argv) > 2 else None
            result = rollback(version)
            print(json.dumps(result, ensure_ascii=False, indent=2))
        elif sys.argv[1] == "list":
            backups = get_backup_list()
            for b in backups[:5]:
                print(f"{b['version_tag']} ({b['timestamp']})")
    else:
        print("Usage: python3 rollback_system.py [backup|rollback|list]")
