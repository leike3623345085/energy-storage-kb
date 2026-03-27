#!/usr/bin/env python3
"""
储能数据批量同步到飞书 Bitable - 调试版
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

# 只处理第一个文件来调试
file_path = files[0]
print(f"\n3. 处理文件: {file_path.name}")

# 加载数据
try:
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    fetch_time = data.get("fetch_time", "")
    articles = data.get("data", [])
    
    print(f"   文章数: {len(articles)}")
    
    if not articles:
        print(f"   ⚠️ 无有效记录，跳过")
        sys.exit(0)
    
    # 解析时间戳
    try:
        dt = datetime.fromisoformat(fetch_time.replace('Z', '+00:00'))
        timestamp_ms = int(dt.timestamp() * 1000)
    except:
        timestamp_ms = int(time.time() * 1000)
    
    # 只取第一条记录测试
    article = articles[0]
    title = article.get("title", "")[:1000]
    link = article.get("url", "")
    source = article.get("source", "未知来源")
    
    # 构建记录
    record = {
        "时间": timestamp_ms,
        "来源": source,
        "标题": title,
        "内容": title[:100],
        "URL": {"text": "查看原文", "link": link},
        "网站": source
    }
    
    print(f"\n   测试记录:")
    print(f"   {json.dumps(record, ensure_ascii=False, indent=2)}")
    
    # 构建请求体
    write_data = {"records": [{"fields": record}]}
    print(f"\n   请求体:")
    print(f"   {json.dumps(write_data, ensure_ascii=False, indent=2)}")
    
    # 写入飞书
    table_id = FEISHU_CONFIG["tables"]["crawler"]
    write_url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_CONFIG['bitable_app_token']}/tables/{table_id}/records"
    write_headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    print(f"\n   发送请求...")
    write_resp = requests.post(write_url, headers=write_headers, json=write_data, timeout=30)
    write_result = write_resp.json()
    
    print(f"   响应:")
    print(f"   {json.dumps(write_result, ensure_ascii=False, indent=2)}")
    
    if write_result.get("code") == 0:
        print(f"\n   ✅ 测试成功！")
    else:
        print(f"\n   ❌ 测试失败: {write_result.get('msg')}")
        
except Exception as e:
    print(f"   ❌ 错误: {e}")
    import traceback
    traceback.print_exc()
