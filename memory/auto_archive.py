#!/usr/bin/env python3
"""
自动归档脚本 - 每6小时运行一次
整理并保存重要对话内容
"""
import json
from datetime import datetime
from pathlib import Path

WORKSPACE = Path("/root/.openclaw/workspace")
MEMORY_DIR = WORKSPACE / "memory"
AUTO_DIR = MEMORY_DIR / "auto"

def get_session_files():
    """获取最近的会话文件（简化版，实际可能需要更复杂的逻辑）"""
    sessions_dir = Path("/root/.openclaw/agents/main/sessions")
    if not sessions_dir.exists():
        return []
    
    # 获取最近6小时内的文件
    now = datetime.now().timestamp()
    six_hours_ago = now - 6 * 3600
    
    recent_files = []
    for f in sessions_dir.glob("*.jsonl"):
        if f.stat().st_mtime > six_hours_ago:
            recent_files.append(f)
    
    return sorted(recent_files, key=lambda x: x.stat().st_mtime, reverse=True)[:5]

def analyze_conversation(filepath):
    """分析对话内容，提取关键信息"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        summary = {
            "topics": [],
            "deliverables": [],
            "decisions": [],
            "files_created": []
        }
        
        for line in lines[-50:]:  # 只看最后50行
            try:
                msg = json.loads(line.strip())
                content = str(msg.get("content", ""))
                
                # 检测主题
                if any(kw in content for kw in ["工作流", "配置", "模板", "方案"]):
                    summary["topics"].append("工作流设计")
                if any(kw in content for kw in ["报告", "文档", "生成"]):
                    summary["topics"].append("文档生成")
                if any(kw in content for kw in ["修复", "bug", "错误", "解决"]):
                    summary["topics"].append("问题修复")
                
                # 检测交付物
                if "已发送" in content and "邮件" in content:
                    summary["deliverables"].append("邮件发送")
                if ".docx" in content or ".md" in content or ".json" in content:
                    # 提取文件名
                    import re
                    files = re.findall(r'[\w\-/]+\.(?:docx|md|json|py)', content)
                    summary["files_created"].extend(files)
                
                # 检测决策
                if any(kw in content for kw in ["决定", "确定", "采用", "选择", "以后"]):
                    summary["decisions"].append(content[:100])
                    
            except json.JSONDecodeError:
                continue
        
        return summary
        
    except Exception as e:
        return {"error": str(e)}

def create_archive(summary):
    """创建归档记录"""
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M")
    
    archive_file = AUTO_DIR / f"{date_str}_auto.md"
    
    content = f"""\n## 自动归档 - {time_str}\n\n"""
    
    if summary.get("topics"):
        content += "**讨论主题**: " + ", ".join(set(summary["topics"])) + "\n\n"
    
    if summary.get("deliverables"):
        content += "**交付物**: " + ", ".join(set(summary["deliverables"])) + "\n\n"
    
    if summary.get("files_created"):
        content += "**创建文件**:\n"
        for f in set(summary["files_created"][:10]):  # 最多10个
            content += f"- `{f}`\n"
        content += "\n"
    
    if summary.get("decisions"):
        content += "**关键决策**:\n"
        for d in summary["decisions"][:3]:  # 最多3个
            content += f"- {d}\n"
        content += "\n"
    
    # 追加到文件
    if archive_file.exists():
        existing = archive_file.read_text(encoding='utf-8')
    else:
        existing = f"# 自动归档 - {date_str}\n\n"
    
    existing += content
    archive_file.write_text(existing, encoding='utf-8')
    
    return str(archive_file)

def main():
    """主函数"""
    AUTO_DIR.mkdir(parents=True, exist_ok=True)
    
    # 获取最近的会话文件
    session_files = get_session_files()
    
    if not session_files:
        print(json.dumps({"status": "no_recent_sessions"}))
        return
    
    # 分析对话
    all_summaries = {
        "topics": [],
        "deliverables": [],
        "decisions": [],
        "files_created": []
    }
    
    for sf in session_files:
        summary = analyze_conversation(sf)
        for key in all_summaries:
            if key in summary:
                all_summaries[key].extend(summary[key])
    
    # 创建归档
    archive_path = create_archive(all_summaries)
    
    print(json.dumps({
        "status": "archived",
        "path": archive_path,
        "sessions_analyzed": len(session_files),
        "summary": {
            "topics": list(set(all_summaries["topics"])),
            "files_count": len(set(all_summaries["files_created"]))
        }
    }, ensure_ascii=False))

if __name__ == "__main__":
    main()
