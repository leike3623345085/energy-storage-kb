#!/usr/bin/env python3
"""
清理飞书Bitable旧数据，为同步腾出空间
"""

import requests
import time

# 飞书配置
FEISHU_CONFIG = {
    "app_id": "cli_a934994591785cb3",
    "app_secret": "uBiJm9Xuv6xsNWHdAOq6Hgovp82mrItY",
    "bitable_app_token": "Pqpwbh5tkaSzdrsKvrhcfggVnGe",
    "tables": {
        "crawler": "tblbWZx9H76QpxCl",
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
            print(f"❌ 获取 Token 失败: {result}")
            return None
    except Exception as e:
        print(f"❌ 获取 Token 错误: {e}")
        return None

def get_old_records(token, table_id, limit=2000):
    """获取最早的记录（按时间排序）"""
    # 使用时间升序获取最早记录
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_CONFIG['bitable_app_token']}/tables/{table_id}/records"
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "page_size": min(limit, 500),  # 每次最多500
        "sort": json.dumps([{"field_name": "时间", "order": "ASC"}])
    }
    
    all_records = []
    page_token = None
    
    while len(all_records) < limit:
        if page_token:
            params["page_token"] = page_token
        
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        result = resp.json()
        
        if result.get("code") != 0:
            print(f"⚠️ 查询失败: {result}")
            break
        
        items = result.get("data", {}).get("items", [])
        if not items:
            break
        
        all_records.extend(items)
        
        if not result.get("data", {}).get("has_more"):
            break
        
        page_token = result.get("data", {}).get("page_token")
    
    return all_records[:limit]

def delete_records_batch(token, table_id, record_ids):
    """批量删除记录"""
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_CONFIG['bitable_app_token']}/tables/{table_id}/records/batch_delete"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # 分批删除，每批最多500
    deleted = 0
    batch_size = 500
    
    for i in range(0, len(record_ids), batch_size):
        batch = record_ids[i:i+batch_size]
        try:
            resp = requests.post(url, headers=headers, json={"records": batch}, timeout=30)
            result = resp.json()
            if result.get("code") == 0:
                deleted += len(batch)
                print(f"    ✅ 删除 {len(batch)} 条记录")
            else:
                print(f"    ⚠️ 删除失败: {result.get('msg', '未知错误')}")
        except Exception as e:
            print(f"    ❌ 删除错误: {e}")
    
    return deleted

def clean_old_records(target_count=5000):
    """清理旧记录，保留指定数量"""
    import json
    
    token = get_access_token()
    if not token:
        print("❌ 认证失败")
        return False
    
    table_id = FEISHU_CONFIG["tables"]["crawler"]
    
    # 获取当前总数
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_CONFIG['bitable_app_token']}/tables/{table_id}/records"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"page_size": 1}
    
    resp = requests.get(url, headers=headers, params=params, timeout=10)
    result = resp.json()
    total = result.get("data", {}).get("total", 0)
    
    print(f"📊 当前记录数: {total}")
    
    if total <= target_count:
        print(f"✅ 记录数已低于目标值，无需清理")
        return True
    
    # 计算需要删除的数量
    to_delete = total - target_count
    print(f"🗑️ 需要删除 {to_delete} 条旧记录，保留 {target_count} 条")
    
    # 获取最早的记录
    print(f"📥 获取最早的 {min(to_delete, 5000)} 条记录...")
    old_records = get_old_records(token, table_id, limit=min(to_delete, 5000))
    
    if not old_records:
        print("⚠️ 没有获取到旧记录")
        return False
    
    record_ids = [r["record_id"] for r in old_records]
    print(f"🗑️ 准备删除 {len(record_ids)} 条记录...")
    
    # 批量删除
    deleted = delete_records_batch(token, table_id, record_ids)
    print(f"✅ 成功删除 {deleted} 条记录")
    
    # 验证结果
    resp = requests.get(url, headers=headers, params=params, timeout=10)
    result = resp.json()
    new_total = result.get("data", {}).get("total", 0)
    print(f"📊 清理后记录数: {new_total}")
    
    return deleted > 0

if __name__ == "__main__":
    # 保留5000条，清理其余
    clean_old_records(target_count=5000)
