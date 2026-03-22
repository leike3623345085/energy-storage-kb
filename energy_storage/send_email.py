#!/usr/bin/env python3
"""
储能行业日报邮件推送脚本
支持 QQ邮箱、163邮箱等 SMTP 发送
"""

import json
import smtplib
import os
import sys
from datetime import datetime
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

# 邮件配置（从环境变量读取，安全考虑）
SMTP_CONFIG = {
    "qq": {
        "host": "smtp.qq.com",
        "port": 465,  # SSL端口
        "use_ssl": True
    },
    "163": {
        "host": "smtp.163.com",
        "port": 465,
        "use_ssl": True
    },
    "gmail": {
        "host": "smtp.gmail.com",
        "port": 587,
        "use_ssl": False  # 使用STARTTLS
    }
}

def load_email_config():
    """从配置文件加载邮件设置"""
    config_file = Path(__file__).parent / "email_config.json"
    if config_file.exists():
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def send_email(subject, content, attachment_path=None, to_email=None):
    """
    发送邮件
    
    参数:
        subject: 邮件主题
        content: 邮件正文（HTML格式）
        attachment_path: 附件路径（可选）
        to_email: 收件人邮箱（可选，默认使用配置中的收件人）
    """
    config = load_email_config()
    if not config:
        print("错误：未找到邮件配置，请先配置 email_config.json")
        return False
    
    smtp_type = config.get("smtp_type", "qq")
    from_email = config.get("from_email")
    password = config.get("password")  # SMTP授权码
    default_to = config.get("to_email")
    
    if not from_email or not password:
        print("错误：发件人邮箱或密码未配置")
        return False
    
    to_email = to_email or default_to
    if not to_email:
        print("错误：收件人邮箱未配置")
        return False
    
    # 获取SMTP配置
    smtp_cfg = SMTP_CONFIG.get(smtp_type, SMTP_CONFIG["qq"])
    
    try:
        # 创建邮件
        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # 添加正文
        msg.attach(MIMEText(content, 'html', 'utf-8'))
        
        # 添加附件
        if attachment_path and Path(attachment_path).exists():
            with open(attachment_path, 'rb') as f:
                attachment = MIMEApplication(f.read())
                attachment.add_header('Content-Disposition', 'attachment', 
                                    filename=Path(attachment_path).name)
                msg.attach(attachment)
        
        # 连接SMTP服务器
        if smtp_cfg["use_ssl"]:
            server = smtplib.SMTP_SSL(smtp_cfg["host"], smtp_cfg["port"])
        else:
            server = smtplib.SMTP(smtp_cfg["host"], smtp_cfg["port"])
            server.starttls()
        
        server.login(from_email, password)
        server.send_message(msg)
        server.quit()
        
        print(f"✅ 邮件发送成功！")
        print(f"   收件人: {to_email}")
        print(f"   主题: {subject}")
        return True
        
    except Exception as e:
        print(f"❌ 邮件发送失败: {e}")
        return False

def send_daily_report(report_date=None):
    """发送储能日报"""
    if report_date is None:
        report_date = datetime.now().strftime("%Y%m%d")
    
    # 查找报告文件
    report_dir = Path(__file__).parent / "data" / "reports"
    report_file = report_dir / f"report_{report_date}.md"
    
    if not report_file.exists():
        # 尝试其他日期格式
        report_file = report_dir / f"report_{datetime.now().strftime('%Y-%m-%d')}.md"
    
    if not report_file.exists():
        print(f"错误：未找到报告文件 {report_file}")
        return False
    
    # 读取报告内容
    with open(report_file, 'r', encoding='utf-8') as f:
        report_content = f.read()
    
    # 转换为HTML格式
    html_content = markdown_to_html(report_content)
    
    # 邮件主题
    subject = f"【KIMICLAW|储能日报】{datetime.now().strftime('%Y年%m月%d日')} 行业动态"
    
    # 发送邮件
    return send_email(subject, html_content, str(report_file))

