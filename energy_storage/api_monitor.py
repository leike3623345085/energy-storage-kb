#!/usr/bin/env python3
"""
储能行业 API 数据源监控
- 新浪财经 API
- 东方财富 API
- 其他公开 API
"""

import json
import urllib.request
import ssl
from datetime import datetime
from pathlib import Path

ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

DATA_DIR = Path(__file__).parent / "data" / "api_data"

def fetch_sina_news():
    """获取新浪财经储能相关新闻"""
    print("\n[新浪财经] 获取储能新闻...")
    
    # 新浪财经 API
    api_url = "https://feed.mix.sina.com.cn/api/roll/get?pageid=153&lid=2516&k=&num=20&page=1&r={}"
    
    try:
        import time
        url = api_url.format(int(time.time() * 1000))
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://finance.sina.com.cn/'
        })
        
        with urllib.request.urlopen(req, timeout=10, context=ssl_context) as response:
            data = json.loads(response.read().decode('utf-8'))
            
            news_list = []
            if data.get('result') and data['result'].get('data'):
                for item in data['result']['data']:
                    title = item.get('title', '')
                    if '储能' in title or '电池' in title:
                        news_list.append({
                            'title': title,
                            'url': item.get('url', ''),
                            'source': '新浪财经',
                            'time': item.get('ctime', ''),
                            'fetched_at': datetime.now().isoformat()
                        })
            
            print(f"  ✓ 获取 {len(news_list)} 条储能相关新闻")
            return news_list
            
    except Exception as e:
        print(f"  ✗ 获取失败: {str(e)[:50]}")
        return []


def fetch_eastmoney_news():
    """获取东方财富储能相关新闻"""
    print("\n[东方财富] 获取储能新闻...")
    
    # 东方财富 API
    api_url = "http://searchapi.eastmoney.com/api/suggest/get?input=%E5%82%A8%E8%83%BD&type=14&count=20"
    
    try:
        req = urllib.request.Request(api_url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        })
        
        with urllib.request.urlopen(req, timeout=10, context=ssl_context) as response:
            data = json.loads(response.read().decode('utf-8'))
            
            news_list = []
            if isinstance(data, list):
                for item in data:
                    title = item.get('Title', '')
                    news_list.append({
                        'title': title,
                        'url': item.get('Url', ''),
                        'source': '东方财富',
                        'time': datetime.now().isoformat(),
                        'fetched_at': datetime.now().isoformat()
                    })
            
            print(f"  ✓ 获取 {len(news_list)} 条")
            return news_list
            
    except Exception as e:
        print(f"  ✗ 获取失败: {str(e)[:50]}")
        return []


def save_data(news_list, source):
    """保存数据到文件"""
    if not news_list:
        return
    
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    date_str = datetime.now().strftime("%Y%m%d_%H%M")
    filename = DATA_DIR / f"{source}_{date_str}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump({
            'source': source,
            'fetch_time': datetime.now().isoformat(),
            'count': len(news_list),
            'data': news_list
        }, f, ensure_ascii=False, indent=2)
    
    print(f"  💾 保存到: {filename}")


def main():
    print("=" * 60)
    print("储能行业 API 数据监控")
    print(f"运行时间: {datetime.now()}")
    print("=" * 60)
    
    # 获取新浪财经数据
    sina_news = fetch_sina_news()
    save_data(sina_news, 'sina')
    
    # 获取东方财富数据
    eastmoney_news = fetch_eastmoney_news()
    save_data(eastmoney_news, 'eastmoney')
    
    total = len(sina_news) + len(eastmoney_news)
    print(f"\n{'=' * 60}")
    print(f"总计获取: {total} 条")
    print("=" * 60)


if __name__ == "__main__":
    main()
