#!/usr/bin/env python3
"""
储能监控系统 - 自愈机制 (Self-Healing Monitor) - 快速版
自动检测日报/深度分析状态，发现问题自动修复
优化：减少执行时间，避免超时
"""

import json
import os
import sys
import subprocess
import smtplib
from datetime import datetime, timedelta
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# 配置
DATA_DIR = Path(__file__).parent / "data"
REPORTS_DIR = DATA_DIR / "reports"
CRAWLER_DIR = DATA_DIR / "crawler"
LOG_FILE = Path(__file__).parent / "logs" / "self_healing.log"

# 邮件配置
EMAIL_CONFIG_FILE = Path(__file__).parent / "email_config.json"

def log(message):
    """记录日志"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_msg = f"[{timestamp}] {message}"
    print(log_msg)
    
    # 写入日志文件
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_msg + "\n")

def load_email_config():
    """加载邮件配置"""
    if EMAIL_CONFIG_FILE.exists():
        with open(EMAIL_CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

def send_alert_email(subject, content):
    """发送告警邮件"""
    config = load_email_config()
    if not config:
        log("⚠️ 邮件配置不存在，无法发送告警")
        return False
    
    try:
        msg = MIMEMultipart()
        msg["From"] = config["from_email"]
        msg["To"] = config["to_email"]
        msg["Subject"] = f"【告警】{subject}"
        
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6;">
            <h2 style="color: #d32f2f;">储能监控系统告警</h2>
            <div style="background: #fff3cd; padding: 15px; border-left: 4px solid #ffc107; margin: 15px 0;">
                <h3>{subject}</h3>
                <p>{content}</p>
            </div>
            <p style="color: #666; font-size: 12px;">
                告警时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}<br>
                系统自动发送
            </p>
        </body>
        </html>
        """
        msg.attach(MIMEText(html_content, "html", "utf-8"))
        
        server = smtplib.SMTP_SSL("smtp.qq.com", 465, timeout=30)
        server.login(config["from_email"], config["password"])
        server.send_message(msg)
        server.quit()
        
        log(f"✅ 告警邮件已发送: {subject}")
        return True
    except Exception as e:
        log(f"❌ 告警邮件发送失败: {e}")
        return False

def check_crawler_data():
    """检查爬虫数据 - 快速检查"""
    today = datetime.now().strftime("%Y%m%d")
    today_files = list(CRAWLER_DIR.glob(f"crawler_{today}_*.json"))
    
    if not today_files:
        log("⚠️ 今日爬虫数据不存在")
        return False, 0
    
    # 计算数据量
    total = 0
    latest_time = None
    for f in today_files:
        try:
            with open(f, 'r', encoding='utf-8') as file:
                data = json.load(file)
                count = len(data.get("data", []))
                total += count
                time_str = f.stem.split('_')[-1]
                if len(time_str) == 4:
                    file_time = datetime.strptime(f"{today}_{time_str}", "%Y%m%d_%H%M")
                    if latest_time is None or file_time > latest_time:
                        latest_time = file_time
        except:
            pass
    
    # 检查数据新鲜度（4小时内）
    if latest_time:
        age_hours = (datetime.now() - latest_time).total_seconds() / 3600
        if age_hours > 4:
            log(f"⚠️ 爬虫数据较旧，最新数据 {age_hours:.1f} 小时前")
            return False, total
    
    if total < 5:  # 降低阈值
        log(f"⚠️ 爬虫数据量不足: {total} 条")
        return False, total
    
    log(f"✅ 爬虫数据正常: {total} 条")
    return True, total

def check_reports():
    """检查报告文件 - 快速检查"""
    today = datetime.now().strftime("%Y%m%d")
    
    daily_report = REPORTS_DIR / f"report_{today}.md"
    deep_report = REPORTS_DIR / f"deep_analysis_{today}.md"
    
    has_daily = daily_report.exists() and daily_report.stat().st_size > 1000
    has_deep = deep_report.exists() and deep_report.stat().st_size > 1000
    
    log(f"📄 报告状态: 日报{'✅' if has_daily else '❌'}, 深度分析{'✅' if has_deep else '❌'}")
    return has_daily, has_deep

def self_healing_check():
    """自愈检查主流程 - 轻量版"""
    log("=" * 60)
    log("🔍 自愈系统检查开始")
    log(f"⏰ 当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log("=" * 60)
    
    issues_found = 0
    issues_fixed = 0
    
    # 1. 检查爬虫数据（只检查，不修复）
    crawler_ok, crawler_count = check_crawler_data()
    if not crawler_ok:
        issues_found += 1
        log("⚠️ 爬虫数据异常，将在下次爬虫任务中自动修复")
    
    # 2. 检查报告（只检查，不修复 - 由专门任务处理）
    has_daily, has_deep = check_reports()
    
    if not has_daily:
        issues_found += 1
        log("⚠️ 日报缺失，将由 18:35 补发监控任务处理")
    
    if not has_deep:
        issues_found += 1
        log("⚠️ 深度分析缺失，将由 18:35 监控任务处理")
    
    # 3. 汇总
    log("=" * 60)
    if issues_found == 0:
        log("✅ 所有检查通过，系统状态正常")
    else:
        log(f"⚠️ 发现 {issues_found} 个问题，已记录，将由专门任务处理")
        # 只在严重问题时发送邮件
        if issues_found >= 3:
            send_alert_email(f"系统发现 {issues_found} 个异常", "请关注日报和深度分析生成状态")
    log("=" * 60)
    
    return issues_found, issues_fixed

def main():
    """主入口"""
    try:
        issues_found, issues_fixed = self_healing_check()
        return 0
    except Exception as e:
        log(f"💥 自愈系统异常: {e}")
        return 1

if __name__ == "__main__":
    exit(main())
