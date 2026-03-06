#!/usr/bin/env python3
"""
日程提醒管理
支持添加临时日程并通过企业微信推送
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 日程存储文件
SCHEDULE_FILE = Path(__file__).parent / "data" / "schedule.json"

def load_schedule():
    """加载日程列表"""
    if SCHEDULE_FILE.exists():
        with open(SCHEDULE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"reminders": []}

def save_schedule(schedule):
    """保存日程列表"""
    SCHEDULE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SCHEDULE_FILE, 'w', encoding='utf-8') as f:
        json.dump(schedule, f, ensure_ascii=False, indent=2)

def add_reminder(title, remind_at, content=""):
    """
    添加日程提醒
    
    参数:
        title: 提醒标题
        remind_at: 提醒时间 (格式: YYYY-MM-DD HH:MM 或 HH:MM)
        content: 详细内容
    """
    schedule = load_schedule()
    
    # 解析时间
    if len(remind_at) == 5 and remind_at[2] == ':':
        # 只有时间，使用今天日期
        today = datetime.now().strftime('%Y-%m-%d')
        remind_at = f"{today} {remind_at}"
    
    reminder = {
        "id": len(schedule["reminders"]) + 1,
        "title": title,
        "content": content,
        "remind_at": remind_at,
        "created_at": datetime.now().isoformat(),
        "status": "pending"
    }
    
    schedule["reminders"].append(reminder)
    save_schedule(schedule)
    
    print(f"✅ 日程已添加")
    print(f"   标题: {title}")
    print(f"   时间: {remind_at}")
    
    return reminder

def list_reminders():
    """列出所有待办日程"""
    schedule = load_schedule()
    
    pending = [r for r in schedule["reminders"] if r["status"] == "pending"]
    
    if not pending:
        print("暂无待办日程")
        return
    
    print(f"\n📋 待办日程 ({len(pending)}项)")
    print("-" * 50)
    
    for r in sorted(pending, key=lambda x: x["remind_at"]):
        print(f"\n[{r['id']}] {r['title']}")
        print(f"    时间: {r['remind_at']}")
        if r['content']:
            print(f"    内容: {r['content'][:50]}...")

def delete_reminder(reminder_id):
    """删除日程"""
    schedule = load_schedule()
    
    for r in schedule["reminders"]:
        if r["id"] == reminder_id:
            r["status"] = "deleted"
            save_schedule(schedule)
            print(f"✅ 已删除日程: {r['title']}")
            return True
    
    print(f"❌ 未找到日程ID: {reminder_id}")
    return False

def check_and_send():
    """检查并发送到期提醒"""
    from wechat_bot import send_alert
    
    schedule = load_schedule()
    now = datetime.now()
    
    triggered = []
    
    for r in schedule["reminders"]:
        if r["status"] != "pending":
            continue
        
        remind_time = datetime.fromisoformat(r["remind_at"].replace(' ', 'T'))
        
        # 如果到了提醒时间（前后1分钟内）
        if abs((now - remind_time).total_seconds()) < 60:
            # 发送企业微信提醒
            send_alert(
                title=f"⏰ 日程提醒: {r['title']}",
                content=r['content'] or "您设置的日程时间到了",
                priority="normal"
            )
            
            r["status"] = "sent"
            r["sent_at"] = now.isoformat()
            triggered.append(r)
    
    if triggered:
        save_schedule(schedule)
        print(f"✅ 已发送 {len(triggered)} 条提醒")
    
    return triggered

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='日程提醒管理')
    parser.add_argument('--add', '-a', help='添加日程（格式: "标题|时间|内容"）')
    parser.add_argument('--list', '-l', action='store_true', help='列出所有日程')
    parser.add_argument('--delete', '-d', type=int, help='删除指定ID的日程')
    parser.add_argument('--check', '-c', action='store_true', help='检查并发送到期提醒')
    
    args = parser.parse_args()
    
    if args.add:
        parts = args.add.split('|')
        title = parts[0]
        remind_at = parts[1] if len(parts) > 1 else ""
        content = parts[2] if len(parts) > 2 else ""
        
        if not remind_at:
            print("错误: 需要指定提醒时间")
            print('格式: python3 schedule.py --add "会议|15:30|项目评审会议"')
            return 1
        
        add_reminder(title, remind_at, content)
    
    elif args.list:
        list_reminders()
    
    elif args.delete:
        delete_reminder(args.delete)
    
    elif args.check:
        check_and_send()
    
    else:
        parser.print_help()
        print("\n示例:")
        print('  添加日程: python3 schedule.py --add "开会|15:30|项目评审"')
        print('  添加日程: python3 schedule.py --add "提交报告|2026-03-05 10:00|周报"')
        print('  列出日程: python3 schedule.py --list')
        print('  删除日程: python3 schedule.py --delete 1')
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
