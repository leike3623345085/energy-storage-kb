#!/usr/bin/env python3
"""
储能报告 - 飞书知识库同步执行器
调用 feishu_wiki 和 feishu_doc 工具完成实际同步
"""

import json
import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path

# 路径配置
KB_DIR = Path(__file__).parent
PENDING_DIR = KB_DIR / "pending_sync"
LOG_FILE = KB_DIR / "logs" / "sync_exec.log"

def log(message: str):
    """记录日志"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_msg = f"[{timestamp}] {message}"
    print(log_msg)
    
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_msg + "\n")

def create_feishu_doc(space_id: str, title: str, content: str, parent_token: str = "") -> dict:
    """
    创建飞书文档
    通过调用 openclaw 命令行工具
    """
    log(f"📄 创建文档: {title}")
    
    # 构建命令
    cmd_parts = [
        "openclaw", "feishu_wiki",
        "--action", "create",
        "--space_id", space_id,
        "--title", title,
    ]
    
    if parent_token:
        cmd_parts.extend(["--parent_node_token", parent_token])
    
    try:
        # 先创建节点获取 obj_token
        result = subprocess.run(
            cmd_parts,
            capture_output=True,
            text=True,
            timeout=30,
            cwd="/root/.openclaw/workspace"
        )
        
        if result.returncode != 0:
            log(f"❌ 创建节点失败: {result.stderr}")
            return None
        
        # 解析结果获取 node_token 和 obj_token
        try:
            response = json.loads(result.stdout)
            node_token = response.get("node_token")
            obj_token = response.get("obj_token")
            
            if not obj_token:
                log(f"⚠️ 未获取到 obj_token")
                return response
            
            # 写入文档内容
            write_result = write_doc_content(obj_token, content)
            if write_result:
                log(f"✅ 文档创建并写入成功")
            else:
                log(f"⚠️ 文档创建成功，但写入内容失败")
            
            return response
            
        except json.JSONDecodeError:
            log(f"⚠️ 无法解析响应: {result.stdout[:200]}")
            return None
            
    except Exception as e:
        log(f"❌ 创建文档异常: {e}")
        return None

def write_doc_content(obj_token: str, content: str) -> bool:
    """
    写入文档内容
    """
    log(f"✏️ 写入文档内容: {obj_token[:20]}...")
    
    # 将内容转换为JSON字符串
    content_json = json.dumps({"content": content}, ensure_ascii=False)
    
    try:
        result = subprocess.run(
            [
                "openclaw", "feishu_doc",
                "--action", "write",
                "--doc_token", obj_token,
                "--content", content,
            ],
            capture_output=True,
            text=True,
            timeout=30,
            cwd="/root/.openclaw/workspace"
        )
        
        if result.returncode == 0:
            return True
        else:
            log(f"⚠️ 写入失败: {result.stderr[:200]}")
            return False
            
    except Exception as e:
        log(f"❌ 写入异常: {e}")
        return False

def process_pending_sync():
    """处理待同步的标记文件"""
    if not PENDING_DIR.exists():
        log("📂 没有待同步文件")
        return 0, 0
    
    pending_files = list(PENDING_DIR.glob("*.json"))
    if not pending_files:
        log("📂 没有待同步文件")
        return 0, 0
    
    log(f"🔄 发现 {len(pending_files)} 个待同步文件")
    
    success_count = 0
    for pending_file in pending_files:
        try:
            with open(pending_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            space_id = data.get("space_id")
            title = data.get("title")
            content = data.get("content")
            parent_token = data.get("parent_token", "")
            
            if not all([space_id, title, content]):
                log(f"⚠️ 同步数据不完整: {pending_file.name}")
                continue
            
            # 创建文档
            result = create_feishu_doc(space_id, title, content, parent_token)
            
            if result:
                # 成功，删除标记文件
                pending_file.unlink()
                log(f"✅ 同步完成，删除标记: {pending_file.name}")
                success_count += 1
            else:
                log(f"❌ 同步失败: {pending_file.name}")
                
        except Exception as e:
            log(f"❌ 处理文件异常 {pending_file.name}: {e}")
    
    log(f"📊 同步完成: {success_count}/{len(pending_files)}")
    return success_count, len(pending_files)

def sync_report_direct(report_file: Path, report_type: str, space_id: str, parent_token: str = "") -> bool:
    """
    直接同步报告文件到飞书
    """
    if not report_file.exists():
        log(f"❌ 报告不存在: {report_file}")
        return False
    
    # 读取内容
    try:
        with open(report_file, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        log(f"❌ 读取报告失败: {e}")
        return False
    
    # 提取日期作为标题
    import re
    match = re.search(r'(\d{8})', report_file.name)
    date_str = match.group(1) if match else datetime.now().strftime("%Y%m%d")
    
    title = f"{report_type}_{date_str}"
    
    # 创建文档
    result = create_feishu_doc(space_id, title, content, parent_token)
    return result is not None

def main():
    """主入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="飞书知识库同步执行器")
    parser.add_argument("--process-pending", action="store_true",
                        help="处理待同步队列")
    parser.add_argument("--sync-file", metavar="PATH",
                        help="同步指定文件")
    parser.add_argument("--type", default="报告",
                        help="报告类型")
    parser.add_argument("--space-id", 
                        help="知识库空间ID")
    parser.add_argument("--parent-token", default="",
                        help="父节点token")
    
    args = parser.parse_args()
    
    if args.process_pending:
        success, total = process_pending_sync()
        print(f"\n同步结果: {success}/{total}")
        return 0 if success == total else 1
    
    if args.sync_file:
        if not args.space_id:
            print("❌ 需要指定 --space-id")
            return 1
        
        success = sync_report_direct(
            Path(args.sync_file),
            args.type,
            args.space_id,
            args.parent_token
        )
        return 0 if success else 1
    
    # 默认处理待同步队列
    success, total = process_pending_sync()
    return 0 if success == total else 1

if __name__ == "__main__":
    exit(main())
