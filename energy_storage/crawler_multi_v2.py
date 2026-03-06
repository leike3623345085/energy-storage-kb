#!/usr/bin/env python3
"""
储能行业网站爬虫 - 多站点修复版
站点：北极星储能网、储能中国网、中关村储能联盟
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

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
]

class SmartScraper:
    def __init__(self):
        self.cookie = None
        self.last_request_time = 0
        self.min_interval = 2  # 减少间隔
    
    def _wait(self):
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed + random.uniform(0, 1))
        self.last_request_time = time.time()
    
    def _get_headers(self):
        headers = {
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Connection': 'keep-alive',
        }
        if self.cookie:
            headers['Cookie'] = self.cookie
        return headers
    
    def fetch(self, url, timeout=15, retry=3):  # 增加重试次数
        self._wait()
        for i in range(retry):
            try:
                req = urllib.request.Request(url, headers=self._get_headers())
                with urllib.request.urlopen(req, timeout=timeout, context=ssl_context) as response:
                    if 'Set-Cookie' in response.headers:
                        self.cookie = response.headers['Set-Cookie'].split(';')[0]
                    return response.read().decode('utf-8', errors='ignore')
            except Exception as e:
                print(f"    重试 {i+1}/{retry}: {str(e)[:40]}")
                if i < retry - 1:
                    time.sleep(2 ** i)  # 指数退避
        return None


def scrape_bjx(scraper):
    """北极星储能网"""
    print("\n[北极星储能网] 抓取中...")
    url = "https://chuneng.bjx.com.cn/"
    html = scraper.fetch(url)
    if not html:
        return []
    
    news = []
    pattern = r'href="https?://(news\.bjx\.com\.cn/html/\d{8}/\d+\.shtml)"[^\u003e]*\u003e([^\u003c]+?)\u003c/a\u003e'
    for link, title in re.findall(pattern, html):
        title = title.strip()
        if len(title) > 10 and '储能' in title:
            news.append({
                "title": title,
                "url": "https://" + link,
                "source": "北极星储能网",
                "fetched_at": datetime.now().isoformat()
            })
    
    seen = set()
    unique = [n for n in news if not (n["url"] in seen or seen.add(n["url"]))]
    print(f"  ✓ 获取 {len(unique)} 条")
    return unique[:20]


def scrape_cnnes(scraper):
    """储能中国网"""
    print("\n[储能中国网] 抓取中...")
    url = "http://www.cnnes.cc/"
    html = scraper.fetch(url)
    if not html:
        return []
    
    news = []
    pattern = r'href="(/hangye/[^"]+\.html)"[^\u003e]*\u003e([^\u003c]+?)\u003c/a\u003e'
    for link, title in re.findall(pattern, html):
        title = title.strip()
        if len(title) > 10 and '储能' in title:
            news.append({
                "title": title,
                "url": "http://www.cnnes.cc" + link,
                "source": "储能中国网",
                "fetched_at": datetime.now().isoformat()
            })
    
    seen = set()
    unique = [n for n in news if not (n["url"] in seen or seen.add(n["url"]))]
    print(f"  ✓ 获取 {len(unique)} 条")
    return unique[:15]


def scrape_cnesa(scraper):
    """中关村储能产业技术联盟 - 修复版"""
    print("\n[中关村储能联盟] 抓取中...")
    # 项目动态栏目
    url = "https://www.cnesa.org/information/?column_id=69"
    html = scraper.fetch(url)
    if not html:
        return []
    
    news = []
    # 提取新闻链接 - 格式: <a href="/information/detail/?column_id=69&id=7658" title="标题">
    pattern = r'<a href="(/information/detail/\?column_id=\d+&id=\d+)" title="([^"]+)"'
    for link, title in re.findall(pattern, html):
        title = title.strip()
        if len(title) > 10:
            news.append({
                "title": title,
                "url": "https://www.cnesa.org" + link,
                "source": "中关村储能联盟",
                "fetched_at": datetime.now().isoformat()
            })
    
    seen = set()
    unique = [n for n in news if not (n["url"] in seen or seen.add(n["url"]))]
    print(f"  ✓ 获取 {len(unique)} 条")
    return unique[:15]


def scrape_jsesa(scraper):
    """江苏省储能行业协会"""
    print("\n[江苏省储能行业协会] 抓取中...")
    url = "https://jsesa.com.cn/"
    html = scraper.fetch(url)
    if not html:
        return []
    
    news = []
    # 提取新闻链接
    pattern = r'href="(/col\d+/\d+\.html)"[^\u003e]*\u003e([^\u003c]+?)\u003c/a\u003e'
    for link, title in re.findall(pattern, html):
        title = title.strip()
        if len(title) > 10 and '储能' in title:
            news.append({
                "title": title,
                "url": "https://jsesa.com.cn" + link,
                "source": "江苏省储能行业协会",
                "fetched_at": datetime.now().isoformat()
            })
    
    seen = set()
    unique = [n for n in news if not (n["url"] in seen or seen.add(n["url"]))]
    print(f"  ✓ 获取 {len(unique)} 条")
    return unique[:15]


def scrape_gf(scraper):
    """北极星光伏网-储能栏目"""
    print("\n[北极星光伏网-储能] 抓取中...")
    url = "https://guangfu.bjx.com.cn/chuneng/"
    html = scraper.fetch(url)
    if not html:
        return []
    
    news = []
    # 提取新闻链接
    pattern = r'href="https?://(guangfu\.bjx\.com\.cn/html/\d{8}/\d+\.shtml)"[^\u003e]*\u003e([^\u003c]+?)\u003c/a\u003e'
    for link, title in re.findall(pattern, html):
        title = title.strip()
        if len(title) > 10 and '储能' in title:
            news.append({
                "title": title,
                "url": "https://" + link,
                "source": "北极星光伏网",
                "fetched_at": datetime.now().isoformat()
            })
    
    seen = set()
    unique = [n for n in news if not (n["url"] in seen or seen.add(n["url"]))]
    print(f"  ✓ 获取 {len(unique)} 条")
    return unique[:15]


def scrape_gglb(scraper):
    """高工储能"""
    print("\n[高工储能] 抓取中...")
    url = "https://www.gg-lb.com/"
    html = scraper.fetch(url)
    if not html:
        return []
    
    news = []
    pattern = r'href="(/news/\d+\.html)"[^>]*>([^<]+?)</a>'
    for link, title in re.findall(pattern, html):
        title = title.strip()
        if len(title) > 10 and '储能' in title:
            news.append({
                "title": title,
                "url": "https://www.gg-lb.com" + link,
                "source": "高工储能",
                "fetched_at": datetime.now().isoformat()
            })
    
    seen = set()
    unique = [n for n in news if not (n["url"] in seen or seen.add(n["url"]))]
    print(f"  ✓ 获取 {len(unique)} 条")
    return unique[:15]


def scrape_ofweek(scraper):
    """OFweek储能"""
    print("\n[OFweek储能] 抓取中...")
    url = "https://libattery.ofweek.com/"
    html = scraper.fetch(url)
    if not html:
        return []
    
    news = []
    pattern = r'href="(/\d{4}-\d{2}/[A-Z]+-\d+\.shtml)"[^>]*>([^<]+?)</a>'
    for link, title in re.findall(pattern, html):
        title = title.strip()
        if len(title) > 10 and ('储能' in title or '电池' in title):
            news.append({
                "title": title,
                "url": "https://libattery.ofweek.com" + link,
                "source": "OFweek储能",
                "fetched_at": datetime.now().isoformat()
            })
    
    seen = set()
    unique = [n for n in news if not (n["url"] in seen or seen.add(n["url"]))]
    print(f"  ✓ 获取 {len(unique)} 条")
    return unique[:15]


def scrape_escn(scraper):
    """中国储能网"""
    print("\n[中国储能网] 抓取中...")
    url = "http://www.escn.com.cn/"
    html = scraper.fetch(url)
    if not html:
        return []
    
    news = []
    pattern = r'href="(/news/show-\d+\.html)"[^>]*>([^<]+?)</a>'
    for link, title in re.findall(pattern, html):
        title = title.strip()
        if len(title) > 10 and '储能' in title:
            news.append({
                "title": title,
                "url": "http://www.escn.com.cn" + link,
                "source": "中国储能网",
                "fetched_at": datetime.now().isoformat()
            })
    
    seen = set()
    unique = [n for n in news if not (n["url"] in seen or seen.add(n["url"]))]
    print(f"  ✓ 获取 {len(unique)} 条")
    return unique[:15]


def main():
    print("=" * 60)
    print("储能行业网站爬虫 - 多站点版")
    print(f"运行时间: {datetime.now()}")
    print("=" * 60)
    
    scraper = SmartScraper()
    all_news = []
    
    all_news.extend(scrape_bjx(scraper))
    all_news.extend(scrape_cnnes(scraper))
    all_news.extend(scrape_cnesa(scraper))
    all_news.extend(scrape_jsesa(scraper))
    all_news.extend(scrape_gf(scraper))
    all_news.extend(scrape_gglb(scraper))
    all_news.extend(scrape_ofweek(scraper))
    all_news.extend(scrape_escn(scraper))
    
    if all_news:
        data_dir = Path(__file__).parent / "data" / "crawler"
        data_dir.mkdir(parents=True, exist_ok=True)
        
        filename = f"crawler_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        filepath = data_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({
                "fetch_time": datetime.now().isoformat(),
                "total_count": len(all_news),
                "sources": list(set(n["source"] for n in all_news)),
                "data": all_news
            }, f, ensure_ascii=False, indent=2)
        
        print(f"\n{'='*60}")
        print(f"✅ 完成! 总计: {len(all_news)} 条")
        print(f"   来源: {', '.join(set(n['source'] for n in all_news))}")
        print(f"   保存: {filepath}")
        
        print(f"\n📰 最新5条:")
        for i, item in enumerate(all_news[:5], 1):
            print(f"   {i}. [{item['source']}] {item['title'][:40]}...")
        return True
    else:
        print("\n⚠️ 未获取到数据")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
