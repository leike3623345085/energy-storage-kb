#!/usr/bin/env python3
"""
会话启动记忆回顾系统
确保保存的记忆真正被使用
"""
import json
from datetime import datetime, timedelta
from pathlib import Path

WORKSPACE = Path("/root/.openclaw/workspace")
MEMORY_DIR = WORKSPACE / "memory"

def get_recent_memories(days=7):
    """获取最近N天的记忆"""
    memories = []
    
    # 1. 最近的项目文档
    for f in (MEMORY_DIR / "system").glob("*.md"):
        content = f.read_text(encoding='utf-8') if f.exists() else ""
        if content:
            memories.append({
                "type": "project",
                "title": f.stem,
                "preview": content[:200],
                "updated": datetime.fromtimestamp(f.stat().st_mtime).isoformat()
            })
    
    # 2. 最近的教训
    for f in (MEMORY_DIR / "lessons").glob("*.md"):
        content = f.read_text(encoding='utf-8') if f.exists() else ""
        if content:
            # 提取最近的问题
            issues = [line for line in content.split('\n') if line.startswith('##')]
            memories.append({
                "type": "lesson",
                "title": f.stem,
                "recent_issues": issues[-3:] if issues else [],
                "updated": datetime.fromtimestamp(f.stat().st_mtime).isoformat()
            })
    
    # 3. 最近的自动归档
    today = datetime.now()
    for i in range(days):
        date_str = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        archive_file = MEMORY_DIR / "auto" / f"{date_str}_auto.md"
        if archive_file.exists():
            content = archive_file.read_text(encoding='utf-8')
            topics = [line for line in content.split('\n') if line.startswith('##')]
            memories.append({
                "type": "archive",
                "date": date_str,
                "topics": topics[-5:] if topics else [],
                "summary": "见归档文件"
            })
    
    return memories

def generate_context_summary(memories):
    """生成上下文摘要"""
    if not memories:
        return "近期无重要记忆更新。"
    
    summary = []
    
    # 项目
    projects = [m for m in memories if m["type"] == "project"]
    if projects:
        summary.append(f"📁 进行中的项目: {', '.join(p['title'] for p in projects)}")
    
    # 教训
    lessons = [m for m in memories if m["type"] == "lesson"]
    if lessons:
        summary.append(f"⚠️ 已记录教训: {len(lessons)} 项")
    
    # 归档
    archives = [m for m in memories if m["type"] == "archive"]
    if archives:
        summary.append(f"📝 近7天对话归档: {len(archives)} 天")
    
    return "\n".join(summary)

def should_search_memory(user_input):
    """判断是否应该搜索历史记忆"""
    # 关键词触发
    triggers = [
        "之前", "上次", "以前", "记得", "说过",
        "项目", "方案", "配置", "设置",
        "修复", "错误", "bug", "问题",
        "储能", "银行", "工作流", "爬虫"
    ]
    
    return any(t in user_input for t in triggers)

def get_relevant_context(user_input):
    """根据用户输入获取相关上下文"""
    # 这里应该调用 memory_search，但简化版先返回提示
    keywords = []
    
    if "储能" in user_input:
        keywords.append("energy-storage")
    if "银行" in user_input or "工作流" in user_input:
        keywords.append("bank-workflow")
    if "修复" in user_input or "错误" in user_input:
        keywords.append("lessons")
    
    return keywords

if __name__ == "__main__":
    # 测试
    memories = get_recent_memories()
    summary = generate_context_summary(memories)
    print(summary)
