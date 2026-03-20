#!/usr/bin/env python3
"""
储能报告自动同步到知识库
与报告生成流程集成，自动生成后自动归档
"""

import json
import sys
from datetime import datetime
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from knowledge_base.kb_manager import KnowledgeBaseManager

def auto_sync_after_report(report_type: str, date_str: str = None):
    """
    报告生成后自动同步
    
    Args:
        report_type: 报告类型 (daily/deep/weekly)
        date_str: 日期字符串，默认为今天
    """
    if date_str is None:
        date_str = datetime.now().strftime("%Y%m%d")
    
    kb = KnowledgeBaseManager()
    
    # 映射报告类型
    type_map = {
        "daily": ("日报", f"report_{date_str}.md"),
        "deep": ("深度分析", f"deep_analysis_{date_str}.md"),
        "weekly": ("周报", f"weekly_report_{date_str}.md"),
    }
    
    if report_type not in type_map:
        print(f"❌ 未知报告类型: {report_type}")
        return False
    
    report_name, filename = type_map[report_type]
    report_file = Path(__file__).parent.parent / "data" / "reports" / filename
    
    print(f"🔄 自动同步{report_name}: {filename}")
    
    return kb.sync_report(report_file, report_name)

def main():
    """主入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="报告自动同步")
    parser.add_argument("type", choices=["daily", "deep", "weekly"],
                        help="报告类型")
    parser.add_argument("--date", 
                        help="日期 (YYYYMMDD)")
    
    args = parser.parse_args()
    
    success = auto_sync_after_report(args.type, args.date)
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())
