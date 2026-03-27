#!/usr/bin/env python3
"""
储能数据批量同步到飞书 Bitable - 调试版本
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
        "search": "tblXS2e1FDVJlJ6m",
        "stocks": "tblKruLIh89NgNNL",
        "reports": "tbla0u1wX7kLQJ09"
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

def get_record_count(table_id):
    """获取表格记录数"""
    token = get_access_token()
    if not token:
        return 0
    
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_CONFIG['bitable_app_token']}/tables/{table_id}/records"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"page_size": 1}
    
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        result = resp.json()
        if result.get("code") == 0:
            data = result.get("data", {})
            total = data.get("total", 0)
            return total
        else:
            print(f"⚠️ 获取记录数失败: {result.get('msg', '未知错误')}")
            return 0
    except Exception as e:
        print(f"⚠️ 获取记录数错误: {e}")
        return 0

if __name__ == "__main__":
    print("🚀 飞书 Bitable 状态检查")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    for name, table_id in FEISHU_CONFIG["tables"].items():
        count = get_record_count(table_id)
        print(f"📊 {name}: {count} 条记录")
