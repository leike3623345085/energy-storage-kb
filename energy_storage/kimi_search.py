#!/usr/bin/env python3
"""
储能行业搜索模块
使用web_search工具搜索行业最新动态
"""

import json
import os
from datetime import datetime

# 确保目录存在
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'news')
os.makedirs(DATA_DIR, exist_ok=True)

def kimi_search(query):
    """
    使用web_search工具搜索储能行业资讯
    由于这是在exec中执行，实际搜索需要调用外部web_search
    
    注意：这个函数会被task_wrapper调用，实际搜索由上层处理
    """
    print(f"搜索查询: {query}")
    print(f"搜索时间: {datetime.now()}")
    
    # 记录搜索历史
    history_file = os.path.join(DATA_DIR, 'search_history.json')
    history = []
    
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
        except:
            history = []
    
    # 添加新记录
    history.append({
        'timestamp': datetime.now().isoformat(),
        'query': query,
        'status': 'requested'
    })
    
    # 保存历史
    with open(history_file, 'w', encoding='utf-8') as f:
        json.dump(history[-100:], f, ensure_ascii=False, indent=2)
    
    print(f"✅ 搜索请求已记录")
    return True

if __name__ == '__main__':
    import sys
    query = sys.argv[1] if len(sys.argv) > 1 else "储能行业最新动态"
    kimi_search(query)