def markdown_to_html(md_content):
    """简单Markdown转HTML"""
    html = md_content
    
    # 标题转换
    html = html.replace("# ", "<h1>").replace("\n## ", "</h1>\n<h2>")
    html = html.replace("\n### ", "</h2>\n<h3>").replace("\n#### ", "</h3>\n<h4>")
    
    # 粗体、斜体
    html = html.replace("**", "<b>").replace("**", "</b>")
    
    # 换行
    html = html.replace("\n\n", "<br><br>")
    html = html.replace("\n", "<br>")
    
    # 表格处理（简化）
    lines = html.split('<br>')
    new_lines = []
    in_table = False
    
    for line in lines:
        if '|' in line and not in_table:
            in_table = True
            new_lines.append('<table border="1" cellpadding="5" style="border-collapse:collapse;">')
        elif '|' not in line and in_table:
            in_table = False
            new_lines.append('</table>')
        
        if in_table and '|' in line and '---' not in line:
            cells = [c.strip() for c in line.split('|') if c.strip()]
            row = '<tr>' + ''.join(f'<td>{c}</td>' for c in cells) + '</tr>'
            new_lines.append(row)
        else:
            new_lines.append(line)
    
    if in_table:
        new_lines.append('</table>')
    
    html = '<br>'.join(new_lines)
    
    # 包裹HTML
    html = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 20px; }}
            h1 {{ color: #1a73e8; border-bottom: 2px solid #1a73e8; padding-bottom: 10px; }}
            h2 {{ color: #2c5aa0; margin-top: 30px; }}
            h3 {{ color: #444; }}
            table {{ width: 100%; margin: 15px 0; }}
            th, td {{ padding: 10px; text-align: left; border: 1px solid #ddd; }}
            th {{ background-color: #f5f5f5; }}
            blockquote {{ border-left: 4px solid #1a73e8; margin: 0; padding-left: 15px; color: #666; }}
            code {{ background-color: #f4f4f4; padding: 2px 6px; border-radius: 3px; }}
        </style>
    </head>
    <body>
        {html}
        <hr>
        <p style="color: #999; font-size: 12px;">
            <b>🤖 KIMICLAW 储能监控系统</b> 自动生成<br>
            发送时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>
            <span style="color: #1a73e8;">KIMICLAW</span> | 智能行业监控助手
        </p>
    </body>
    </html>
    """
    
    return html

def send_deep_analysis(report_date=None):
    """发送深度分析报告"""
    if report_date is None:
        report_date = datetime.now().strftime("%Y%m%d")
    
    # 查找报告文件
    report_dir = Path(__file__).parent / "data" / "reports"
    report_file = report_dir / f"deep_analysis_{report_date}.md"
    
    if not report_file.exists():
        print(f"错误：未找到深度分析报告文件 {report_file}")
        return False
    
    # 读取报告内容
    with open(report_file, 'r', encoding='utf-8') as f:
        report_content = f.read()
    
    # 转换为HTML格式
    html_content = markdown_to_html(report_content)
    
    # 邮件主题
    subject = f"【KIMICLAW|储能深度分析】{datetime.now().strftime('%Y年%m月%d日')} 行业研究报告"
    
    # 发送邮件
    return send_email(subject, html_content, str(report_file))

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='储能日报邮件推送')
    parser.add_argument('--date', help='报告日期 (YYYYMMDD)')
    parser.add_argument('--test', action='store_true', help='发送测试邮件')
    parser.add_argument('--deep', action='store_true', help='发送深度分析报告')
    parser.add_argument('--weekly', action='store_true', help='发送周报')
    
    args = parser.parse_args()
    
    if args.test:
        # 发送测试邮件
        subject = "【KIMICLAW|测试】储能监控系统邮件推送测试"
        content = """
        <h2>邮件推送测试</h2>
        <p>如果您收到这封邮件，说明储能监控系统的邮件推送功能已配置成功！</p>
        <p>今后每天18:00，您将收到储能行业日报。</p>
        <hr>
        <p>配置时间: {}</p>
        """.format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        
        success = send_email(subject, content)
        return 0 if success else 1
    
    if args.deep:
        # 发送深度分析报告
        success = send_deep_analysis(args.date)
        return 0 if success else 1
    
    # 发送日报
    success = send_daily_report(args.date)
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
