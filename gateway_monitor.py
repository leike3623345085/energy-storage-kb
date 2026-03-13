#!/usr/bin/env python3
"""
Gateway 健康监控脚本
检测 Gateway 是否响应，如果异常自动重启
"""

import subprocess
import sys
import time
from pathlib import Path

def check_gateway():
    """检查 Gateway 是否正常运行"""
    try:
        result = subprocess.run(
            ["pgrep", "-f", "openclaw-gateway"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            pid = result.stdout.strip().split('\n')[0]
            return True, pid
        return False, None
    except:
        return False, None

def restart_gateway():
    """重启 Gateway"""
    try:
        # 杀掉旧进程
        subprocess.run(["pkill", "-f", "openclaw-gateway"], timeout=5)
        time.sleep(2)
        
        # 启动新进程（后台运行）
        subprocess.Popen(
            ["openclaw", "gateway", "start"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        return True
    except Exception as e:
        print(f"重启失败: {e}")
        return False

def main():
    ok, pid = check_gateway()
    if not ok:
        print("⚠️ Gateway 未运行，尝试重启...")
        if restart_gateway():
            print("✅ Gateway 已重启")
            return 0
        else:
            print("❌ Gateway 重启失败")
            return 1
    else:
        print(f"✅ Gateway 运行中 (PID: {pid})")
        return 0

if __name__ == "__main__":
    sys.exit(main())
