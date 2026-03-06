#!/usr/bin/env python3
"""
储能行业网站爬虫 - 简化版
使用北极星储能网 https://chuneng.bjx.com.cn/
"""

import json
import re
import ssl
import time
import random
import urllib.request
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

def fetch(url, timeout=15):
    """抓取网页"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    }
    try:
        time.sleep(random.uniform(0.5, 1.0))
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout, context=ssl_context) as response:
            return response.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"  ✗ 获取失败: {e}")
        return None

def parse_bjx(html):
    """解析北极星储能网"""
    news = []
    # 提取新闻标题和链接
    # 格式: news.bjx.com.cn/html/20260304/1486100.shtml
    pattern = r'href="https?://(news\.bjx\.com\.cn/html/\d{8}/\d+\.shtml)"[^>]*>([^<]+?)</a>'
    for link, title in re.findall(pattern, html):
        title = title.strip()
        if len(title) > 10 and '储能' in title:
            news.append({
                "title": title,
                "url": "https://" + link,
                "source": "北极星储能网",
                "fetched_at": datetime.now().isoformat()
            })
    # 去重
    seen = set()
    unique_news = [n for n in news if not (n["url"] in seen or seen.add(n["url"]))]
    return unique_news[:30]

def main():
    print("=" * 60)
    print("储能行业网站爬虫")
    print(f"运行时间: {datetime.now()}")
    print("=" * 60)
    
    url = "https://chuneng.bjx.com.cn/"
    print(f"\n[北极星储能网] 抓取中...")
    print(f"  URL: {url}")
    
    html = fetch(url, timeout=20)
    if not html:
        print("  ✗ 无法获取页面")
        return False
    
    news = parse_bjx(html)
    print(f"  ✓ 解析到 {len(news)} 条新闻")
    
    if news:
        # 保存数据
        data_dir = Path(__file__).parent / "data" / "crawler"
        data_dir.mkdir(parents=True, exist_ok=True)
        
        filename = f"crawler_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        filepath = data_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({
                "fetch_time": datetime.now().isoformat(),
                "total_count": len(news),
                "sources": ["北极星储能网"],
                "data": news
            }, f, ensure_ascii=False, indent=2)
        
        print(f"\n{'='*60}")
        print(f"✅ 完成! 总计: {len(news)} 条")
        print(f"   保存: {filepath}")
        
        print(f"\n📰 最新5条:")
        for i, item in enumerate(news[:5], 1):
            print(f"   {i}. {item['title'][:50]}...")
        return True
    else:
        print("\n⚠️ 未解析到新闻")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
