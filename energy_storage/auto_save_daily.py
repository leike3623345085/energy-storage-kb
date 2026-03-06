#!/usr/bin/env python3
"""
每日自动保存脚本
自动记录：经验教训、对话重点、重要操作
运行时间：每天 23:30（日报之后）
"""

import json
import os
from datetime import datetime
from pathlib import Path

WORKSPACE = "/root/.openclaw/workspace"
MEMORY_DIR = f"{WORKSPACE}/memory"

def ensure_memory_dir():
    """确保 memory 目录存在"""
    os.makedirs(MEMORY_DIR, exist_ok=True)

def get_today_file():
    """获取今天的 memory 文件路径"""
    today = datetime.now().strftime("%Y-%m-%d")
    return f"{MEMORY_DIR}/{today}.md"

def read_existing_content(filepath):
    """读取已有内容（如果存在）"""
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    return ""

def extract_key_points():
    """提取今天的关键信息"""
    today = datetime.now()
    
    key_points = {
        "date": today.strftime("%Y-%m-%d"),
        "weekday": today.strftime("%A"),
        "summary": [],
        "lessons": [],
        "actions": [],
        "decisions": [],
        "todos": []
    }
    
    # 这里可以通过分析会话历史来自动提取
    # 目前作为模板，实际内容需要手动或半自动填充
    
    return key_points

def generate_daily_memory(data):
    """生成每日 memory 内容"""
    
    content = f"""# {data['date']} 工作日志

## 今日概览
- **日期**：{data['date']} ({data['weekday']})
- **生成时间**：{datetime.now().strftime("%H:%M")}

## 对话重点
<!-- 记录与用户的重要对话内容 -->

## 经验教训
<!-- 今天学到的重要教训 -->

## 重要操作
<!-- 执行的关键操作 -->

## 关键决策
<!-- 做出的重要决定 -->

## 待办事项
<!-- 遗留的 TODO -->

## 系统状态
<!-- 定时任务、配置变更等 -->

---
*本文件由自动保存脚本生成，内容由人工补充*
"""
    return content

def save_daily_memory():
    """保存每日 memory"""
    ensure_memory_dir()
    
    filepath = get_today_file()
    
    # 如果文件已存在，保留已有内容
    existing = read_existing_content(filepath)
    
    if not existing:
        # 生成新文件
        data = extract_key_points()
        content = generate_daily_memory(data)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ 已创建今日 memory 文件: {filepath}")
    else:
        print(f"⏭️ 今日 memory 文件已存在: {filepath}")
    
    return filepath

def update_memory_md():
    """更新 MEMORY.md 的更新记录"""
    memory_md = f"{WORKSPACE}/MEMORY.md"
    
    if not os.path.exists(memory_md):
        return
    
    today = datetime.now().strftime("%Y-%m-%d")
    
    with open(memory_md, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查是否已记录今天
    if today in content:
        return
    
    # 在更新记录中添加今天
    update_line = f"| {today} | 自动保存工作日志 |"
    
    # 找到更新记录表格，添加新行
    if "## 更新记录" in content:
        # 简单插入到表格中
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if line.startswith("| 日期 |"):
                # 在表头后两行插入
                lines.insert(i + 2, update_line)
                break
        
        with open(memory_md, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        print(f"✅ 已更新 MEMORY.md 更新记录")

def git_commit():
    """自动提交到 git"""
    os.chdir(WORKSPACE)
    
    today = datetime.now().strftime("%Y-%m-%d")
    
    # 添加所有变更
    os.system("git add -A")
    
    # 提交
    result = os.system(f'git commit -m "memory: 自动保存 {today} 工作日志" > /dev/null 2>&1')
    
    if result == 0:
        print(f"✅ 已提交 Git: memory: 自动保存 {today} 工作日志")
    else:
        print("⏭️ 无变更需要提交")

if __name__ == "__main__":
    print("=" * 60)
    print("每日自动保存")
    print("=" * 60)
    
    # 保存每日 memory
    filepath = save_daily_memory()
    
    # 更新 MEMORY.md
    update_memory_md()
    
    # Git 提交
    git_commit()
    
    print("=" * 60)
    print("自动保存完成")
    print("=" * 60)
