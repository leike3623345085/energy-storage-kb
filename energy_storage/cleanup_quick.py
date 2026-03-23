#!/usr/bin/env python3
"""
快速清理 Bitable 旧记录 - 直接删除前 N 条
"""

import time
import requests

FEISHU_CONFIG = {
    "app_id": "cli_a934994591785cb3",
    "app_secret": "uBiJm9Xuv6xsNWHdAOq6Hgovp82mrItY",
    "bitable_app_token": "Pqpwbh5tkaSzdrsKvrhcfggVnGe",
    "table_id": "tblbWZx9H76QpxCl"
}

def get_access_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    resp = requests.post(url, json={
        "app_id": FEISHU_CONFIG["app_id"],
        "app_secret": FEISHU_CONFIG["app_secret"]
    }, timeout=10)
    return resp.json().get("tenant_access_token")

def delete_oldest_records(token, count=10000):
    """删除最旧的 count 条记录"""
    deleted = 0
    batch_size = 500
    
    while deleted < count:
        # 获取一批记录（默认按创建时间排序，先获取的是最旧的）
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_CONFIG['bitable_app_token']}/tables/{FEISHU_CONFIG['table_id']}/records"
        headers = {"Authorization": f"Bearer {token}"}
        params = {"page_size": min(batch_size, count - deleted)}
        
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        data = resp.json()
        
        if data.get("code") != 0:
            print(f"❌ 获取记录失败: {data}")
            break
        
        items = data.get("data", {}).get("items", [])
        if not items:
            print("ℹ️ 没有更多记录可删除")
            break
        
        record_ids = [item["record_id"] for item in items]
        
        # 批量删除
        del_url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_CONFIG['bitable_app_token']}/tables/{FEISHU_CONFIG['table_id']}/records/batch_delete"
        del_resp = requests.post(del_url, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, 
                                json={"records": record_ids}, timeout=30)
        del_result = del_resp.json()
        
        if del_result.get("code") == 0:
            deleted += len(record_ids)
            print(f"  ✅ 已删除 {len(record_ids)} 条记录 (共 {deleted}/{count})")
        else:
            print(f"  ⚠️ 删除失败: {del_result.get('msg')}")
            break
        
        time.sleep(0.3)
    
    return deleted

if __name__ == "__main__":
    token = get_access_token()
    if not token:
        print("❌ 获取 Token 失败")
        exit(1)
    
    print("🗑️ 开始清理旧记录...")
    deleted = delete_oldest_records(token, count=15000)  # 删除15000条，保留约5000条
    print(f"✅ 共删除 {deleted} 条记录")
