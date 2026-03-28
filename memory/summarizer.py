#!/usr/bin/env python3
"""
记忆摘要生成器 - L0/L1/L2 三层摘要系统
借鉴 OpenViking 的分层记忆加载思想
"""
import json
import re
from datetime import datetime
from pathlib import Path

WORKSPACE = Path("/root/.openclaw/workspace")
MEMORY_DIR = WORKSPACE / "memory"
INDEX_DIR = MEMORY_DIR / "index"

def ensure_dirs():
    """确保目录存在"""
    INDEX_DIR.mkdir(parents=True, exist_ok=True)

def extract_sections(content: str) -> list:
    """提取文档的章节结构"""
    sections = []
    lines = content.split('\n')
    current_section = None
    
    for line in lines:
        if line.startswith('# '):
            # 一级标题
            if current_section:
                sections.append(current_section)
            current_section = {'level': 1, 'title': line[2:], 'content': []}
        elif line.startswith('## '):
            # 二级标题
            if current_section:
                sections.append(current_section)
            current_section = {'level': 2, 'title': line[3:], 'content': []}
        elif current_section:
            current_section['content'].append(line)
    
    if current_section:
        sections.append(current_section)
    
    return sections

def generate_l0_summary(file_path: Path, content: str) -> str:
    """
    生成 L0 层摘要 - 一句话概括 (约 100 tokens)
    用于快速判断这条记忆是否与当前问题相关
    """
    # 优先提取文档标题和第一行非空内容
    lines = [l.strip() for l in content.split('\n') if l.strip()]
    
    # 找标题
    title = ""
    for line in lines[:5]:
        if line.startswith('# '):
            title = line[2:]
            break
        elif line.startswith('## '):
            title = line[3:]
            break
    
    # 找核心内容（第一条记录或第一段话）
    core_content = ""
    for line in lines:
        if line and not line.startswith('#') and not line.startswith('---'):
            # 去除markdown标记
            clean = re.sub(r'\[.*?\]\(.*?\)', '', line)  # 移除链接
            clean = re.sub(r'[*_`]', '', clean)  # 移除格式标记
            if len(clean) > 20:  # 至少20个字符才算有效内容
                core_content = clean[:100]
                break
    
    # 组合 L0 摘要
    if title and core_content:
        return f"[{file_path.stem}] {title}: {core_content}"
    elif title:
        return f"[{file_path.stem}] {title}"
    else:
        return f"[{file_path.stem}] {core_content[:80] if core_content else '无摘要'}"

def generate_l1_summary(file_path: Path, content: str) -> dict:
    """
    生成 L1 层摘要 - 核心信息和适用场景 (约 2000 tokens)
    供 AI 在规划阶段做决策
    """
    sections = extract_sections(content)
    
    l1_summary = {
        "file": str(file_path.relative_to(WORKSPACE)),
        "title": "",
        "one_liner": generate_l0_summary(file_path, content),
        "sections": [],
        "key_points": [],
        "updated": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
    }
    
    # 提取所有二级标题作为章节
    for section in sections:
        if section['level'] == 1:
            l1_summary["title"] = section['title']
        elif section['level'] == 2:
            section_summary = {
                "title": section['title'],
                "preview": ' '.join(section['content'])[:200]  # 每节预览200字符
            }
            l1_summary["sections"].append(section_summary)
            
            # 提取关键信息（列表项、重点标记等）
            for line in section['content']:
                if line.strip().startswith('- ') or line.strip().startswith('* '):
                    clean = re.sub(r'^[*-]\s*', '', line.strip())
                    if len(clean) > 10:
                        l1_summary["key_points"].append(clean[:150])
                elif '**' in line:
                    # 加粗内容通常是要点
                    matches = re.findall(r'\*\*(.*?)\*\*', line)
                    l1_summary["key_points"].extend(matches)
    
    # 限制 key_points 数量
    l1_summary["key_points"] = l1_summary["key_points"][:10]
    
    return l1_summary

