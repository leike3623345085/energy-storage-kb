#!/usr/bin/env python3
"""
储能数据实时同步到飞书 Bitable
实时监控 data/ 目录，新数据自动同步
"""

import os
import json
import time
import sys
from datetime import datetime
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# 飞书配置
FEISHU_CONFIG = {
    "app_id": "cli_a934994591785cb3",
    "app_secret": "uBiJm9Xuv6xsNWHdAOq6Hgovp82mrItY",
    "bitable_app_token": "Pqpwbh5tkaSzdrsKvrhcfggVnGe",
    "tables": {
        "crawler": "tblbWZx9H76QpxCl",
        "search": "tblXS2e1FDVJlJ6m",
        "stocks": "tblKruLIh89NgNNL",
        "reports": "tbla0u1wX7kLQJ09"
    }
}

# 数据目录
DATA_DIR = Path("/root/.openclaw/workspace/energy_storage/data")

class FeishuSync:
    """飞书同步类"""
    
    def __init__(self):
        self.access_token = None
        self.token_expires = 0
        
    def get_access_token(self):
        """获取飞书访问令牌"""
        if self.access_token and time.time() < self.token_expires:
            return self.access_token
            
        import requests
        
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        headers = {"Content-Type": "application/json"}
        data = {
            "app_id": FEISHU_CONFIG["app_id"],
            "app_secret": FEISHU_CONFIG["app_secret"]
        }
        
        try:
            resp = requests.post(url, headers=headers, json=data, timeout=10)
            result = resp.json()
            if result.get("code") == 0:
                self.access_token = result["tenant_access_token"]
                self.token_expires = time.time() + result["expire"] - 60
                return self.access_token
            else:
                print(f"获取 Token 失败: {result}")
                return None
        except Exception as e:
            print(f"获取 Token 错误: {e}")
            return None
    
    def create_bitable(self, name, description="储能行业监控数据"):
        """创建多维表格"""
        import requests
        
        token = self.get_access_token()
        if not token:
            return None
            
        url = "https://open.feishu.cn/open-apis/bitable/v1/apps"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        data = {
            "name": name,
            "description": description
        }
        
        try:
            resp = requests.post(url, headers=headers, json=data, timeout=10)
            result = resp.json()
            print(f"API 响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
            if result.get("code") == 0:
                app_token = result["data"]["app"]["app_token"]
                print(f"✅ 创建 Bitable 成功: {app_token}")
                return app_token
            else:
                print(f"创建 Bitable 失败: {result}")
                return None
        except Exception as e:
            print(f"创建 Bitable 错误: {e}")
            return None
    
    def add_record(self, table_id, fields):
        """添加记录到 Bitable"""
        import requests
        
        token = self.get_access_token()
        if not token:
            return False
        
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_CONFIG['bitable_app_token']}/tables/{table_id}/records"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        # 转换字段格式 - 处理日期字段
        record_fields = {}
        for key, value in fields.items():
            # 日期字段需要转换为时间戳（毫秒）
            if key == "日期" or key == "时间":
                if value and isinstance(value, str):
                    # 尝试转换为 ISO 格式或时间戳
                    try:
                        from datetime import datetime
                        if len(value) == 10 and value.count('-') == 2:  # YYYY-MM-DD
                            dt = datetime.strptime(value, "%Y-%m-%d")
                            record_fields[key] = int(dt.timestamp() * 1000)
                        elif len(value) == 8 and value.isdigit():  # YYYYMMDD
                            dt = datetime.strptime(value, "%Y%m%d")
                            record_fields[key] = int(dt.timestamp() * 1000)
                        else:
                            record_fields[key] = value
                    except:
                        record_fields[key] = value
                else:
                    record_fields[key] = value
            elif isinstance(value, (int, float)):
                record_fields[key] = value
            elif isinstance(value, str) and len(value) > 1000:
                record_fields[key] = value[:1000] + "..."
            else:
                record_fields[key] = value or ""
        
        data = {"fields": record_fields}
        
        try:
            resp = requests.post(url, headers=headers, json=data, timeout=10)
            result = resp.json()
            if result.get("code") == 0:
                return True
            else:
                print(f"  ⚠️ 写入失败: {result.get('msg', '未知错误')}")
                return False
        except Exception as e:
            print(f"  ⚠️ 写入错误: {e}")
            return False

    def sync_crawler_data(self, file_path):
        """同步爬虫数据"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            table_id = FEISHU_CONFIG["tables"]["crawler"]
            if not table_id:
                print("  ⚠️ 爬虫表未配置")
                return
            
            # 提取新闻列表
            news_list = data.get("news", [])
            if not news_list and "data" in data:
                news_list = data.get("data", [])
            
            count = 0
            for item in news_list[:20]:  # 每次最多20条
                record = {
                    "时间": data.get("fetch_time", ""),
                    "来源": item.get("source", ""),
                    "标题": item.get("title", ""),
                    "内容": item.get("content", "")[:500],
                    "URL": item.get("url", ""),
                    "网站": item.get("site", "")
                }
                if self.add_record(table_id, record):
                    count += 1
            
            print(f"  ✅ 同步 {count}/{len(news_list)} 条爬虫数据")
            
        except Exception as e:
            print(f"  ⚠️ 解析失败 {file_path}: {e}")
    
    def sync_search_data(self, file_path):
        """同步搜索数据"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            table_id = FEISHU_CONFIG["tables"]["search"]
            if not table_id:
                print("  ⚠️ 搜索表未配置")
                return
            
            results = data.get("results", [])
            count = 0
            for item in results[:10]:  # 每次最多10条
                record = {
                    "时间": data.get("timestamp", ""),
                    "类型": data.get("type", ""),
                    "标题": item.get("title", ""),
                    "摘要": item.get("summary", "")[:500],
                    "URL": item.get("url", ""),
                    "日期": item.get("date", "")
                }
                if self.add_record(table_id, record):
                    count += 1
            
            print(f"  ✅ 同步 {count}/{len(results)} 条搜索数据")
                
        except Exception as e:
            print(f"  ⚠️ 解析失败 {file_path}: {e}")

    def sync_stock_data(self, file_path):
        """同步股票数据"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            table_id = FEISHU_CONFIG["tables"]["stocks"]
            if not table_id:
                print("  ⚠️ 股票表未配置")
                return
            
            stocks = data.get("stocks", [])
            count = 0
            for item in stocks:
                record = {
                    "日期": data.get("date", ""),
                    "股票代码": item.get("code", ""),
                    "股票名称": item.get("name", ""),
                    "最新价": item.get("price", 0),
                    "涨跌幅": item.get("change", 0),
                    "成交量": item.get("volume", 0),
                    "市值": item.get("market_cap", 0)
                }
                if self.add_record(table_id, record):
                    count += 1
            
            print(f"  ✅ 同步 {count}/{len(stocks)} 条股票数据")
                
        except Exception as e:
            print(f"  ⚠️ 解析失败 {file_path}: {e}")
    
    def sync_report(self, file_path):
        """同步报告"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            table_id = FEISHU_CONFIG["tables"]["reports"]
            if not table_id:
                print("  ⚠️ 报告表未配置")
                return
            
            # 提取标题和日期
            filename = file_path.name
            if filename.startswith("deep_analysis_"):
                report_type = "深度分析"
                date_str = filename.replace("deep_analysis_", "").replace(".md", "")
            elif filename.startswith("daily_report_"):
                report_type = "日报"
                date_str = filename.replace("daily_report_", "").replace(".md", "")
            elif filename.startswith("weekly_report_"):
                report_type = "周报"
                date_str = filename.replace("weekly_report_", "").replace(".md", "")
            else:
                report_type = "其他"
                date_str = ""
            
            # 提取标题（第一行）
            title = ""
            for line in content.split('\n')[:5]:
                if line.startswith('# '):
                    title = line.replace('# ', '')
                    break
            
            # 转换日期格式
            formatted_date = ""
            if date_str and len(date_str) == 8:
                formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
            
            record = {
                "类型": report_type,
                "日期": formatted_date or date_str,
                "标题": title or filename,
                "内容": content[:2000],
                "文件名": filename
            }
            
            if self.add_record(table_id, record):
                print(f"  ✅ 同步报告: {report_type} - {date_str}")
            
        except Exception as e:
            print(f"  ⚠️ 解析失败 {file_path}: {e}")


