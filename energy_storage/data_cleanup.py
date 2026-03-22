#!/usr/bin/env python3
"""
数据清理脚本 - 只保留7天内的数据
用于清理爬虫和搜索数据目录
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

DATA_RETENTION_DAYS = 7

def clean_old_data(data_dir: Path, pattern: str = "*.json"):
    """清理指定目录的旧数据"""
    cutoff_date = datetime.now() - timedelta(days=DATA_RETENTION_DAYS)
    deleted_count = 0
    kept_count = 0
    
    if not data_dir.exists():
        print(f"目录不存在: {data_dir}")
        return 0, 0
    
    for file_path in data_dir.glob(pattern):
        try:
            # 从文件名提取日期
            # 格式: crawler_20260322_0004.json 或 search_morning_2026-03-22.json
            filename = file_path.stem
            
            # 尝试多种日期格式
            file_date = None
            
            # 格式1: crawler_20260322_0004
            if 'crawler_' in filename or 'search_' in filename:
                parts = filename.split('_')
                for part in parts:
                    if len(part) == 8 and part.isdigit():
                        try:
                            file_date = datetime.strptime(part, "%Y%m%d")
                            break
                        except:
                            pass
                    # 格式2: 2026-03-22
                    if '-' in part and len(part.split('-')) == 3:
                        try:
                            file_date = datetime.strptime(part, "%Y-%m-%d")
                            break
                        except:
                            pass
            
            # 如果无法从文件名解析，使用文件修改时间
            if file_date is None:
                file_date = datetime.fromtimestamp(file_path.stat().st_mtime)
            
            # 判断是否过期
            if file_date < cutoff_date:
                print(f"🗑️ 删除过期文件: {file_path.name} ({file_date.strftime('%Y-%m-%d')})")
                file_path.unlink()
                deleted_count += 1
            else:
                kept_count += 1
                
        except Exception as e:
            print(f"⚠️ 处理失败: {file_path.name} - {e}")
    
    return deleted_count, kept_count

def main():
    """主入口"""
    print("=" * 60)
    print("🧹 数据清理脚本")
    print(f"⏰ 清理时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📅 保留期限: {DATA_RETENTION_DAYS} 天内")
    print(f"📅 截止日期: {(datetime.now() - timedelta(days=DATA_RETENTION_DAYS)).strftime('%Y-%m-%d')}")
    print("=" * 60)
    
    base_dir = Path(__file__).parent / "data"
    
    # 清理爬虫数据
    print("\n📂 清理爬虫数据...")
    crawler_dir = base_dir / "crawler"
    deleted, kept = clean_old_data(crawler_dir, "*.json")
    print(f"   已删除: {deleted} 个文件, 保留: {kept} 个文件")
    
    # 清理搜索数据
    print("\n📂 清理搜索数据...")
    news_dir = base_dir / "news"
    deleted, kept = clean_old_data(news_dir, "*.json")
    print(f"   已删除: {deleted} 个文件, 保留: {kept} 个文件")
    
    # 清理AI技术监控数据
    print("\n📂 清理AI技术监控数据...")
    ai_dir = base_dir / "ai_tech"
    deleted, kept = clean_old_data(ai_dir, "*.json")
    print(f"   已删除: {deleted} 个文件, 保留: {kept} 个文件")
    
    print("\n" + "=" * 60)
    print("✅ 数据清理完成")
    print("=" * 60)

if __name__ == "__main__":
    main()
