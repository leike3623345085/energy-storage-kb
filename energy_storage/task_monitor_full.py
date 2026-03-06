#!/usr/bin/env python3
"""
定时任务执行监控 - 完整版
监控所有重要任务的执行状态
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 监控配置
MONITOR_CONFIG = {
    "daily_report": {
        "name": "日报生成",
        "schedule": "18:00",
        "check_at": "18:30",
        "check_file": "data/reports/report_{date}.md",
        "check_hour": 18
    },
    "weekly_report": {
        "name": "周报生成",
        "schedule": "周一 09:00",
        "check_at": "周一 09:30",
        "check_file": "data/reports/weekly_{date}.md",
        "check_hour": 9,
        "check_weekday": 0  # 周一
    },
    "deep_analysis": {
        "name": "深度分析",
        "schedule": "18:00",
        "check_at": "18:30",
        "check_file": "data/reports/deep_analysis_{date}.md",
        "check_hour": 18
    },
    "crawler": {
        "name": "网站爬虫",
        "schedule": "每3小时",
        "check_file": "data/crawler/crawler_{date}*.json",
        "max_age_minutes": 180  # 3小时
    },
    "stock": {
        "name": "股票行情",
        "schedule": "交易日 9:00/15:00",
        "check_file": "data/finance/stocks_{date}.json",
        "max_age_minutes": 480  # 8小时
    }
}

def check_file_exists(pattern, date_str):
    """检查文件是否存在"""
    base_dir = Path(__file__).parent
    file_path = base_dir / pattern.format(date=date_str)
    
    # 支持通配符
    if '*' in str(file_path):
        files = list(file_path.parent.glob(file_path.name))
        return len(files) > 0, files
    
    return file_path.exists(), [file_path] if file_path.exists() else []

def check_file_freshness(files, max_age_minutes):
    """检查文件是否新鲜"""
    if not files:
        return False
    
    now = datetime.now()
    for f in files:
        mtime = datetime.fromtimestamp(f.stat().st_mtime)
        age_minutes = (now - mtime).total_seconds() / 60
        
        if age_minutes <= max_age_minutes:
            return True, mtime
    
    return False, None

def check_task(task_key, config):
    """检查单个任务"""
    print(f"\n📋 检查: {config['name']}")
    print(f"   计划执行: {config['schedule']}")
    
    today = datetime.now().strftime("%Y%m%d")
    
    # 检查文件
    exists, files = check_file_exists(config['check_file'], today)
    
    if not exists:
        print(f"   ❌ 未找到输出文件")
        return False, "文件未生成"
    
    # 检查时效性
    if 'max_age_minutes' in config:
        fresh, mtime = check_file_freshness(files, config['max_age_minutes'])
        if not fresh:
            print(f"   ⚠️ 文件存在但可能过期")
            return False, "文件过期"
    else:
        # 检查生成时间
        if files:
            mtime = datetime.fromtimestamp(files[0].stat().st_mtime)
            if config.get('check_hour') and mtime.hour < config['check_hour']:
                print(f"   ⚠️ 文件不是今天生成的（生成时间: {mtime.hour}:{mtime.minute:02d}）")
                return False, "文件时间不符"
    
    print(f"   ✅ 正常 (文件: {files[0].name})")
    return True, "正常"

def resend_task(task_key):
    """重新执行任务"""
    print(f"\n🔄 尝试补发: {MONITOR_CONFIG[task_key]['name']}")
    
    if task_key == "daily_report":
        # 重新发送日报
        os.system("cd /root/.openclaw/workspace/energy_storage && python3 send_email.py")
        from wechat_bot import send_markdown
        send_markdown("## 📊 日报补发\n\n原定时任务执行异常，现已补发。\n\n请查看邮件获取完整报告。")
        
    elif task_key == "weekly_report":
        # 重新发送周报
        os.system("cd /root/.openclaw/workspace/energy_storage && python3 send_email.py --weekly")
        
    elif task_key == "deep_analysis":
        # 触发深度分析
        print("   深度分析需要手动触发或等待下次执行")
        
    elif task_key == "crawler":
        # 重新运行爬虫
        os.system("cd /root/.openclaw/workspace/energy_storage && python3 crawler_multi.py")
        
    elif task_key == "stock":
        # 重新获取股票数据
        os.system("cd /root/.openclaw/workspace/energy_storage && python3 rss_monitor.py --stocks")

def send_alert(failed_tasks):
    """发送失败警报"""
    try:
        from wechat_bot import send_alert
        
        content = "🚨 定时任务执行异常\n\n"
        for task, reason in failed_tasks:
            content += f"• {MONITOR_CONFIG[task]['name']}: {reason}\n"
        
        content += f"\n时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        content += "已尝试自动补发，请检查系统。"
        
        send_alert(
            title="🚨 定时任务监控警报",
            content=content,
            priority="critical"
        )
        print("\n✅ 警报已发送")
    except Exception as e:
        print(f"\n❌ 发送警报失败: {e}")

def main():
    """主函数"""
    print("=" * 60)
    print("定时任务执行监控 - 完整检查")
    print(f"时间: {datetime.now()}")
    print("=" * 60)
    
    failed_tasks = []
    
    # 检查所有任务
    for task_key, config in MONITOR_CONFIG.items():
        success, reason = check_task(task_key, config)
        
        if not success:
            failed_tasks.append((task_key, reason))
            # 尝试补发
            resend_task(task_key)
    
    # 总结
    print("\n" + "=" * 60)
    print("检查总结")
    print("=" * 60)
    
    if failed_tasks:
        print(f"\n⚠️ 发现 {len(failed_tasks)} 个异常任务:")
        for task, reason in failed_tasks:
            print(f"   • {MONITOR_CONFIG[task]['name']}: {reason}")
        
        # 发送警报
        send_alert(failed_tasks)
        return 1
    else:
        print("\n✅ 所有任务执行正常")
        return 0

if __name__ == "__main__":
    sys.exit(main())
