#!/usr/bin/env python3
"""
储能数据批量同步到飞书 Bitable
最多同步5个历史文件
直接写入 Bitable，不走 Markdown 中间格式
"""

import os
import sys
import json
import time
import requests
from datetime import datetime, timedelta
from pathlib import Path

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

# 记录上限配置
MAX_RECORDS = 20000
WARNING_THRESHOLD = 19500


class FeishuSync:
    def __init__(self):
        self.access_token = None
        self.token_expires = 0
        
    def get_access_token(self):
        """获取飞书访问令牌"""
        if self.access_token and time.time() < self.token_expires:
            return self.access_token
            
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
                print(f"❌ 获取 Token 失败: {result}")
                return None
        except Exception as e:
            print(f"❌ 获取 Token 错误: {e}")
            return None
    
    def get_record_count(self, table_id):
        """获取表格记录数"""
        token = self.get_access_token()
        if not token:
            return 0
        
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_CONFIG['bitable_app_token']}/tables/{table_id}/records"
        headers = {"Authorization": f"Bearer {token}"}
        params = {"page_size": 1}
        
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=10)
            result = resp.json()
            if result.get("code") == 0:
                data = result.get("data", {})
                total = data.get("total", 0)
                return total
            else:
                print(f"⚠️ 获取记录数失败: {result.get('msg', '未知错误')}")
                return 0
        except Exception as e:
            print(f"⚠️ 获取记录数错误: {e}")
            return 0
    
    def delete_oldest_records_simple(self, table_id, count):
        """简单删除最早的记录 - 限制最多删除50条避免超时"""
        token = self.get_access_token()
        if not token:
            return 0
        
        headers = {"Authorization": f"Bearer {token}"}
        deleted = 0
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_CONFIG['bitable_app_token']}/tables/{table_id}/records"
        
        # 限制最多删除50条
        count = min(count, 50)
        max_iterations = 5  # 最多5轮
        iteration = 0
        
        while deleted < count and iteration < max_iterations:
            iteration += 1
            batch_size = min(10, count - deleted)  # 每批10条
            
            try:
                resp = requests.get(url, headers=headers, params={"page_size": batch_size}, timeout=10)
                result = resp.json()
                if result.get("code") != 0:
                    print(f"      ⚠️ 获取记录失败: {result.get('msg', '未知错误')}")
                    break
                
                items = result.get("data", {}).get("items", [])
                if not items:
                    print(f"      ℹ️ 没有更多记录可删除")
                    break
                
                batch_deleted = 0
                for record in items:
                    record_id = record.get("record_id")
                    if record_id:
                        del_url = f"{url}/{record_id}"
                        try:
                            del_resp = requests.delete(del_url, headers=headers, timeout=5)
                            del_result = del_resp.json()
                            if del_result.get("code") == 0:
                                deleted += 1
                                batch_deleted += 1
                            else:
                                print(f"      ⚠️ 删除单条失败: {del_result.get('msg', '未知错误')}")
                        except Exception as del_e:
                            print(f"      ⚠️ 删除单条异常: {del_e}")
                
                print(f"      📍 第{iteration}轮删除 {batch_deleted} 条")
                
                if batch_deleted == 0:
                    break
                    
            except Exception as e:
                print(f"      ⚠️ 删除错误: {e}")
                break
        
        return deleted
    
    def add_records(self, table_id, records):
        """批量添加记录"""
        token = self.get_access_token()
        if not token or not records:
            return 0
        
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_CONFIG['bitable_app_token']}/tables/{table_id}/records/batch_create"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        added = 0
        for i in range(0, len(records), 500):
            batch = records[i:i+500]
            records_payload = [{"fields": r} for r in batch]
            data = {"records": records_payload}
            
            try:
                resp = requests.post(url, headers=headers, json=data, timeout=30)
                result = resp.json()
                
                if result.get("code") == 0:
                    added += len(batch)
                else:
                    print(f"   ⚠️ 添加失败: {result.get('msg')}")
                    if "limit" in result.get('msg', '').lower() or "exceed" in result.get('msg', '').lower():
                        print(f"   ⚠️ 达到记录上限，停止添加")
                        break
            except Exception as e:
                print(f"   ⚠️ 添加错误: {e}")
        
        return added


def find_data_files(base_dir="/root/.openclaw/workspace/energy_storage/data"):
    """查找所有数据文件"""
    data_path = Path(base_dir)
    if not data_path.exists():
        return []
    
    files = []
    crawler_dir = data_path / "crawler"
    if crawler_dir.exists():
        files.extend(sorted(crawler_dir.glob("*.json"), reverse=True))
    
    news_dir = data_path / "news"
    if news_dir.exists():
        files.extend(sorted(news_dir.glob("*.json"), reverse=True))
    
    return sorted(files, key=lambda x: x.stat().st_mtime, reverse=True)


