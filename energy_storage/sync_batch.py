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
MAX_RECORDS = 18000  # 保留空间，避免达到 20000 上限
DELETE_BATCH_SIZE = 500  # 每次删除数量


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
    
    def delete_oldest_records(self, table_id, count):
        """删除最旧的记录"""
        token = self.get_access_token()
        if not token:
            return 0
        
        # 获取最旧的记录
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_CONFIG['bitable_app_token']}/tables/{table_id}/records"
        headers = {"Authorization": f"Bearer {token}"}
        params = {"page_size": min(count, 500)}
        
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=10)
            result = resp.json()
            if result.get("code") != 0:
                print(f"⚠️ 获取记录失败: {result.get('msg')}")
                return 0
            
            records = result.get("data", {}).get("items", [])
            deleted = 0
            
            for record in records:
                record_id = record.get("record_id")
                if record_id:
                    del_url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_CONFIG['bitable_app_token']}/tables/{table_id}/records/{record_id}"
                    del_resp = requests.delete(del_url, headers=headers, timeout=5)
                    if del_resp.json().get("code") == 0:
                        deleted += 1
            
            return deleted
        except Exception as e:
            print(f"⚠️ 删除记录错误: {e}")
            return 0
    
    def add_records(self, table_id, records):
        """批量添加记录"""
        token = self.get_access_token()
        if not token or not records:
            return 0
        
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_CONFIG['bitable_app_token']}/tables/{table_id}/records"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        added = 0
        # 每次最多 500 条
        for i in range(0, len(records), 500):
            batch = records[i:i+500]
            
            # 飞书 API 要求的格式: {"records": [{"fields": {...}}, ...]}
            records_payload = []
            for r in batch:
                records_payload.append({"fields": r})
            
            data = {"records": records_payload}
            
            try:
                resp = requests.post(url, headers=headers, json=data, timeout=30)
                result = resp.json()
                
                if result.get("code") == 0:
                    added += len(batch)
                else:
                    print(f"⚠️ 添加记录失败: {result.get('msg')}")
                    if result.get('error', {}).get('field_violations'):
                        for v in result['error']['field_violations']:
                            print(f"   字段错误: {v['field']} - {v['description']}")
                    # 打印第一条记录帮助调试
                    if batch:
                        print(f"   示例记录: {json.dumps(batch[0], ensure_ascii=False)[:200]}")
            except Exception as e:
                print(f"⚠️ 添加记录错误: {e}")
        
        return added


def find_data_files(base_dir="/root/.openclaw/workspace/energy_storage/data"):
    """查找所有数据文件"""
    data_path = Path(base_dir)
    if not data_path.exists():
        print(f"❌ 数据目录不存在: {base_dir}")
        return []
    
    files = []
    # 查找爬虫数据 (.log 和 .json)
    crawler_dir = data_path / "crawler"
    if crawler_dir.exists():
        files.extend(sorted(crawler_dir.glob("*.json"), reverse=True))
        files.extend(sorted(crawler_dir.glob("*.log"), reverse=True))
    
    # 查找搜索结果 (.json)
    news_dir = data_path / "news"
    if news_dir.exists():
        files.extend(sorted(news_dir.glob("*.json"), reverse=True))
    
    return sorted(files, key=lambda x: x.stat().st_mtime, reverse=True)


