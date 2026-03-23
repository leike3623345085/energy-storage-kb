#!/usr/bin/env python3
"""
记忆保存触发器 - 在对话中检测并保存关键内容
"""
import sys
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
from auto_saver import (
    save_code_snippet, 
    update_user_preference, 
    update_memory_rule,
    save_lesson,
    save_project_tech,
    auto_archive_conversation,
    should_save
)

def extract_code_blocks(text):
    """提取代码块"""
    import re
    pattern = r"```(\w+)?\n(.*?)```"
    matches = re.findall(pattern, text, re.DOTALL)
    return [(lang if lang else "txt", code.strip()) for lang, code in matches]

def extract_preferences(text):
    """提取用户偏好"""
    import re
    # 匹配 "记住..." 或 "以后..." 或 "默认..."
    patterns = [
        r"(?:记住|记得|保存|设置|默认).*?(\w+).*?(?:为|是|用|使用|设置成|改成|改为)\s*[:：]?\s*(.+?)(?:[。！\n]|$)",
        r"(?:以后|下次|往后).*?(?:用|使用|采用|选择|选)\s*[:：]?\s*(.+?)(?:[。！\n]|$)",
    ]
    
    preferences = []
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        preferences.extend(matches)
    
    return preferences

def main():
    """主函数 - 分析对话内容并保存"""
    # 读取输入（从stdin或文件）
    if len(sys.argv) > 1:
        text = sys.argv[1]
    else:
        text = sys.stdin.read()
    
    if not text:
        print(json.dumps({"saved": False, "reason": "no content"}))
        return
    
    results = {
        "saved": False,
        "actions": []
    }
    
    # 1. 检测并保存代码块
    code_blocks = extract_code_blocks(text)
    for lang, code in code_blocks:
        if len(code) > 50:  # 只保存有意义的代码
            filepath = save_code_snippet(code, f"Language: {lang}")
            results["actions"].append({"type": "code", "path": filepath})
            results["saved"] = True
    
    # 2. 检测并保存用户偏好
    preferences = extract_preferences(text)
    for pref in preferences:
        if isinstance(pref, tuple) and len(pref) == 2:
            key, value = pref
            filepath = update_user_preference(key, value)
            results["actions"].append({"type": "preference", "key": key, "path": filepath})
            results["saved"] = True
    
    # 3. 检测是否应该整体归档
    should, types = should_save(text)
    if should and len(text) > 500:
        summary = text[:300] + "..." if len(text) > 300 else text
        filepath = auto_archive_conversation(summary)
        results["actions"].append({"type": "archive", "types": types, "path": filepath})
        results["saved"] = True
    
    # 输出结果
    print(json.dumps(results, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