def build_memory_index():
    """
    构建全量记忆索引
    每天运行一次，为所有记忆文件生成 L0/L1 摘要
    """
    ensure_dirs()
    
    index = {
        "generated_at": datetime.now().isoformat(),
        "l0_index": [],  # 快速判断层
        "l1_index": {},  # 概览层
        "files_count": 0
    }
    
    # 扫描所有记忆文件
    memory_files = []
    
    # 1. 每日日志
    for f in MEMORY_DIR.glob("2026-*.md"):
        if f.is_file():
            memory_files.append(("daily", f))
    
    # 2. 项目文档
    for f in (MEMORY_DIR / "system").glob("*.md"):
        memory_files.append(("project", f))
    
    # 3. 经验教训
    for f in (MEMORY_DIR / "lessons").glob("*.md"):
        memory_files.append(("lesson", f))
    
    # 4. 自动归档
    for f in (MEMORY_DIR / "auto").glob("*_auto.md"):
        memory_files.append(("archive", f))
    
    print(f"扫描到 {len(memory_files)} 个记忆文件")
    
    # 生成摘要
    for mem_type, file_path in memory_files:
        try:
            content = file_path.read_text(encoding='utf-8')
            if len(content) < 50:  # 跳过太短的文件
                continue
            
            # L0 摘要 - 一句话
            l0 = generate_l0_summary(file_path, content)
            index["l0_index"].append({
                "type": mem_type,
                "file": str(file_path.relative_to(WORKSPACE)),
                "summary": l0
            })
            
            # L1 摘要 - 详细概览
            l1 = generate_l1_summary(file_path, content)
            l1["type"] = mem_type
            index["l1_index"][str(file_path.relative_to(WORKSPACE))] = l1
            
        except Exception as e:
            print(f"  处理失败 {file_path}: {e}")
            continue
    
    index["files_count"] = len(index["l0_index"])
    
    # 保存索引
    index_file = INDEX_DIR / "memory_index.json"
    with open(index_file, 'w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    
    print(f"索引已保存: {index_file}")
    print(f"总计: {index['files_count']} 个文件")
    
    return index

def quick_search(query: str, top_k: int = 5) -> list:
    """
    基于 L0 摘要的快速搜索
    用于第一阶段：快速判断哪些记忆可能相关
    """
    index_file = INDEX_DIR / "memory_index.json"
    if not index_file.exists():
        print("索引不存在，先构建索引...")
        build_memory_index()
    
    with open(index_file, 'r', encoding='utf-8') as f:
        index = json.load(f)
    
    # 简单的关键词匹配（可以升级为向量相似度）
    query_lower = query.lower()
    query_words = set(query_lower.split())
    
    matches = []
    for item in index["l0_index"]:
        summary_lower = item["summary"].lower()
        # 计算匹配度
        match_score = sum(1 for word in query_words if word in summary_lower)
        if match_score > 0:
            matches.append({
                **item,
                "score": match_score
            })
    
    # 排序返回前 K 个
    matches.sort(key=lambda x: x["score"], reverse=True)
    return matches[:top_k]

def get_l1_detail(file_path: str) -> dict:
    """
    获取 L1 层详细摘要
    用于第二阶段：确认相关后加载详细信息
    """
    index_file = INDEX_DIR / "memory_index.json"
    if not index_file.exists():
        return None
    
    with open(index_file, 'r', encoding='utf-8') as f:
        index = json.load(f)
    
    return index["l1_index"].get(file_path)

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "search":
        # 测试搜索
        query = sys.argv[2] if len(sys.argv) > 2 else "储能"
        print(f"搜索: {query}")
        results = quick_search(query)
        for r in results:
            print(f"  [{r['score']}] {r['summary'][:80]}...")
    else:
        # 构建索引
        build_memory_index()
