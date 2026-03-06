#!/usr/bin/env python3
"""
储能行业网站爬虫 - 反反爬修复版
功能：带Cookie、随机UA、代理、降频
"""

import json
import re
import ssl
import time
import random
import urllib.request
from datetime import datetime
from pathlib import Path

ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

# 随机UA池
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
]

class SmartScraper:
    """智能爬虫"""
    
    def __init__(self):
        self.cookie = None
        self.last_request_time = 0
        self.min_interval = 3  # 最小请求间隔3秒
    
    def _wait(self):
        """请求间隔控制"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_interval:
            sleep_time = self.min_interval - elapsed + random.uniform(0, 2)
            time.sleep(sleep_time)
        self.last_request_time = time.time()
    
    def _get_headers(self):
        """生成请求头"""
        headers = {
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0',
        }
        if self.cookie:
            headers['Cookie'] = self.cookie
        return headers
    
    def fetch(self, url, timeout=20, retry=3):
        """抓取网页，带重试"""
        self._wait()
        
        for i in range(retry):
            try:
                req = urllib.request.Request(url, headers=self._get_headers())
                with urllib.request.urlopen(req, timeout=timeout, context=ssl_context) as response:
                    # 保存Cookie
                    if 'Set-Cookie' in response.headers:
                        self.cookie = response.headers['Set-Cookie'].split(';')[0]
                    
                    html = response.read()
                    # 尝试解压gzip
                    try:
                        import gzip
                        html = gzip.decompress(html)
                    except:
                        pass
                    return html.decode('utf-8', errors='ignore')
                    
            except Exception as e:
                print(f"    重试 {i+1}/{retry}: {str(e)[:50]}")
                if i < retry - 1:
                    time.sleep(5 + random.uniform(0, 5))
        return None


def parse_bjx(html):
    """解析北极星储能网"""
    news = []
    # 匹配格式: news.bjx.com.cn/html/20260304/1486100.shtml
    pattern = r'href="https?://(news\.bjx\.com\.cn/html/\d{8}/\d+\.shtml)"[^>]*>([^<]+?)</a>'
    
    for link, title in re.findall(pattern, html):
        title = title.strip()
        if len(title) > 10 and '储能' in title and 'href' not in title:
            news.append({
                "title": title,
                "url": "https://" + link,
                "source": "北极星储能网",
                "fetched_at": datetime.now().isoformat()
            })
    
    # 去重
    seen = set()
    return [n for n in news if not (n["url"] in seen or seen.add(n["url"]))][:25]


def main():
    print("=" * 60)
    print("储能行业网站爬虫 - 反反爬修复版")
    print(f"运行时间: {datetime.now()}")
    print("=" * 60)
    
    scraper = SmartScraper()
    url = "https://chuneng.bjx.com.cn/"
    
    print(f"\n[北极星储能网] 抓取中...")
    print(f"  URL: {url}")
    print(f"  策略: 随机UA + Cookie + 降频(3-5秒)")
    
    html = scraper.fetch(url, timeout=25)
    if not html:
        print("  ✗ 无法获取页面")
        return False
    
    print(f"  ✓ 页面获取成功 ({len(html)} 字符)")
    
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
            print(f"   {i}. {item['title'][:45]}...")
        return True
    else:
        print("\n⚠️ 未解析到新闻")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
