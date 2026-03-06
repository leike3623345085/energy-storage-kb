#!/usr/bin/env python3
"""
储能行业数据源监控
结合搜索API和直接抓取获取最新资讯
"""

import json
import subprocess
from datetime import datetime
from pathlib import Path

# 数据源配置
SOURCES = {
    "ofweek": {
        "name": "OFweek储能/锂电",
        "queries": [
            "site:ofweek.com 储能 固态电池 钠电池",
            "site:ofweek.com 宁德时代 比亚迪 储能",
            "site:libattery.ofweek.com 电池"
        ]
    },
    "bjx": {
        "name": "北极星储能网", 
        "queries": [
            "site:news.bjx.com.cn 储能",
            "site:news.bjx.com.cn 储能电站"
        ]
    },
    "zhihu": {
        "name": "知乎储能话题",
        "queries": [
            "site:zhuanlan.zhihu.com 储能行业 2025",
            "site:zhuanlan.zhihu.com 固态电池 钠电池"
        ]
    }
}

def run_search(query, limit=5):
    """执行搜索"""
    try:
        # 使用 kimi_search 工具
        result = subprocess.run(
            ['python3', '-c', f'''
import sys
sys.path.insert(0, "/root/.openclaw/extensions/kimi-search")
from kimi_search import kimi_search
results = kimi_search("{query}", limit={limit})
print(json.dumps(results, ensure_ascii=False))
'''],
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
    except Exception as e:
        print(f"搜索失败: {e}")
    return []

def fetch_all_sources():
    """获取所有数据源"""
    all_news = []
    
    for source_key, source_config in SOURCES.items():
        print(f"\n正在获取: {source_config['name']}...")
        
        for query in source_config['queries']:
            print(f"  搜索: {query[:50]}...")
            results = run_search(query, limit=3)
            
            for item in results:
                news_item = {
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "summary": item.get("summary", "")[:500],
                    "source": source_config["name"],
                    "query": query,
                    "fetched_at": datetime.now().isoformat()
                }
                all_news.append(news_item)
            
            print(f"    获取 {len(results)} 条")
    
    return all_news

def save_news(news_items):
    """保存新闻数据"""
    if not news_items:
        print("\n没有获取到新数据")
        return
    
    # 去重
    seen_urls = set()
    unique_news = []
    for item in news_items:
        if item["url"] not in seen_urls:
            seen_urls.add(item["url"])
            unique_news.append(item)
    
    # 保存
    data_dir = Path(__file__).parent / "data" / "sources"
    data_dir.mkdir(parents=True, exist_ok=True)
    
    date_str = datetime.now().strftime("%Y%m%d_%H%M")
    output_file = data_dir / f"news_{date_str}.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "fetch_time": datetime.now().isoformat(),
            "total_count": len(unique_news),
            "data": unique_news
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 保存完成: {output_file}")
    print(f"   总计: {len(unique_news)} 条（去重后）")
    
    return output_file

def main():
    """主函数"""
    print("=" * 60)
    print("储能行业数据源监控")
    print(f"运行时间: {datetime.now()}")
    print("=" * 60)
    
    news = fetch_all_sources()
    save_news(news)
    
    print("\n监控完成!")

if __name__ == "__main__":
    main()
