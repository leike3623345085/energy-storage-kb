#!/usr/bin/env python3
"""使用 OpenClaw feishu_bitable_create_record 工具同步"""
import json
import subprocess
import time
from datetime import datetime
from pathlib import Path

def run_sync():
    print(f"🚀 储能数据飞书同步 {datetime.now().strftime('%H:%M:%S')}")
    
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
        
        print(f"\n📄 [{i}/{len(files)}] {fp.name} - {len(articles)} 条记录")
        
        added = 0
        for article in articles[:50]:  # 每文件最多50条，避免超时
            record = {
                "时间": ts_ms,
                "来源": article.get("source", source),
                "标题": article.get("title", "")[:1000],
                "URL": {"text": "查看原文", "link": article.get("url", "")}
            }
            
            # 使用 feishu_bitable_create_record
            cmd = [
                "python3", "-c",
                f"""
import sys
sys.path.insert(0, '/usr/lib/node_modules/openclaw/extensions/feishu')
from feishu_bitable_create_record import feishu_bitable_create_record
result = feishu_bitable_create_record(
    app_token='Pqpwbh5tkaSzdrsKvrhcfggVnGe',
    table_id='tblbWZx9H76QpxCl',
    fields={json.dumps(record, ensure_ascii=False)}
)
print(result)
"""
            ]
            
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                if '"code": 0' in result.stdout or 'success' in result.stdout:
                    added += 1
            except Exception as e:
                print(f"  错误: {e}")
                break
            
            time.sleep(0.1)  # 避免限流
        
        print(f"  ✅ 成功写入 {added} 条")
        total += added
    
    print(f"\n🎉 同步完成，共写入 {total} 条记录")

if __name__ == "__main__":
    run_sync()
