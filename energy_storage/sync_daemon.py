#!/usr/bin/env python3
"""
储能数据实时同步守护进程（轻量版）
只监控新文件，不同步历史数据
"""

import os
import json
import time
import sys
from datetime import datetime
from pathlib import Path

# 数据目录
DATA_DIR = Path("/root/.openclaw/workspace/energy_storage/data")
STATE_FILE = Path("/tmp/sync_feishu_state.json")

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

class FeishuSync:
    def __init__(self):
        self.access_token = None
        self.token_expires = 0
        
    def get_access_token(self):
        import requests
        if self.access_token and time.time() < self.token_expires:
            return self.access_token
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        resp = requests.post(url, json={
            "app_id": FEISHU_CONFIG["app_id"],
            "app_secret": FEISHU_CONFIG["app_secret"]
        }, timeout=10)
        result = resp.json()
        if result.get("code") == 0:
            self.access_token = result["tenant_access_token"]
            self.token_expires = time.time() + result["expire"] - 60
            return self.access_token
        return None
    
    def add_record(self, table_id, fields):
        import requests
        token = self.get_access_token()
        if not token:
            return False
        
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_CONFIG['bitable_app_token']}/tables/{table_id}/records"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        
        # 处理日期字段
        record_fields = {}
        for key, value in fields.items():
            if key in ["日期", "时间"] and value and isinstance(value, str):
                try:
                    if len(value) == 10 and value.count('-') == 2:
                        dt = datetime.strptime(value, "%Y-%m-%d")
                        record_fields[key] = int(dt.timestamp() * 1000)
                    elif len(value) == 8 and value.isdigit():
                        dt = datetime.strptime(value, "%Y%m%d")
                        record_fields[key] = int(dt.timestamp() * 1000)
                    else:
                        record_fields[key] = value
                except:
                    record_fields[key] = value
            elif isinstance(value, str) and len(value) > 1000:
                record_fields[key] = value[:1000] + "..."
            else:
                record_fields[key] = value or ""
        
        try:
            resp = requests.post(url, headers=headers, json={"fields": record_fields}, timeout=10)
            result = resp.json()
            if result.get("code") == 0:
                return True
            else:
                print(f"  ⚠️ 写入失败: {result.get('msg', '未知错误')}")
                return False
        except Exception as e:
            print(f"  ⚠️ 写入错误: {e}")
            return False

    def sync_report(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            table_id = FEISHU_CONFIG["tables"]["reports"]
            filename = file_path.name
            
            # 解析类型和日期（支持更多格式）
            date_str = ""
            if filename.startswith("deep_analysis_"):
                report_type = "深度分析"
                date_str = filename.replace("deep_analysis_", "").replace(".md", "")
            elif filename.startswith("daily_report_"):
                report_type = "日报"
                date_str = filename.replace("daily_report_", "").replace(".md", "")
            elif filename.startswith("weekly_report_"):
                report_type = "周报"
                date_str = filename.replace("weekly_report_", "").replace(".md", "")
            elif filename.startswith("investment_brief_"):
                report_type = "投资简报"
                date_str = filename.replace("investment_brief_", "").replace(".md", "")[:8]
            elif filename.startswith("quick_report_"):
                report_type = "速报"
                date_str = filename.replace("quick_report_", "").replace(".md", "")[:8]
            elif filename.startswith("report_"):
                report_type = "报告"
                date_str = filename.replace("report_", "").replace(".md", "")
            else:
                report_type = "其他"
                date_str = ""
            
            # 格式化日期
            formatted_date = ""
            if date_str and len(date_str) == 8 and date_str.isdigit():
                formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
            else:
                formatted_date = date_str
            
            # 提取标题
            title = ""
            for line in content.split('\n')[:5]:
                if line.startswith('# '):
                    title = line.replace('# ', '')
                    break
            
            # 在内容前添加日期信息
            content_with_date = f"日期: {formatted_date or '未知'}\n\n{content}"
            
            record = {
                "类型": report_type,
                "标题": title or filename,
                "内容": content_with_date[:2000],
                "文件名": filename
            }
            
            if self.add_record(table_id, record):
                print(f"✅ 同步报告: {report_type} - {date_str}")
                return True
            return False
        except Exception as e:
            print(f"⚠️ 解析失败 {file_path}: {e}")
            return False

    def sync_crawler_data(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            table_id = FEISHU_CONFIG["tables"]["crawler"]
            news_list = data.get("news", []) or data.get("data", [])
            
            count = 0
            for item in news_list[:10]:  # 只同步前10条
                record = {
                    "时间": str(data.get("fetch_time", "")),
                    "来源": item.get("source", ""),
                    "标题": item.get("title", ""),
                    "内容": item.get("content", "")[:500],
                    "URL": item.get("url", ""),
                    "网站": item.get("site", "")
                }
                if self.add_record(table_id, record):
                    count += 1
            
            print(f"✅ 同步爬虫数据: {count}条")
            return True
        except Exception as e:
            print(f"⚠️ 解析失败 {file_path}: {e}")
            return False

    def sync_search_data(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            table_id = FEISHU_CONFIG["tables"]["search"]
            results = data.get("results", [])
            
            count = 0
            for item in results[:5]:  # 只同步前5条
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
            
            print(f"✅ 同步搜索数据: {count}条")
            return True
        except Exception as e:
            print(f"⚠️ 解析失败 {file_path}: {e}")
            return False


def load_state():
    """加载已处理文件状态"""
    if STATE_FILE.exists():
        with open(STATE_FILE, 'r') as f:
            return set(json.load(f))
    return set()


def save_state(processed):
    """保存已处理文件状态"""
    with open(STATE_FILE, 'w') as f:
        json.dump(list(processed), f)


def scan_new_files():
    """扫描新文件"""
    new_files = []
    
    # 扫描报告
    reports_dir = DATA_DIR / "reports"
    if reports_dir.exists():
        for f in reports_dir.glob("*.md"):
            new_files.append(("report", f))
    
    # 扫描爬虫数据
    crawler_dir = DATA_DIR / "crawler"
    if crawler_dir.exists():
        for f in crawler_dir.glob("*.json"):
            new_files.append(("crawler", f))
    
    # 扫描搜索数据
    news_dir = DATA_DIR / "news"
    if news_dir.exists():
        for f in news_dir.glob("*.json"):
            # 跳过搜索历史日志文件
            if f.name == "search_history.json":
                continue
            new_files.append(("search", f))
    
    return new_files


def main():
    sync = FeishuSync()
    processed = load_state()
    
    print("🔄 启动储能数据实时同步...")
    print(f"监控目录: {DATA_DIR}")
    print(f"已处理文件: {len(processed)}个")
    print("="*50)
    
    while True:
        try:
            files = scan_new_files()
            new_count = 0
            
            # 限制每次最多处理5个新文件，避免阻塞
            batch_count = 0
            max_batch = 5
            
            for file_type, file_path in files:
                if batch_count >= max_batch:
                    print(f"\n⏸️ 本轮已达上限({max_batch})，剩余文件下次处理")
                    break
                
                file_key = str(file_path)
                if file_key in processed:
                    continue
                
                print(f"\n📁 新文件: {file_path.name}")
                
                success = False
                if file_type == "report":
                    success = sync.sync_report(file_path)
                elif file_type == "crawler":
                    success = sync.sync_crawler_data(file_path)
                elif file_type == "search":
                    success = sync.sync_search_data(file_path)
                
                if success:
                    processed.add(file_key)
                    save_state(processed)
                    new_count += 1
                    batch_count += 1
                
                # 避免API频率限制
                time.sleep(1)
            
            if new_count > 0:
                print(f"\n本次同步完成: {new_count}个文件")
            
            # 每10秒扫描一次
            time.sleep(10)
            
        except KeyboardInterrupt:
            print("\n⏹️ 同步已停止")
            break
        except Exception as e:
            print(f"\n⚠️ 错误: {e}")
            time.sleep(30)  # 出错后等待30秒


if __name__ == "__main__":
    main()
