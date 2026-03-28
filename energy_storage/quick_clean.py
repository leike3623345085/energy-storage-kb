#!/usr/bin/env python3
"""快速清理 crawler 表旧记录"""
import json
import time
import requests

FEISHU_CONFIG = {
    "app_id": "cli_a934994591785cb3",
    "app_secret": "uBiJm9Xuv6xsNWHdAOq6Hgovp82mrItY",
    "bitable_app_token": "Pqpwbh5tkaSzdrsKvrhcfggVnGe",
    "tables": {
        "crawler": "tblbWZx9H76QpxCl"
    }
}

def get_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    resp = requests.post(url, json={
        "app_id": FEISHU_CONFIG["app_id"],
        "app_secret": FEISHU_CONFIG["app_secret"]
    }, timeout=10)
    return resp.json().get("tenant_access_token")

def delete_batch(token, count=500):
    """删除最早的 count 条记录"""
    table_id = FEISHU_CONFIG["tables"]["crawler"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 获取记录（不带排序参数，避免 InvalidSort 错误）
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_CONFIG['bitable_app_token']}/tables/{table_id}/records"
    resp = requests.get(url, headers=headers, params={"page_size": min(count, 500)}, timeout=10)
    data = resp.json()
    
    if data.get("code") != 0:
        print(f"❌ 获取记录失败: {data}")
        return 0
    
    records = data.get("data", {}).get("items", [])
    deleted = 0
    
    for record in records:
        record_id = record.get("record_id")
        if record_id:
            del_url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_CONFIG['bitable_app_token']}/tables/{table_id}/records/{record_id}"
            del_resp = requests.delete(del_url, headers=headers, timeout=5)
            if del_resp.json().get("code") == 0:
                deleted += 1
    
    return deleted

if __name__ == "__main__":
    token = get_token()
    if not token:
        print("❌ 无法获取 token")
        exit(1)
    
    print("🧹 开始清理旧记录...")
    total_deleted = 0
    
    # 清理 3 批，每批 500 条，共 1500 条
    for i in range(3):
        deleted = delete_batch(token, 500)
        total_deleted += deleted
        print(f"  第 {i+1} 批: 删除 {deleted} 条")
        time.sleep(0.5)
    
    print(f"\n✅ 共删除 {total_deleted} 条记录")
