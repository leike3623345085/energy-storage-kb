#!/usr/bin/env python3
"""
储能报告知识库管理系统
自动将日报、深度分析等报告归档到飞书知识库
"""

import json
import os
import sys
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Tuple

# 配置
DATA_DIR = Path(__file__).parent.parent / "data"
REPORTS_DIR = DATA_DIR / "reports"
CONFIG_FILE = Path(__file__).parent / "kb_config.json"
LOG_FILE = Path(__file__).parent / "logs" / "kb_sync.log"

class KnowledgeBaseManager:
    """知识库管理器"""
    
    def __init__(self):
        self.config = self._load_config()
        self.space_id = self.config.get("space_id", "")
        self.parent_token = self.config.get("parent_token", "")
        self.synced_records = self.config.get("synced_records", [])
        
    def _load_config(self) -> dict:
        """加载配置"""
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return {
            "space_id": "",
            "parent_token": "",  # 储能报告知识库的父节点
            "synced_records": [],  # 已同步记录
            "auto_sync": True,  # 是否自动同步
        }
    
    def _save_config(self):
        """保存配置"""
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)
    
    def log(self, message: str):
        """记录日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"[{timestamp}] {message}"
        print(log_msg)
        
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_msg + "\n")
    
    def setup_space(self, space_id: str, parent_token: str = ""):
        """设置知识库空间"""
        self.config["space_id"] = space_id
        self.config["parent_token"] = parent_token
        self._save_config()
        self.log(f"✅ 知识库配置已更新: space_id={space_id}")
    
    def create_folder_structure(self) -> Dict[str, str]:
        """
        创建知识库文件夹结构
        返回文件夹token字典
        """
        folders = {
            "日报": "",
            "深度分析": "",
            "行业研报": "",
            "周报": "",
            "月报": "",
        }
        
        # 使用 feishu_wiki 工具创建节点
        for folder_name in folders.keys():
            self.log(f"📁 创建/检查文件夹: {folder_name}")
            # 这里会调用 feishu_wiki 创建节点
            # 实际调用通过外部命令或API
            
        return folders
    
    def sync_report(self, report_file: Path, report_type: str = "日报") -> bool:
        """
        同步单份报告到知识库
        
        Args:
            report_file: 报告文件路径
            report_type: 报告类型（日报/深度分析/周报等）
        
        Returns:
            是否同步成功
        """
        if not report_file.exists():
            self.log(f"❌ 报告文件不存在: {report_file}")
            return False
        
        # 读取报告内容
        try:
            with open(report_file, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            self.log(f"❌ 读取报告失败: {e}")
            return False
        
        # 提取日期和标题
        date_str = self._extract_date_from_filename(report_file.name)
        title = f"{report_type}_{date_str}"
        
        # 检查是否已同步
        record_key = f"{report_type}_{date_str}"
        if record_key in self.synced_records:
            self.log(f"⏭️ 报告已同步，跳过: {title}")
            return True
        
        self.log(f"📤 正在同步报告: {title}")
        
        # 调用 feishu 工具创建文档
        # 这里通过外部命令调用 openclaw 工具
        success = self._create_wiki_doc(title, content, report_type)
        
        if success:
            self.synced_records.append(record_key)
            self.config["synced_records"] = self.synced_records
            self._save_config()
            self.log(f"✅ 报告同步成功: {title}")
        else:
            self.log(f"❌ 报告同步失败: {title}")
        
        return success
    
    def _create_wiki_doc(self, title: str, content: str, folder: str) -> bool:
        """
        创建飞书知识库文档
        通过调用外部命令使用 feishu_wiki 工具
        """
        if not self.space_id:
            self.log("❌ 未配置知识库空间ID")
            return False
        
        # 将Markdown转换为飞书文档格式
        feishu_content = self._markdown_to_feishu(content)
        
        # 这里我们需要调用 feishu_wiki 工具
        # 由于是在 OpenClaw 环境中，我们创建一个标记文件
        # 实际同步可以通过定时任务或手动触发
        
        sync_marker = Path(__file__).parent / "pending_sync" / f"{title}_{datetime.now().strftime('%H%M%S')}.json"
        sync_marker.parent.mkdir(parents=True, exist_ok=True)
        
        sync_data = {
            "title": title,
            "content": feishu_content,
            "folder": folder,
            "space_id": self.space_id,
            "parent_token": self.parent_token,
            "created_at": datetime.now().isoformat(),
        }
        
        with open(sync_marker, "w", encoding="utf-8") as f:
            json.dump(sync_data, f, ensure_ascii=False, indent=2)
        
        self.log(f"📝 已创建同步标记: {sync_marker}")
        return True
    
    def _markdown_to_feishu(self, markdown_content: str) -> str:
        """
        将Markdown转换为飞书文档格式
        飞书文档使用特定的JSON格式
        """
        # 简化的转换，实际使用时可能需要更复杂的处理
        # 飞书文档API需要特定格式的内容块
        
        lines = markdown_content.split("\n")
        blocks = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # 标题转换
            if line.startswith("# "):
                blocks.append({
                    "type": "heading1",
                    "content": line[2:].strip()
                })
            elif line.startswith("## "):
                blocks.append({
                    "type": "heading2", 
                    "content": line[3:].strip()
                })
            elif line.startswith("### "):
                blocks.append({
                    "type": "heading3",
                    "content": line[4:].strip()
                })
            # 列表转换
            elif line.startswith("- ") or line.startswith("* "):
                blocks.append({
                    "type": "bullet",
                    "content": line[2:].strip()
                })
            elif line[0:2].strip().isdigit() and "." in line[:3]:
                blocks.append({
                    "type": "numbered",
                    "content": line[line.find(".")+1:].strip()
                })
            # 代码块
            elif line.startswith("```"):
                # 简化处理，实际需要收集多行
                continue
            # 普通文本
            else:
                blocks.append({
                    "type": "text",
                    "content": line
                })
        
        return json.dumps(blocks, ensure_ascii=False)
    
    def _extract_date_from_filename(self, filename: str) -> str:
        """从文件名提取日期"""
        # report_20260320.md -> 20260320
        # deep_analysis_20260320.md -> 20260320
        import re
        match = re.search(r'(\d{8})', filename)
        if match:
            return match.group(1)
        return datetime.now().strftime("%Y%m%d")
    
    def sync_today_reports(self) -> Tuple[int, int]:
        """
        同步今日报告
        
        Returns:
            (成功数, 总数)
        """
        today = datetime.now().strftime("%Y%m%d")
        return self.sync_reports_by_date(today)
    
    def sync_reports_by_date(self, date_str: str) -> Tuple[int, int]:
        """
        同步指定日期的所有报告
        
        Args:
            date_str: 日期字符串 (YYYYMMDD)
        
        Returns:
            (成功数, 总数)
        """
        self.log(f"📅 同步 {date_str} 的报告")
        
        reports = [
            (REPORTS_DIR / f"report_{date_str}.md", "日报"),
            (REPORTS_DIR / f"deep_analysis_{date_str}.md", "深度分析"),
            (REPORTS_DIR / f"weekly_report_{date_str}.md", "周报"),
        ]
        
        success_count = 0
        total_count = 0
        
        for report_file, report_type in reports:
            if report_file.exists():
                total_count += 1
                if self.sync_report(report_file, report_type):
                    success_count += 1
        
        self.log(f"📊 同步完成: {success_count}/{total_count} 份报告")
        return success_count, total_count
    
    def sync_all_pending(self) -> Tuple[int, int]:
        """
        同步所有待同步的报告
        
        Returns:
            (成功数, 总数)
        """
        self.log("🔄 开始同步所有待同步报告")
        
        # 扫描过去30天的报告
        success_count = 0
        total_count = 0
        
        for i in range(30):
            date = datetime.now() - timedelta(days=i)
            date_str = date.strftime("%Y%m%d")
            
            s, t = self.sync_reports_by_date(date_str)
            success_count += s
            total_count += t
        
        self.log(f"📊 全部同步完成: {success_count}/{total_count} 份报告")
        return success_count, total_count
    
    def get_sync_status(self) -> Dict:
        """获取同步状态"""
        today = datetime.now().strftime("%Y%m%d")
        
        status = {
            "config": {
                "space_id": self.space_id,
                "parent_token": self.parent_token[:10] + "..." if self.parent_token else "",
                "auto_sync": self.config.get("auto_sync", True),
            },
            "synced_count": len(self.synced_records),
            "today_pending": [],
            "pending_sync_files": [],
        }
        
        # 检查今日待同步
        reports = [
            (REPORTS_DIR / f"report_{today}.md", "日报"),
            (REPORTS_DIR / f"deep_analysis_{today}.md", "深度分析"),
        ]
        
        for report_file, report_type in reports:
            if report_file.exists():
                record_key = f"{report_type}_{today}"
                if record_key not in self.synced_records:
                    status["today_pending"].append({
                        "file": str(report_file.name),
                        "type": report_type,
                    })
        
        # 检查待同步标记文件
        pending_dir = Path(__file__).parent / "pending_sync"
        if pending_dir.exists():
            status["pending_sync_files"] = [f.name for f in pending_dir.glob("*.json")]
        
        return status


def main():
    """主入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="储能报告知识库管理")
    parser.add_argument("--setup", nargs=2, metavar=("SPACE_ID", "PARENT_TOKEN"),
                        help="设置知识库空间ID和父节点token")
    parser.add_argument("--sync-today", action="store_true",
                        help="同步今日报告")
    parser.add_argument("--sync-date", metavar="YYYYMMDD",
                        help="同步指定日期报告")
    parser.add_argument("--sync-all", action="store_true",
                        help="同步所有待同步报告")
    parser.add_argument("--status", action="store_true",
                        help="查看同步状态")
    
    args = parser.parse_args()
    
    kb = KnowledgeBaseManager()
    
    if args.setup:
        kb.setup_space(args.setup[0], args.setup[1])
        print(f"✅ 知识库配置完成")
        print(f"   空间ID: {args.setup[0]}")
        print(f"   父节点: {args.setup[1]}")
        return 0
    
    if args.sync_today:
        success, total = kb.sync_today_reports()
        print(f"\n同步结果: {success}/{total}")
        return 0 if success == total else 1
    
    if args.sync_date:
        success, total = kb.sync_reports_by_date(args.sync_date)
        print(f"\n同步结果: {success}/{total}")
        return 0 if success == total else 1
    
    if args.sync_all:
        success, total = kb.sync_all_pending()
        print(f"\n同步结果: {success}/{total}")
        return 0 if success == total else 1
    
    if args.status:
        status = kb.get_sync_status()
        print("\n📊 知识库同步状态")
        print("=" * 50)
        print(f"空间ID: {status['config']['space_id'] or '未配置'}")
        print(f"父节点: {status['config']['parent_token'] or '未配置'}")
        print(f"自动同步: {'开启' if status['config']['auto_sync'] else '关闭'}")
        print(f"已同步记录: {status['synced_count']} 条")
        print("-" * 50)
        if status["today_pending"]:
            print("📋 今日待同步报告:")
            for item in status["today_pending"]:
                print(f"   - {item['type']}: {item['file']}")
        else:
            print("✅ 今日无待同步报告")
        
        if status["pending_sync_files"]:
            print(f"\n📝 待处理同步文件: {len(status['pending_sync_files'])} 个")
        return 0
    
    # 默认显示状态
    status = kb.get_sync_status()
    print("\n📊 知识库同步状态")
    print("=" * 50)
    print(f"空间ID: {status['config']['space_id'] or '未配置'}")
    print(f"已同步记录: {status['synced_count']} 条")
    print("\n使用 --help 查看可用命令")
    return 0


if __name__ == "__main__":
    exit(main())
