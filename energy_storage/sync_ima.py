#!/usr/bin/env python3
"""
储能报告同步到 IMA
"""

import json
from pathlib import Path
import requests

DATA_DIR = Path("/root/.openclaw/workspace/energy_storage/data/reports")
STATE_FILE = Path("/tmp/ima_sync_state.json")

HEADERS = {
    "Content-Type": "application/json",
    "ima-openapi-clientid": "ce839f70acfed5aaffb7eb06cea559fe",
    "ima-openapi-apikey": "cdCO7OyFhmlglo5TSZQQu1YKVE+dcvPU8UlCnjI5YWo2AhaIc37gsX61qiWIfifXo/3djbOqkw=="
}

def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return set(json.load(f))
    return set()

def save_state(processed):
    with open(STATE_FILE, 'w') as f:
        json.dump(list(processed), f)

def create_note(title, content):
    """创建 IMA 笔记"""
    url = "https://ima.qq.com/openapi/note/v1/import_doc"
    data = {
        "content_format": 1,
        "content": content
    }
    try:
        resp = requests.post(url, headers=HEADERS, json=data, timeout=15)
        result = resp.json()
        if "doc_id" in result:
            return result["doc_id"]
        else:
            print(f"  ⚠️ 创建失败: {result}")
            return None
    except Exception as e:
        print(f"  ⚠️ 请求错误: {e}")
        return None

def sync_reports():
    processed = load_state()
    
    # 获取所有报告文件
    reports = sorted(DATA_DIR.glob("*.md"))
    new_reports = [f for f in reports if str(f) not in processed][:3]  # 每次最多3个
    
    if not new_reports:
        print("✅ 所有报告已同步到 IMA")
        return 0
    
    print(f"🔄 同步 {len(new_reports)}/{len(reports)-len(processed)} 个报告到 IMA...")
    
    for file_path in new_reports:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 添加同步标记
            content += "\n\n---\n*此笔记由 OpenClaw 自动同步*"
            
            # 截断过长的内容（IMA可能有限制）
            if len(content) > 50000:
                content = content[:50000] + "\n\n...[内容已截断]"
            
            doc_id = create_note(file_path.name, content)
            if doc_id:
                print(f"  ✅ {file_path.name} -> {doc_id}")
                processed.add(str(file_path))
                save_state(processed)
            else:
                print(f"  ❌ {file_path.name}")
                
        except Exception as e:
            print(f"  ⚠️ {file_path.name}: {e}")
    
    remaining = len(reports) - len(processed)
    print(f"完成，剩余 {remaining} 个文件")
    return remaining

if __name__ == "__main__":
    sync_reports()
