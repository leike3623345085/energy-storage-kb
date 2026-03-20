#!/usr/bin/env python3
"""
储能报告向量知识库
基于文本向量化的语义检索系统
"""

import json
import os
import re
import hashlib
import math
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Optional

# 配置
DATA_DIR = Path(__file__).parent.parent / "data"
REPORTS_DIR = DATA_DIR / "reports"
VECTOR_DIR = Path(__file__).parent / "vector_db"
VECTOR_FILE = VECTOR_DIR / "vectors.json"
INDEX_FILE = VECTOR_DIR / "index.json"

def get_embedding(text: str) -> List[float]:
    """
    获取文本的向量嵌入
    使用简单的词频向量作为baseline，实际可替换为OpenAI/Kimi等API
    """
    # 简单的文本特征提取（基于词频和关键词权重）
    
    # 储能行业关键词词典（带权重）
    keywords = {
        # 核心技术
        "储能": 3.0, "电池": 2.5, "锂电池": 2.5, "磷酸铁锂": 2.5,
        "钠离子电池": 3.0, "钠电": 3.0, "固态电池": 3.0, "液流电池": 3.0,
        "全钒液流": 3.0, "压缩空气储能": 3.0, "飞轮储能": 3.0,
        "氢能": 2.5, "储能系统": 2.5,
        
        # 应用场景
        "新型电力系统": 3.0, "新能源并网": 3.0, "风光消纳": 3.0,
        "削峰填谷": 3.0, "调峰调频": 2.5, "独立储能": 2.5,
        "共享储能": 2.5, "虚拟电厂": 3.0, "VPP": 3.0,
        "源网荷储": 3.0, "微电网": 2.5, "车网互动": 2.5, "V2G": 2.5,
        
        # 设备与技术
        "PCS": 2.5, "储能变流器": 2.5, "逆变器": 2.0,
        "构网型储能": 3.0, "grid-forming": 3.0, "高压直挂": 2.5,
        "BMS": 2.0, "EMS": 2.0, "电池管理系统": 2.0,
        
        # 安全与标准
        "储能消防": 3.0, "pack级消防": 3.0, "电池热失控": 3.0,
        "全氟己酮": 2.5, "储能安全": 2.5,
        
        # 政策与市场
        "储能政策": 2.5, "储能标准": 2.5, "储能调度": 2.5,
        "电力现货市场": 3.0, "容量电价": 2.5, "辅助服务": 2.5,
        "容量租赁": 2.5, "电力交易": 2.0,
        
        # 企业
        "宁德时代": 2.0, "比亚迪": 2.0, "亿纬锂能": 2.0,
        "阳光电源": 2.0, "特斯拉": 2.0, "Fluence": 2.0,
    }
    
    # 分词并统计
    text = text.lower()
    vector_dim = 512
    vector = [0.0] * vector_dim
    
    # 基于关键词匹配构建向量
    idx = 0
    for keyword, weight in keywords.items():
        count = text.count(keyword.lower())
        if count > 0:
            vector[idx % vector_dim] += count * weight
        idx += 1
    
    # 添加n-gram特征
    words = re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z]+', text)
    for i, word in enumerate(words[:100]):  # 限制长度
        hash_val = int(hashlib.md5(word.encode()).hexdigest(), 16)
        vector[hash_val % vector_dim] += 1
    
    # 归一化
    norm = math.sqrt(sum(x * x for x in vector))
    if norm > 0:
        vector = [x / norm for x in vector]
    
    return vector

def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """计算余弦相似度"""
    dot_product = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot_product / (norm1 * norm2)

