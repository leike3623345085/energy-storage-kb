#!/usr/bin/env python3
"""
直接添加储能网站爬虫定时任务到 jobs.json
"""
import json
import os

jobs_file = "/root/.openclaw/cron/jobs.json"

# 读取现有任务
with open(jobs_file, 'r') as f:
    data = json.load(f)

# 新任务配置
new_job = {
    "id": "1d5eb11b-91f7-40b4-8a67-94513f3ae803",
    "agentId": "main",
    "name": "储能网站爬虫-多站点V2",
    "enabled": True,
    "createdAtMs": 1772506188262,
    "updatedAtMs": 1774124827855,
    "schedule": {
        "expr": "0 */4 * * *",
        "kind": "cron",
        "tz": "Asia/Shanghai"
    },
    "sessionTarget": "isolated",
    "wakeMode": "now",
    "payload": {
        "kind": "agentTurn",
        "message": "【储能网站爬虫】执行多站点爬虫（V2稳定版）\n\ncd /root/.openclaw/workspace/energy_storage && timeout 300 python3 crawler_multi_v2.py\n\n检查数据量：\nls -lh /root/.openclaw/workspace/energy_storage/data/crawler/*.json | tail -3",
        "model": "kimi-coding/k2p5",
        "timeoutSeconds": 360
    },
    "delivery": {
        "mode": "announce",
        "channel": "kimi-claw",
        "to": "main"
    },
    "state": {
        "nextRunAtMs": 1774137600000
    }
}

# 检查是否已存在
existing_ids = [job.get("id") for job in data.get("jobs", [])]
if new_job["id"] in existing_ids:
    print(f"任务 {new_job['id']} 已存在，跳过添加")
else:
    data["jobs"].append(new_job)
    print(f"已添加任务: {new_job['name']}")

# 写回文件
with open(jobs_file, 'w') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print("jobs.json 已更新")
print(f"总任务数: {len(data['jobs'])}")
