#!/usr/bin/env python3
"""
储能数据批量同步到飞书
最多同步5个历史文件
"""

import os
import subprocess
from datetime import datetime

def get_existing_feishu_files():
    """获取飞书中已存在的文件列表"""
    result = subprocess.run(
        ['openclaw', 'feishu', 'drive', 'list'],
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        # 简单解析输出中的文件名
        return result.stdout
    return ""

def sync_to_feishu(max_files=5):
    """同步储能数据文件到飞书"""
    data_dir = "/root/.openclaw/workspace/energy_storage/data"
    
    if not os.path.exists(data_dir):
        print(f"❌ 数据目录不存在: {data_dir}")
        return 0
    
    # 获取所有储能数据文件（按时间排序）
    files = sorted([f for f in os.listdir(data_dir) if f.endswith('.md')])
    
    if not files:
        print("📭 没有待同步的数据文件")
        return 0
    
    print(f"📁 发现 {len(files)} 个数据文件，本次最多同步 {max_files} 个")
    
    synced_count = 0
    for file in files[:max_files]:
        file_path = os.path.join(data_dir, file)
        feishu_filename = f"储能_{file}"
        
        print(f"  📤 同步中: {file}")
        
        # 读取文件内容
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 上传为飞书文档
        result = subprocess.run(
            ['openclaw', 'feishu', 'doc', 'create', 
             '--title', feishu_filename.replace('.md', ''),
             '--content', content],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            synced_count += 1
            print(f"  ✅ 同步成功: {feishu_filename}")
        else:
            print(f"  ❌ 同步失败: {result.stderr}")
    
    print(f"\n📊 同步完成: {synced_count}/{min(max_files, len(files))} 个文件")
    return synced_count

if __name__ == "__main__":
    sync_to_feishu(max_files=5)
