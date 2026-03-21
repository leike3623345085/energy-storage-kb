#!/usr/bin/env python3
"""
自动增量备份脚本 - 储能系统数据备份到GitHub
每天检查变更，自动提交并推送
"""

import subprocess
import os
import sys
from datetime import datetime

WORKSPACE = "/root/.openclaw/workspace"
REPO_URL = "https://github.com/leike3623345085/energy-storage-kb.git"

def run_cmd(cmd, cwd=None):
    """执行命令并返回结果"""
    try:
        result = subprocess.run(
            cmd, shell=True, cwd=cwd or WORKSPACE,
            capture_output=True, text=True, timeout=60
        )
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def check_changes():
    """检查是否有未提交的变更"""
    success, stdout, stderr = run_cmd("git status --porcelain")
    if not success:
        print(f"❌ 检查变更失败: {stderr}")
        return False, []
    
    changes = [line for line in stdout.strip().split('\n') if line.strip()]
    return len(changes) > 0, changes

def configure_git():
    """配置Git用户信息（如未配置）"""
    run_cmd('git config user.email "backup@energy-storage.local"')
    run_cmd('git config user.name "Energy Storage Backup Bot"')

def add_and_commit():
    """添加所有变更并提交"""
    # 添加所有变更
    success, _, stderr = run_cmd("git add -A")
    if not success:
        print(f"❌ git add 失败: {stderr}")
        return False
    
    # 提交
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    commit_msg = f"auto: 每日增量备份 {timestamp}"
    success, _, stderr = run_cmd(f'git commit -m "{commit_msg}"')
    if not success:
        print(f"⚠️ 提交失败（可能没有变更）: {stderr}")
        return False
    
    print(f"✅ 已提交: {commit_msg}")
    return True

def push_to_github():
    """推送到GitHub"""
    # 检查是否有GITHUB_TOKEN环境变量
    token = os.environ.get("GITHUB_TOKEN", "")
    
    if token:
        # 使用Token推送
        auth_url = f"https://{token}@github.com/leike3623345085/energy-storage-kb.git"
        success, _, stderr = run_cmd(f"git push {auth_url} main")
        if success:
            print("✅ 已推送到GitHub (使用Token)")
            return True
        else:
            print(f"⚠️ Token推送失败: {stderr}")
    
    # 尝试普通推送（如果配置了SSH或其他认证）
    success, _, stderr = run_cmd("git push origin main")
    if success:
        print("✅ 已推送到GitHub")
        return True
    else:
        print(f"❌ 推送失败: {stderr}")
        return False

def main():
    print(f"🔄 自动备份检查 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 50)
    
    # 检查工作目录
    if not os.path.exists(f"{WORKSPACE}/.git"):
        print(f"❌ 不是Git仓库: {WORKSPACE}")
        sys.exit(1)
    
    # 配置Git
    configure_git()
    
    # 检查变更
    has_changes, changes = check_changes()
    
    if not has_changes:
        print("ℹ️ 没有变更需要备份")
        sys.exit(0)
    
    print(f"📦 检测到 {len(changes)} 个变更:")
    for change in changes[:10]:  # 只显示前10个
        print(f"   {change}")
    if len(changes) > 10:
        print(f"   ... 还有 {len(changes) - 10} 个变更")
    
    # 提交
    if not add_and_commit():
        print("❌ 提交失败，跳过推送")
        sys.exit(1)
    
    # 推送
    if push_to_github():
        print("✅ 增量备份完成")
    else:
        print("❌ 推送失败，但本地已提交")
        sys.exit(1)

if __name__ == "__main__":
    main()
