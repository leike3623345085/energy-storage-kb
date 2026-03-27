#!/usr/bin/env python3
"""
测试飞书 Bitable 单条记录写入
"""
import requests
import json
import time
from datetime import datetime

FEISHU_CONFIG = {
    "app_id": "cli_a934994591785cb3",
    "app_secret": "uBiJm9Xuv6xsNWHdAOq6Hgovp82mrItY",
    "bitable_app_token": "Pqpwbh5tkaSzdrsKvrhcfggVnGe",
    "tables": {
        "crawler": "tblbWZx9H76QpxCl"
    }
}

# 获取 Token
url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
resp = requests.post(url, json={
    "app_id": FEISHU_CONFIG["app_id"],
    "app_secret": FEISHU_CONFIG["app_secret"]
})
token = resp.json()["tenant_access_token"]
print(f"✅ Token: {token[:20]}...")

# 测试写入单条记录
table_id = FEISHU_CONFIG["tables"]["crawler"]
write_url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_CONFIG['bitable_app_token']}/tables/{table_id}/records"
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

# 使用当前时间戳
current_ms = int(time.time() * 1000)
print(f"⏰ 当前毫秒时间戳: {current_ms}")

# 构建测试记录
test_record = {
    "records": [
        {
            "fields": {
                "时间": current_ms,
                "来源": "test",
                "标题": "测试标题",
                "内容": "测试内容",
                "网站": "test_site"
            }
        }
    ]
}

print(f"\n📤 请求体:\n{json.dumps(test_record, ensure_ascii=False, indent=2)}")

write_resp = requests.post(write_url, headers=headers, json=test_record)
result = write_resp.json()

print(f"\n📥 响应:\n{json.dumps(result, ensure_ascii=False, indent=2)}")
