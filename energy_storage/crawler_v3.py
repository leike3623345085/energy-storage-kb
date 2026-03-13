#!/usr/bin/env python3
"""
储能爬虫 - 带重试和故障转移的健壮版 V3
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
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15',
]

class RobustScraper:
    """健壮的爬虫，带多重容错机制"""
    
    def __init__(self):
        self.cookie = None
        self.last_request_time = 0
        self.min_interval = 3  # 增加间隔到3秒
        self.errors = []
        self.success_count = 0
    
    def log_error(self, source, message):
        self.errors.append({
            "source": source,
            "message": message,
            "time": datetime.now().isoformat()
        })
    
    def _wait(self):
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_interval:
            sleep_time = self.min_interval - elapsed + random.uniform(0.5, 2)
            time.sleep(sleep_time)
        self.last_request_time = time.time()
    
    def _get_headers(self, referer=""):
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
        if referer:
            headers['Referer'] = referer
        return headers
    
    def fetch(self, url, timeout=20, retry=5, source=""):
        """增强版获取，带多次重试和更长超时"""
        for i in range(retry):
            try:
                self._wait()
                req = urllib.request.Request(url, headers=self._get_headers())
                
                with urllib.request.urlopen(req, timeout=timeout, context=ssl_context) as response:
                    if 'Set-Cookie' in response.headers:
                        self.cookie = response.headers['Set-Cookie'].split(';')[0]
                    
                    content = response.read()
                    
                    # 尝试解压gzip
                    try:
                        import gzip
                        content = gzip.decompress(content)
                    except:
                        pass
                    
                    text = content.decode('utf-8', errors='ignore')
                    
                    if len(text) < 1000:
                        self.log_error(source, f"内容过少: {len(text)} bytes")
                        if i < retry - 1:
                            time.sleep(3 + i * 2)
                        continue
                    
                    self.success_count += 1
                    return text
                    
            except Exception as e:
                error_msg = str(e)[:80]
                self.log_error(source, f"尝试{i+1}/{retry}: {error_msg}")
                
                if i < retry - 1:
                    # 指数退避 + 随机抖动
                    sleep_time = (2 ** i) + random.uniform(1, 3)
                    time.sleep(sleep_time)
        
        return None


def scrape_with_fallback(scraper, name, primary_url, fallback_urls, pattern, base_url=""):
    """带故障转移的抓取"""
    all_urls = [primary_url] + fallback_urls
    
    for i, url in enumerate(all_urls):
        print(f"  [{name}] 尝试来源 {i+1}/{len(all_urls)}...")
        html = scraper.fetch(url, source=name)
        
        if html:
            items = extract_items(html, pattern, base_url or url, name)
            if len(items) >= 3:  # 至少获取3条才算成功
                print(f"    ✓ 成功获取 {len(items)} 条")
                return items
            else:
                print(f"    ⚠ 数据量不足: {len(items)} 条")
        
        if i < len(all_urls) - 1:
            time.sleep(2)
    
    print(f"    ✗ 所有来源都失败")
    return []


def extract_items(html, pattern, base_url, source_name):
    """提取新闻条目"""
    items = []
    matches = re.findall(pattern, html, re.DOTALL)
    
    for match in matches[:50]:  # 最多50条
        try:
            if isinstance(match, tuple):
                title = match[0].strip()
                url = match[1] if len(match) > 1 else ""
                date = match[2] if len(match) > 2 else ""
            else:
                title = match.strip()
                url = ""
                date = ""
            
            # 清理标题
            title = re.sub(r'<[^>]+>', '', title)
            title = title.replace('&quot;', '"').replace('&amp;', '&')
            title = title.strip()
            
            if not title or len(title) < 5:
                continue
            
            # 补全URL
            if url and not url.startswith('http'):
                if url.startswith('/'):
                    from urllib.parse import urlparse
                    parsed = urlparse(base_url)
                    url = f"{parsed.scheme}://{parsed.netloc}{url}"
                elif url.startswith('./'):
                    url = base_url.rstrip('/') + url[1:]
                else:
                    url = base_url.rstrip('/') + '/' + url
            
            items.append({
                "title": title,
                "url": url,
                "date": date,
                "source": source_name,
                "fetch_time": datetime.now().isoformat()
            })
        except Exception as e:
            continue
    
    return items


def main():
    print("=" * 60)
    print("储能行业网站爬虫 - 健壮版 V3")
    print(f"运行时间: {datetime.now()}")
    print("=" * 60)
    
    scraper = RobustScraper()
    all_data = []
    source_stats = {}
    
    # 定义爬取配置 - 带备用URL
    sources = [
        {
            "name": "北极星储能网",
            "primary": "https://news.bjx.com.cn/list?catid=599",
            "fallbacks": [
                "https://chuneng.bjx.com.cn/",
                "https://news.bjx.com.cn/list?catid=599&page=1",
            ],
            "pattern": r'<a[^>]*href="([^"]*\/\d{6,}\/[^"]*)"[^>]*>([^<]+)</a>',
            "base": "https://news.bjx.com.cn",
        },
        {
            "name": "中国储能网",
            "primary": "http://www.escn.com.cn/news/",
            "fallbacks": [
                "http://www.escn.com.cn/news/list-2.html",
            ],
            "pattern": r'<a[^>]*href="([^"]*\/\d{6,}[^"]*)"[^>]*>([^<]+)</a>',
            "base": "http://www.escn.com.cn",
        },
        {
            "name": "中关村储能联盟",
            "primary": "https://www.cnesa.org/news/",
            "fallbacks": [],
            "pattern": r'<a[^>]*href="([^"]*\/news\/[^"]*)"[^>]*>([^<]+)</a>',
            "base": "https://www.cnesa.org",
        },
        {
            "name": "储能中国网",
            "primary": "http://www.chinaenergystorage.com/News/",
            "fallbacks": [],
            "pattern": r'<a[^>]*href="([^"]*News\/[^"]*)"[^>]*>([^<]+)</a>',
            "base": "http://www.chinaenergystorage.com",
        },
    ]
    
    for source in sources:
        items = scrape_with_fallback(
            scraper,
            source["name"],
            source["primary"],
            source["fallbacks"],
            source["pattern"],
            source["base"]
        )
        all_data.extend(items)
        source_stats[source["name"]] = len(items)
    
    # 保存结果
    output_dir = Path(__file__).parent / "data" / "crawler"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    output_file = output_dir / f"crawler_{timestamp}.json"
    log_file = output_dir / f"crawler_{timestamp}.log"
    
    # 去重
    seen = set()
    unique_data = []
    for item in all_data:
        key = item.get("title", "") + item.get("url", "")
        if key and key not in seen:
            seen.add(key)
            unique_data.append(item)
    
    # 保存JSON
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "fetch_time": datetime.now().isoformat(),
            "total": len(unique_data),
            "sources": list(source_stats.keys()),
            "data": unique_data
        }, f, ensure_ascii=False, indent=2)
    
    # 保存日志
    with open(log_file, 'w', encoding='utf-8') as f:
        f.write(f"爬虫执行日志\n")
        f.write(f"时间: {datetime.now()}\n")
        f.write(f"总计获取: {len(unique_data)} 条\n")
        f.write(f"来源: {', '.join([k for k, v in source_stats.items() if v > 0])}\n\n")
        f.write(f"来源详情:\n")
        for name, count in source_stats.items():
            f.write(f"  {name}: {count} 条\n")
        
        if scraper.errors:
            f.write(f"\n错误记录 ({len(scraper.errors)}条):\n")
            for err in scraper.errors[:20]:
                f.write(f"  [{err['time']}] {err['source']}: {err['message']}\n")
    
    print(f"\n{'='*60}")
    print(f"✅ 完成! 总计: {len(unique_data)} 条")
    for name, count in source_stats.items():
        status = "✓" if count > 0 else "✗"
        print(f"   {status} {name}: {count} 条")
    print(f"   保存: {output_file}")
    
    if len(unique_data) < 10:
        print(f"\n⚠️ 警告: 数据量过少，可能爬取失败!")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
