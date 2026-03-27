#!/usr/bin/env python3
"""直接同步 - 一次性完成"""
import json
import time
import requests
from datetime import datetime
from pathlib import Path

# 配置
APP_ID = "cli_a934994591785cb3"
APP_SECRET = "uBiJm9Xuv6xsNWHdAOq6Hgovp82mrItY"
APP_TOKEN = "Pqpwbh5tkaSzdrsKvrhcfggVnGe"
TABLE_CRAWLER = "tblbWZx9H76QpxCl"
MAX_RECORDS = 18000

def get_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    resp = requests.post(url, json={"app_id": APP_ID, "app_secret": APP_SECRET}, timeout=10)
    return resp.json().get("tenant_access_token")

def sync():
    print(f"🚀 开始同步 {datetime.now().strftime('%H:%M:%S')}")
    
    # 获取 Token
    token = get_token()
    if not token:
        print("❌ Token 失败")
        return
    print("✅ Token 获取成功")
    
    # 查找最新5个文件
    data_dir = Path("/root/.openclaw/workspace/energy_storage/data/crawler")
    files = sorted(data_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True)[:5]
    print(f"📁 找到 {len(files)} 个文件")
    
    total = 0
    for i, fp in enumerate(files, 1):
        # 读取文件
        with open(fp, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 解析时间
        ts = data.get("fetch_time", "")
        try:
            if 'T' in ts:
                ts = ts.split('.')[0].replace('T', ' ')
            dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
            ts_ms = int(dt.timestamp() * 1000)
        except:
            ts_ms = int(time.time() * 1000)
        
        source = data.get("source", "unknown")
        articles = data.get("data", [])
        
        # 构建记录 - 只包含表格中存在的字段
        records = []
        for article in articles:
            record = {
                "时间": ts_ms,
                "来源": source,
                "标题": article.get("title", "")[:1000],
                "URL": {"text": "查看原文", "link": article.get("link", "")}
            }
            records.append(record)
        
        if not records:
            print(f"  [{i}] {fp.name}: 无记录")
            continue
        
        # 添加记录
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_CRAWLER}/records"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        
        added = 0
        for j in range(0, len(records), 500):
            batch = records[j:j+500]
            resp = requests.post(url, headers=headers, json={"records": [{"fields": r} for r in batch]}, timeout=30)
            result = resp.json()
            if result.get("code") == 0:
                added += len(batch)
            else:
                print(f"  错误: {result.get('msg', '未知')}")
                if result.get('error'):
                    print(f"  详情: {result.get('error')}")
        
        print(f"  [{i}] {fp.name}: +{added} 条")
        total += added
        time.sleep(0.3)
    
    print(f"\n🎉 完成！共写入 {total} 条记录")

if __name__ == "__main__":
    sync()
