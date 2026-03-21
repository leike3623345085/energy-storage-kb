#!/usr/bin/env python3
"""初始化飞书 Bitable 数据结构"""

import json
import requests

FEISHU_CONFIG = {
    "app_id": "cli_a934994591785cb3",
    "app_secret": "uBiJm9Xuv6xsNWHdAOq6Hgovp82mrItY",
    "app_token": "Pqpwbh5tkaSzdrsKvrhcfggVnGe"
}

def get_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    resp = requests.post(url, json={
        "app_id": FEISHU_CONFIG["app_id"],
        "app_secret": FEISHU_CONFIG["app_secret"]
    })
    return resp.json()["tenant_access_token"]

def create_table(token, name, fields):
    """创建数据表"""
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_CONFIG['app_token']}/tables"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    data = {
        "table": {
            "name": name,
            "fields": fields
        }
    }
    resp = requests.post(url, headers=headers, json=data)
    result = resp.json()
    if result.get("code") == 0:
        table_id = result["data"]["table_id"]
        print(f"✅ 创建表 '{name}' 成功: {table_id}")
        return table_id
    else:
        print(f"❌ 创建表 '{name}' 失败: {result}")
        return None

def main():
    token = get_token()
    print("🚀 初始化 Bitable 数据表...\n")
    
    # 1. 爬虫数据表
    crawler_fields = [
        {"field_name": "时间", "type": 5},  # DateTime
        {"field_name": "来源", "type": 1},  # Text
        {"field_name": "标题", "type": 1},  # Text
        {"field_name": "内容", "type": 1},  # Text
        {"field_name": "URL", "type": 15},  # URL
        {"field_name": "网站", "type": 1},  # Text
    ]
    crawler_id = create_table(token, "爬虫数据", crawler_fields)
    
    # 2. 搜索数据表
    search_fields = [
        {"field_name": "时间", "type": 5},
        {"field_name": "类型", "type": 1},  # 深夜搜索/白天搜索
        {"field_name": "标题", "type": 1},
        {"field_name": "摘要", "type": 1},
        {"field_name": "URL", "type": 15},
        {"field_name": "日期", "type": 5},
    ]
    search_id = create_table(token, "搜索数据", search_fields)
    
    # 3. 股票数据表
    stock_fields = [
        {"field_name": "日期", "type": 5},
        {"field_name": "股票代码", "type": 1},
        {"field_name": "股票名称", "type": 1},
        {"field_name": "最新价", "type": 2},  # Number
        {"field_name": "涨跌幅", "type": 2},
        {"field_name": "成交量", "type": 2},
        {"field_name": "市值", "type": 2},
    ]
    stock_id = create_table(token, "股票行情", stock_fields)
    
    # 4. 报告数据表
    report_fields = [
        {"field_name": "类型", "type": 1},  # 日报/周报/深度分析
        {"field_name": "日期", "type": 5},
        {"field_name": "标题", "type": 1},
        {"field_name": "内容", "type": 1},
        {"field_name": "文件名", "type": 1},
    ]
    report_id = create_table(token, "报告数据", report_fields)
    
    print("\n" + "="*50)
    print("请将以下表 ID 填入 sync_feishu.py:")
    print(f'"crawler": "{crawler_id or ""}",')
    print(f'"search": "{search_id or ""}",')
    print(f'"stocks": "{stock_id or ""}",')
    print(f'"reports": "{report_id or ""}"')

if __name__ == "__main__":
    main()
