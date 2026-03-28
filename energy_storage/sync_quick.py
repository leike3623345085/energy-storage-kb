#!/usr/bin/env python3
"""
储能数据批量同步到飞书 Bitable - 快速版
跳过删除操作，直接同步未超限文件
"""

import os
import sys
import json
import time
import requests
from datetime import datetime
from pathlib import Path

FEISHU_CONFIG = {
    "app_id": "cli_a934994591785cb3",
    "app_secret": "uBiJm9Xuv6xsNWHdAOq6Hgovp82mrItY",
    "bitable_app_token": "Pqpwbh5tkaSzdrsKvrhcfggVnGe",
    "tables": {
        "crawler": "tblbWZx9H76QpxCl",
        "search": "tblXS2e1FDVJlJ6m"
    }
}

class FeishuSync:
    def __init__(self):
        self.access_token = None
        
    def get_access_token(self):
        if self.access_token:
            return self.access_token
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        try:
            resp = requests.post(url, json={
                "app_id": FEISHU_CONFIG["app_id"],
                "app_secret": FEISHU_CONFIG["app_secret"]
            }, timeout=10)
            result = resp.json()
            if result.get("code") == 0:
                self.access_token = result["tenant_access_token"]
                return self.access_token
        except Exception as e:
            print(f"Token error: {e}")
        return None
    
    def get_record_count(self, table_id):
        token = self.get_access_token()
        if not token:
            return 0
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_CONFIG['bitable_app_token']}/tables/{table_id}/records"
        try:
            resp = requests.get(url, headers={"Authorization": f"Bearer {token}"}, params={"page_size": 1}, timeout=10)
            result = resp.json()
            if result.get("code") == 0:
                return result.get("data", {}).get("total", 0)
        except Exception as e:
            print(f"Count error: {e}")
        return 0
    
    def add_records(self, table_id, records):
        token = self.get_access_token()
        if not token or not records:
            return 0
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_CONFIG['bitable_app_token']}/tables/{table_id}/records/batch_create"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        added = 0
        for i in range(0, len(records), 500):
            batch = records[i:i+500]
            try:
                resp = requests.post(url, headers=headers, json={"records": [{"fields": r} for r in batch]}, timeout=30)
                result = resp.json()
                if result.get("code") == 0:
                    added += len(batch)
                else:
                    print(f"   Add error: {result.get('msg')}")
                    break
            except Exception as e:
                print(f"   Request error: {e}")
                break
        return added

def find_files():
    base = Path("/root/.openclaw/workspace/energy_storage/data")
    files = []
    crawler_dir = base / "crawler"
    if crawler_dir.exists():
        files.extend(sorted(crawler_dir.glob("*.json"), reverse=True))
    return sorted(files, key=lambda x: x.stat().st_mtime, reverse=True)

def load_crawler(path, start_ms):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        records = []
        source = data.get("source", "储能产业网")
        for idx, article in enumerate(data.get("data", [])):
            rec = {
                "时间": start_ms + idx * 100,
                "来源": source if source != "unknown" else "储能产业网",
                "标题": article.get("title", ")")[:1000],
                "内容": article.get("summary", "")[:2000] if article.get("summary") else "-"
            }
            link = article.get("link", "").strip()
            if link.startswith("http"):
                rec["URL"] = {"text": "查看原文", "link": link}
            records.append(rec)
        return records, start_ms + len(records) * 100
    except Exception as e:
        print(f"   Load error: {e}")
        return [], start_ms

def sync_fast(max_files=5):
    print(f"🚀 储能数据飞书同步 (快速版)")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 40)
    
    files = find_files()
    if not files:
        print("⚠️ 无数据文件")
        return 0, 0
    
    print(f"📁 {len(files)} 个文件待处理")
    
    fs = FeishuSync()
    if not fs.get_access_token():
        print("❌ Token 失败")
        return 0, 0
    
    synced = 0
    total = 0
    skipped = 0
    time_ms = int(time.time() * 1000)
    
    for i, f in enumerate(files[:max_files], 1):
        print(f"\n[{i}/{max_files}] {f.name}")
        
        records, time_ms = load_crawler(f, time_ms)
        if not records:
            print("   ⚠️ 无记录")
            continue
        
        table_id = FEISHU_CONFIG["tables"]["crawler"]
        current = fs.get_record_count(table_id)
        print(f"   表内: {current} 条, 待加: {len(records)} 条")
        
        if current + len(records) > 19500:
            print(f"   ⚠️ 将超限，跳过")
            skipped += 1
            continue
        
        added = fs.add_records(table_id, records)
        print(f"   ✅ +{added} 条")
        total += added
        synced += 1
        time.sleep(0.2)
    
    print(f"\n{'=' * 40}")
    print(f"🎉 完成: {synced}/{max_files} 文件, {total} 条记录, 跳过 {skipped}")
    return synced, total

if __name__ == "__main__":
    max_f = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    sync_fast(max_f)
