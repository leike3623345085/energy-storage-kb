#!/usr/bin/env python3
"""
每日日记自动保存脚本
读取今天的对话历史，提取重要信息，追加写入日记文件
"""

import os
import json
import subprocess
from datetime import datetime, timedelta

WORKSPACE = "/root/.openclaw/workspace"
MEMORY_DIR = os.path.join(WORKSPACE, "memory")

def get_today_date():
    """获取今天的日期"""
    return datetime.now().strftime("%Y-%m-%d")

def get_diary_file_path():
    """获取今天的日记文件路径"""
    today = get_today_date()
    return os.path.join(MEMORY_DIR, f"{today}.md")

def read_session_history():
    """读取今天的对话历史"""
    try:
        # 使用 openclaw CLI 读取对话历史
        result = subprocess.run(
            ["openclaw", "sessions", "history", "main", "--limit", "100"],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            return result.stdout
        return None
    except Exception as e:
        print(f"读取对话历史失败: {e}")
        return None

def extract_important_info(history_text):
    """从对话历史中提取重要信息"""
    if not history_text:
        return []
    
    important_items = []
    lines = history_text.split('\n')
    
    # 简单的启发式规则提取重要信息
    for line in lines:
        line = line.strip()
        # 跳过心跳消息
        if 'HEARTBEAT_OK' in line or 'Read HEARTBEAT.md' in line:
            continue
        # 提取用户消息
        if line.startswith('User:') or line.startswith('用户:'):
            content = line[5:].strip()
            if len(content) > 10 and not content.startswith('Conversation info'):
                important_items.append(f"- 用户: {content[:200]}")
        # 提取关键系统事件
        elif 'Cron' in line and 'error' in line.lower():
            important_items.append(f"- 系统事件: {line[:200]}")
    
    return important_items[:20]  # 限制条目数

def append_to_diary(content_items):
    """追加内容到日记文件"""
    if not content_items:
        print("没有重要内容需要记录")
        return
    
    # 确保 memory 目录存在
    os.makedirs(MEMORY_DIR, exist_ok=True)
    
    diary_path = get_diary_file_path()
    today = get_today_date()
    
    # 准备日记条目
    timestamp = datetime.now().strftime("%H:%M")
    diary_entry = f"\n## {timestamp} 自动记录\n\n"
    diary_entry += "\n".join(content_items)
    diary_entry += "\n\n---\n"
    
    # 如果文件不存在，添加文件头
    if not os.path.exists(diary_path):
        header = f"# 日记 - {today}\n\n"
        with open(diary_path, 'w', encoding='utf-8') as f:
            f.write(header)
    
    # 追加内容
    with open(diary_path, 'a', encoding='utf-8') as f:
        f.write(diary_entry)
    
    print(f"日记已追加到: {diary_path}")
    print(f"记录了 {len(content_items)} 条重要信息")

def main():
    """主函数"""
    print(f"开始保存日记 - {get_today_date()}")
    
    # 读取对话历史
    history = read_session_history()
    if not history:
        print("无法读取对话历史，跳过本次保存")
        return
    
    # 提取重要信息
    important_items = extract_important_info(history)
    
    # 追加到日记
    append_to_diary(important_items)
    
    print("日记保存完成")

if __name__ == "__main__":
    main()
