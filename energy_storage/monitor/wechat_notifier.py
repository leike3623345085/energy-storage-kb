#!/usr/bin/env python3
"""
任务执行监控 - 企微消息推送版
简单轻量，无需Web面板
"""

import os
import sys
import json
import subprocess
import requests
from datetime import datetime

# 企微机器人Webhook（从环境变量读取，或在这里配置）
WECHAT_WEBHOOK = os.getenv('WECHAT_WEBHOOK', 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY')


def send_wechat_message(content: str, mentioned_list: list = None):
    """发送企微消息"""
    try:
        data = {
            "msgtype": "markdown",
            "markdown": {
                "content": content
            }
        }
        if mentioned_list:
            data["mentioned_list"] = mentioned_list
            
        resp = requests.post(WECHAT_WEBHOOK, json=data, timeout=10)
        return resp.json()
    except Exception as e:
        print(f"发送企微消息失败: {e}")
        return None


def notify_task_start(task_name: str, task_id: str = None):
    """任务开始执行通知"""
    time_str = datetime.now().strftime("%H:%M:%S")
    content = f"""## ⏳ 任务开始执行

**任务名称**: {task_name}
**任务ID**: {task_id or 'N/A'}
**开始时间**: {time_str}

---
正在执行中，请稍候...
"""
    send_wechat_message(content)
    print(f"[{time_str}] 📤 已发送开始通知: {task_name}")


def notify_task_success(task_name: str, duration: str = None, output: str = None):
    """任务执行成功通知"""
    time_str = datetime.now().strftime("%H:%M:%S")
    duration_str = f"**执行时长**: {duration}\\n" if duration else ""
    output_str = f"\\n**输出摘要**: \\n```\\n{output[:500]}\\n```" if output else ""
    
    content = f"""## ✅ 任务执行成功

**任务名称**: {task_name}
**完成时间**: {time_str}
{duration_str}
状态: <font color=\"info\">成功</font>{output_str}
"""
    send_wechat_message(content)
    print(f"[{time_str}] 📤 已发送成功通知: {task_name}")


def notify_task_error(task_name: str, error: str, duration: str = None):
    """任务执行失败通知"""
    time_str = datetime.now().strftime("%H:%M:%S")
    duration_str = f"**执行时长**: {duration}\\n" if duration else ""
    
    content = f"""## ❌ 任务执行失败

**任务名称**: {task_name}
**失败时间**: {time_str}
{duration_str}
状态: <font color=\"warning\">失败</font>

**错误信息**:
```
{error[:1000]}
```

@all 请尽快处理
"""
    send_wechat_message(content, mentioned_list=["@all"])
    print(f"[{time_str}] 📤 已发送失败通知: {task_name}")


def notify_daily_summary():
    """发送每日执行汇总"""
    try:
        # 读取今日执行记录
        from collector import TaskMonitorCollector
        c = TaskMonitorCollector()
        data = c.get_dashboard_data()
        
        today = datetime.now().strftime("%Y-%m-%d")
        total = data['today_executions']['total']
        success = data['today_executions']['success']
        error = data['today_executions']['error']
        rate = (success / total * 100) if total > 0 else 0
        
        content = f"""## 📊 任务执行日报 ({today})

| 指标 | 数值 |
|------|------|
| 总执行次数 | {total} |
| 成功 | <font color=\"info\">{success}</font> |
| 失败 | <font color=\"{'warning' if error > 0 else 'info'}\">{error}</font> |
| 成功率 | {rate:.1f}% |

{f"⚠️ 今日有 {error} 个任务失败，请关注" if error > 0 else "✅ 今日所有任务执行正常"}
"""
        send_wechat_message(content)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 📤 已发送日报")
        
    except Exception as e:
        print(f"生成日报失败: {e}")


# 包装函数，用于装饰cron任务
def monitored_task(task_name: str, task_id: str = None):
    """
    装饰器：包装任务，自动发送企微通知
    
    用法:
        @monitored_task("数据爬虫")
        def my_crawl_task():
            # 任务代码
            pass
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            import time
            start_time = time.time()
            
            # 发送开始通知
            notify_task_start(task_name, task_id)
            
            try:
                # 执行实际任务
                result = func(*args, **kwargs)
                
                # 计算时长
                duration = time.time() - start_time
                duration_str = f"{int(duration // 60)}分{int(duration % 60)}秒"
                
                # 发送成功通知
                notify_task_success(task_name, duration_str, str(result) if result else None)
                return result
                
            except Exception as e:
                # 计算时长
                duration = time.time() - start_time
                duration_str = f"{int(duration // 60)}分{int(duration % 60)}秒"
                
                # 发送失败通知
                notify_task_error(task_name, str(e), duration_str)
                raise
        
        return wrapper
    return decorator


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python3 wechat_notifier.py <命令>")
        print()
        print("命令:")
        print("  test_start  - 测试开始通知")
        print("  test_success - 测试成功通知")
        print("  test_error   - 测试失败通知")
        print("  daily        - 发送日报")
        print()
        print("环境变量:")
        print("  WECHAT_WEBHOOK - 企微机器人Webhook地址")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "test_start":
        notify_task_start("测试任务", "test-001")
    elif cmd == "test_success":
        notify_task_success("测试任务", "2分30秒", "抓取数据100条")
    elif cmd == "test_error":
        notify_task_error("测试任务", "连接超时，请检查网络配置", "1分15秒")
    elif cmd == "daily":
        notify_daily_summary()
    elif cmd == "internal_start" and len(sys.argv) >= 5:
        # 内部命令: internal_start <task_name> <task_id> <start_time>
        notify_task_start(sys.argv[2], sys.argv[3])
    elif cmd == "internal_success" and len(sys.argv) >= 5:
        # 内部命令: internal_success <task_name> <duration> <output>
        notify_task_success(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else None)
    elif cmd == "internal_error" and len(sys.argv) >= 5:
        # 内部命令: internal_error <task_name> <duration> <error>
        notify_task_error(sys.argv[2], sys.argv[4], sys.argv[3])
    else:
        print(f"未知命令: {cmd}")
