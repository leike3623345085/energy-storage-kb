#!/usr/bin/env python3
"""
检索审计系统 - 记录每次 memory_search 的轨迹
借鉴 OpenViking 的"检索过程全程可见"思想
"""
import json
import uuid
from datetime import datetime
from pathlib import Path

WORKSPACE = Path("/root/.openclaw/workspace")
AUDIT_LOG = WORKSPACE / "memory" / "retrieval_audit.jsonl"

def log_retrieval(query: str, results: list, context: dict = None) -> str:
    """
    记录一次检索操作
    
    Args:
        query: 搜索关键词
        results: 搜索结果列表
        context: 额外上下文（如用户输入、触发原因等）
    
    Returns:
        retrieval_id: 本次检索的唯一ID，可用于追溯
    """
    retrieval_id = str(uuid.uuid4())[:8]
    
    audit_entry = {
        "id": retrieval_id,
        "timestamp": datetime.now().isoformat(),
        "query": query,
        "result_count": len(results),
        "results": []
    }
    
    # 记录结果摘要（不存完整内容，只存引用）
    for result in results:
        audit_entry["results"].append({
            "path": result.get("path", "unknown"),
            "score": result.get("score", 0),
            "lines": f"{result.get('startLine', 0)}-{result.get('endLine', 0)}",
            "preview": result.get("snippet", "")[:100]  # 只存前100字符
        })
    
    if context:
        audit_entry["context"] = context
    
    # 追加写入日志
    with open(AUDIT_LOG, 'a', encoding='utf-8') as f:
        f.write(json.dumps(audit_entry, ensure_ascii=False) + '\n')
    
    return retrieval_id

def get_retrieval_trace(retrieval_id: str) -> dict:
    """
    根据ID获取某次检索的完整轨迹
    用于"出了问题直接回放检索轨迹"
    """
    if not AUDIT_LOG.exists():
        return None
    
    with open(AUDIT_LOG, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                entry = json.loads(line.strip())
                if entry.get("id") == retrieval_id:
                    return entry
            except:
                continue
    
    return None

def get_recent_retrievals(n: int = 10) -> list:
    """获取最近 N 次检索记录"""
    if not AUDIT_LOG.exists():
        return []
    
    entries = []
    with open(AUDIT_LOG, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                entry = json.loads(line.strip())
                entries.append(entry)
            except:
                continue
    
    # 返回最近的 N 条
    return entries[-n:]

def analyze_retrieval_patterns() -> dict:
    """
    分析检索模式
    发现哪些记忆经常被检索、哪些检索结果不好
    """
    if not AUDIT_LOG.exists():
        return {}
    
    stats = {
        "total_retrievals": 0,
        "unique_queries": set(),
        "most_accessed_files": {},
        "zero_result_queries": []
    }
    
    with open(AUDIT_LOG, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                entry = json.loads(line.strip())
                stats["total_retrievals"] += 1
                stats["unique_queries"].add(entry.get("query", ""))
                
                # 统计文件访问频率
                for result in entry.get("results", []):
                    path = result.get("path", "unknown")
                    stats["most_accessed_files"][path] = \
                        stats["most_accessed_files"].get(path, 0) + 1
                
                # 记录无结果查询
                if entry.get("result_count", 0) == 0:
                    stats["zero_result_queries"].append({
                        "query": entry.get("query"),
                        "time": entry.get("timestamp")
                    })
                    
            except:
                continue
    
    # 转换为可序列化的格式
    stats["unique_queries"] = len(stats["unique_queries"])
    stats["most_accessed_files"] = sorted(
        stats["most_accessed_files"].items(),
        key=lambda x: x[1],
        reverse=True
    )[:10]
    
    return stats

# 上下文管理器，用于自动记录检索
class RetrievalAuditor:
    """
    检索审计上下文管理器
    用法:
        with RetrievalAuditor("用户询问储能配置") as auditor:
            results = memory_search("储能配置")
            auditor.record(results)
    """
    def __init__(self, context: str = None):
        self.context = context
        self.retrieval_id = None
        self.start_time = None
    
    def __enter__(self):
        self.start_time = datetime.now()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # 退出时如果发生异常也记录
        if exc_type:
            self._log_error(exc_val)
    
    def record(self, results: list, query: str = None):
        """记录检索结果"""
        context = {
            "description": self.context,
            "duration_ms": (datetime.now() - self.start_time).total_seconds() * 1000
        }
        self.retrieval_id = log_retrieval(query or self.context, results, context)
        return self.retrieval_id
    
    def _log_error(self, error):
        """记录检索过程中的错误"""
        audit_entry = {
            "id": str(uuid.uuid4())[:8],
            "timestamp": datetime.now().isoformat(),
            "error": str(error),
            "context": self.context
        }
        with open(AUDIT_LOG, 'a', encoding='utf-8') as f:
            f.write(json.dumps(audit_entry, ensure_ascii=False) + '\n')

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "stats":
            stats = analyze_retrieval_patterns()
            print(json.dumps(stats, ensure_ascii=False, indent=2))
        elif cmd == "recent":
            n = int(sys.argv[2]) if len(sys.argv) > 2 else 5
            recent = get_recent_retrievals(n)
            for r in recent:
                print(f"[{r['id']}] {r['timestamp']} - '{r['query']}' -> {r['result_count']} results")
        elif cmd == "trace" and len(sys.argv) > 2:
            trace = get_retrieval_trace(sys.argv[2])
            if trace:
                print(json.dumps(trace, ensure_ascii=False, indent=2))
            else:
                print(f"未找到检索ID: {sys.argv[2]}")
    else:
        print("用法:")
        print("  python3 retrieval_audit.py stats      # 统计检索模式")
        print("  python3 retrieval_audit.py recent [n] # 最近N次检索")
        print("  python3 retrieval_audit.py trace <id>  # 查看具体检索轨迹")
