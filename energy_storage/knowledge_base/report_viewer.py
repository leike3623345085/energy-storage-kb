#!/usr/bin/env python3
"""
储能报告查看与导出工具
方便查看历史报告和导出到不同格式
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

REPORTS_DIR = Path(__file__).parent.parent / "data" / "reports"

def list_reports(date_str: Optional[str] = None) -> List[dict]:
    """列出报告文件"""
    reports = []
    
    if date_str:
        # 查找指定日期的报告
        patterns = [
            (f"report_{date_str}.md", "日报"),
            (f"deep_analysis_{date_str}.md", "深度分析"),
            (f"weekly_report_{date_str}.md", "周报"),
        ]
        for pattern, rtype in patterns:
            fpath = REPORTS_DIR / pattern
            if fpath.exists():
                size = fpath.stat().st_size
                mtime = datetime.fromtimestamp(fpath.stat().st_mtime)
                reports.append({
                    "file": pattern,
                    "type": rtype,
                    "path": str(fpath),
                    "size_kb": round(size / 1024, 1),
                    "modified": mtime.strftime("%Y-%m-%d %H:%M"),
                })
    else:
        # 列出最近30天的所有报告
        for i in range(30):
            date = datetime.now() - timedelta(days=i)
            date_str = date.strftime("%Y%m%d")
            
            patterns = [
                (f"report_{date_str}.md", "日报"),
                (f"deep_analysis_{date_str}.md", "深度分析"),
                (f"weekly_report_{date_str}.md", "周报"),
            ]
            for pattern, rtype in patterns:
                fpath = REPORTS_DIR / pattern
                if fpath.exists():
                    size = fpath.stat().st_size
                    mtime = datetime.fromtimestamp(fpath.stat().st_mtime)
                    reports.append({
                        "file": pattern,
                        "type": rtype,
                        "path": str(fpath),
                        "size_kb": round(size / 1024, 1),
                        "modified": mtime.strftime("%Y-%m-%d %H:%M"),
                        "date": date_str,
                    })
    
    return reports

def show_report_content(file_path: str, lines: int = 50):
    """显示报告内容"""
    path = Path(file_path)
    if not path.exists():
        print(f"❌ 文件不存在: {file_path}")
        return
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        
        all_lines = content.split("\n")
        print(f"\n📄 {path.name} ({len(all_lines)} 行)")
        print("=" * 60)
        
        for line in all_lines[:lines]:
            print(line)
        
        if len(all_lines) > lines:
            print(f"\n... 还有 {len(all_lines) - lines} 行 ...")
        
        print("=" * 60)
    except Exception as e:
        print(f"❌ 读取失败: {e}")

def export_to_json(date_str: Optional[str] = None, output_dir: str = "./exports"):
    """导出报告为JSON格式（便于知识库导入）"""
    reports = list_reports(date_str)
    
    if not reports:
        print("❌ 未找到报告")
        return
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    exported = []
    for report in reports:
        try:
            with open(report["path"], "r", encoding="utf-8") as f:
                content = f.read()
            
            export_data = {
                "title": report["type"],
                "date": report.get("date", date_str or datetime.now().strftime("%Y%m%d")),
                "type": report["type"],
                "content": content,
                "metadata": {
                    "file": report["file"],
                    "size_kb": report["size_kb"],
                    "modified": report["modified"],
                }
            }
            
            filename = f"{report['type']}_{report.get('date', date_str)}.json"
            filepath = output_path / filename
            
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            exported.append(filepath)
            print(f"✅ 导出: {filepath}")
            
        except Exception as e:
            print(f"❌ 导出失败 {report['file']}: {e}")
    
    print(f"\n📊 导出完成: {len(exported)}/{len(reports)}")

def main():
    """主入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="储能报告查看与导出")
    parser.add_argument("--list", action="store_true",
                        help="列出最近报告")
    parser.add_argument("--date", 
                        help="指定日期 (YYYYMMDD)")
    parser.add_argument("--show", metavar="FILE",
                        help="显示报告内容")
    parser.add_argument("--lines", type=int, default=50,
                        help="显示行数（默认50）")
    parser.add_argument("--export-json", action="store_true",
                        help="导出为JSON格式")
    parser.add_argument("--output", default="./exports",
                        help="导出目录")
    
    args = parser.parse_args()
    
    if args.show:
        show_report_content(args.show, args.lines)
        return 0
    
    if args.list or not any([args.show, args.export_json]):
        reports = list_reports(args.date)
        if not reports:
            print("📭 未找到报告")
            return 0
        
        print(f"\n📊 找到 {len(reports)} 份报告")
        print("=" * 80)
        print(f"{'类型':<10} {'文件名':<35} {'大小':<10} {'修改时间':<20}")
        print("-" * 80)
        
        for r in reports:
            print(f"{r['type']:<10} {r['file']:<35} {r['size_kb']:<10}KB {r['modified']:<20}")
        
        print("=" * 80)
        print("\n查看内容: python3 report_viewer.py --show 文件路径")
        return 0
    
    if args.export_json:
        export_to_json(args.date, args.output)
        return 0
    
    return 0

if __name__ == "__main__":
    exit(main())
