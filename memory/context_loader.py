#!/usr/bin/env python3
"""
会话启动记忆回顾系统 v2
整合 OpenViking 三层摘要思想 + 检索审计
"""
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path("/root/.openclaw/workspace/memory")))

# 导入新模块
from summarizer import quick_search, get_l1_detail, build_memory_index
from retrieval_audit import RetrievalAuditor, log_retrieval

WORKSPACE = Path("/root/.openclaw/workspace")
MEMORY_DIR = WORKSPACE / "memory"

def get_recent_memories(days=7):
    """获取最近N天的记忆（保留兼容旧版）"""
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
    triggers = [
        "之前", "上次", "以前", "记得", "说过",
        "项目", "方案", "配置", "设置",
        "修复", "错误", "bug", "问题",
        "储能", "银行", "工作流", "爬虫"
    ]
    return any(t in user_input for t in triggers)

def smart_memory_search(query: str, user_context: str = None) -> dict:
    """
    智能记忆搜索 - 分层检索
    L0: 快速判断哪些记忆可能相关
    L1: 加载详细概览
    L2: 按需加载完整内容
    """
    with RetrievalAuditor(user_context or f"搜索: {query}") as auditor:
        
        # === L0 层: 快速筛选 ===
        l0_candidates = quick_search(query, top_k=5)
        
        if not l0_candidates:
            auditor.record([], query)
            return {"level": "L0", "candidates": [], "message": "未找到相关记忆"}
        
        # === L1 层: 加载详细概览 ===
        l1_details = []
        for candidate in l0_candidates:
            file_path = candidate["file"]
            l1 = get_l1_detail(file_path)
            if l1:
                l1_details.append({
                    "l0_score": candidate["score"],
                    **l1
                })
        
        # 记录审计日志
        audit_results = [{"path": c["file"], "score": c["score"]} for c in l0_candidates]
        retrieval_id = auditor.record(audit_results, query)
        
        return {
            "level": "L1",
            "retrieval_id": retrieval_id,  # 可用于追溯
            "query": query,
            "candidate_count": len(l0_candidates),
            "candidates": l1_details
        }

def get_relevant_context(user_input):
    """根据用户输入获取相关上下文 - 新版分层检索"""
    keywords = []
    
    if "储能" in user_input:
        keywords.append("energy-storage")
    if "银行" in user_input or "工作流" in user_input:
        keywords.append("bank-workflow")
    if "修复" in user_input or "错误" in user_input:
        keywords.append("lessons")
    
    # 如果有关键词，使用智能搜索
    if keywords:
        primary_keyword = keywords[0]
        search_result = smart_memory_search(primary_keyword, user_input)
        return {
            "keywords": keywords,
            "search_result": search_result
        }
    
    return {"keywords": keywords}

def print_context_summary():
    """打印上下文摘要（用于会话启动）"""
    print("=" * 50)
    print("📋 会话记忆摘要")
    print("=" * 50)
    
    # 1. 传统摘要
    memories = get_recent_memories()
    summary = generate_context_summary(memories)
    print(summary)
    
    # 2. L0 索引摘要（如果存在）
    index_file = MEMORY_DIR / "index" / "memory_index.json"
    if index_file.exists():
        with open(index_file, 'r', encoding='utf-8') as f:
            index = json.load(f)
        print(f"\n📚 记忆索引: {index.get('files_count', 0)} 个文件")
        print(f"   最后更新: {index.get('generated_at', 'unknown')[:10]}")
    
    print("=" * 50)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="记忆上下文加载器")
    parser.add_argument("--search", "-s", help="搜索关键词")
    parser.add_argument("--build-index", "-b", action="store_true", help="构建记忆索引")
    parser.add_argument("--test", "-t", action="store_true", help="测试模式")
    
    args = parser.parse_args()
    
    if args.build_index:
        print("构建记忆索引...")
        build_memory_index()
    elif args.search:
        print(f"智能搜索: {args.search}")
        result = smart_memory_search(args.search)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.test:
        print("测试检索审计...")
        with RetrievalAuditor("测试检索") as auditor:
            test_results = [{"path": "test.md", "score": 0.9}]
            rid = auditor.record(test_results, "测试查询")
            print(f"检索ID: {rid}")
    else:
        print_context_summary()
