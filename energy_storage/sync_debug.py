#!/usr/bin/env python3
"""
储能数据批量同步到飞书 Bitable - 简化调试版本
"""

import os
import sys
import json
import time
import requests
from datetime import datetime
from pathlib import Path

# 飞书配置
FEISHU_CONFIG = {
    "app_id": "cli_a934994591785cb3",
    "app_secret": "uBiJm9Xuv6xsNWHdAOq6Hgovp82mrItY",
    "bitable_app_token": "Pqpwbh5tkaSzdrsKvrhcfggVnGe",
    "tables": {
        "crawler": "tblbWZx9H76QpxCl",
        "search": "tblXS2e1FDVJlJ6m"
    }
}

print(f"🚀 开始同步（最多 5 个文件）")
print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# 获取访问令牌
print("\n1. 获取飞书访问令牌...")
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
        token = result["tenant_access_token"]
        print(f"   ✅ Token 获取成功")
    else:
        print(f"   ❌ Token 获取失败: {result}")
        sys.exit(1)
except Exception as e:
    print(f"   ❌ Token 获取错误: {e}")
    sys.exit(1)

# 查找数据文件
print("\n2. 查找数据文件...")
base_dir = "/root/.openclaw/workspace/energy_storage/data"
data_path = Path(base_dir)

files = []
crawler_dir = data_path / "crawler"
if crawler_dir.exists():
    files.extend(sorted(crawler_dir.glob("*.json"), reverse=True))

news_dir = data_path / "news"
if news_dir.exists():
    files.extend(sorted(news_dir.glob("*.json"), reverse=True))

files = sorted(files, key=lambda x: x.stat().st_mtime, reverse=True)
print(f"   📁 发现 {len(files)} 个数据文件")

# 处理前5个文件
max_files = 5
total_records = 0
synced_count = 0

for i, file_path in enumerate(files[:max_files], 1):
    print(f"\n3.{i} 处理文件: {file_path.name}")
    
    # 加载数据
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        timestamp = data.get("fetch_time", "")
        source = data.get("source", "unknown")
        articles = data.get("data", [])
        
        print(f"   来源: {source}, 文章数: {len(articles)}")
        
        if not articles:
            print(f"   ⚠️ 无有效记录，跳过")
            continue
        
        # 准备记录
        records = []
        for article in articles:
            title = article.get("title", "")[:1000]
            summary = article.get("summary", "")[:2000]
            link = article.get("link", "")
            record = {
                "时间": int(time.time() * 1000),
                "来源": source,
                "标题": title,
                "内容": summary,
                "URL": {"text": "查看原文", "link": link},
                "网站": source
            }
            records.append(record)
        
        print(f"   准备写入 {len(records)} 条记录到 crawler 表")
        
        # 写入飞书
        table_id = FEISHU_CONFIG["tables"]["crawler"]
        write_url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_CONFIG['bitable_app_token']}/tables/{table_id}/records"
        write_headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        # 批量添加
        batch_size = 100
        added = 0
        for j in range(0, len(records), batch_size):
            batch = records[j:j+batch_size]
            write_data = {"records": [{"fields": r} for r in batch]}
            
            try:
                write_resp = requests.post(write_url, headers=write_headers, json=write_data, timeout=30)
                write_result = write_resp.json()
                if write_result.get("code") == 0:
                    added += len(batch)
                    print(f"   ✅ 批次 {j//batch_size + 1}: 写入 {len(batch)} 条")
                else:
                    print(f"   ⚠️ 批次 {j//batch_size + 1} 失败: {write_result.get('msg', '未知错误')}")
            except Exception as e:
                print(f"   ⚠️ 批次 {j//batch_size + 1} 错误: {e}")
        
        print(f"   ✅ 文件完成: 成功写入 {added}/{len(records)} 条")
        total_records += added
        synced_count += 1
        
        # 间隔避免限流
        time.sleep(0.5)
        
    except Exception as e:
        print(f"   ❌ 处理文件错误: {e}")

print(f"\n🎉 同步完成")
print(f"   文件数: {synced_count}/{max_files}")
print(f"   记录数: {total_records}")
print(f"   剩余: {len(files) - synced_count} 个文件待处理")
