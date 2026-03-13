#!/usr/bin/env python3
"""
储能行业网站爬虫 - 多站点修复版 V2
站点：北极星储能网、储能中国网、中关村储能联盟、中国储能网等
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
        self.min_interval = 2
        self.errors = []  # 记录错误
    
    def log_error(self, source, message):
        """记录错误"""
        self.errors.append({
            "source": source,
            "message": message,
            "time": datetime.now().isoformat()
        })
    
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
    
    def fetch(self, url, timeout=15, retry=3, source=""):
        """获取网页内容，带重试机制"""
        self._wait()
        for i in range(retry):
            try:
                req = urllib.request.Request(url, headers=self._get_headers())
                with urllib.request.urlopen(req, timeout=timeout, context=ssl_context) as response:
                    if 'Set-Cookie' in response.headers:
                        self.cookie = response.headers['Set-Cookie'].split(';')[0]
                    content = response.read().decode('utf-8', errors='ignore')
                    if len(content) < 1000:  # 内容太少，可能是反爬或错误页面
                        self.log_error(source, f"内容过少: {len(content)} bytes")
                        return None
                    return content
            except Exception as e:
                error_msg = str(e)[:60]
                print(f"    重试 {i+1}/{retry}: {error_msg}")
                self.log_error(source, f"第{i+1}次请求失败: {error_msg}")
                if i < retry - 1:
                    time.sleep(2 ** i)  # 指数退避
        return None


def scrape_source(scraper, name, url, pattern, source_key, base_url="", min_count=5):
    """
    通用爬虫函数
    
    参数:
        scraper: SmartScraper实例
        name: 来源名称
        url: 目标URL
        pattern: 正则匹配模式
        source_key: 来源标识
        base_url: 基础URL(用于拼接完整链接)
        min_count: 最少期望获取数量
    """
    print(f"\n[{name}] 抓取中...")
    html = scraper.fetch(url, source=name)
    
    if not html:
        scraper.log_error(name, "无法获取页面内容")
        return []
    
    news = []
    try:
        for link, title in re.findall(pattern, html):
            title = title.strip()
            if len(title) > 10:
                full_url = link if link.startswith('http') else base_url + link
                news.append({
                    "title": title,
                    "url": full_url,
                    "source": name,
                    "fetched_at": datetime.now().isoformat()
                })
    except Exception as e:
        scraper.log_error(name, f"解析失败: {str(e)[:50]}")
    
    # 去重
    seen = set()
    unique = [n for n in news if not (n["url"] in seen or seen.add(n["url"]))]
    
    if len(unique) < min_count:
        scraper.log_error(name, f"数据量不足: 仅获取{len(unique)}条, 期望{min_count}条")
    
    print(f"  ✓ 获取 {len(unique)} 条")
    return unique


def scrape_bjx(scraper):
    """北极星储能网"""
    return scrape_source(
        scraper, "北极星储能网",
        "https://chuneng.bjx.com.cn/",
        r'href="https?://(news\.bjx\.com\.cn/html/\d{8}/\d+\.shtml)"[^>]*>([^<]+?)</a>',
        "北极星储能网",
        "https://",
        min_count=10
    )


def scrape_cnnes(scraper):
    """储能中国网"""
    return scrape_source(
        scraper, "储能中国网",
        "http://www.cnnes.cc/",
        r'href="(/hangye/[^"]+\.html)"[^>]*>([^<]+?)</a>',
        "储能中国网",
        "http://www.cnnes.cc",
        min_count=5
    )


def scrape_cnesa(scraper):
    """中关村储能产业技术联盟"""
    return scrape_source(
        scraper, "中关村储能联盟",
        "https://www.cnesa.org/information/?column_id=69",
        r'<a href="(/information/detail/\?column_id=\d+&id=\d+)" title="([^"]+)"',
        "中关村储能联盟",
        "https://www.cnesa.org",
        min_count=5
    )


def scrape_jsesa(scraper):
    """江苏省储能行业协会"""
    return scrape_source(
        scraper, "江苏省储能行业协会",
        "https://jsesa.com.cn/",
        r'href="(/col\d+/\d+\.html)"[^>]*>([^<]+?)</a>',
        "江苏省储能行业协会",
        "https://jsesa.com.cn",
        min_count=3
    )


def scrape_gf(scraper):
    """北极星光伏网-储能栏目"""
    return scrape_source(
        scraper, "北极星光伏网",
        "https://guangfu.bjx.com.cn/chuneng/",
        r'href="https?://(guangfu\.bjx\.com\.cn/html/\d{8}/\d+\.shtml)"[^>]*>([^<]+?)</a>',
        "北极星光伏网",
        "https://",
        min_count=5
    )


def scrape_gglb(scraper):
    """高工储能"""
    return scrape_source(
        scraper, "高工储能",
        "https://www.gg-lb.com/",
        r'href="(/news/\d+\.html)"[^>]*>([^<]+?)</a>',
        "高工储能",
        "https://www.gg-lb.com",
        min_count=5
    )


def scrape_ofweek(scraper):
    """OFweek储能"""
    return scrape_source(
        scraper, "OFweek储能",
        "https://libattery.ofweek.com/",
        r'href="(/\d{4}-\d{2}/[A-Z]+-\d+\.shtml)"[^>]*>([^<]+?)</a>',
        "OFweek储能",
        "https://libattery.ofweek.com",
        min_count=5
    )


def scrape_escn(scraper):
    """中国储能网"""
    return scrape_source(
        scraper, "中国储能网",
        "http://www.escn.com.cn/",
        r'href="(/news/show-\d+\.html)"[^>]*>([^<]+?)</a>',
        "中国储能网",
        "http://www.escn.com.cn",
        min_count=10
    )


def save_result(data_dir, all_news, errors, sources_status):
    """保存爬取结果和日志"""
    data_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now()
    filename = f"crawler_{timestamp.strftime('%Y%m%d_%H%M')}.json"
    filepath = data_dir / filename
    
    # 构建结果数据
    result = {
        "fetch_time": timestamp.isoformat(),
        "total_count": len(all_news),
        "sources": list(set(n["source"] for n in all_news)),
        "sources_status": sources_status,  # 每个来源的状态
        "errors": errors,  # 错误记录
        "data": all_news
    }
    
    # 保存JSON文件（无论是否有数据）
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    # 同时保存日志文件
    log_filename = f"crawler_{timestamp.strftime('%Y%m%d_%H%M')}.log"
    log_filepath = data_dir / log_filename
    
    with open(log_filepath, 'w', encoding='utf-8') as f:
        f.write(f"爬虫执行日志\n")
        f.write(f"时间: {timestamp}\n")
        f.write(f"总计获取: {len(all_news)} 条\n")
        f.write(f"来源: {', '.join(set(n['source'] for n in all_news))}\n")
        f.write(f"\n来源详情:\n")
        for source, count in sources_status.items():
            f.write(f"  {source}: {count} 条\n")
        if errors:
            f.write(f"\n错误记录 ({len(errors)}条):\n")
            for err in errors:
                f.write(f"  [{err['time']}] {err['source']}: {err['message']}\n")
        else:
            f.write(f"\n无错误记录\n")
    
    return filepath, log_filepath


def main():
    print("=" * 60)
    print("储能行业网站爬虫 - 多站点修复版 V2")
    print(f"运行时间: {datetime.now()}")
    print("=" * 60)
    
    scraper = SmartScraper()
    all_news = []
    sources_status = {}
    
    # 定义所有爬虫任务
    tasks = [
        ("北极星储能网", scrape_bjx),
        ("储能中国网", scrape_cnnes),
        ("中关村储能联盟", scrape_cnesa),
        ("江苏省储能行业协会", scrape_jsesa),
        ("北极星光伏网", scrape_gf),
        ("高工储能", scrape_gglb),
        ("OFweek储能", scrape_ofweek),
        ("中国储能网", scrape_escn),
    ]
    
    # 执行所有爬虫任务
    for name, func in tasks:
        try:
            news = func(scraper)
            sources_status[name] = len(news)
            all_news.extend(news)
        except Exception as e:
            scraper.log_error(name, f"执行异常: {str(e)[:50]}")
            sources_status[name] = 0
            print(f"  ✗ {name} 执行失败: {str(e)[:40]}")
    
    # 数据目录
    data_dir = Path(__file__).parent / "data" / "crawler"
    
    # 保存结果（无论是否有数据）
    filepath, logpath = save_result(data_dir, all_news, scraper.errors, sources_status)
    
    # 输出结果
    print(f"\n{'='*60}")
    if all_news:
        print(f"✅ 完成! 总计: {len(all_news)} 条")
        print(f"   来源: {', '.join(set(n['source'] for n in all_news))}")
        print(f"   保存: {filepath}")
        print(f"   日志: {logpath}")
        
        print(f"\n📰 最新5条:")
        for i, item in enumerate(all_news[:5], 1):
            print(f"   {i}. [{item['source']}] {item['title'][:40]}...")
    else:
        print(f"⚠️ 未获取到数据")
        print(f"   日志: {logpath}")
        print(f"   请检查日志了解失败原因")
    
    if scraper.errors:
        print(f"\n⚠️ 警告: 发生 {len(scraper.errors)} 个错误")
        for err in scraper.errors[:5]:
            print(f"   - {err['source']}: {err['message']}")
    
    # 数据量检查
    if len(all_news) < 20:
        print(f"\n⚠️ 数据量偏少({len(all_news)}条)，建议检查网络或目标网站状态")
        return False  # 返回失败状态，便于定时任务监控
    
    return True


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
