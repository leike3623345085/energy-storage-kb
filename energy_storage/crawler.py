#!/usr/bin/env python3
"""
储能行业网站爬虫
直接抓取重点网站的最新资讯
"""

import json
import re
import ssl
import urllib.request
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

# 创建SSL上下文
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

class WebScraper:
    """网页抓取基类"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }
    
    def fetch(self, url, timeout=30):
        """获取网页内容"""
        try:
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=timeout, context=ssl_context) as response:
                return response.read().decode('utf-8', errors='ignore')
        except Exception as e:
            print(f"  ✗ 获取失败 {url}: {e}")
            return None
    
    def save_data(self, data, filename):
        """保存数据"""
        data_dir = Path(__file__).parent / "data" / "crawler"
        data_dir.mkdir(parents=True, exist_ok=True)
        
        filepath = data_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return filepath

class OFweekScraper(WebScraper):
    """OFweek储能/锂电爬虫"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://libattery.ofweek.com"
        self.name = "OFweek锂电"
    
    def scrape_list(self, page=1):
        """抓取列表页"""
        url = f"{self.base_url}/CAT-36001-8120.html?page={page}"
        html = self.fetch(url)
        
        if not html:
            return []
        
        news_list = []
        
        # 使用正则提取新闻
        # 匹配模式: 文章链接和标题
        pattern = r'<a[^>]*href="([^"]*ART-\d+-\d+-\d+[^"]*)"[^>]*>\s*<[^>]*>\s*([^<]+)</'
        matches = re.findall(pattern, html, re.DOTALL)
        
        for link, title in matches[:10]:  # 每页取前10条
            # 清理标题
            title = re.sub(r'\s+', ' ', title).strip()
            if title and link:
                full_url = urljoin(self.base_url, link)
                news_list.append({
                    "title": title,
                    "url": full_url,
                    "source": self.name,
                    "fetched_at": datetime.now().isoformat()
                })
        
        return news_list
    
    def scrape(self, max_pages=2):
        """抓取多页"""
        print(f"\n[{self.name}] 开始抓取...")
        all_news = []
        
        for page in range(1, max_pages + 1):
            print(f"  抓取第 {page} 页...")
            news = self.scrape_list(page)
            all_news.extend(news)
            print(f"    获取 {len(news)} 条")
        
        # 去重
        seen = set()
        unique = []
        for item in all_news:
            if item["url"] not in seen:
                seen.add(item["url"])
                unique.append(item)
        
        print(f"  总计: {len(unique)} 条（去重后）")
        return unique

class BJXScraper(WebScraper):
    """北极星储能网爬虫"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://news.bjx.com.cn"
        self.name = "北极星储能网"
    
    def scrape_list(self, page=1):
        """抓取列表页"""
        # 北极星储能栏目
        url = f"{self.base_url}/list?catid=3939&page={page}"
        html = self.fetch(url)
        
        if not html:
            return []
        
        news_list = []
        
        # 提取新闻链接和标题
        pattern = r'<a[^>]*href="(/news/\d{8}/\d+\.shtml)"[^>]*[^<]*>([^<]+)</a>'
        matches = re.findall(pattern, html)
        
        for link, title in matches[:15]:
            title = title.strip()
            if title and len(title) > 10:  # 过滤短标题
                full_url = urljoin(self.base_url, link)
                news_list.append({
                    "title": title,
                    "url": full_url,
                    "source": self.name,
                    "fetched_at": datetime.now().isoformat()
                })
        
        return news_list
    
    def scrape(self, max_pages=2):
        """抓取多页"""
        print(f"\n[{self.name}] 开始抓取...")
        all_news = []
        
        for page in range(1, max_pages + 1):
            print(f"  抓取第 {page} 页...")
            news = self.scrape_list(page)
            all_news.extend(news)
            print(f"    获取 {len(news)} 条")
        
        # 去重
        seen = set()
        unique = []
        for item in all_news:
            if item["url"] not in seen:
                seen.add(item["url"])
                unique.append(item)
        
        print(f"  总计: {len(unique)} 条（去重后）")
        return unique

class ESCNScraper(WebScraper):
    """中国储能网爬虫"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "http://www.escn.com.cn"
        self.name = "中国储能网"
    
    def scrape_list(self):
        """抓取首页新闻"""
        html = self.fetch(self.base_url)
        
        if not html:
            return []
        
        news_list = []
        
        # 提取新闻链接
        pattern = r'<a[^>]*href="(/news/show-\d+\.html)"[^>]*>([^<]+)</a>'
        matches = re.findall(pattern, html)
        
        for link, title in matches[:20]:
            title = title.strip()
            if title and len(title) > 5:
                full_url = urljoin(self.base_url, link)
                news_list.append({
                    "title": title,
                    "url": full_url,
                    "source": self.name,
                    "fetched_at": datetime.now().isoformat()
                })
        
        return news_list
    
    def scrape(self):
        """抓取"""
        print(f"\n[{self.name}] 开始抓取...")
        news = self.scrape_list()
        print(f"  获取 {len(news)} 条")
        return news