class VectorKnowledgeBase:
    """向量知识库"""
    
    def __init__(self):
        VECTOR_DIR.mkdir(parents=True, exist_ok=True)
        self.vectors = self._load_vectors()
        self.index = self._load_index()
    
    def _load_vectors(self) -> Dict[str, List[float]]:
        """加载向量数据"""
        if VECTOR_FILE.exists():
            with open(VECTOR_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}
    
    def _load_index(self) -> List[Dict]:
        """加载索引"""
        if INDEX_FILE.exists():
            with open(INDEX_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return []
    
    def _save(self):
        """保存数据"""
        with open(VECTOR_FILE, "w", encoding="utf-8") as f:
            json.dump(self.vectors, f, ensure_ascii=False)
        with open(INDEX_FILE, "w", encoding="utf-8") as f:
            json.dump(self.index, f, ensure_ascii=False, indent=2)
    
    def add_document(self, doc_id: str, title: str, content: str, 
                     doc_type: str = "report", date: str = None) -> bool:
        """
        添加文档到知识库
        
        Args:
            doc_id: 文档唯一ID
            title: 文档标题
            content: 文档内容
            doc_type: 文档类型 (report/analysis/weekly)
            date: 日期 (YYYYMMDD)
        """
        try:
            # 分块处理（长文档切分）
            chunks = self._split_content(content, chunk_size=500, overlap=100)
            
            for i, chunk in enumerate(chunks):
                chunk_id = f"{doc_id}_chunk_{i}"
                vector = get_embedding(chunk)
                
                self.vectors[chunk_id] = vector
                self.index.append({
                    "chunk_id": chunk_id,
                    "doc_id": doc_id,
                    "title": title,
                    "content": chunk,
                    "type": doc_type,
                    "date": date or datetime.now().strftime("%Y%m%d"),
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                })
            
            self._save()
            return True
        except Exception as e:
            print(f"❌ 添加文档失败: {e}")
            return False
    
    def _split_content(self, content: str, chunk_size: int = 500, 
                       overlap: int = 100) -> List[str]:
        """
        将长文本切分为小块
        保持段落完整性
        """
        # 按段落分割
        paragraphs = content.split('\n')
        chunks = []
        current_chunk = ""
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            # 如果当前段落加入后超过chunk_size，先保存当前chunk
            if len(current_chunk) + len(para) > chunk_size and current_chunk:
                chunks.append(current_chunk.strip())
                # 保留overlap部分
                words = current_chunk.split()
                overlap_text = ' '.join(words[-overlap//10:]) if len(words) > overlap//10 else current_chunk
                current_chunk = overlap_text + "\n" + para
            else:
                current_chunk += "\n" + para if current_chunk else para
        
        # 添加最后一个chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        # 如果内容很短，直接作为一个chunk
        if not chunks and content.strip():
            chunks = [content.strip()]
        
        return chunks
    
    def search(self, query: str, top_k: int = 5, 
               date_filter: str = None) -> List[Dict]:
        """
        语义搜索
        
        Args:
            query: 查询语句
            top_k: 返回结果数量
            date_filter: 日期过滤 (YYYYMMDD)
        
        Returns:
            匹配的结果列表
        """
        if not self.vectors:
            return []
        
        # 获取查询向量
        query_vector = get_embedding(query)
        
        # 计算相似度
        similarities = []
        for item in self.index:
            # 日期过滤
            if date_filter and item.get("date") != date_filter:
                continue
            
            chunk_id = item["chunk_id"]
            if chunk_id in self.vectors:
                sim = cosine_similarity(query_vector, self.vectors[chunk_id])
                similarities.append((sim, item))
        
        # 排序并返回top_k
        similarities.sort(key=lambda x: x[0], reverse=True)
        
        results = []
        for sim, item in similarities[:top_k]:
            result = item.copy()
            result["similarity"] = round(sim, 4)
            results.append(result)
        
        return results
    
    def query(self, question: str, context_chunks: int = 3) -> Dict:
        """
        智能问答
        
        1. 搜索相关内容
        2. 组合上下文
        3. 返回答案结构
        """
        # 搜索相关内容
        results = self.search(question, top_k=context_chunks)
        
        if not results:
            return {
                "answer": "未找到相关内容",
                "sources": [],
                "confidence": 0,
            }
        
        # 组合上下文
        context = []
        sources = []
        total_similarity = 0
        
        for r in results:
            context.append(f"[{r['title']}] {r['content']}")
            sources.append({
                "title": r['title'],
                "date": r['date'],
                "type": r['type'],
                "relevance": r['similarity'],
            })
            total_similarity += r['similarity']
        
        avg_similarity = total_similarity / len(results)
        
        return {
            "context": "\n\n".join(context),
            "sources": sources,
            "confidence": round(avg_similarity, 4),
            "question": question,
        }
    
    def index_report_file(self, report_file: Path) -> bool:
        """索引单个报告文件"""
        if not report_file.exists():
            return False
        
        try:
            with open(report_file, "r", encoding="utf-8") as f:
                content = f.read()
            
            # 解析文件名获取信息
            filename = report_file.stem
            
            if filename.startswith("report_"):
                doc_type = "日报"
                date = filename.replace("report_", "")
                title = f"储能行业日报_{date}"
            elif filename.startswith("deep_analysis_"):
                doc_type = "深度分析"
                date = filename.replace("deep_analysis_", "")
                title = f"储能行业深度分析_{date}"
            elif filename.startswith("weekly_report_"):
                doc_type = "周报"
                date = filename.replace("weekly_report_", "")
                title = f"储能行业周报_{date}"
            else:
                doc_type = "报告"
                date = datetime.now().strftime("%Y%m%d")
                title = filename
            
            doc_id = filename
            
            # 检查是否已索引
            existing = [i for i in self.index if i["doc_id"] == doc_id]
            if existing:
                print(f"⏭️ 已索引: {filename}")
                return True
            
            print(f"📄 索引中: {filename}")
            return self.add_document(doc_id, title, content, doc_type, date)
            
        except Exception as e:
            print(f"❌ 索引失败 {report_file}: {e}")
            return False
    
    def index_all_reports(self, days: int = 30) -> Tuple[int, int]:
        """
        索引最近N天的所有报告
        
        Returns:
            (成功数, 总数)
        """
        from datetime import timedelta
        success = 0
        total = 0
        
        for i in range(days):
            date = datetime.now() - timedelta(days=i)
            date_str = date.strftime("%Y%m%d")
            
            files = [
                REPORTS_DIR / f"report_{date_str}.md",
                REPORTS_DIR / f"deep_analysis_{date_str}.md",
                REPORTS_DIR / f"weekly_report_{date_str}.md",
            ]
            
            for f in files:
                if f.exists():
                    total += 1
                    if self.index_report_file(f):
                        success += 1
        
        return success, total
    
    def get_stats(self) -> Dict:
        """获取知识库统计"""
        return {
            "total_vectors": len(self.vectors),
            "total_chunks": len(self.index),
            "unique_documents": len(set(i["doc_id"] for i in self.index)),
            "date_range": {
                "earliest": min((i["date"] for i in self.index), default=None),
                "latest": max((i["date"] for i in self.index), default=None),
            } if self.index else None,
        }

def main():
    """CLI入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="向量知识库管理")
    parser.add_argument("--index-file", metavar="PATH",
                        help="索引单个报告文件")
    parser.add_argument("--index-all", action="store_true",
                        help="索引所有历史报告")
    parser.add_argument("--search", metavar="QUERY",
                        help="搜索查询")
    parser.add_argument("--query", metavar="QUESTION",
                        help="智能问答")
    parser.add_argument("--top-k", type=int, default=5,
                        help="返回结果数量")
    parser.add_argument("--stats", action="store_true",
                        help="查看统计信息")
    
    args = parser.parse_args()
    
    kb = VectorKnowledgeBase()
    
    if args.stats:
        stats = kb.get_stats()
        print("\n📊 向量知识库统计")
        print("=" * 40)
        print(f"向量总数: {stats['total_vectors']}")
        print(f"文本块数: {stats['total_chunks']}")
        print(f"文档数量: {stats['unique_documents']}")
        if stats['date_range']:
            print(f"日期范围: {stats['date_range']['earliest']} ~ {stats['date_range']['latest']}")
        return 0
    
    if args.index_file:
        success = kb.index_report_file(Path(args.index_file))
        print(f"\n{'✅ 成功' if success else '❌ 失败'}")
        return 0 if success else 1
    
    if args.index_all:
        print("🔄 开始索引历史报告...")
        success, total = kb.index_all_reports()
        print(f"\n📊 索引完成: {success}/{total}")
        return 0
    
    if args.search:
        results = kb.search(args.search, top_k=args.top_k)
        print(f"\n🔍 搜索: {args.search}")
        print("=" * 60)
        for i, r in enumerate(results, 1):
            print(f"\n[{i}] {r['title']} (相关度: {r['similarity']})")
            print(f"日期: {r['date']} | 类型: {r['type']}")
            print(f"内容: {r['content'][:200]}...")
        return 0
    
    if args.query:
        result = kb.query(args.query)
        print(f"\n❓ 问题: {result['question']}")
        print(f"置信度: {result['confidence']}")
        print("=" * 60)
        print("\n📄 相关内容:\n")
        print(result['context'])
        print("\n📚 信息来源:")
        for s in result['sources']:
            print(f"  - {s['title']} ({s['date']}, 相关度{s['relevance']})")
        return 0
    
    # 默认显示统计
    stats = kb.get_stats()
    print("\n📊 向量知识库")
    print("=" * 40)
    print(f"已索引文档: {stats['unique_documents']} 份")
    print(f"文本块数: {stats['total_chunks']} 个")
    print("\n使用 --help 查看可用命令")
    return 0

if __name__ == "__main__":
    exit(main())
