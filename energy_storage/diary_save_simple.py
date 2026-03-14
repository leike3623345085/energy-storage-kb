#!/usr/bin/env python3
"""
每日日记自动保存脚本 - 简化版
不依赖 openclaw CLI，直接读取内存文件
"""

import os
from datetime import datetime

WORKSPACE = "/root/.openclaw/workspace"
MEMORY_DIR = os.path.join(WORKSPACE, "memory")
DIARY_DIR = os.path.join(WORKSPACE, "diary")

def get_today_date():
    """获取今天的日期"""
    return datetime.now().strftime("%Y-%m-%d")

def get_diary_file_path():
    """获取今天的日记文件路径"""
    today = get_today_date()
    return os.path.join(DIARY_DIR, f"{today}.md")

def read_memory_file():
    """读取今天的 memory 文件"""
    today = get_today_date()
    memory_path = os.path.join(MEMORY_DIR, f"{today}.md")
    
    if os.path.exists(memory_path):
        try:
            with open(memory_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"读取 memory 文件失败: {e}")
    return None

def append_to_diary(content):
    """追加内容到日记文件"""
    if not content:
        print("没有内容需要记录")
        return
    
    # 确保目录存在
    os.makedirs(DIARY_DIR, exist_ok=True)
    
    diary_path = get_diary_file_path()
    today = get_today_date()
    
    # 准备日记条目
    timestamp = datetime.now().strftime("%H:%M")
    diary_entry = f"\n## {timestamp} 自动记录\n\n"
    diary_entry += content[:2000]  # 限制长度
    diary_entry += "\n\n---\n"
    
    # 如果文件不存在，添加文件头
    if not os.path.exists(diary_path):
        header = f"# 日记 - {today}\n\n"
        with open(diary_path, 'w', encoding='utf-8') as f:
            f.write(header)
    
    # 追加内容
    with open(diary_path, 'a', encoding='utf-8') as f:
        f.write(diary_entry)
    
    print(f"✅ 日记已追加到: {diary_path}")

def main():
    """主函数"""
    print(f"开始保存日记 - {get_today_date()}")
    
    # 读取 memory 文件
    content = read_memory_file()
    if content:
        # 提取前2000字符作为摘要
        summary = f"今日 memory 文件摘要:\n{content[:1500]}..."
        append_to_diary(summary)
    else:
        print("今日 memory 文件不存在或为空")
        append_to_diary("今日暂无重要记录")
    
    print("日记保存完成")

if __name__ == "__main__":
    main()
