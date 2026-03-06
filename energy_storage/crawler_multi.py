#!/usr/bin/env python3
"""
储能行业网站爬虫 - 修复版
可用源：北极星储能网、OFweek储能
已移除：中国储能网（连接被拒绝）、高工储能（503错误）
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

# 创建SSL上下文
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

class WebScraper:
    """网页抓取基类"""
    
    def __init__(self):
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        ]
    
    def get_headers(self):
        return {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }
    
    def fetch(self, url, timeout=15, retry=2):
        """抓取网页，带超时和重试"""
        for i in range(retry):
            try:
                time.sleep(random.uniform(0.5, 1.0))
                req = urllib.request.Request(url, headers=self.get_headers())
                with urllib.request.urlopen(req, timeout=timeout, context=ssl_context) as response:
                    return response.read().decode('utf-8', errors='ignore')
            except Exception as e:
                print(f"    重试 {i+1}/{retry}: {e}")
                if i < retry - 1:
                    time.sleep(2)
        return None


class BJXScraper(WebScraper):
    """北极星储能网 - 可用"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://news.bjx.com.cn"
        self.name = "北极星储能网"
    
    def scrape(self):
        print(f"\n[{self.name}] 抓取中...")
        all_news = []
        
        list_urls = [
            "https://news.bjx.com.cn/list?catid=3939",  # 储能
            "https://news.bjx.com.cn/list?catid=3940",  # 储能技术
        ]
        
        for url in list_urls:
            html = self.fetch(url, timeout=15)
            if html:
                news = self._parse_list(html)
                all_news.extend(news)
                print(f"  ✓ {url.split('catid=')[1]}: {len(news)}条")
            else:
                print(f"  ✗ {url.split('catid=')[1]}: 获取失败")
        
        return self._dedup(all_news)
    
    def _parse_list(self, html):
        news = []
        pattern = r'<a[^>]*href="(/news/\d{8}/\d+\.shtml)"[^>]*>\s*([^<]+?)</a>'
        for link, title in re.findall(pattern, html):
            title = title.strip()
            if len(title) > 10 and '储能' in title:
                news.append({
                    "title": title,
                    "url": urljoin(self.base_url, link),
                    "source": self.name,
                    "fetched_at": datetime.now().isoformat()
                })
        return news[:20]
    
    def _dedup(self, news):
        seen = set()
        return [n for n in news if not (n["url"] in seen or seen.add(n["url"]))]


class OFweekScraper(WebScraper):
    """OFweek储能 - 可用"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://chuneng.ofweek.com"
        self.name = "OFweek储能"
    
    def scrape(self):
        print(f"\n[{self.name}] 抓取中...")
        all_news = []
        
        url = self.base_url
        html = self.fetch(url, timeout=15)
        if html:
            news = self._parse(html)
            all_news.extend(news)
            print(f"  ✓ 首页: {len(news)}条")
        else:
            print(f"  ✗ 首页: 获取失败")
        
        return self._dedup(all_news)
    
    def _parse(self, html):
        news = []
        # OFweek新闻链接格式
        pattern = r'<a[^>]*href="(/\d{4}-\d{2}/[A-Z]+-\d+-\d+\.html)"[^>]*>([^<]+)</a>'
        for link, title in re.findall(pattern, html):
            title = title.strip()
            if len(title) > 10:
                news.append({
                    "title": title,
                    "url": urljoin(self.base_url, link),
                    "source": self.name,
                    "fetched_at": datetime.now().isoformat()
                })
        return news[:20]
    
    def _dedup(self, news):
        seen = set()
        return [n for n in news if not (n["url"] in seen or seen.add(n["url"]))]


def main():
    print("=" * 60)
    print("储能行业网站爬虫 - 修复版")
    print(f"运行时间: {datetime.now()}")
    print("=" * 60)
    
    all_news = []
    scrapers = [
        BJXScraper(),      # 北极星储能网 - 可用
        OFweekScraper(),   # OFweek储能 - 可用
    ]
    
    for scraper in scrapers:
        try:
            news = scraper.scrape()
            all_news.extend(news)
        except Exception as e:
            print(f"  ✗ 异常: {e}")
    
    # 保存数据
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
            print(f"   {i}. [{item['source']}] {item['title'][:45]}...")
        return True
    else:
        print("\n⚠️ 未获取到数据")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
