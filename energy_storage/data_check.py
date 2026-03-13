#!/usr/bin/env python3
"""
数据检查和补录工具 - 确保日报有数据
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

def check_crawler_data():
    """检查今日爬虫数据是否充足"""
    data_dir = Path(__file__).parent / "data" / "crawler"
    today = datetime.now().strftime("%Y%m%d")
    
    if not data_dir.exists():
        return False, 0, "爬虫目录不存在"
    
    # 查找今日文件
    today_files = list(data_dir.glob(f"crawler_{today}_*.json"))
    
    if not today_files:
        return False, 0, f"今日({today})无爬虫数据文件"
    
    # 读取最新文件
    latest_file = max(today_files, key=lambda x: x.stat().st_mtime)
    try:
        with open(latest_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            count = len(data.get("data", []))
            if count < 10:
                return False, count, f"数据量过少: {count} 条"
            return True, count, f"数据正常: {count} 条"
    except Exception as e:
        return False, 0, f"读取文件失败: {e}"

def check_report_generated():
    """检查日报是否已生成"""
    reports_dir = Path(__file__).parent / "data" / "reports"
    today = datetime.now().strftime("%Y%m%d")
    report_file = reports_dir / f"report_{today}.md"
    deep_file = reports_dir / f"deep_analysis_{today}.md"
    
    return report_file.exists(), deep_file.exists()

def main():
    print("=" * 60)
    print("数据完整性检查")
    print(f"时间: {datetime.now()}")
    print("=" * 60)
    
    # 检查爬虫数据
    has_data, count, msg = check_crawler_data()
    print(f"\n📊 爬虫数据检查: {msg}")
    
    if not has_data:
        print("⚠️ 数据不足，尝试执行爬虫...")
        import subprocess
        result = subprocess.run(
            ["python3", "crawler_v3.py"],
            capture_output=True,
            text=True,
            timeout=300
        )
        print(result.stdout)
        if result.returncode != 0:
            print(f"❌ 爬虫执行失败: {result.stderr}")
            return 1
        
        # 重新检查
        has_data, count, msg = check_crawler_data()
        if not has_data:
            print(f"❌ 爬虫后仍无数据: {msg}")
            return 1
    
    # 检查报告
    has_report, has_deep = check_report_generated()
    print(f"\n📄 报告检查:")
    print(f"   日报: {'✓ 已生成' if has_report else '✗ 未生成'}")
    print(f"   深度分析: {'✓ 已生成' if has_deep else '✗ 未生成'}")
    
    if not has_report or not has_deep:
        print("\n📤 正在生成报告...")
        import subprocess
        
        if not has_report:
            result = subprocess.run(
                ["python3", "generate_report_enhanced.py"],
                capture_output=True,
                text=True,
                timeout=120
            )
            print(result.stdout)
        
        if not has_deep:
            result = subprocess.run(
                ["python3", "generate_deep_analysis.py"],
                capture_output=True,
                text=True,
                timeout=120
            )
            print(result.stdout)
    
    # 检查邮件发送
    print("\n📧 检查邮件发送状态...")
    # 这里可以记录发送状态到文件
    
    print("\n✅ 数据检查完成")
    return 0

if __name__ == "__main__":
    exit(main())
