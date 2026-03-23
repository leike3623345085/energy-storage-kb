#!/usr/bin/env python3
"""
清理飞书 Bitable 超容记录
删除最旧的记录，保留最近 10000 条
"""

import requests
import time

FEISHU_CONFIG = {
    "app_id": "cli_a934994591785cb3",
    "app_secret": "uBiJm9Xuv6xsNWHdAOq6Hgovp82mrItY",
    "bitable_app_token": "Pqpwbh5tkaSzdrsKvrhcfggVnGe",
    "table_id": "tblbWZx9H76QpxCl"
}

class FeishuCleaner:
    def __init__(self):
        self.access_token = None
        
    def get_token(self):
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        resp = requests.post(url, json={
            "app_id": FEISHU_CONFIG["app_id"],
            "app_secret": FEISHU_CONFIG["app_secret"]
        })
        self.access_token = resp.json()["tenant_access_token"]
        return self.access_token
    
    def get_all_records(self):
        """获取所有记录 ID（按时间升序，最旧的在前）"""
        token = self.get_token()
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_CONFIG['bitable_app_token']}/tables/{FEISHU_CONFIG['table_id']}/records"
        headers = {"Authorization": f"Bearer {token}"}
        
        all_records = []
        page_token = None
        
        while True:
            params = {"page_size": 500, "sort": "时间-asc"}  # 按时间升序
            if page_token:
                params["page_token"] = page_token
                
            resp = requests.get(url, headers=headers, params=params)
            data = resp.json()
            
            if data.get("code") != 0:
                print(f"❌ 获取记录失败: {data}")
                break
                
            records = data.get("data", {}).get("items", [])
            all_records.extend([r["record_id"] for r in records])
            
            if not data.get("data", {}).get("has_more"):
                break
            page_token = data["data"].get("page_token")
            time.sleep(0.1)
        
        return all_records
    
    def delete_records_batch(self, record_ids):
        """批量删除记录"""
        token = self.get_token()
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_CONFIG['bitable_app_token']}/tables/{FEISHU_CONFIG['table_id']}/records/batch_delete"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        
        # 每批最多 100 条
        batch_size = 100
        deleted = 0
        for i in range(0, len(record_ids), batch_size):
            batch = record_ids[i:i+batch_size]
            resp = requests.post(url, headers=headers, json={"records": batch})
            result = resp.json()
            if result.get("code") == 0:
                deleted += len(batch)
                print(f"  ✅ 已删除 {len(batch)} 条")
            else:
                print(f"  ⚠️ 删除失败: {result.get('msg')}")
            time.sleep(0.1)
        return deleted

def main():
    cleaner = FeishuCleaner()
    print("🔍 获取所有记录...")
    all_ids = cleaner.get_all_records()
    total = len(all_ids)
    print(f"📊 当前共有 {total} 条记录")
    
    if total <= 9000:
        print("✅ 记录数在安全范围内，无需清理")
        return
    
    # 保留最新的 9000 条，删除其余的
    to_delete = all_ids[:-9000]  # 删除最旧的
    print(f"🗑️  将删除最旧的 {len(to_delete)} 条记录，保留最新 9000 条")
    
    deleted = cleaner.delete_records_batch(to_delete)
    print(f"\n✅ 清理完成，共删除 {deleted} 条记录")

if __name__ == "__main__":
    main()
