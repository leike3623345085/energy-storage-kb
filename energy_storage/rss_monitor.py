#!/usr/bin/env python3
"""
储能行业RSS订阅监控
直接抓取特定网站的RSS源，获取最新资讯
"""

import json
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
import urllib.request
import urllib.error
import ssl

# RSS源配置
RSS_SOURCES = {
    "ofweek_storage": {
        "name": "OFweek储能网",
        "url": "https://chuneng.ofweek.com/rss/",
        "category": "行业媒体",
        "enabled": False  # 404 Not Found
    },
    "bjx_storage": {
        "name": "北极星储能网",
        "url": "https://news.bjx.com.cn/rss/",
        "category": "行业媒体", 
        "enabled": False  # 404 Not Found
    },
    "escn": {
        "name": "中国储能网",
        "url": "http://www.escn.com.cn/rss/",
        "category": "行业媒体",
        "enabled": False  # 连接超时
    },
    "gg_storage": {
        "name": "高工储能",
        "url": "https://www.gg-lb.com/rss/",
        "category": "行业媒体",
        "enabled": False  # 可能需要验证
    },
    "energy_trend": {
        "name": "集邦新能源",
        "url": "https://newenergy.ofweek.com/rss/",
        "category": "行业媒体",
        "enabled": False  # 可能失效
    }
}

# 财经API配置
FINANCE_APIS = {
    "eastmoney": {
        "name": "东方财富",
        "base_url": "https://push2.eastmoney.com/api/qt/clist/get",
        "params": {
            "pn": 1,
            "pz": 20,
            "po": 1,
            "np": 1,
            "fltt": 2,
            "invt": 2,
            "fid": "f12",
            "fs": "m:0+t:11,m:1+t:2",  # 储能相关板块
            "fields": "f12,f13,f14,f20,f21,f23,f24,f25,f26,f27,f28,f29,f30,f31,f32,f33,f34,f35,f36,f37,f38,f39,f40,f41,f42,f43,f44,f45,f46,f47,f48,f49,f50,f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65,f66,f67,f68,f69,f70,f71,f72,f73,f74,f75,f76,f77,f78,f79,f80,f81,f82,f83,f84,f85,f86,f87,f88,f89,f90,f91"
        }
    },
    "sina_finance": {
        "name": "新浪财经",
        "base_url": "https://finance.sina.com.cn/stock/",
        "enabled": True
    }
}