def load_and_transform_crawler(file_path, start_time_ms):
    """加载爬虫数据并转换为 Bitable 格式 - 使用字段名而非 field_id"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        records = []
        source = data.get("source", "储能产业网")
        articles = data.get("data", [])
        
        # 使用传入的起始时间戳，每条记录递增 1 秒（1000ms）
        for idx, article in enumerate(articles):
            unique_time_ms = start_time_ms + (idx * 1000)
            
            # URL 处理：空链接时跳过 URL 字段
            link = article.get("link", "").strip()
            
            # 使用字段名（中文）而不是 field_id
            # DateTime 字段使用毫秒时间戳
            record = {
                "时间": unique_time_ms,  # 时间 (DateTime)
                "来源": source if source and source != "unknown" else "储能产业网",  # 来源
                "标题": article.get("title", "")[:1000],  # 标题
                "内容": article.get("summary", "")[:2000] if article.get("summary") else "-",  # 内容
                "网站": source if source and source != "unknown" else "储能产业网"  # 网站
            }
            
            # 只在有有效链接时添加 URL 字段（飞书 URL 字段不能为空）
            if link and link.startswith("http"):
                record["URL"] = {"text": "查看原文", "link": link}
            
            records.append(record)
        
        return records, start_time_ms + (len(articles) * 1000)  # 返回下一个可用的时间戳
    except Exception as e:
        print(f"⚠️ 加载文件失败 {file_path}: {e}")
        return [], start_time_ms


def load_and_transform_news(file_path, start_time_ms):
    """加载搜索数据并转换为 Bitable 格式"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        records = []
        query = data.get("query", "")
        results = data.get("results", [])
        
        # 使用传入的起始时间戳，每条记录递增 1 秒（1000ms）
        for idx, result in enumerate(results):
            unique_time_ms = start_time_ms + (idx * 1000)
            
            record = {
                "时间": unique_time_ms,  # DateTime 字段用毫秒时间戳
                "类型": query,
                "标题": result.get("title", "")[:1000],
                "摘要": result.get("snippet", "")[:2000] if result.get("snippet") else "-",
            }
            
            # URL 处理
            link = result.get("url", "").strip()
            if link and link.startswith("http"):
                record["URL"] = {"text": "查看原文", "link": link}
            
            records.append(record)
        
        return records, start_time_ms + (len(results) * 1000)
    except Exception as e:
        print(f"⚠️ 加载文件失败 {file_path}: {e}")
        return [], start_time_ms


def sync_files(max_files=5):
    """同步数据文件到飞书"""
    print(f"🚀 开始同步（最多 {max_files} 个文件）")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 查找数据文件
    files = find_data_files()
    if not files:
        print("⚠️ 未找到数据文件")
        return 0, 0
    
    print(f"📁 发现 {len(files)} 个数据文件")
    
    # 初始化飞书同步
    fs = FeishuSync()
    token = fs.get_access_token()
    if not token:
        print("❌ 无法获取飞书访问令牌")
        return 0, 0
    
    synced_count = 0
    total_records = 0
    
    # 使用当前时间戳作为起始点，确保不与现有记录冲突
    current_time_ms = int(time.time() * 1000)
    next_time_ms = current_time_ms
    
    # 处理前 max_files 个文件
    for i, file_path in enumerate(files[:max_files], 1):
        print(f"\n📄 [{i}/{max_files}] {file_path.name}")
        
        # 根据文件类型选择处理方式
        if "crawler" in str(file_path):
            records, next_time_ms = load_and_transform_crawler(file_path, next_time_ms)
            table_id = FEISHU_CONFIG["tables"]["crawler"]
        else:
            records, next_time_ms = load_and_transform_news(file_path, next_time_ms)
            table_id = FEISHU_CONFIG["tables"]["search"]
        
        if not records:
            print(f"   ⚠️ 无有效记录")
            continue
        
        # 检查并清理空间
        current_count = fs.get_record_count(table_id)
        if current_count + len(records) > MAX_RECORDS:
            need_delete = current_count + len(records) - MAX_RECORDS + DELETE_BATCH_SIZE
            print(f"   🧹 记录数接近上限 ({current_count}/{MAX_RECORDS})，删除 {need_delete} 条旧记录")
            deleted = fs.delete_oldest_records(table_id, need_delete)
            print(f"   ✅ 已删除 {deleted} 条旧记录")
        
        # 添加记录
        added = fs.add_records(table_id, records)
        print(f"   ✅ 成功写入 {added}/{len(records)} 条记录")
        
        total_records += added
        synced_count += 1
        
        # 间隔，避免 API 限流
        time.sleep(0.5)
    
    print(f"\n🎉 同步完成")
    print(f"   文件数: {synced_count}/{max_files}")
    print(f"   记录数: {total_records}")
    print(f"   剩余: {len(files) - synced_count} 个文件待处理")
    
    return synced_count, total_records


if __name__ == "__main__":
    max_files = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    sync_files(max_files)
