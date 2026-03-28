#!/usr/bin/env python3
"""
储能数据批量同步到飞书 Bitable - 修复版
使用 OpenClaw feishu_bitable_create_record 工具
"""

import os
import sys
import json
import time
import subprocess
from datetime import datetime, timedelta
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

# 记录上限配置
MAX_RECORDS = 18000  # 保留空间，避免达到 20000 上限


def feishu_create_record(app_token, table_id, fields):
    """使用 OpenClaw CLI 创建飞书记录"""
    cmd = [
        "openclaw", "feishu", "bitable", "create-record",
        "--app-token", app_token,
        "--table-id", table_id,
        "--fields", json.dumps(fields, ensure_ascii=False)
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            return True, result.stdout
        else:
            return False, result.stderr
    except Exception as e:
        return False, str(e)


def find_data_files(base_dir="/root/.openclaw/workspace/energy_storage/data"):
    """查找所有数据文件"""
    data_path = Path(base_dir)
    if not data_path.exists():
        print(f"❌ 数据目录不存在: {base_dir}")
        return []
    
    files = []
    # 查找爬虫数据 (.log 和 .json)
    crawler_dir = data_path / "crawler"
    if crawler_dir.exists():
        files.extend(sorted(crawler_dir.glob("*.json"), reverse=True))
        files.extend(sorted(crawler_dir.glob("*.log"), reverse=True))
    
    # 查找搜索结果 (.json)
    news_dir = data_path / "news"
    if news_dir.exists():
        files.extend(sorted(news_dir.glob("*.json"), reverse=True))
    
    return sorted(files, key=lambda x: x.stat().st_mtime, reverse=True)


def parse_timestamp_to_iso(timestamp_str):
    """将各种时间格式转换为 ISO 8601 格式"""
    try:
        # 如果是数字（Unix 时间戳）
        if isinstance(timestamp_str, (int, float)):
            dt = datetime.fromtimestamp(timestamp_str)
            return dt.strftime("%Y-%m-%dT%H:%M:%S")
        
        # 尝试解析常见格式
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
            "%Y/%m/%d %H:%M:%S",
            "%Y/%m/%d",
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(timestamp_str, fmt)
                return dt.strftime("%Y-%m-%dT%H:%M:%S")
            except:
                continue
        
        # 如果都失败，返回当前时间
        return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    except:
        return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def load_and_transform_crawler(file_path):
    """加载爬虫数据并转换为 Bitable 格式"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        records = []
        source = data.get("source", "储能产业网")
        articles = data.get("data", [])
        
        # 使用文件修改时间作为基准时间
        file_mtime = Path(file_path).stat().st_mtime
        base_time = datetime.fromtimestamp(file_mtime)
        
        for idx, article in enumerate(articles):
            # 每条记录时间递增 1 秒
            record_time = base_time + timedelta(seconds=idx)
            
            # URL 处理：空链接时跳过 URL 字段
            link = article.get("link", "").strip()
            
            record = {
                "时间": record_time.strftime("%Y-%m-%dT%H:%M:%S"),
                "来源": source if source and source != "unknown" else "储能产业网",
                "标题": article.get("title", "")[:1000],
                "内容": article.get("summary", "")[:2000] if article.get("summary") else "-",
                "网站": source if source and source != "unknown" else "储能产业网"
            }
            
            # 只在有有效链接时添加 URL 字段（飞书 URL 字段不能为空）
            if link and link.startswith("http"):
                record["URL"] = {"text": "查看原文", "link": link}
            
            records.append(record)
        
        return records
    except Exception as e:
        print(f"⚠️ 加载文件失败 {file_path}: {e}")
        return []


def load_and_transform_news(file_path):
    """加载搜索数据并转换为 Bitable 格式"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        records = []
        query = data.get("query", "")
        results = data.get("results", [])
        
        # 使用文件修改时间作为基准时间
        file_mtime = Path(file_path).stat().st_mtime
        base_time = datetime.fromtimestamp(file_mtime)
        
        for idx, result in enumerate(results):
            # 每条记录时间递增 1 秒
            record_time = base_time + timedelta(seconds=idx)
            
            record = {
                "时间": record_time.strftime("%Y-%m-%dT%H:%M:%S"),
                "类型": query,
                "标题": result.get("title", "")[:1000],
                "摘要": result.get("snippet", "")[:2000] if result.get("snippet") else "-",
            }
            
            # URL 处理
            link = result.get("url", "").strip()
            if link and link.startswith("http"):
                record["URL"] = {"text": "查看原文", "link": link}
            
            records.append(record)
        
        return records
    except Exception as e:
        print(f"⚠️ 加载文件失败 {file_path}: {e}")
        return []


def sync_files(max_files=5):
    """同步数据文件到飞书"""
    print(f"🚀 开始同步（最多 {max_files} 个文件）")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 查找数据文件
    files = find_data_files()
    if not files:
        print("⚠️ 未找到数据文件")
        return 0, 0
    
    print(f"📁 发现 {len(files)} 个数据文件")
    
    synced_count = 0
    total_records = 0
    
    # 处理前 max_files 个文件
    for i, file_path in enumerate(files[:max_files], 1):
        print(f"\n📄 [{i}/{max_files}] {file_path.name}")
        
        # 根据文件类型选择处理方式
        if "crawler" in str(file_path):
            records = load_and_transform_crawler(file_path)
            table_id = FEISHU_CONFIG["tables"]["crawler"]
        else:
            records = load_and_transform_news(file_path)
            table_id = FEISHU_CONFIG["tables"]["search"]
        
        if not records:
            print(f"   ⚠️ 无有效记录")
            continue
        
        print(f"   📝 准备写入 {len(records)} 条记录")
        
        # 逐条添加记录
        added = 0
        for record in records:
            success, msg = feishu_create_record(
                FEISHU_CONFIG["bitable_app_token"],
                table_id,
                record
            )
            if success:
                added += 1
            else:
                # 只在失败时打印错误
                if added == 0:  # 第一次失败时显示错误信息
                    print(f"   ⚠️ 写入失败: {msg[:100]}...")
            
            # 小间隔避免限流
            time.sleep(0.05)
        
        print(f"   ✅ 成功写入 {added}/{len(records)} 条记录")
        
        total_records += added
        synced_count += 1
        
        # 文件间间隔
        time.sleep(0.5)
    
    print(f"\n🎉 同步完成")
    print(f"   文件数: {synced_count}/{max_files}")
    print(f"   记录数: {total_records}")
    print(f"   剩余: {len(files) - synced_count} 个文件待处理")
    
    return synced_count, total_records


if __name__ == "__main__":
    max_files = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    sync_files(max_files)
