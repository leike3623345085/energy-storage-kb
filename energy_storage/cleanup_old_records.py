#!/usr/bin/env python3
"""
紧急清理飞书 Bitable 旧记录
删除爬虫表中最旧的 5000 条记录
"""

import requests
import json
import time

FEISHU_CONFIG = {
    "app_id": "cli_a934994591785cb3",
    "app_secret": "uBiJm9Xuv6xsNWHdAOq6Hgovp82mrItY",
    "bitable_app_token": "Pqpwbh5tkaSzdrsKvrhcfggVnGe",
    "tables": {
        "crawler": "tblbWZx9H76QpxCl",
    }
}

def get_access_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    headers = {"Content-Type": "application/json"}
    data = {
        "app_id": FEISHU_CONFIG["app_id"],
        "app_secret": FEISHU_CONFIG["app_secret"]
    }
    resp = requests.post(url, headers=headers, json=data, timeout=10)
    result = resp.json()
    if result.get("code") == 0:
        return result["tenant_access_token"]
    return None

def get_old_records(token, table_id, count=500):
    """获取最旧的记录 - 按时间字段升序"""
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_CONFIG['bitable_app_token']}/tables/{table_id}/records"
    headers = {"Authorization": f"Bearer {token}"}
    # 修正：使用正确的 sort 参数格式
    params = {
        "page_size": min(count, 500),
        "sort": json.dumps([{"field_name": "时间", "desc": False}]),
    }
    
    resp = requests.get(url, headers=headers, params=params, timeout=10)
    result = resp.json()
    if result.get("code") == 0:
        return result.get("data", {}).get("items", [])
    else:
        print(f"获取记录失败: {result}")
        return []

def delete_record(token, table_id, record_id):
    """删除单条记录"""
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_CONFIG['bitable_app_token']}/tables/{table_id}/records/{record_id}"
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.delete(url, headers=headers, timeout=5)
    return resp.json().get("code") == 0

def main():
    print("🧹 开始清理旧记录...")
    
    token = get_access_token()
    if not token:
        print("❌ 无法获取 Token")
        return
    
    table_id = FEISHU_CONFIG["tables"]["crawler"]
    total_deleted = 0
    target = 5000  # 清理 5000 条
    batch_size = 500
    
    while total_deleted < target:
        print(f"\n📦 获取第 {total_deleted//batch_size + 1} 批记录...")
        records = get_old_records(token, table_id, batch_size)
        
        if not records:
            print("⚠️ 没有更多记录可删除")
            break
        
        deleted_in_batch = 0
        for record in records:
            record_id = record.get("record_id")
            if record_id and delete_record(token, table_id, record_id):
                deleted_in_batch += 1
                total_deleted += 1
            
            if total_deleted >= target:
                break
            
            # 避免 API 限流
            if deleted_in_batch % 100 == 0:
                time.sleep(0.1)
        
        print(f"   ✅ 本批删除 {deleted_in_batch} 条，累计 {total_deleted} 条")
        time.sleep(0.5)
    
    print(f"\n🎉 清理完成！共删除 {total_deleted} 条旧记录")

if __name__ == "__main__":
    main()