class DataSyncHandler(FileSystemEventHandler):
    """文件监控处理器"""
    
    def __init__(self, sync_client):
        self.sync = sync_client
        self.processed_files = set()
        
    def on_created(self, event):
        """新文件创建时触发"""
        if event.is_directory:
            return
            
        file_path = Path(event.src_path)
        
        # 避免重复处理
        if file_path in self.processed_files:
            return
        self.processed_files.add(file_path)
        
        print(f"\n📁 检测到新文件: {file_path}")
        
        # 根据目录判断数据类型
        parent = file_path.parent.name
        
        if parent == "crawler" and file_path.suffix == ".json":
            self.sync.sync_crawler_data(file_path)
        elif parent == "news" and file_path.suffix == ".json":
            self.sync.sync_search_data(file_path)
        elif parent == "finance" and file_path.suffix == ".json":
            self.sync.sync_stock_data(file_path)
        elif parent == "reports" and file_path.suffix in [".md", ".html"]:
            self.sync.sync_report(file_path)
        else:
            print(f"  ℹ️ 跳过: {parent}/{file_path.name}")


def init_bitable():
    """初始化 Bitable"""
    sync = FeishuSync()
    
    print("🚀 初始化飞书多维表格...")
    print("=" * 50)
    
    # 创建主表格
    app_token = sync.create_bitable("储能行业监控数据", "实时同步储能行业新闻、搜索、股票数据")
    
    if app_token:
        print(f"\n✅ Bitable App Token: {app_token}")
        print("\n请将此 Token 填入 FEISHU_CONFIG['bitable_app_token']")
        return app_token
    else:
        print("\n❌ 创建失败")
        return None


