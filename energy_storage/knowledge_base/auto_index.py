#!/usr/bin/env python3
"""
向量知识库自动索引钩子
报告生成后自动调用此脚本进行向量化索引
"""

import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
from vector_kb import VectorKnowledgeBase

def auto_index_report(report_type: str, date_str: str = None):
    """
    自动索引报告
    
    Args:
        report_type: 报告类型 (daily/deep/weekly)
        date_str: 日期字符串 (YYYYMMDD)，默认为今天
    """
    if date_str is None:
        date_str = datetime.now().strftime("%Y%m%d")
    
    # 映射文件路径
    type_map = {
        "daily": (f"report_{date_str}.md", "日报"),
        "deep": (f"deep_analysis_{date_str}.md", "深度分析"),
        "weekly": (f"weekly_report_{date_str}.md", "周报"),
    }
    
    if report_type not in type_map:
        print(f"❌ 未知报告类型: {report_type}")
        return False
    
    filename, type_name = type_map[report_type]
    report_file = Path(__file__).parent.parent / "data" / "reports" / filename
    
    if not report_file.exists():
        print(f"❌ 报告不存在: {report_file}")
        return False
    
    print(f"🔄 自动索引{type_name}: {filename}")
    
    kb = VectorKnowledgeBase()
    success = kb.index_report_file(report_file)
    
    if success:
        stats = kb.get_stats()
        print(f"✅ 索引完成！当前共 {stats['unique_documents']} 份文档，{stats['total_chunks']} 个文本块")
    else:
        print(f"❌ 索引失败")
    
    return success

def main():
    """主入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="向量知识库自动索引")
    parser.add_argument("type", choices=["daily", "deep", "weekly"],
                        help="报告类型")
    parser.add_argument("--date", 
                        help="日期 (YYYYMMDD)")
    
    args = parser.parse_args()
    
    success = auto_index_report(args.type, args.date)
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())
