#!/usr/bin/env python3
"""
经验自动保存系统 - Auto Lesson Learner
每次错误和修复自动记录到长期记忆，避免重复犯错

使用方法:
    from lesson_logger import log_lesson
    
    log_lesson(
        category="错误类型",
        description="问题描述",
        root_cause="根本原因",
        fix="修复措施",
        verification="验证结果"
    )
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

# 配置
WORKSPACE = Path("/root/.openclaw/workspace")
MEMORY_FILE = WORKSPACE / "MEMORY.md"
DAILY_DIR = WORKSPACE / "memory"
LESSON_INDEX = WORKSPACE / "memory" / "lesson_index.json"

def ensure_dirs():
    """确保目录存在"""
    DAILY_DIR.mkdir(parents=True, exist_ok=True)

def load_lesson_index():
    """加载经验教训索引"""
    if LESSON_INDEX.exists():
        with open(LESSON_INDEX, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"lessons": [], "categories": {}}

def save_lesson_index(index):
    """保存经验教训索引"""
    with open(LESSON_INDEX, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)

def update_daily_log(lesson):
    """更新当日日志"""
    today = datetime.now().strftime("%Y-%m-%d")
    daily_file = DAILY_DIR / f"{today}.md"
    
    timestamp = datetime.now().strftime("%H:%M")
    
    entry = f"""
## 🚨 {lesson['category']} - {timestamp}

**问题**: {lesson['description']}
**根因**: {lesson['root_cause']}
**修复**: {lesson['fix']}
**验证**: {lesson['verification']}

---
"""
    
    if daily_file.exists():
        with open(daily_file, "a", encoding="utf-8") as f:
            f.write(entry)
    else:
        # 创建新文件
        header = f"""# {today} 工作日志

> 自动生成于 {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

---
"""
        with open(daily_file, "w", encoding="utf-8") as f:
            f.write(header + entry)
    
    return daily_file

def update_memory_md(lesson):
    """更新长期记忆文件"""
    today = datetime.now().strftime("%Y-%m-%d")
    
    # 构建经验教训条目
    lesson_entry = f"""### {lesson['category']}（{today}）
**问题**：{lesson['description']}
**根因**：{lesson['root_cause']}
**修复**：{lesson['fix']}
**验证**：{lesson['verification']}
**详情**：见 memory/{today}.md

---

"""
    
    if MEMORY_FILE.exists():
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            content = f.read()
        
        # 查找插入位置（在## 🚨 经验教训 之后）
        marker = "## 🚨 经验教训"
        if marker in content:
            # 在标记后插入
            insert_pos = content.find(marker) + len(marker)
            new_content = content[:insert_pos] + "\n\n" + lesson_entry + content[insert_pos:]
        else:
            # 在文件末尾添加新章节
            new_content = content + "\n\n## 🚨 经验教训\n\n" + lesson_entry
        
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            f.write(new_content)
    else:
        # 创建新文件
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            f.write(f"# MEMORY.md\n\n## 🚨 经验教训\n\n{lesson_entry}")
    
    return MEMORY_FILE

def update_lesson_index(lesson):
    """更新经验教训索引"""
    index = load_lesson_index()
    
    lesson_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    lesson_record = {
        "id": lesson_id,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "time": datetime.now().strftime("%H:%M:%S"),
        "category": lesson["category"],
        "description": lesson["description"][:100] + "..." if len(lesson["description"]) > 100 else lesson["description"],
        "file": f"memory/{datetime.now().strftime('%Y-%m-%d')}.md"
    }
    
    index["lessons"].insert(0, lesson_record)  # 新经验放前面
    
    # 按分类统计
    cat = lesson["category"]
    if cat not in index["categories"]:
        index["categories"][cat] = []
    index["categories"][cat].insert(0, lesson_id)
    
    save_lesson_index(index)
    return index

def log_lesson(category, description, root_cause, fix, verification="待验证"):
    """
    记录经验教训（主入口）
    
    参数:
        category: 错误类型/分类
        description: 问题描述
        root_cause: 根本原因分析
        fix: 修复措施
        verification: 验证结果
    """
    ensure_dirs()
    
    lesson = {
        "category": category,
        "description": description,
        "root_cause": root_cause,
        "fix": fix,
        "verification": verification,
        "timestamp": datetime.now().isoformat()
    }
    
    # 更新所有存储位置
    daily_file = update_daily_log(lesson)
    memory_file = update_memory_md(lesson)
    index = update_lesson_index(lesson)
    
    # 输出确认
    print(f"✅ 经验教训已保存")
    print(f"   当日日志: {daily_file}")
    print(f"   长期记忆: {memory_file}")
    print(f"   索引记录: {len(index['lessons'])} 条")
    
    return lesson

def search_lessons(keyword):
    """搜索历史经验教训"""
    index = load_lesson_index()
    results = []
    
    for lesson in index["lessons"]:
        if keyword.lower() in lesson["description"].lower() or keyword.lower() in lesson["category"].lower():
            results.append(lesson)
    
    return results

def get_lesson_stats():
    """获取经验教训统计"""
    index = load_lesson_index()
    
    stats = {
        "total_lessons": len(index["lessons"]),
        "categories": {k: len(v) for k, v in index["categories"].items()},
        "recent": index["lessons"][:5]
    }
    
    return stats

def main():
    """命令行入口"""
    if len(sys.argv) < 2:
        print(__doc__)
        print("\n使用方法:")
        print(f"  python3 {sys.argv[0]} log '分类' '问题描述' '根因' '修复措施' '验证结果'")
        print(f"  python3 {sys.argv[0]} stats              # 查看统计")
        print(f"  python3 {sys.argv[0]} search <关键词>    # 搜索经验")
        return 1
    
    cmd = sys.argv[1]
    
    if cmd == "log" and len(sys.argv) >= 6:
        log_lesson(
            category=sys.argv[2],
            description=sys.argv[3],
            root_cause=sys.argv[4],
            fix=sys.argv[5],
            verification=sys.argv[6] if len(sys.argv) > 6 else "待验证"
        )
        return 0
    
    elif cmd == "stats":
        stats = get_lesson_stats()
        print("=== 经验教训统计 ===")
        print(f"总计: {stats['total_lessons']} 条")
        print("\n按分类:")
        for cat, count in stats["categories"].items():
            print(f"  {cat}: {count} 条")
        print("\n最近5条:")
        for lesson in stats["recent"]:
            print(f"  [{lesson['date']}] {lesson['category']}: {lesson['description'][:50]}...")
        return 0
    
    elif cmd == "search" and len(sys.argv) >= 3:
        keyword = sys.argv[2]
        results = search_lessons(keyword)
        print(f"=== 搜索结果: '{keyword}' ===")
        print(f"找到 {len(results)} 条相关经验:\n")
        for r in results:
            print(f"[{r['date']}] {r['category']}")
            print(f"  {r['description']}")
            print(f"  文件: {r['file']}")
            print()
        return 0
    
    else:
        print(f"❌ 未知命令: {cmd}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