def start_sync():
    """启动实时同步"""
    sync = FeishuSync()
    handler = DataSyncHandler(sync)
    
    print("🔄 启动储能数据实时同步...")
    print("=" * 50)
    print(f"监控目录: {DATA_DIR}")
    print("按 Ctrl+C 停止\n")
    
    # 创建观察者
    observer = Observer()
    observer.schedule(handler, str(DATA_DIR), recursive=True)
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("\n⏹️ 同步已停止")
    
    observer.join()


def sync_all_history():
    """同步所有历史数据"""
    sync = FeishuSync()
    
    print("📚 同步历史数据...")
    print("=" * 50)
    
    # 同步爬虫数据
    crawler_dir = DATA_DIR / "crawler"
    if crawler_dir.exists():
        for file in sorted(crawler_dir.glob("*.json")):
            sync.sync_crawler_data(file)
    
    # 同步搜索数据
    news_dir = DATA_DIR / "news"
    if news_dir.exists():
        for file in sorted(news_dir.glob("*.json")):
            sync.sync_search_data(file)
    
    # 同步报告
    reports_dir = DATA_DIR / "reports"
    if reports_dir.exists():
        for file in sorted(reports_dir.glob("*.md")):
            sync.sync_report(file)
    
    print("\n✅ 历史数据同步完成")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="储能数据飞书同步工具")
    parser.add_argument("command", choices=["init", "sync", "realtime"], 
                       help="init: 初始化Bitable, sync: 同步历史数据, realtime: 实时同步")
    
    args = parser.parse_args()
    
    if args.command == "init":
        init_bitable()
    elif args.command == "sync":
        sync_all_history()
    elif args.command == "realtime":
        start_sync()
