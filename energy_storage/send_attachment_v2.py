#!/usr/bin/env python3
"""
发送带附件的邮件 - 使用 email.message 新API
"""
import smtplib
import json
from email.message import EmailMessage
from pathlib import Path
import mimetypes
import sys

# 读取邮箱配置
config_path = Path(__file__).parent / 'email_config.json'
with open(config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

SMTP_SERVERS = {
    'qq': ('smtp.qq.com', 587),
    '163': ('smtp.163.com', 587),
    'gmail': ('smtp.gmail.com', 587)
}

def send_email_with_attachment(subject, body, attachment_path):
    """发送带附件的邮件"""
    
    # 获取SMTP配置
    smtp_type = config.get('smtp_type', 'qq')
    smtp_server, smtp_port = SMTP_SERVERS.get(smtp_type, SMTP_SERVERS['qq'])
    
    from_email = config['from_email']
    password = config['password']
    to_emails = config['to_email'].split(',')
    
    # 创建邮件
    msg = EmailMessage()
    msg['From'] = from_email
    msg['To'] = ', '.join(to_emails)
    msg['Subject'] = subject
    
    # 添加正文
    msg.set_content(body)
    
    # 添加附件
    attachment_path = Path(attachment_path)
    if attachment_path.exists():
        # 手动设置PPTX的MIME类型
        ext = attachment_path.suffix.lower()
        if ext == '.pptx':
            maintype = 'application'
            subtype = 'vnd.openxmlformats-officedocument.presentationml.presentation'
        else:
            ctype, encoding = mimetypes.guess_type(str(attachment_path))
            if ctype is None or encoding is not None:
                ctype = 'application/octet-stream'
            maintype, subtype = ctype.split('/', 1)
        
        with open(attachment_path, 'rb') as f:
            msg.add_attachment(
                f.read(),
                maintype=maintype,
                subtype=subtype,
                filename=attachment_path.name
            )
        print(f"已添加附件: {attachment_path.name} ({maintype}/{subtype})")
    else:
        print(f"警告: 附件不存在 {attachment_path}")
        return False
    
    # 发送邮件
    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(from_email, password)
        server.send_message(msg)
        server.quit()
        print(f"✅ 邮件发送成功！")
        print(f"   收件人: {', '.join(to_emails)}")
        print(f"   主题: {subject}")
        return True
    except Exception as e:
        print(f"❌ 邮件发送失败: {e}")
        return False

if __name__ == '__main__':
    if len(sys.argv) < 2:
        # 默认发送系统总结报告
        attachment = "/root/.openclaw/workspace/系统体系总结报告_20260322.pptx"
        subject = "系统体系总结报告 - 2026年3月22日"
        body = """您好，

附件是储能行业监控系统的体系总结报告（PPT格式）。

报告包含以下内容：
1. 系统架构总览
2. 记忆系统 v2.0（六大控制面板）
3. Harness Engineering 架构
4. 研报分析框架
5. 储能监控系统
6. 数据流与自愈系统
7. 定时任务体系
8. 系统演进路线图

如有任何问题，请随时联系。

—— 储能行业监控系统
"""
        send_email_with_attachment(subject, body, attachment)
    else:
        attachment = sys.argv[1]
        subject = sys.argv[2] if len(sys.argv) > 2 else "附件"
        body = sys.argv[3] if len(sys.argv) > 3 else "请查看附件"
        send_email_with_attachment(subject, body, attachment)
