#!/usr/bin/env python3
"""简化版同步脚本 - 用于手动执行"""
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

MAX_RECORDS = 18000

def get_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    resp = requests.post(url, json={
        "app_id": FEISHU_CONFIG["app_id"],
        "app_secret": FEISHU_CONFIG["app_secret"]
    }, timeout=10)
    return resp.json().get("tenant_access_token")

def get_count(table_id, token):
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_CONFIG['bitable_app_token']}/tables/{table_id}/records"
    resp = requests.get(url, headers={"Authorization": f"Bearer {token}"}, params={"page_size": 1}, timeout=10)
    return resp.json().get("data", {}).get("total", 0)

def delete_records(table_id, token, count):
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_CONFIG['bitable_app_token']}/tables/{table_id}/records"
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(url, headers=headers, params={"page_size": min(count, 500)}, timeout=10)
    items = resp.json().get("data", {}).get("items", [])
    deleted = 0
    for item in items:
        rid = item.get("record_id")
        if rid:
            del_url = f"{url}/{rid}"
            requests.delete(del_url, headers=headers, timeout=5)
            deleted += 1
    return deleted

def add_records(table_id, token, records):
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_CONFIG['bitable_app_token']}/tables/{table_id}/records"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    added = 0
    for i in range(0, len(records), 500):
        batch = records[i:i+500]
        data = {"records": [{"fields": r} for r in batch]}
        resp = requests.post(url, headers=headers, json=data, timeout=30)
        if resp.json().get("code") == 0:
            added += len(batch)
        else:
            print(f"  错误: {resp.json().get('msg')}")
    return added

def load_crawler(fp):
    with open(fp, 'r', encoding='utf-8') as f:
        data = json.load(f)
    records = []
    ts = data.get("fetch_time", "")
    if ts:
        try:
            # 尝试 ISO 格式 2026-03-24T00:44:16.750360
            if 'T' in ts:
                ts = ts.split('.')[0]  # 去掉微秒部分
                dt = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S")
            else:
                dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
            ts_ms = int(dt.timestamp() * 1000)
        except:
            ts_ms = int(time.time() * 1000)
    else:
        ts_ms = int(time.time() * 1000)
    source = data.get("source", "unknown")
    for article in data.get("data", []):
        records.append({
            "时间": ts_ms,
            "来源": source,
            "标题": article.get("title", "")[:1000],
            "内容": article.get("summary", "")[:2000],
            "URL": {"text": "查看原文", "link": article.get("link", "")},
            "网站": source
        })
    return records

def main():
    print(f"🚀 储能数据飞书同步 - {datetime.now().strftime('%H:%M:%S')}")
    
    token = get_token()
    if not token:
        print("❌ Token 获取失败")
        return
    
    # 查找文件
    data_dir = Path("/root/.openclaw/workspace/energy_storage/data/crawler")
    files = sorted(data_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True)[:5]
    print(f"📁 找到 {len(files)} 个文件待同步")
    
    total_added = 0
    for i, fp in enumerate(files, 1):
        print(f"\n📄 [{i}/5] {fp.name}")
        records = load_crawler(fp)
        if not records:
            print("  ⚠️ 无记录")
            continue
        
        table_id = FEISHU_CONFIG["tables"]["crawler"]
        current = get_count(table_id, token)
        print(f"  当前表记录: {current}")
        
        # 清理空间
        if current + len(records) > MAX_RECORDS:
            need = current + len(records) - MAX_RECORDS + 500
            print(f"  🧹 需清理 {need} 条旧记录")
            deleted = delete_records(table_id, token, need)
            print(f"  ✅ 已清理 {deleted} 条")
        
        # 添加记录
        added = add_records(table_id, token, records)
        print(f"  ✅ 成功写入 {added} 条记录")
        total_added += added
        time.sleep(0.5)
    
    print(f"\n🎉 同步完成，共写入 {total_added} 条记录")

if __name__ == "__main__":
    main()