class GGScraper(WebScraper):
    """高工储能爬虫"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://www.gg-lb.com"
        self.name = "高工储能"
    
    def scrape_list(self, page=1):
        """抓取列表"""
        url = f"{self.base_url}/news/lists/p/{page}.html"
        html = self.fetch(url)
        
        if not html:
            return []
        
        news_list = []
        
        # 提取新闻
        pattern = r'<a[^>]*href="(/news/detail/\d+\.html)"[^>]*>\s*<[^>]*>\s*([^<]+)</'
        matches = re.findall(pattern, html, re.DOTALL)
        
        for link, title in matches[:10]:
            title = re.sub(r'\s+', ' ', title).strip()
            if title:
                full_url = urljoin(self.base_url, link)
                news_list.append({
                    "title": title,
                    "url": full_url,
                    "source": self.name,
                    "fetched_at": datetime.now().isoformat()
                })
        
        return news_list
    
    def scrape(self, max_pages=2):
        """抓取多页"""
        print(f"\n[{self.name}] 开始抓取...")
        all_news = []
        
        for page in range(1, max_pages + 1):
            print(f"  抓取第 {page} 页...")
            news = self.scrape_list(page)
            all_news.extend(news)
            print(f"    获取 {len(news)} 条")
        
        # 去重
        seen = set()
        unique = []
        for item in all_news:
            if item["url"] not in seen:
                seen.add(item["url"])
                unique.append(item)
        
        print(f"  总计: {len(unique)} 条（去重后）")
        return unique

def main():
    """主函数 - 抓取所有网站"""
    print("=" * 60)
    print("储能行业网站爬虫")
    print(f"运行时间: {datetime.now()}")
    print("=" * 60)
    
    all_news = []
    scrapers = [
        OFweekScraper(),
        BJXScraper(),
        ESCNScraper(),
        GGScraper(),
    ]
    
    for scraper in scrapers:
        try:
            if isinstance(scraper, ESCNScraper):
                news = scraper.scrape()
            else:
                news = scraper.scrape(max_pages=2)
            all_news.extend(news)
        except Exception as e:
            print(f"  错误: {e}")
    
    # 保存所有数据
    if all_news:
        scraper = WebScraper()
        filename = f"crawler_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        filepath = scraper.save_data({
            "fetch_time": datetime.now().isoformat(),
            "total_count": len(all_news),
            "sources": list(set(item["source"] for item in all_news)),
            "data": all_news
        }, filename)
        
        print(f"\n{'='*60}")
        print(f"✅ 抓取完成!")
        print(f"   总计: {len(all_news)} 条")
        print(f"   来源: {', '.join(set(item['source'] for item in all_news))}")
        print(f"   保存: {filepath}")
    else:
        print("\n⚠️ 未获取到数据")

if __name__ == "__main__":
    main()
