#!/usr/bin/env python3
"""
OpenClaw 独立守护进程
功能：代替系统心跳，定期执行巡检任务，不干扰主会话

使用方法：
    python3 daemon_guardian.py start   # 启动守护进程
    python3 daemon_guardian.py stop    # 停止守护进程
    python3 daemon_guardian.py status  # 查看状态
"""

import os
import sys
import time
import json
import signal
import subprocess
from datetime import datetime
from pathlib import Path

# 配置
PID_FILE = Path("/tmp/openclaw_guardian.pid")
LOG_FILE = Path(__file__).parent / "logs" / "guardian.log"
CHECK_INTERVAL = 300  # 5分钟检查一次

# 巡检任务列表
CHECK_TASKS = [
    {
        "name": "爬虫数据检查",
        "script": "cd /root/.openclaw/workspace/energy_storage && python3 -c \"from pathlib import Path; files=list(Path('data/crawler').glob('crawler_*_*.json')); print(f'爬虫文件: {len(files)}个')\"",
        "interval": 300,  # 5分钟
    },
    {
        "name": "定时任务状态检查",
        "script": "cd /root/.openclaw/workspace/energy_storage && python3 -c \"import subprocess; r=subprocess.run(['openclaw','cron','list'], capture_output=True, text=True); print('Cron任务正常') if r.returncode==0 else print('Cron异常')\"",
        "interval": 600,  # 10分钟
    },
    {
        "name": "磁盘空间检查",
        "script": "df -h / | tail -1 | awk '{print $5}' | sed 's/%//' | xargs -I {} bash -c 'if [ {} -gt 90 ]; then echo \"警告：磁盘使用率{}%\"; else echo \"磁盘正常：{}%\"; fi'",
        "interval": 3600,  # 1小时
    },
]

def log(message):
    """记录日志"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_msg = f"[{timestamp}] {message}"
    
    # 确保日志目录存在
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    # 写入文件
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_msg + "\n")
    
    # 同时输出到控制台（如果是前台运行）
    print(log_msg)

def run_check(task):
    """执行单个检查任务"""
    try:
        result = subprocess.run(
            task["script"],
            shell=True,
            capture_output=True,
            text=True,
            timeout=60
        )
        output = result.stdout.strip() if result.stdout else "无输出"
        if result.returncode == 0:
            log(f"✅ {task['name']}: {output}")
        else:
            log(f"⚠️ {task['name']}: 执行异常 - {output}")
    except Exception as e:
        log(f"❌ {task['name']}: 错误 - {e}")

def daemon_main():
    """守护进程主循环"""
    log("=" * 60)
    log("🚀 OpenClaw Guardian 守护进程启动")
    log(f"⏰ 检查间隔: {CHECK_INTERVAL}秒")
    log(f"📝 日志文件: {LOG_FILE}")
    log("=" * 60)
    
    # 记录任务最后执行时间
    last_run = {task["name"]: 0 for task in CHECK_TASKS}
    
    while True:
        try:
            current_time = time.time()
            
            # 检查每个任务是否需要执行
            for task in CHECK_TASKS:
                if current_time - last_run[task["name"]] >= task["interval"]:
                    run_check(task)
                    last_run[task["name"]] = current_time
            
            # 主循环睡眠
            time.sleep(CHECK_INTERVAL)
            
        except KeyboardInterrupt:
            log("🛑 收到中断信号，守护进程退出")
            break
        except Exception as e:
            log(f"💥 主循环异常: {e}")
            time.sleep(60)  # 出错后等待1分钟再试

def start_daemon():
    """启动守护进程"""
    # 检查是否已在运行
    if PID_FILE.exists():
        with open(PID_FILE, "r") as f:
            old_pid = f.read().strip()
        if old_pid and os.path.exists(f"/proc/{old_pid}"):
            print(f"⚠️ 守护进程已在运行 (PID: {old_pid})")
            return 1
        else:
            # PID文件过期，删除
            PID_FILE.unlink()
    
    # 创建守护进程
    try:
        pid = os.fork()
        if pid > 0:
            # 父进程退出
            print(f"✅ 守护进程已启动 (PID: {pid})")
            return 0
    except OSError as e:
        print(f"❌ Fork失败: {e}")
        return 1
    
    # 子进程继续
    os.chdir("/")
    os.setsid()
    os.umask(0)
    
    # 第二次fork
    try:
        pid = os.fork()
        if pid > 0:
            # 写入PID文件
            with open(PID_FILE, "w") as f:
                f.write(str(pid))
            os._exit(0)
    except OSError as e:
        print(f"❌ 第二次Fork失败: {e}")
        return 1
    
    # 孙子进程（真正的守护进程）
    # 重定向标准输入输出
    sys.stdout.flush()
    sys.stderr.flush()
    
    with open("/dev/null", "r") as f:
        os.dup2(f.fileno(), sys.stdin.fileno())
    with open(LOG_FILE, "a+") as f:
        os.dup2(f.fileno(), sys.stdout.fileno())
        os.dup2(f.fileno(), sys.stderr.fileno())
    
    # 启动主循环
    daemon_main()
    return 0

def stop_daemon():
    """停止守护进程"""
    if not PID_FILE.exists():
        print("⚠️ 守护进程未运行")
        return 1
    
    with open(PID_FILE, "r") as f:
        pid = f.read().strip()
    
    if not pid:
        print("❌ PID文件为空")
        return 1
    
    try:
        os.kill(int(pid), signal.SIGTERM)
        PID_FILE.unlink()
        print(f"✅ 守护进程已停止 (PID: {pid})")
        return 0
    except ProcessLookupError:
        print(f"⚠️ 进程已不存在，清理PID文件")
        PID_FILE.unlink()
        return 0
    except Exception as e:
        print(f"❌ 停止失败: {e}")
        return 1

def status_daemon():
    """查看守护进程状态"""
    if not PID_FILE.exists():
        print("⚠️ 守护进程未运行")
        return 1
    
    with open(PID_FILE, "r") as f:
        pid = f.read().strip()
    
    if os.path.exists(f"/proc/{pid}"):
        print(f"✅ 守护进程运行中 (PID: {pid})")
        # 显示最近日志
        if LOG_FILE.exists():
            print(f"\n📋 最近日志 ({LOG_FILE}):")
            result = subprocess.run(
                f"tail -20 {LOG_FILE}",
                shell=True,
                capture_output=True,
                text=True
            )
            print(result.stdout)
        return 0
    else:
        print(f"⚠️ PID文件存在但进程已死亡 (PID: {pid})")
        PID_FILE.unlink()
        return 1

def main():
    """主入口"""
    if len(sys.argv) < 2:
        print(__doc__)
        print(f"\n使用方法: python3 {sys.argv[0]} [start|stop|status]")
        return 1
    
    command = sys.argv[1].lower()
    
    if command == "start":
        return start_daemon()
    elif command == "stop":
        return stop_daemon()
    elif command == "status":
        return status_daemon()
    elif command == "run":
        # 前台运行模式（调试用）
        daemon_main()
        return 0
    else:
        print(f"❌ 未知命令: {command}")
        print(f"使用方法: python3 {sys.argv[0]} [start|stop|status|run]")
        return 1

if __name__ == "__main__":
    sys.exit(main())
