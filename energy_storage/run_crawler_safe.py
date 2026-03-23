#!/usr/bin/env python3
"""
爬虫任务包装器 - 确保稳定执行
"""
import subprocess
import sys
from datetime import datetime
from pathlib import Path

def main():
    # 执行爬虫
    result = subprocess.run(
        ["python3", "crawler_multi_v2.py"],
        cwd="/root/.openclaw/workspace/energy_storage",
        capture_output=True,
        text=True,
        timeout=300
    )
    
    # 检查结果
    crawler_dir = Path("/root/.openclaw/workspace/energy_storage/data/crawler")
    json_files = list(crawler_dir.glob("*.json")) if crawler_dir.exists() else []
    
    # 输出摘要
    print("=== 爬虫执行结果 ===")
    print(f"返回码: {result.returncode}")
    print(f"数据文件数: {len(json_files)}")
    
    if json_files:
        latest = sorted(json_files, key=lambda x: x.stat().st_mtime, reverse=True)[:3]
        print("\n最新3个文件:")
        for f in latest:
            size_mb = f.stat().st_size / (1024*1024)
            print(f"  - {f.name}: {size_mb:.2f} MB")
    
    if result.stdout:
        print(f"\n输出:\n{result.stdout[:500]}")
    if result.stderr:
        print(f"\n错误:\n{result.stderr[:500]}")
    
    return result.returncode

if __name__ == "__main__":
    sys.exit(main())
