#!/usr/bin/env python3
"""
储能行业网站爬虫 - 增强版
支持更多网站，更好的反爬处理
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
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
        ]
    
    def get_headers(self):
        """获取随机请求头"""
        return {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
    
    def fetch(self, url, timeout=30, retry=2):
        """获取网页内容，带重试"""
        for i in range(retry):
            try:
                # 随机延迟，避免被封
                time.sleep(random.uniform(0.5, 1.5))
                
                req = urllib.request.Request(url, headers=self.get_headers())
                with urllib.request.urlopen(req, timeout=timeout, context=ssl_context) as response:
                    return response.read().decode('utf-8', errors='ignore')
            except Exception as e:
                print(f"  重试 {i+1}/{retry}: {e}")
                time.sleep(2)
        
        return None
    
    def save_data(self, data, filename):
        """保存数据"""
        data_dir = Path(__file__).parent / "data" / "crawler"
        data_dir.mkdir(parents=True, exist_ok=True)
        
        filepath = data_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return filepath

class ESCNScraper(WebScraper):
    """中国储能网爬虫 - 已验证可用"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "http://www.escn.com.cn"
        self.name = "中国储能网"
    
    def scrape(self):
        """抓取首页和栏目页"""
        print(f"\n[{self.name}] 开始抓取...")
        all_news = []
        
        # 抓取首页
        print("  抓取首页...")
        html = self.fetch(self.base_url)
        if html:
            news = self._parse_html(html)
            all_news.extend(news)
            print(f"    获取 {len(news)} 条")
        
        # 抓取新闻栏目
        print("  抓取新闻栏目...")
        news_url = f"{self.base_url}/news/"
        html = self.fetch(news_url)
        if html:
            news = self._parse_html(html)
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
    
    def _parse_html(self, html):
        """解析HTML提取新闻"""
        news_list = []
        
        # 匹配新闻链接
        patterns = [
            r'<a[^\u003e]*href="(/news/show-\d+\.html)"[^\u003e]*\u003e\s*([^\u003c]+)\u003c/a\u003e',
            r'<a[^\u003e]*href="(/news/show-\d+\.html)"[^\u003e]*title="([^"]+)"',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, html)
            for link, title in matches:
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

class InEnScraper(WebScraper):
    """国际能源网爬虫"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://www.in-en.com"
        self.name = "国际能源网储能"
    
    def scrape(self):
        """抓取储能栏目"""
        print(f"\n[{self.name}] 开始抓取...")
        
        # 储能栏目
        url = f"{self.base_url}/storage/"
        html = self.fetch(url)
        
        if not html:
            return []
        
        news_list = []
        
        # 提取新闻
        pattern = r'<a[^\u003e]*href="(/storage/\d+/\d+\.html)"[^\u003e]*\u003e\s*([^\u003c]+?)\s*\u003c/a\u003e'
        matches = re.findall(pattern, html)
        
        for link, title in matches[:20]:
            title = title.strip()
            if title and len(title) > 10:
                full_url = urljoin(self.base_url, link)
                news_list.append({
                    "title": title,
                    "url": full_url,
                    "source": self.name,
                    "fetched_at": datetime.now().isoformat()
                })
        
        print(f"  获取 {len(news_list)} 条")
        return news_list

class OFweekNewsScraper(WebScraper):
    """OFweek新闻爬虫"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://www.ofweek.com"
        self.name = "OFweek高科技"
    
    def scrape(self):
        """抓取储能相关新闻"""
        print(f"\n[{self.name}] 开始抓取...")
        
        # 新能源栏目
        url = f"{self.base_url}/CATListNew-25000-8000.html"
        html = self.fetch(url)
        
        if not html:
            return []
        
        news_list = []
        
        # 提取新闻
        pattern = r'<a[^\u003e]*href="(https?://[^"]+)"[^\u003e]*title="([^"]+)"[^\u003e]*\u003e'
        matches = re.findall(pattern, html)
        
        # 过滤储能相关
        keywords = ['储能', '电池', '锂电', '固态', '钠', '光伏', '新能源']
        
        for link, title in matches[:30]:
            title = title.strip()
            if any(kw in title for kw in keywords):
                news_list.append({
                    "title": title,
                    "url": link,
                    "source": self.name,
                    "fetched_at": datetime.now().isoformat()
                })
        
        print(f"  获取 {len(news_list)} 条")
        return news_list

class NeteaseScraper(WebScraper):
    """网易科技爬虫"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://tech.163.com"
        self.name = "网易科技储能"
    
    def scrape(self):
        """抓取科技频道储能相关内容"""
        print(f"\n[{self.name}] 开始抓取...")
        
        url = f"{self.base_url}/dy/article/"
        html = self.fetch(url)
        
        if not html:
            return []
        
        news_list = []
        
        # 提取新闻
        pattern = r'<a[^\u003e]*href="(https?://[^"]+\.html)"[^\u003e]*\u003e\s*([^\u003c]*(?:储能|电池|锂电|固态|新能源)[^\u003c]*)\s*\u003c/a\u003e'
        matches = re.findall(pattern, html, re.IGNORECASE)
        
        for link, title in matches[:15]:
            title = title.strip()
            if title and len(title) > 10:
                news_list.append({
                    "title": title,
                    "url": link,
                    "source": self.name,
                    "fetched_at": datetime.now().isoformat()
                })
        
        print(f"  获取 {len(news_list)} 条")
        return news_list

def main():
    """主函数"""
    print("=" * 60)
    print("储能行业网站爬虫 - 增强版")
    print(f"运行时间: {datetime.now()}")
    print("=" * 60)
    
    all_news = []
    scrapers = [
        ESCNScraper(),      # 中国储能网 - 已验证
        InEnScraper(),      # 国际能源网
        OFweekNewsScraper(), # OFweek
        NeteaseScraper(),       # 网易科技
    ]
    
    for scraper in scrapers:
        try:
            news = scraper.scrape()
            all_news.extend(news)
        except Exception as e:
            print(f"  错误: {e}")
    
    # 保存所有数据
    if all_news:
        scraper = WebScraper()
        filename = f"crawler_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        
        # 去重
        seen = set()
        unique_news = []
        for item in all_news:
            if item["url"] not in seen:
                seen.add(item["url"])
                unique_news.append(item)
        
        filepath = scraper.save_data({
            "fetch_time": datetime.now().isoformat(),
            "total_count": len(unique_news),
            "sources": list(set(item["source"] for item in unique_news)),
            "data": unique_news
        }, filename)
        
        print(f"\n{'='*60}")
        print(f"✅ 抓取完成!")
        print(f"   总计: {len(unique_news)} 条（去重后）")
        print(f"   来源: {', '.join(set(item['source'] for item in unique_news))}")
        print(f"   保存: {filepath}")
        
        # 打印前5条预览
        print(f"\n📰 最新资讯预览:")
        for i, item in enumerate(unique_news[:5], 1):
            print(f"   {i}. [{item['source']}] {item['title'][:50]}...")
    else:
        print("\n⚠️ 未获取到数据")

if __name__ == "__main__":
    main()
