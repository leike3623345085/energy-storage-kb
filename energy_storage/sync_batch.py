#!/usr/bin/env python3
"""分批同步历史数据到飞书"""

import json
from pathlib import Path
from sync_daemon import FeishuSync, load_state, save_state, DATA_DIR

def main():
    sync = FeishuSync()
    processed = load_state()
    
    # 扫描所有文件
    files = []
    
    reports_dir = DATA_DIR / "reports"
    if reports_dir.exists():
        for f in reports_dir.glob("*.md"):
            files.append(("report", f))
    
    crawler_dir = DATA_DIR / "crawler"
    if crawler_dir.exists():
        for f in crawler_dir.glob("*.json"):
            files.append(("crawler", f))
    
    news_dir = DATA_DIR / "news"
    if news_dir.exists():
        for f in news_dir.glob("*.json"):
            # 跳过搜索历史日志文件
            if f.name == "search_history.json":
                continue
            files.append(("search", f))
    
    # 找出新文件（最多5个）
    new_files = [(t, f) for t, f in files if str(f) not in processed][:5]
    
    if not new_files:
        print("✅ 所有文件已同步完成")
        return
    
    print(f"🔄 本轮同步 {len(new_files)}/{len(files)-len(processed)} 个文件...")
    
    for file_type, file_path in new_files:
        print(f"  📁 {file_path.name}")
        
        success = False
        if file_type == "report":
            success = sync.sync_report(file_path)
        elif file_type == "crawler":
            success = sync.sync_crawler_data(file_path)
        elif file_type == "search":
            success = sync.sync_search_data(file_path)
        
        if success:
            processed.add(str(file_path))
            save_state(processed)
    
    remaining = len(files) - len(processed)
    print(f"✅ 完成，剩余 {remaining} 个文件")

if __name__ == "__main__":
    main()
