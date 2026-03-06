#!/usr/bin/env python3
"""
企业微信机器人推送
用于储能行业监控系统的即时提醒
"""

import json
import urllib.request
import ssl
from datetime import datetime

# 企业微信机器人Webhook
WECHAT_WEBHOOK = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=bad9dacb-9e31-423b-9480-d34ac0084ee9"

# 创建SSL上下文
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

def send_text(content, mentioned_list=None):
    """
    发送文本消息
    
    参数:
        content: 消息内容
        mentioned_list: @用户列表，如 ["@all"] 或 ["UserID1"]
    """
    data = {
        "msgtype": "text",
        "text": {
            "content": content,
            "mentioned_list": mentioned_list or []
        }
    }
    
    return _send(data)

def send_markdown(content):
    """
    发送Markdown消息
    支持格式：标题、加粗、链接、颜色等
    """
    data = {
        "msgtype": "markdown",
        "markdown": {
            "content": content
        }
    }
    
    return _send(data)

def send_news(title, description, url, picurl=None):
    """
    发送图文消息
    
    参数:
        title: 标题
        description: 描述
        url: 点击后跳转的链接
        picurl: 图片URL
    """
    data = {
        "msgtype": "news",
        "news": {
            "articles": [
                {
                    "title": title,
                    "description": description,
                    "url": url,
                    "picurl": picurl or ""
                }
            ]
        }
    }
    
    return _send(data)

def send_file(filepath):
    """
    发送文件（企业微信暂不支持直接上传文件，改为发送文件路径提示）
    实际使用时需要先将文件上传到企业微信临时素材，再发送
    """
    import os
    
    if not os.path.exists(filepath):
        print(f"❌ 文件不存在: {filepath}")
        return False
    
    filename = os.path.basename(filepath)
    file_size = os.path.getsize(filepath)
    
    # 企业微信机器人不支持直接发送文件，发送提示信息
    content = f"📄 分析报告已生成\n\n文件名: {filename}\n大小: {file_size/1024:.1f} KB\n\n请查看邮件获取完整报告。"
    
    return send_text(content)

def _send(data):
    """发送请求"""
    try:
        headers = {
            'Content-Type': 'application/json; charset=utf-8'
        }
        
        req = urllib.request.Request(
            WECHAT_WEBHOOK,
            data=json.dumps(data, ensure_ascii=False).encode('utf-8'),
            headers=headers,
            method='POST'
        )
        
        with urllib.request.urlopen(req, context=ssl_context, timeout=10) as response:
            result = json.loads(response.read().decode('utf-8'))
            
            if result.get('errcode') == 0:
                print("✅ 企业微信推送成功")
                return True
            else:
                print(f"❌ 推送失败: {result}")
                return False
                
    except Exception as e:
        print(f"❌ 推送异常: {e}")
        return False

def send_daily_summary(title, content, report_url=None):
    """
    发送日报摘要
    """
    markdown = f"""## {title}

{content}

---
⏰ 发送时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}
"""
    
    if report_url:
        markdown += f"\n📄 [查看完整报告]({report_url})"
    
    return send_markdown(markdown)

def send_alert(title, content, priority="normal"):
    """
    发送重要提醒
    
    priority: normal/warning/critical
    """
    if priority == "critical":
        emoji = "🚨"
    elif priority == "warning":
        emoji = "⚠️"
    else:
        emoji = "📢"
    
    text = f"{emoji} **{title}**\n\n{content}\n\n⏰ {datetime.now().strftime('%H:%M')}"
    
    return send_markdown(text)

def main():
    """测试推送"""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        # 发送测试消息
        result = send_text(
            "🔔 储能监控系统测试\n\n"
            "企业微信机器人配置成功！\n"
            "今后重要动态将实时推送至此。",
            mentioned_list=["@all"]
        )
        return 0 if result else 1
    
    print("用法: python3 wechat_bot.py --test")
    return 0

if __name__ == "__main__":
    exit(main())
