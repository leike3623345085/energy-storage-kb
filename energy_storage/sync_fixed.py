#!/usr/bin/env python3
"""
储能数据批量同步到飞书 Bitable - 修复版
处理 URL 空值问题
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

def get_access_token():
    """获取飞书访问令牌"""
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
            return result["tenant_access_token"]
        else:
            print(f"❌ Token 获取失败: {result}")
            return None
    except Exception as e:
        print(f"❌ Token 获取错误: {e}")
        return None

def sync_files(max_files=5):
    """同步数据文件到飞书"""
    print(f"🚀 开始同步（最多 {max_files} 个文件）")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 获取访问令牌
    token = get_access_token()
    if not token:
        return 0, 0
    
    # 查找数据文件
    base_dir = "/root/.openclaw/workspace/energy_storage/data"
    data_path = Path(base_dir)
    
    files = []
    crawler_dir = data_path / "crawler"
    if crawler_dir.exists():
        files.extend(sorted(crawler_dir.glob("*.json"), reverse=True))
    
    files = sorted(files, key=lambda x: x.stat().st_mtime, reverse=True)
    print(f"📁 发现 {len(files)} 个数据文件")
    
    table_id = FEISHU_CONFIG["tables"]["crawler"]
    write_url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_CONFIG['bitable_app_token']}/tables/{table_id}/records"
    write_headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    total_records = 0
    synced_count = 0
    
    for i, file_path in enumerate(files[:max_files], 1):
        print(f"\n📄 [{i}/{max_files}] {file_path.name}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            source = data.get("source", "unknown")
            articles = data.get("data", [])
            
            if not articles:
                print(f"   ⚠️ 无有效记录")
                continue
            
            # 准备记录
            records = []
            base_time = int(time.time() * 1000)
            
            for idx, article in enumerate(articles):
                # 确保时间唯一（主键）
                unique_time = base_time + (idx * 100)
                
                # 构建记录 - 只包含非空字段
                record = {
                    "时间": unique_time,
                    "来源": source if source else "unknown",
                    "标题": article.get("title", "")[:1000],
                    "内容": article.get("summary", "")[:2000],
                    "网站": source if source else "unknown"
                }
                
                # URL 字段：只有非空时才添加
                link = article.get("link", "").strip()
                if link and link.startswith(("http://", "https://")):
                    record["URL"] = {"text": "查看原文", "link": link}
                
                records.append(record)
            
            print(f"   准备写入 {len(records)} 条记录")
            
            # 批量添加 - 单次最多500条
            added = 0
            batch_size = 100
            for j in range(0, len(records), batch_size):
                batch = records[j:j+batch_size]
                write_data = {"records": [{"fields": r} for r in batch]}
                
                # 打印第一个批次用于调试
                if j == 0:
                    print(f"   示例记录: {json.dumps(batch[0], ensure_ascii=False)[:150]}...")
                
                try:
                    write_resp = requests.post(write_url, headers=write_headers, json=write_data, timeout=30)
                    write_result = write_resp.json()
                    if write_result.get("code") == 0:
                        added += len(batch)
                    else:
                        print(f"   ⚠️ 批次 {j//batch_size + 1} 失败: {write_result.get('msg', '未知错误')}")
                        # 打印详细错误
                        if "error" in write_result:
                            print(f"      详情: {write_result['error']}")
                except Exception as e:
                    print(f"   ⚠️ 批次 {j//batch_size + 1} 错误: {e}")
            
            print(f"   ✅ 成功写入 {added}/{len(records)} 条")
            total_records += added
            synced_count += 1
            
            time.sleep(0.3)
            
        except Exception as e:
            print(f"   ❌ 处理文件错误: {e}")
    
    print(f"\n🎉 同步完成")
    print(f"   文件数: {synced_count}/{max_files}")
    print(f"   记录数: {total_records}")
    
    return synced_count, total_records

if __name__ == "__main__":
    max_files = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    sync_files(max_files)
