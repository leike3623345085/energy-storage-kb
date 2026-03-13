#!/usr/bin/env python3
"""
储能监控系统 - 自愈机制 (Self-Healing Monitor)
自动检测日报/深度分析状态，发现问题自动修复
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

# 添加lesson_logger导入
sys.path.insert(0, str(Path(__file__).parent.parent))
try:
    from lesson_logger import log_lesson
    LESSON_LOGGER_AVAILABLE = True
except ImportError:
    LESSON_LOGGER_AVAILABLE = False
    print("⚠️ lesson_logger不可用，经验将不会自动保存")

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
        
        server = smtplib.SMTP_SSL("smtp.qq.com", 465)
        server.login(config["from_email"], config["password"])
        server.send_message(msg)
        server.quit()
        
        log(f"✅ 告警邮件已发送: {subject}")
        return True
    except Exception as e:
        log(f"❌ 告警邮件发送失败: {e}")
        return False

def run_command(cmd, timeout=120, description=""):
    """执行命令并返回结果"""
    if description:
        log(f"▶️ {description}: {cmd}")
    
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd="/root/.openclaw/workspace/energy_storage"
        )
        
        if result.returncode == 0:
            log(f"✅ 成功: {description or cmd}")
            return True, result.stdout
        else:
            log(f"❌ 失败: {description or cmd}")
            log(f"   错误: {result.stderr[-500:]}")
            return False, result.stderr
    except subprocess.TimeoutExpired:
        log(f"⏱️ 超时: {description or cmd}")
        return False, "timeout"
    except Exception as e:
        log(f"💥 异常: {description or cmd} - {e}")
        return False, str(e)

def check_crawler_data():
    """检查爬虫数据"""
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
                # 提取时间
                time_str = f.stem.split('_')[-1]
                if len(time_str) == 4:  # HHMM
                    file_time = datetime.strptime(f"{today}_{time_str}", "%Y%m%d_%H%M")
                    if latest_time is None or file_time > latest_time:
                        latest_time = file_time
        except:
            pass
    
    # 检查数据新鲜度（最新的数据是否在2小时内）
    if latest_time:
        age_hours = (datetime.now() - latest_time).total_seconds() / 3600
        if age_hours > 2:
            log(f"⚠️ 爬虫数据较旧，最新数据 {age_hours:.1f} 小时前")
            return False, total
    
    if total < 10:
        log(f"⚠️ 爬虫数据量不足: {total} 条")
        return False, total
    
    log(f"✅ 爬虫数据正常: {total} 条，最新 {latest_time.strftime('%H:%M') if latest_time else 'N/A'}")
    return True, total

def check_reports():
    """检查报告文件"""
    today = datetime.now().strftime("%Y%m%d")
    
    daily_report = REPORTS_DIR / f"report_{today}.md"
    deep_report = REPORTS_DIR / f"deep_analysis_{today}.md"
    
    has_daily = daily_report.exists()
    has_deep = deep_report.exists()
    
    # 检查文件修改时间
    daily_time = None
    deep_time = None
    
    if has_daily:
        mtime = daily_report.stat().st_mtime
        daily_time = datetime.fromtimestamp(mtime)
        age_hours = (datetime.now() - daily_time).total_seconds() / 3600
        if age_hours > 4:
            log(f"⚠️ 日报较旧，{age_hours:.1f} 小时前生成")
            has_daily = False
    
    if has_deep:
        mtime = deep_report.stat().st_mtime
        deep_time = datetime.fromtimestamp(mtime)
        age_hours = (datetime.now() - deep_time).total_seconds() / 3600
        if age_hours > 4:
            log(f"⚠️ 深度分析较旧，{age_hours:.1f} 小时前生成")
            has_deep = False
    
    log(f"📄 报告状态: 日报{'✅' if has_daily else '❌'}, 深度分析{'✅' if has_deep else '❌'}")
    return has_daily, has_deep, daily_time, deep_time

def fix_crawler_data():
    """修复爬虫数据缺失"""
    log("🔧 开始修复爬虫数据...")
    
    # 尝试运行爬虫
    success, output = run_command(
        "timeout 300 python3 crawler_multi_v2.py",
        timeout=320,
        description="执行多站点爬虫"
    )
    
    if success:
        log("✅ 爬虫数据修复成功")
        return True
    else:
        log("❌ 爬虫数据修复失败")
        return False

def fix_daily_report():
    """修复日报缺失"""
    log("🔧 开始修复日报...")
    
    # 生成日报
    success, output = run_command(
        "python3 generate_report_enhanced.py",
        timeout=180,
        description="生成日报"
    )
    
    if not success:
        log("❌ 日报生成失败")
        return False
    
    # 发送邮件
    success, output = run_command(
        "python3 send_email.py",
        timeout=60,
        description="发送日报邮件"
    )
    
    if success and "成功" in output:
        log("✅ 日报修复并发送成功")
        send_alert_email("日报已自动修复并发送", "系统检测到日报缺失，已自动重新生成并发送")
        
        # 自动记录经验教训
        if LESSON_LOGGER_AVAILABLE:
            try:
                log_lesson(
                    category="日报缺失自动修复",
                    description="定时任务未正常发送日报，自愈系统检测到并自动修复",
                    root_cause="定时任务执行异常或Agent工具调用错误",
                    fix="自愈系统自动生成日报并重新发送邮件",
                    verification="日报修复并发送成功，邮件已送达"
                )
            except Exception as e:
                log(f"⚠️ 记录经验失败: {e}")
        
        return True
    else:
        log("❌ 日报邮件发送失败")
        return False

def fix_deep_analysis():
    """修复深度分析缺失"""
    log("🔧 开始修复深度分析...")
    
    # 生成深度分析
    success, output = run_command(
        "python3 generate_deep_analysis.py",
        timeout=180,
        description="生成深度分析"
    )
    
    if not success:
        log("❌ 深度分析生成失败")
        return False
    
    # 发送邮件
    success, output = run_command(
        "python3 send_email.py --deep",
        timeout=60,
        description="发送深度分析邮件"
    )
    
    if success and "成功" in output:
        log("✅ 深度分析修复并发送成功")
        send_alert_email("深度分析已自动修复并发送", "系统检测到深度分析报告缺失，已自动重新生成并发送")
        return True
    else:
        log("❌ 深度分析邮件发送失败")
        return False

def self_healing_check():
    """自愈检查主流程"""
    log("=" * 60)
    log("🔍 自愈系统检查开始")
    log(f"⏰ 当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log("=" * 60)
    
    issues_found = 0
    issues_fixed = 0
    
    # 1. 检查爬虫数据
    crawler_ok, crawler_count = check_crawler_data()
    if not crawler_ok:
        issues_found += 1
        if fix_crawler_data():
            issues_fixed += 1
    
    # 2. 检查报告
    has_daily, has_deep, daily_time, deep_time = check_reports()
    
    if not has_daily:
        issues_found += 1
        if fix_daily_report():
            issues_fixed += 1
    
    if not has_deep:
        issues_found += 1
        if fix_deep_analysis():
            issues_fixed += 1
    
    # 3. 汇总
    log("=" * 60)
    if issues_found == 0:
        log("✅ 所有检查通过，系统状态正常")
    else:
        log(f"🔧 发现 {issues_found} 个问题，修复 {issues_fixed} 个")
        
        # 自动记录经验教训
        if LESSON_LOGGER_AVAILABLE and issues_found > 0:
            try:
                log_lesson(
                    category="自愈系统触发",
                    description=f"系统检查发现 {issues_found} 个问题（日报/深度分析/数据缺失）",
                    root_cause="定时任务执行失败或数据未生成",
                    fix=f"自愈系统自动修复了 {issues_fixed}/{issues_found} 个问题",
                    verification="修复成功" if issues_fixed == issues_found else f"部分修复，{issues_found - issues_fixed} 个问题待处理"
                )
            except Exception as e:
                log(f"⚠️ 记录经验失败: {e}")
        
        if issues_fixed < issues_found:
            # 有未修复的问题，发送告警
            send_alert_email(
                f"自愈系统发现 {issues_found - issues_fixed} 个未修复问题",
                f"系统自动修复了 {issues_fixed}/{issues_found} 个问题，请人工检查。"
            )
    log("=" * 60)
    
    return issues_found, issues_fixed

def main():
    """主入口"""
    try:
        issues_found, issues_fixed = self_healing_check()
        return 0 if issues_found == issues_fixed else 1
    except Exception as e:
        log(f"💥 自愈系统异常: {e}")
        send_alert_email("自愈系统异常", f"执行过程中发生错误: {e}")
        return 1

if __name__ == "__main__":
    exit(main())
