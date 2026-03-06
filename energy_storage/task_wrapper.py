#!/usr/bin/env python3
"""
定时任务执行包装器
支持失败重试和错误通知
"""

import subprocess
import time
import sys
from datetime import datetime

# 重试配置
MAX_RETRIES = 5      # 最大重试次数
RETRY_DELAY = 60     # 重试间隔（秒）

def run_with_retry(command, task_name="任务"):
    """
    执行命令，失败时自动重试
    
    参数:
        command: 要执行的命令（字符串或列表）
        task_name: 任务名称（用于日志）
    """
    print(f"[{datetime.now()}] 开始执行: {task_name}")
    print(f"命令: {command}")
    print("-" * 60)
    
    for attempt in range(MAX_RETRIES + 1):
        try:
            # 执行命令
            if isinstance(command, str):
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=300  # 5分钟超时
                )
            else:
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=300
                )
            
            # 检查执行结果
            if result.returncode == 0:
                print(f"✅ {task_name} 执行成功")
                if result.stdout:
                    print("输出:", result.stdout[:500])
                return True
            else:
                raise Exception(f"返回码: {result.returncode}, 错误: {result.stderr}")
                
        except Exception as e:
            print(f"❌ {task_name} 第 {attempt + 1}/{MAX_RETRIES + 1} 次执行失败: {e}")
            
            # 如果不是最后一次，则等待后重试
            if attempt < MAX_RETRIES:
                print(f"⏳ {RETRY_DELAY}秒后重试...")
                time.sleep(RETRY_DELAY)
            else:
                # 所有重试都失败，发送通知
                print(f"🚨 {task_name} 连续{MAX_RETRIES + 1}次执行失败")
                send_error_notification(task_name, str(e))
                return False
    
    return False

def send_error_notification(task_name, error_msg):
    """发送错误通知"""
    try:
        from wechat_bot import send_alert
        
        send_alert(
            title=f"🚨 定时任务执行失败",
            content=f"任务: {task_name}\n错误: {error_msg}\n时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n已重试{MAX_RETRIES}次仍失败，请检查系统。",
            priority="critical"
        )
        print("✅ 错误通知已发送")
    except Exception as e:
        print(f"❌ 发送通知失败: {e}")

def main():
    """主函数"""
    if len(sys.argv) < 3:
        print("用法: python3 task_wrapper.py <任务名称> <命令>")
        print('示例: python3 task_wrapper.py "早班搜索" "python3 crawler.py"')
        return 1
    
    task_name = sys.argv[1]
    command = " ".join(sys.argv[2:])
    
    success = run_with_retry(command, task_name)
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
