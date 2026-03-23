#!/usr/bin/env python3
"""
记忆自动保存系统 - Auto Memory Saver
自动检测并保存关键对话内容
"""
import json
import re
from datetime import datetime
from pathlib import Path

WORKSPACE = Path("/root/.openclaw/workspace")
MEMORY_DIR = WORKSPACE / "memory"
SYSTEM_DIR = MEMORY_DIR / "system"
LESSONS_DIR = MEMORY_DIR / "lessons"
AUTO_DIR = MEMORY_DIR / "auto"

def ensure_dirs():
    """确保目录存在"""
    for d in [MEMORY_DIR, SYSTEM_DIR, LESSONS_DIR, AUTO_DIR]:
        d.mkdir(parents=True, exist_ok=True)

def detect_content_type(text):
    """检测内容类型"""
    patterns = {
        "code": r"```(?:python|bash|javascript|java|go|rust|cpp|c|sql|yaml|json|xml)",
        "config": r"(配置|config|设置|setup|环境变量|api.?key|token|密码|密钥)",
        "preference": r"(记住|preference|偏好|设置|以后|默认|习惯)",
        "deliverable": r"(报告|文档|模板|配置|工作流|方案|设计|分析)",
        "lesson": r"(问题|修复|错误|bug|教训|注意|避免|解决|方案)",
        "project_tech": r"(架构|技术|实现|模块|组件|接口|数据库|缓存|部署)"
    }
    
    detected = []
    for content_type, pattern in patterns.items():
        if re.search(pattern, text, re.IGNORECASE):
            detected.append(content_type)
    return detected

def save_code_snippet(content, metadata=None):
    """保存代码片段到临时文件"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"snippet_{timestamp}.py"
    filepath = AUTO_DIR / filename
    
    with open(filepath, 'w', encoding='utf-8') as f:
        if metadata:
            f.write(f"# {metadata}\n")
        f.write(content)
    
    return str(filepath)

def update_user_preference(key, value):
    """更新用户偏好到 USER.md"""
    user_file = WORKSPACE / "USER.md"
    
    content = user_file.read_text(encoding='utf-8') if user_file.exists() else "# USER.md - About Your Human\n\n"
    
    # 检查是否已存在该偏好
    pattern = rf"(^|\n)- \*\*{key}\*\*:.*?(\n|$)"
    replacement = f"\n- **{key}**: {value}\n"
    
    if re.search(pattern, content, re.IGNORECASE):
        content = re.sub(pattern, replacement, content, flags=re.IGNORECASE)
    else:
        content += f"\n- **{key}**: {value}\n"
    
    user_file.write_text(content, encoding='utf-8')
    return str(user_file)

def update_memory_rule(category, rule):
    """更新 MEMORY.md 规则"""
    memory_file = WORKSPACE / "MEMORY.md"
    
    content = memory_file.read_text(encoding='utf-8') if memory_file.exists() else "# MEMORY.md\n\n"
    
    timestamp = datetime.now().strftime("%Y-%m-%d")
    entry = f"\n### {category} ({timestamp})\n{rule}\n"
    
    content += entry
    memory_file.write_text(content, encoding='utf-8')
    return str(memory_file)

def save_lesson(project, problem, solution):
    """保存经验教训"""
    lesson_file = LESSONS_DIR / f"{project}.md"
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = f"\n## {timestamp}\n\n**问题**: {problem}\n\n**解决方案**: {solution}\n"
    
    content = lesson_file.read_text(encoding='utf-8') if lesson_file.exists() else f"# {project} - 经验教训\n\n"
    content += entry
    
    lesson_file.write_text(content, encoding='utf-8')
    return str(lesson_file)

def save_project_tech(project, tech_doc):
    """保存项目技术文档"""
    tech_file = SYSTEM_DIR / f"{project}.md"
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = f"\n## 更新 - {timestamp}\n\n{tech_doc}\n"
    
    content = tech_file.read_text(encoding='utf-8') if tech_file.exists() else f"# {project} - 技术文档\n\n"
    content += entry
    
    tech_file.write_text(content, encoding='utf-8')
    return str(tech_file)

def auto_archive_conversation(summary):
    """自动归档对话摘要"""
    today = datetime.now().strftime("%Y-%m-%d")
    daily_file = AUTO_DIR / f"{today}_auto.md"
    
    timestamp = datetime.now().strftime("%H:%M:%S")
    entry = f"\n## {timestamp}\n\n{summary}\n"
    
    content = daily_file.read_text(encoding='utf-8') if daily_file.exists() else f"# 自动归档 - {today}\n\n"
    content += entry
    
    daily_file.write_text(content, encoding='utf-8')
    return str(daily_file)

def should_save(text):
    """判断是否应该保存"""
    # 检查长度（太短的不值得保存）
    if len(text) < 100:
        return False, None
    
    # 检测内容类型
    types = detect_content_type(text)
    
    # 如果有代码、配置、偏好、交付物、教训、技术文档，则保存
    save_types = ["code", "config", "preference", "deliverable", "lesson", "project_tech"]
    should = any(t in types for t in save_types)
    
    return should, types

# 初始化
ensure_dirs()

if __name__ == "__main__":
    # 测试
    print("记忆自动保存系统已初始化")
    print(f"目录: {MEMORY_DIR}")