class RSSMonitor:
    """RSS监控器"""
    
    def __init__(self, data_dir=None):
        if data_dir is None:
            self.data_dir = Path(__file__).parent / "data" / "rss"
        else:
            self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建SSL上下文（忽略证书验证）
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE
    
    def fetch_rss(self, url, timeout=10):
        """获取RSS内容"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout, context=self.ssl_context) as response:
                return response.read().decode('utf-8', errors='ignore')
        except Exception as e:
            print(f"获取RSS失败 {url}: {e}")
            return None
    
    def parse_rss(self, xml_content, source_name, category):
        """解析RSS内容"""
        if not xml_content:
            return []
        
        items = []
        try:
            root = ET.fromstring(xml_content)
            
            # 处理不同命名空间
            ns = {'content': 'http://purl.org/rss/1.0/modules/content/'}
            
            for item in root.findall('.//item'):
                title = item.find('title')
                link = item.find('link')
                pub_date = item.find('pubDate')
                description = item.find('description')
                
                news_item = {
                    "title": title.text if title is not None else "",
                    "url": link.text if link is not None else "",
                    "pub_date": pub_date.text if pub_date is not None else "",
                    "description": description.text if description is not None else "",
                    "source": source_name,
                    "category": category,
                    "fetched_at": datetime.now().isoformat()
                }
                items.append(news_item)
        except Exception as e:
            print(f"解析RSS失败: {e}")
        
        return items
    
    def fetch_all(self):
        """获取所有RSS源"""
        all_news = []
        
        for key, config in RSS_SOURCES.items():
            if not config.get("enabled", True):
                continue
            
            print(f"正在获取: {config['name']}...")
            xml_content = self.fetch_rss(config["url"])
            
            if xml_content:
                items = self.parse_rss(xml_content, config["name"], config["category"])
                all_news.extend(items)
                print(f"  ✓ 获取到 {len(items)} 条资讯")
            else:
                print(f"  ✗ 获取失败")
        
        return all_news
    
    def save_news(self, news_items):
        """保存新闻到文件"""
        if not news_items:
            return
        
        date_str = datetime.now().strftime("%Y%m%d")
        output_file = self.data_dir / f"rss_news_{date_str}.json"
        
        # 加载已有数据
        existing = []
        if output_file.exists():
            with open(output_file, 'r', encoding='utf-8') as f:
                existing = json.load(f)
        
        # 去重（基于URL）
        existing_urls = {item["url"] for item in existing}
        new_items = [item for item in news_items if item["url"] not in existing_urls]
        
        # 合并保存
        all_items = existing + new_items
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_items, f, ensure_ascii=False, indent=2)
        
        print(f"\n保存完成: {output_file}")
        print(f"新增 {len(new_items)} 条，总计 {len(all_items)} 条")
        
        return new_items

class FinanceAPI:
    """财经API接口"""
    
    def __init__(self):
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE
    
    def get_storage_stocks(self):
        """获取储能相关股票行情"""
        # 储能概念股代码
        storage_codes = [
            "300750",  # 宁德时代
            "002594",  # 比亚迪
            "300014",  # 亿纬锂能
            "002074",  # 国轩高科
            "300438",  # 鹏辉能源
            "002121",  # 科陆电子
            "300068",  # 南都电源
            "002335",  # 科华数据
            "300274",  # 阳光电源
            "002518",  # 科士达
        ]
        
        results = []
        for code in storage_codes:
            try:
                data = self._fetch_stock_data(code)
                if data:
                    results.append(data)
            except Exception as e:
                print(f"获取股票 {code} 失败: {e}")
        
        return results
    
    def _fetch_stock_data(self, code):
        """获取单只股票数据"""
        # 东方财富API
        url = f"https://push2.eastmoney.com/api/qt/stock/get?secid=0.{code}&fields=f43,f44,f45,f46,f47,f48,f49,f50,f51,f52,f57,f58,f60,f170"
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10, context=self.ssl_context) as response:
                data = json.loads(response.read().decode('utf-8'))
                return data.get('data', {})
        except:
            return None

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='储能行业RSS监控')
    parser.add_argument('--rss', action='store_true', help='获取RSS资讯')
    parser.add_argument('--stocks', action='store_true', help='获取股票行情')
    parser.add_argument('--all', action='store_true', help='获取所有数据')
    
    args = parser.parse_args()
    
    if args.all or args.rss:
        print("=" * 50)
        print("获取RSS资讯...")
        print("=" * 50)
        
        monitor = RSSMonitor()
        news = monitor.fetch_all()
        monitor.save_news(news)
    
    if args.all or args.stocks:
        print("\n" + "=" * 50)
        print("获取储能股票行情...")
        print("=" * 50)
        
        finance = FinanceAPI()
        stocks = finance.get_storage_stocks()
        print(f"获取到 {len(stocks)} 只股票数据")
        
        # 保存股票数据
        data_dir = Path(__file__).parent / "data" / "finance"
        data_dir.mkdir(parents=True, exist_ok=True)
        
        date_str = datetime.now().strftime("%Y%m%d")
        stock_file = data_dir / f"stocks_{date_str}.json"
        
        with open(stock_file, 'w', encoding='utf-8') as f:
            json.dump({
                "date": date_str,
                "stocks": stocks,
                "updated_at": datetime.now().isoformat()
            }, f, ensure_ascii=False, indent=2)
        
        print(f"股票数据已保存: {stock_file}")
    
    if not any([args.all, args.rss, args.stocks]):
        parser.print_help()

if __name__ == "__main__":
    main()