def load_and_transform_crawler(file_path, start_time_ms):
    """加载爬虫数据并转换为 Bitable 格式"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        records = []
        source = data.get("source", "储能产业网")
        articles = data.get("data", [])
        
        for idx, article in enumerate(articles):
            unique_time_ms = start_time_ms + (idx * 100)
            link = article.get("link", "").strip()
            
            record = {
                "时间": unique_time_ms,
                "来源": source if source and source != "unknown" else "储能产业网",
                "标题": article.get("title", "")[:1000],
                "内容": article.get("summary", "")[:2000] if article.get("summary") else "-",
                "网站": source if source and source != "unknown" else "储能产业网"
            }
            
            if link and link.startswith("http"):
                record["URL"] = {"text": "查看原文", "link": link}
            
            records.append(record)
        
        return records, start_time_ms + (len(articles) * 100)
    except Exception as e:
        print(f"   ⚠️ 加载失败: {e}")
        return [], start_time_ms


def load_and_transform_news(file_path, start_time_ms):
    """加载搜索数据并转换为 Bitable 格式"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        records = []
        query = data.get("query", "")
        results = data.get("results", [])
        
        for idx, result in enumerate(results):
            unique_time_ms = start_time_ms + (idx * 100)
            
            record = {
                "时间": unique_time_ms,
                "类型": query,
                "标题": result.get("title", "")[:1000],
                "摘要": result.get("snippet", "")[:2000] if result.get("snippet") else "-",
            }
            
            link = result.get("url", "").strip()
            if link and link.startswith("http"):
                record["URL"] = {"text": "查看原文", "link": link}
            
            records.append(record)
        
        return records, start_time_ms + (len(results) * 100)
    except Exception as e:
        print(f"   ⚠️ 加载失败: {e}")
        return [], start_time_ms


def sync_files(max_files=5):
    """同步数据文件到飞书"""
    print(f"🚀 储能数据飞书同步")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    sys.stdout.flush()
    
    files = find_data_files()
    if not files:
        print("⚠️ 未找到数据文件")
        return 0, 0
    
    print(f"📁 发现 {len(files)} 个数据文件")
    sys.stdout.flush()
    
    fs = FeishuSync()
    token = fs.get_access_token()
    if not token:
        print("❌ 无法获取飞书访问令牌")
        return 0, 0
    
    synced_count = 0
    total_records = 0
    skipped_count = 0
    current_time_ms = int(time.time() * 1000)
    next_time_ms = current_time_ms
    
    for i, file_path in enumerate(files[:max_files], 1):
        print(f"\n📄 [{i}/{max_files}] {file_path.name}")
        sys.stdout.flush()
        
        if "crawler" in str(file_path):
            records, next_time_ms = load_and_transform_crawler(file_path, next_time_ms)
            table_id = FEISHU_CONFIG["tables"]["crawler"]
        else:
            records, next_time_ms = load_and_transform_news(file_path, next_time_ms)
            table_id = FEISHU_CONFIG["tables"]["search"]
        
        if not records:
            print(f"   ⚠️ 无有效记录")
            continue
        
        # 检查记录数
        current_count = fs.get_record_count(table_id)
        print(f"   📊 当前 {current_count} 条记录")
        sys.stdout.flush()
        
        # 如果接近上限，尝试删除少量旧记录
        if current_count + len(records) > MAX_RECORDS:
            print(f"   ⚠️ 达到记录上限 ({current_count}/{MAX_RECORDS})，跳过")
            skipped_count += 1
            continue
        elif current_count + len(records) > WARNING_THRESHOLD:
            # 只删除少量记录（最多50条）避免超时
            need_delete = min(current_count + len(records) - WARNING_THRESHOLD + 50, 50)
            print(f"   🧹 接近上限，删除 {need_delete} 条旧记录...")
            sys.stdout.flush()
            deleted = fs.delete_oldest_records_simple(table_id, need_delete)
            print(f"   ✅ 已删除 {deleted} 条")
            sys.stdout.flush()
        
        # 添加记录
        added = fs.add_records(table_id, records)
        print(f"   ✅ 写入 {added}/{len(records)} 条")
        sys.stdout.flush()
        
        total_records += added
        synced_count += 1
        time.sleep(0.3)
    
    print(f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"🎉 同步完成")
    print(f"   成功: {synced_count}/{max_files} 个文件")
    print(f"   跳过: {skipped_count} 个文件（达到上限）")
    print(f"   记录: {total_records} 条")
    
    return synced_count, total_records


if __name__ == "__main__":
    max_files = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    sync_files(max_files)