#!/usr/bin/env python3
"""
邮件补发监控 - 检查今天是否收到邮件，如未收到则自动补发
"""

import json
import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path

def check_today_report_sent():
    """检查今天是否已发送报告"""
    # 检查报告文件是否存在
    reports_dir = Path(__file__).parent / "data" / "reports"
    today = datetime.now().strftime("%Y%m%d")
    
    report_file = reports_dir / f"report_{today}.md"
    deep_file = reports_dir / f"deep_analysis_{today}.md"
    
    has_report = report_file.exists()
    has_deep = deep_file.exists()
    
    return has_report, has_deep

def check_today_crawler_data():
    """检查今天是否有爬虫数据"""
    crawler_dir = Path(__file__).parent / "data" / "crawler"
    today = datetime.now().strftime("%Y%m%d")
    
    if not crawler_dir.exists():
        return False, 0
    
    today_files = list(crawler_dir.glob(f"crawler_{today}_*.json"))
    if not today_files:
        return False, 0
    
    # 读取数据量
    total_count = 0
    for f in today_files:
        try:
            with open(f, 'r', encoding='utf-8') as file:
                data = json.load(file)
                total_count += len(data.get("data", []))
        except:
            pass
    
    return total_count >= 10, total_count

def main():
    print("=" * 60)
    print("邮件补发监控")
    print(f"时间: {datetime.now()}")
    print("=" * 60)
    
    today_str = datetime.now().strftime("%Y年%m月%d日")
    
    # 检查数据
    has_data, data_count = check_today_crawler_data()
    print(f"\n📊 爬虫数据: {'✓' if has_data else '✗'} ({data_count} 条)")
    
    if not has_data:
        print("⚠️ 数据不足，尝试补爬...")
        result = subprocess.run(
            ["python3", "crawler_v3.py"],
            capture_output=True,
            text=True,
            timeout=400
        )
        print(result.stdout[-1000:] if len(result.stdout) > 1000 else result.stdout)
    
    # 检查报告
    has_report, has_deep = check_today_report_sent()
    print(f"\n📄 报告文件:")
    print(f"   日报: {'✓ 已存在' if has_report else '✗ 不存在'}")
    print(f"   深度分析: {'✓ 已存在' if has_deep else '✗ 不存在'}")
    
    # 如果没报告，重新生成
    if not has_report:
        print("\n📤 补发日报...")
        subprocess.run(
            ["python3", "generate_report_enhanced.py"],
            capture_output=True,
            text=True,
            timeout=120
        )
    
    if not has_deep:
        print("\n📤 补发深度分析...")
        subprocess.run(
            ["python3", "generate_deep_analysis.py"],
            capture_output=True,
            text=True,
            timeout=120
        )
    
    # 发送邮件
    print("\n📧 发送邮件...")
    
    # 发送日报
    result1 = subprocess.run(
        ["python3", "send_email.py"],
        capture_output=True,
        text=True,
        timeout=60
    )
    if "成功" in result1.stdout:
        print("   ✅ 日报邮件发送成功")
    else:
        print(f"   ⚠️ 日报发送结果: {result1.stdout[-200:]}")
    
    # 发送深度分析
    result2 = subprocess.run(
        ["python3", "send_email.py", "--deep"],
        capture_output=True,
        text=True,
        timeout=60
    )
    if "成功" in result2.stdout:
        print("   ✅ 深度分析邮件发送成功")
    else:
        print(f"   ⚠️ 深度分析发送结果: {result2.stdout[-200:]}")
    
    print("\n✅ 补发监控完成")
    return 0

if __name__ == "__main__":
    exit(main())
