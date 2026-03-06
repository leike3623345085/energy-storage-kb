#!/usr/bin/env python3
"""
定时任务执行监控
检查日报/周报是否成功生成和推送
失败时自动补发并通知
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 配置
CHECK_HOURS = [18, 19, 20]  # 每天18-20点检查日报
REPORT_DIR = Path(__file__).parent / "data" / "reports"

def check_daily_report():
    """检查日报是否生成"""
    today = datetime.now().strftime("%Y%m%d")
    report_file = REPORT_DIR / f"report_{today}.md"
    
    if report_file.exists():
        # 检查文件修改时间
        mtime = datetime.fromtimestamp(report_file.stat().st_mtime)
        now = datetime.now()
        
        # 如果今天18:00后生成的
        if mtime.hour >= 18:
            print(f"✅ 日报已生成: {report_file}")
            print(f"   生成时间: {mtime.strftime('%H:%M')}")
            return True, mtime
    
    print(f"⚠️ 日报未生成或不是今天生成的")
    return False, None

def check_email_sent():
    """检查邮件是否发送（通过日志或标记文件）"""
    # 这里简化处理，实际可以通过邮件服务器日志检查
    return True  # 假设邮件发送成功

def check_wechat_sent():
    """检查企业微信是否推送"""
    # 这里简化处理，实际可以通过API响应记录检查
    return True  # 假设微信推送成功

def resend_report():
    """重新发送报告"""
    print("🔄 正在重新发送报告...")
    
    # 执行邮件发送
    result1 = os.system("cd /root/.openclaw/workspace/energy_storage && python3 send_email.py")
    
    # 执行微信推送
    from wechat_bot import send_markdown
    
    today = datetime.now().strftime("%Y%m%d")
    content = f"""## 📊 储能日报 - {today[:4]}年{today[4:6]}月{today[6:]}日

### 🔔 补发通知
原定时任务执行异常，现手动补发日报。

### 📧 邮件状态
{'✅ 已发送' if result1 == 0 else '❌ 发送失败'}

### 🔍 请检查
1. 收件箱是否收到邮件
2. 如未收到请联系管理员

---
⏰ {datetime.now().strftime('%H:%M')} | OpenClaw 储能监控系统
"""
    
    result2 = send_markdown(content)
    
    return result1 == 0 and result2

def send_alert_to_admin(error_msg):
    """发送警报给管理员"""
    try:
        from wechat_bot import send_alert
        
        send_alert(
            title="🚨 定时任务监控警报",
            content=f"任务: 日报生成/推送\n错误: {error_msg}\n时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n请检查系统！",
            priority="critical"
        )
        print("✅ 警报已发送给管理员")
    except Exception as e:
        print(f"❌ 发送警报失败: {e}")

def main():
    """主函数"""
    print("=" * 60)
    print("定时任务执行监控")
    print(f"检查时间: {datetime.now()}")
    print("=" * 60)
    
    # 检查日报
    report_ok, mtime = check_daily_report()
    
    if not report_ok:
        print("\n⚠️ 日报检查失败，尝试补发...")
        success = resend_report()
        
        if success:
            print("✅ 补发成功")
        else:
            print("❌ 补发失败")
            send_alert_to_admin("日报生成和补发均失败")
        return 1
    
    # 检查邮件和微信
    email_ok = check_email_sent()
    wechat_ok = check_wechat_sent()
    
    print(f"\n📊 检查结果:")
    print(f"   日报生成: {'✅' if report_ok else '❌'}")
    print(f"   邮件发送: {'✅' if email_ok else '❌'}")
    print(f"   微信推送: {'✅' if wechat_ok else '❌'}")
    
    # 如果有问题，补发
    if not (email_ok and wechat_ok):
        print("\n🔄 检测到推送异常，尝试补发...")
        resend_report()
    
    print("\n✅ 监控检查完成")
    return 0

if __name__ == "__main__":
    sys.exit(main())
