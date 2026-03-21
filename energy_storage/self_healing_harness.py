#!/usr/bin/env python3
"""
储能监控系统 - 自愈机制 (Harness Engineering 版)
基于 Harness Engineering 架构的自愈系统
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

# 添加 harness 到路径
sys.path.insert(0, str(Path(__file__).parent / 'harness'))

from agent_runner import AgentRunner
from feedback_loop import FeedbackLoop

# 配置
DATA_DIR = Path(__file__).parent / "data"
REPORTS_DIR = DATA_DIR / "reports"
CRAWLER_DIR = DATA_DIR / "crawler"
LOG_FILE = Path(__file__).parent / "logs" / "self_healing_harness.log"

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
        msg["Subject"] = f"【Harness自愈系统】{subject}"
        
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6;">
            <h2 style="color: #1976d2;">储能监控系统 - Harness 自愈告警</h2>
            <div style="background: #e3f2fd; padding: 15px; border-left: 4px solid #1976d2; margin: 15px 0;">
                <h3>{subject}</h3>
                <p>{content}</p>
            </div>
            <p style="color: #666; font-size: 12px;">
                告警时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}<br>
                系统: Harness Engineering 架构<br>
                自动发送
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


def check_and_heal_crawler():
    """检查并修复爬虫 - Harness 方式"""
    log("\n[检查] 爬虫数据状态...")
    
    today = datetime.now().strftime("%Y%m%d")
    today_files = list(CRAWLER_DIR.glob(f"crawler_{today}_*.json"))
    
    if not today_files:
        log("⚠️ 今日爬虫数据不存在，触发反馈循环...")
        
        # 使用 Feedback Loop
        feedback = FeedbackLoop()
        result = feedback.process_error(
            code="E001",
            message="爬虫数据缺失",
            context={'date': today, 'component': 'crawler'}
        )
        
        if result['auto_fixed']:
            log(f"✅ 自动修复已执行: {result['fix_action']}")
            return True
        else:
            log("⚠️ 需要人工干预")
            return False
    
    # 计算数据量
    total = 0
    for f in today_files:
        try:
            with open(f, 'r', encoding='utf-8') as file:
                data = json.load(file)
                total += len(data.get("data", []))
        except:
            pass
    
    log(f"✅ 爬虫数据正常: {total} 条")
    return True


def check_and_heal_reports():
    """检查并修复报告 - Harness 方式"""
    log("\n[检查] 报告状态...")
    
    today = datetime.now().strftime("%Y%m%d")
    
    daily_report = REPORTS_DIR / f"report_{today}.md"
    deep_report = REPORTS_DIR / f"deep_analysis_{today}.md"
    
    issues = []
    
    if not daily_report.exists() or daily_report.stat().st_size < 1000:
        issues.append("日报缺失")
    
    if not deep_report.exists() or deep_report.stat().st_size < 1000:
        issues.append("深度分析缺失")
    
    if issues:
        log(f"⚠️ 发现 {len(issues)} 个问题: {', '.join(issues)}")
        
        # 使用 Feedback Loop
        feedback = FeedbackLoop()
        for issue in issues:
            result = feedback.process_error(
                code="E002",
                message=issue,
                context={'date': today, 'component': 'report'}
            )
            log(f"  - {issue}: {'自动修复' if result['auto_fixed'] else '需人工处理'}")
        
        return False
    
    log("✅ 报告状态正常")
    return True


def harness_self_healing_workflow():
    """
    Harness 自愈工作流
    基于 harness_config.yaml 中定义的 self_healing 工作流
    """
    log("=" * 60)
    log("🔍 Harness 自愈系统启动")
    log(f"⏰ 当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log("=" * 60)
    
    # 使用 AgentRunner 执行完整工作流
    runner = AgentRunner()
    
    # 步骤1: 扫描系统状态
    log("\n[步骤1/5] 扫描系统状态...")
    health = runner.get_system_health()
    log(f"  ✓ 系统组件: {health['guardrails']}")
    log(f"  ✓ 学习模式: {health['learned_patterns']} 个")
    
    # 步骤2: 检查爬虫
    log("\n[步骤2/5] 检查爬虫状态...")
    crawler_ok = check_and_heal_crawler()
    
    # 步骤3: 检查报告
    log("\n[步骤3/5] 检查报告状态...")
    reports_ok = check_and_heal_reports()
    
    # 步骤4: 获取错误统计
    log("\n[步骤4/5] 错误统计...")
    stats = runner.feedback.get_error_stats()
    if stats:
        for error_type, count in stats.items():
            log(f"  - {error_type}: {count} 次")
    else:
        log("  ✓ 无错误记录")
    
    # 步骤5: 生成报告
    log("\n[步骤5/5] 生成自愈报告...")
    issues_count = (0 if crawler_ok else 1) + (0 if reports_ok else 1)
    
    if issues_count == 0:
        log("✅ 所有检查通过，系统状态正常")
    else:
        log(f"⚠️ 发现 {issues_count} 个问题，已记录到反馈循环")
    
    log("=" * 60)
    log("Harness 自愈系统检查完成")
    log("=" * 60)
    
    return issues_count == 0


def main():
    """主入口"""
    try:
        success = harness_self_healing_workflow()
        return 0 if success else 1
    except Exception as e:
        log(f"💥 Harness 自愈系统异常: {e}")
        import traceback
        log(traceback.format_exc())
        return 1


if __name__ == "__main__":
    exit(main())
