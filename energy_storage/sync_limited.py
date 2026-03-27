#!/usr/bin/env python3
"""储能数据同步到飞书 - 优化版（限制数量）"""
import json
import time
import requests
from datetime import datetime
from pathlib import Path

FEISHU_CONFIG = {
    "app_id": "cli_a934994591785cb3",
    "app_secret": "uBiJm9Xuv6xsNWHdAOq6Hgovp82mrItY",
    "app_token": "Pqpwbh5tkaSzdrsKvrhcfggVnGe",
    "table_id": "tblbWZx9H76QpxCl"
}

def get_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    resp = requests.post(url, json={
        "app_id": FEISHU_CONFIG["app_id"],
        "app_secret": FEISHU_CONFIG["app_secret"]
    }, timeout=10)
    return resp.json().get("tenant_access_token")

def add_record(token, record):
    """单条插入记录"""
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_CONFIG['app_token']}/tables/{FEISHU_CONFIG['table_id']}/records"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    resp = requests.post(url, headers=headers, json={"fields": record}, timeout=10)
    return resp.json().get("code") == 0

def sync():
    print(f"🚀 储能数据飞书同步 {datetime.now().strftime('%H:%M:%S')}", flush=True)
    
    token = get_token()
    if not token:
        print("❌ Token 获取失败")
        return 0
    print("✅ Token 获取成功")
    
    # 查找最新5个文件
    data_dir = Path("/root/.openclaw/workspace/energy_storage/data/crawler")
    files = sorted(data_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True)[:5]
    print(f"📁 找到 {len(files)} 个文件待同步")
    
    total = 0
    max_per_file = 30  # 每个文件最多同步30条，避免超时
    
    for i, fp in enumerate(files, 1):
        print(f"\n📄 [{i}/{len(files)}] 处理 {fp.name}...", flush=True)
        
        # 读取文件
        try:
            with open(fp, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            print(f"  ❌ 读取文件失败: {e}")
            continue
        
        # 解析时间
        ts = data.get("fetch_time", "")
        try:
            if 'T' in ts:
                ts = ts.split('.')[0].replace('T', ' ')
            dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
            ts_ms = int(dt.timestamp() * 1000)
        except:
            ts_ms = int(time.time() * 1000)
        
        articles = data.get("data", [])
        if not articles:
            print(f"  ⚠️ 无记录")
            continue
        
        # 限制数量
        articles_to_sync = articles[:max_per_file]
        print(f"  将同步 {len(articles_to_sync)}/{len(articles)} 条记录", flush=True)
        
        added = 0
        for j, article in enumerate(articles_to_sync):
            record = {
                "时间": ts_ms,
                "来源": article.get("source", "unknown"),
                "标题": article.get("title", "")[:1000],
                "URL": {"text": "查看原文", "link": article.get("url", "")}
            }
            
            if add_record(token, record):
                added += 1
            
            if (j + 1) % 10 == 0:
                print(f"    进度: {j+1}/{len(articles_to_sync)}", flush=True)
            
            time.sleep(0.05)
        
        print(f"  ✅ 成功写入 {added}/{len(articles_to_sync)} 条", flush=True)
        total += added
    
    print(f"\n🎉 同步完成，共写入 {total} 条记录")
    return total

if __name__ == "__main__":
    sync()
