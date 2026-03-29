#!/usr/bin/env python3
"""
储能行业爬虫 - 并行版本 (Parallel Crawler Prototype)
===============================================
使用 ThreadPoolExecutor 并行抓取多个数据源

改进点:
- 并行抓取多个站点 (从串行 → 并行)
- 统一结果聚合
- 性能统计
- 错误隔离 (单点失败不影响整体)

用法:
    python3 crawler_parallel.py
    python3 crawler_parallel.py --max-workers 4
    python3 crawler_parallel.py --sources bjx,cnnes
"""

import json
import re
import ssl
import time
import random
import argparse
import urllib.request
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict

# SSL 上下文
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
]


@dataclass
class CrawlResult:
    """爬取结果数据类"""
    source: str
    success: bool
    items: List[Dict[str, Any]]
    duration: float
    error: Optional[str] = None
    item_count: int = 0


class SmartScraper:
    """智能爬虫 - 每个线程独立实例"""
    
    def __init__(self, min_interval: float = 1.0):
        self.cookie = None
        self.min_interval = min_interval
        self.last_request_time = 0
    
    def _wait(self):
        """请求间隔控制"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed + random.uniform(0, 0.5))
        self.last_request_time = time.time()
    
    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        headers = {
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Connection': 'keep-alive',
        }
        if self.cookie:
            headers['Cookie'] = self.cookie
        return headers
    
    def fetch(self, url: str, timeout: int = 15, retry: int = 2, source: str = "") -> Optional[str]:
        """获取网页内容"""
        self._wait()
        
        for i in range(retry):
            try:
                req = urllib.request.Request(url, headers=self._get_headers())
                with urllib.request.urlopen(req, timeout=timeout, context=ssl_context) as resp:
                    if 'Set-Cookie' in resp.headers:
                        self.cookie = resp.headers['Set-Cookie'].split(';')[0]
                    content = resp.read().decode('utf-8', errors='ignore')
                    if len(content) < 500:
                        return None
                    return content
            except Exception as e:
                if i < retry - 1:
                    time.sleep(2 ** i)
        return None


# ============== 数据源配置 ==============

SOURCES_CONFIG = {
    "bjx": {
        "name": "北极星储能网",
        "url": "https://chuneng.bjx.com.cn/",
        "pattern": r'href="https?://(news\.bjx\.com\.cn/html/\d{8}/\d+\.shtml)"[^>]*>([^<]+?)</a>',
        "base_url": "https://",
        "min_count": 10,
    },
    "cnnes": {
        "name": "储能中国网",
        "url": "http://www.cnnes.cc/",
        "pattern": r'href="(/hangye/[^"]+\.html)"[^>]*>([^<]+?)</a>',
        "base_url": "http://www.cnnes.cc",
        "min_count": 5,
    },
    "ofweek": {
        "name": "OFweek储能",
        "url": "https://chuneng.ofweek.com/",
        "pattern": r'href="(/\d{4}-\d{2}/[\w-]+\.shtml)"[^>]*>([^<]+?)</a>',
        "base_url": "https://chuneng.ofweek.com",
        "min_count": 5,
    },
    "gg": {
        "name": "高工储能",
        "url": "https://www.gg-lb.com/",
        "pattern": r'href="(/news/\d+\.html)"[^>]*>([^<]+?)</a>',
        "base_url": "https://www.gg-lb.com",
        "min_count": 3,
    },
}


# ============== 爬虫函数 ==============

def scrape_source(source_key: str, config: Dict) -> CrawlResult:
    """
    爬取单个数据源
    
    这是一个独立函数，用于线程池执行
    """
    start_time = time.time()
    scraper = SmartScraper(min_interval=0.5)
    
    try:
        html = scraper.fetch(config["url"], source=config["name"])
        
        if not html:
            return CrawlResult(
                source=config["name"],
                success=False,
                items=[],
                duration=time.time() - start_time,
                error="无法获取页面内容"
            )
        
        # 解析内容
        news = []
        try:
            for link, title in re.findall(config["pattern"], html):
                title = title.strip()
                if len(title) > 10:
                    full_url = link if link.startswith('http') else config["base_url"] + link
                    news.append({
                        "title": title,
                        "url": full_url,
                        "source": config["name"],
                        "fetched_at": datetime.now().isoformat()
                    })
        except Exception as e:
            return CrawlResult(
                source=config["name"],
                success=False,
                items=[],
                duration=time.time() - start_time,
                error=f"解析失败: {str(e)[:50]}"
            )
        
        # 去重
        seen = set()
        unique = [n for n in news if not (n["url"] in seen or seen.add(n["url"]))]
        
        return CrawlResult(
            source=config["name"],
            success=len(unique) >= config.get("min_count", 3),
            items=unique,
            duration=time.time() - start_time,
            item_count=len(unique)
        )
        
    except Exception as e:
        return CrawlResult(
            source=config["name"],
            success=False,
            items=[],
            duration=time.time() - start_time,
            error=f"异常: {str(e)[:50]}"
        )


# ============== 并行爬虫主类 ==============

class ParallelCrawler:
    """并行爬虫控制器"""
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.stats = {
            "start_time": None,
            "end_time": None,
            "total_duration": 0,
            "sources_attempted": 0,
            "sources_success": 0,
            "total_items": 0,
        }
    
    def crawl(self, source_keys: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        并行爬取多个数据源
        
        Args:
            source_keys: 指定爬取的数据源，None = 全部
        
        Returns:
            聚合结果和统计信息
        """
        self.stats["start_time"] = datetime.now().isoformat()
        start = time.time()
        
        # 选择数据源
        if source_keys:
            configs = {k: SOURCES_CONFIG[k] for k in source_keys if k in SOURCES_CONFIG}
        else:
            configs = SOURCES_CONFIG
        
        self.stats["sources_attempted"] = len(configs)
        
        print(f"🚀 启动并行爬虫 (max_workers={self.max_workers})")
        print(f"📡 数据源: {', '.join(configs.keys())}")
        print("-" * 60)
        
        results = []
        all_items = []
        
        # 使用线程池并行执行
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            future_to_source = {
                executor.submit(scrape_source, key, config): (key, config)
                for key, config in configs.items()
            }
            
            # 处理完成的任务
            for future in as_completed(future_to_source):
                source_key, config = future_to_source[future]
                try:
                    result = future.result()
                    results.append(result)
                    
                    status = "✅" if result.success else "⚠️"
                    print(f"{status} {result.source:12s} | {result.item_count:2d}条 | {result.duration:.1f}s")
                    
                    if result.error:
                        print(f"   └─ 错误: {result.error}")
                    
                    if result.success:
                        self.stats["sources_success"] += 1
                        all_items.extend(result.items)
                        
                except Exception as e:
                    print(f"❌ {config['name']:12s} | 异常: {str(e)[:40]}")
                    results.append(CrawlResult(
                        source=config["name"],
                        success=False,
                        items=[],
                        duration=0,
                        error=str(e)
                    ))
        
        # 全局去重
        seen_urls = set()
        unique_items = [item for item in all_items if not (item["url"] in seen_urls or seen_urls.add(item["url"]))]
        
        self.stats["end_time"] = datetime.now().isoformat()
        self.stats["total_duration"] = time.time() - start
        self.stats["total_items"] = len(unique_items)
        
        return {
            "items": unique_items,
            "results": [asdict(r) for r in results],
            "stats": self.stats,
        }
    
    def save(self, data: Dict[str, Any], output_dir: Optional[Path] = None) -> Path:
        """保存结果到文件"""
        if output_dir is None:
            output_dir = Path(__file__).parent / "data" / "crawled"
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"parallel_crawl_{timestamp}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return output_file


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="并行爬虫原型")
    parser.add_argument("--max-workers", "-w", type=int, default=4, help="并行线程数")
    parser.add_argument("--sources", "-s", type=str, help="指定数据源，逗号分隔 (如: bjx,cnnes)")
    parser.add_argument("--output", "-o", type=str, help="输出目录")
    args = parser.parse_args()
    
    # 解析数据源
    source_keys = None
    if args.sources:
        source_keys = [s.strip() for s in args.sources.split(",")]
    
    # 运行爬虫
    crawler = ParallelCrawler(max_workers=args.max_workers)
    result = crawler.crawl(source_keys)
    
    # 打印统计
    print("-" * 60)
    print(f"📊 统计结果:")
    print(f"   总耗时: {result['stats']['total_duration']:.1f}s")
    print(f"   数据源: {result['stats']['sources_success']}/{result['stats']['sources_attempted']} 成功")
    print(f"   总条数: {result['stats']['total_items']} 条（去重后）")
    
    # 对比串行时间估算
    total_parallel_time = sum(r.duration for r in [CrawlResult(**x) for x in result['results']])
    print(f"   串行估算: ~{total_parallel_time:.1f}s")
    print(f"   效率提升: {total_parallel_time / result['stats']['total_duration']:.1f}x")
    
    # 保存结果
    output_dir = Path(args.output) if args.output else None
    output_file = crawler.save(result, output_dir)
    print(f"\n💾 结果保存: {output_file}")


if __name__ == "__main__":
    main()
