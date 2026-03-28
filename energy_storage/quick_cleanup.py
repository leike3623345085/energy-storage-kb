#!/usr/bin/env python3
"""快速清理飞书Bitable旧记录"""
import requests
import time

FEISHU_CONFIG = {
    "app_id": "cli_a934994591785cb3",
    "app_secret": "uBiJm9Xuv6xsNWHdAOq6Hgovp82mrItY",
    "bitable_app_token": "Pqpwbh5tkaSzdrsKvrhcfggVnGe",
    "tables": {"crawler": "tblbWZx9H76QpxCl"}
}

def get_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    resp = requests.post(url, json={"app_id": FEISHU_CONFIG["app_id"], "app_secret": FEISHU_CONFIG["app_secret"]})
    return resp.json().get("tenant_access_token")

def quick_delete(table_id, target_count=19200):
    """快速删除到目标数量"""
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    base_url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_CONFIG['bitable_app_token']}/tables/{table_id}/records"
    
    # 获取当前数量
    resp = requests.get(base_url, headers=headers, params={"page_size": 1})
    total = resp.json().get("data", {}).get("total", 0)
    print(f"当前 {total} 条，目标 {target_count} 条")
    
    if total <= target_count:
        print("无需清理")
        return
    
    need_delete = total - target_count
    print(f"需要删除 {need_delete} 条")
    
    deleted = 0
    batch_size = 50  # 每批获取50条
    
    while deleted < need_delete:
        # 获取最旧的一批记录
        resp = requests.get(base_url, headers=headers, 
                          params={"page_size": min(batch_size, need_delete - deleted)},
                          timeout=10)
        items = resp.json().get("data", {}).get("items", [])
        if not items:
            break
        
        # 批量删除
        for item in items:
            if deleted >= need_delete:
                break
            record_id = item.get("record_id")
            if record_id:
                del_url = f"{base_url}/{record_id}"
                try:
                    requests.delete(del_url, headers=headers, timeout=3)
                    deleted += 1
                    if deleted % 100 == 0:
                        print(f"  已删除 {deleted}/{need_delete}")
                except:
                    pass
        time.sleep(0.1)
    
    print(f"✅ 完成，删除 {deleted} 条")

if __name__ == "__main__":
    quick_delete("tblbWZx9H76QpxCl", target_count=19200)
