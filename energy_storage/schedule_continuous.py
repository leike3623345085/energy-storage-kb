#!/usr/bin/env python3
"""
日程提醒系统 - 连续提醒版
1分钟内连续提醒，直到用户确认取消
"""

import json
import time
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 日程存储文件
SCHEDULE_FILE = Path(__file__).parent / "data" / "schedule.json"
REMINDER_STATE_FILE = Path(__file__).parent / "data" / "reminder_state.json"

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

def load_reminder_state():
    """加载提醒状态"""
    if REMINDER_STATE_FILE.exists():
        with open(REMINDER_STATE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"active_reminders": {}}

def save_reminder_state(state):
    """保存提醒状态"""
    with open(REMINDER_STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def send_continuous_reminder(reminder):
    """发送连续提醒"""
    from wechat_bot import send_alert
    
    reminder_id = str(reminder["id"])
    title = reminder["title"]
    content = reminder.get("content", "")
    
    # 连续提醒消息
    message = f"""🚨 日程提醒 #{reminder_id}

⏰ 时间到了！
📋 {title}
📝 {content}

⚠️ 此提醒将持续发送，直到您回复"取消{reminder_id}"

回复方式：
• "取消{reminder_id}" - 停止提醒
• "完成{reminder_id}" - 标记完成
"""
    
    # 发送提醒
    send_alert(
        title=f"⏰ 日程提醒 #{reminder_id}: {title}",
        content=message,
        priority="critical"
    )
    
    print(f"   已发送提醒 #{reminder_id}: {title}")

def check_and_remind():
    """检查并发送提醒"""
    schedule = load_schedule()
    state = load_reminder_state()
    now = datetime.now()
    
    # 检查待提醒的日程
    for reminder in schedule["reminders"]:
        if reminder["status"] != "pending":
            continue
        
        remind_time = datetime.fromisoformat(reminder["remind_at"].replace(' ', 'T'))
        reminder_id = str(reminder["id"])
        
        # 如果到了提醒时间
        if now >= remind_time:
            # 检查是否已经在连续提醒中
            if reminder_id not in state["active_reminders"]:
                # 首次触发，加入活跃提醒列表
                state["active_reminders"][reminder_id] = {
                    "start_time": now.isoformat(),
                    "last_remind": now.isoformat(),
                    "remind_count": 0
                }
                print(f"🚨 触发日程提醒 #{reminder_id}: {reminder['title']}")
            
            # 获取提醒状态
            active = state["active_reminders"][reminder_id]
            last_remind = datetime.fromisoformat(active["last_remind"])
            
            # 如果距离上次提醒超过1分钟，再次提醒
            if (now - last_remind).total_seconds() >= 60:
                send_continuous_reminder(reminder)
                active["last_remind"] = now.isoformat()
                active["remind_count"] += 1
                print(f"   第 {active['remind_count']} 次提醒")
    
    # 保存状态
    save_reminder_state(state)

def cancel_reminder(reminder_id):
    """取消提醒"""
    schedule = load_schedule()
    state = load_reminder_state()
    
    # 更新日程状态
    for r in schedule["reminders"]:
        if str(r["id"]) == str(reminder_id):
            r["status"] = "cancelled"
            save_schedule(schedule)
            
            # 从活跃提醒中移除
            if str(reminder_id) in state["active_reminders"]:
                del state["active_reminders"][str(reminder_id)]
                save_reminder_state(state)
            
            print(f"✅ 已取消提醒 #{reminder_id}")
            
            # 发送确认
            from wechat_bot import send_text
            send_text(f"✅ 提醒 #{reminder_id} 已取消\n\n不再发送连续提醒。")
            return True
    
    return False

def complete_reminder(reminder_id):
    """标记完成"""
    schedule = load_schedule()
    state = load_reminder_state()
    
    for r in schedule["reminders"]:
        if str(r["id"]) == str(reminder_id):
            r["status"] = "completed"
            r["completed_at"] = datetime.now().isoformat()
            save_schedule(schedule)
            
            # 从活跃提醒中移除
            if str(reminder_id) in state["active_reminders"]:
                del state["active_reminders"][str(reminder_id)]
                save_reminder_state(state)
            
            print(f"✅ 已完成提醒 #{reminder_id}")
            
            # 发送确认
            from wechat_bot import send_text
            send_text(f"✅ 提醒 #{reminder_id} 已完成\n\n恭喜！任务已标记完成。")
            return True
    
    return False

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='日程提醒系统 - 连续提醒版')
    parser.add_argument('--check', '-c', action='store_true', help='检查并发送提醒')
    parser.add_argument('--cancel', type=int, help='取消指定ID的提醒')
    parser.add_argument('--complete', type=int, help='标记指定ID的提醒为完成')
    
    args = parser.parse_args()
    
    if args.check:
        print("=" * 60)
        print("日程提醒系统 - 连续提醒检查")
        print(f"时间: {datetime.now()}")
        print("=" * 60)
        check_and_remind()
        print("\n检查完成")
    elif args.cancel:
        cancel_reminder(args.cancel)
    elif args.complete:
        complete_reminder(args.complete)
    else:
        parser.print_help()

if __name__ == "__main__":
    sys.exit(main())
