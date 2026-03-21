#!/usr/bin/env python3
"""
储能数据三平台统一读取工具
支持从 GitHub(本地)、飞书 Bitable、IMA 笔记读取数据
"""

import json
import requests
from pathlib import Path
from datetime import datetime

# 配置
DATA_DIR = Path("/root/.openclaw/workspace/energy_storage/data")
FEISHU_CONFIG = {
    "app_id": "cli_a934994591785cb3",
    "app_secret": "uBiJm9Xuv6xsNWHdAOq6Hgovp82mrItY",
    "app_token": "Pqpwbh5tkaSzdrsKvrhcfggVnGe",
    "tables": {
        "crawler": "tblbWZx9H76QpxCl",
        "search": "tblXS2e1FDVJlJ6m",
        "stocks": "tblKruLIh89NgNNL",
        "reports": "tbla0u1wX7kLQJ09"
    }
}
IMA_HEADERS = {
    "Content-Type": "application/json",
    "ima-openapi-clientid": "ce839f70acfed5aaffb7eb06cea559fe",
    "ima-openapi-apikey": "cdCO7OyFhmlglo5TSZQQu1YKVE+dcvPU8UlCnjI5YWo2AhaIc37gsX61qiWIfifXo/3djbOqkw=="
}

class DataReader:
    """三平台数据读取器"""
    
    # ============== GitHub (本地) ==============
    def read_local_reports(self, limit=5):
        """从本地读取报告"""
        reports_dir = DATA_DIR / "reports"
        if not reports_dir.exists():
            return []
        
        files = sorted(reports_dir.glob("*.md"), reverse=True)[:limit]
        results = []
        for f in files:
            with open(f, 'r', encoding='utf-8') as file:
                content = file.read()
            results.append({
                "source": "GitHub(本地)",
                "filename": f.name,
                "title": self._extract_title(content),
                "content_preview": content[:200] + "...",
                "size": len(content),
                "modified": datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            })
        return results
    
    def read_local_crawler(self, limit=3):
        """从本地读取爬虫数据"""
        crawler_dir = DATA_DIR / "crawler"
        if not crawler_dir.exists():
            return []
        
        files = sorted(crawler_dir.glob("*.json"), reverse=True)[:limit]
        results = []
        for f in files:
            with open(f, 'r', encoding='utf-8') as file:
                data = json.load(file)
            results.append({
                "source": "GitHub(本地)",
                "filename": f.name,
                "fetch_time": data.get("fetch_time", "未知"),
                "total_count": data.get("total_count", 0),
                "sources": data.get("sources", [])
            })
        return results
    
    # ============== 飞书 Bitable ==============
    def _get_feishu_token(self):
        """获取飞书访问令牌"""
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        resp = requests.post(url, json={
            "app_id": FEISHU_CONFIG["app_id"],
            "app_secret": FEISHU_CONFIG["app_secret"]
        }, timeout=10)
        result = resp.json()
        return result.get("tenant_access_token") if result.get("code") == 0 else None
    
    def read_feishu_reports(self, limit=5):
        """从飞书读取报告数据"""
        token = self._get_feishu_token()
        if not token:
            return []
        
        table_id = FEISHU_CONFIG["tables"]["reports"]
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_CONFIG['app_token']}/tables/{table_id}/records?page_size={limit}"
        headers = {"Authorization": f"Bearer {token}"}
        
        resp = requests.get(url, headers=headers, timeout=10)
        result = resp.json()
        
        if result.get("code") != 0:
            return []
        
        items = result.get("data", {}).get("items", [])
        results = []
        for item in items:
            fields = item.get("fields", {})
            results.append({
                "source": "飞书 Bitable",
                "record_id": item.get("record_id", ""),
                "type": fields.get("类型", ""),
                "title": fields.get("标题", ""),
                "filename": fields.get("文件名", ""),
                "content_preview": fields.get("内容", "")[:100] + "..." if fields.get("内容") else ""
            })
        return results
    
    def read_feishu_crawler(self, limit=5):
        """从飞书读取爬虫数据"""
        token = self._get_feishu_token()
        if not token:
            return []
        
        table_id = FEISHU_CONFIG["tables"]["crawler"]
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_CONFIG['app_token']}/tables/{table_id}/records?page_size={limit}"
        headers = {"Authorization": f"Bearer {token}"}
        
        resp = requests.get(url, headers=headers, timeout=10)
        result = resp.json()
        
        if result.get("code") != 0:
            return []
        
        items = result.get("data", {}).get("items", [])
        results = []
        for item in items:
            fields = item.get("fields", {})
            results.append({
                "source": "飞书 Bitable",
                "record_id": item.get("record_id", ""),
                "time": fields.get("时间", ""),
                "title": fields.get("标题", ""),
                "source_site": fields.get("网站", ""),
                "url": fields.get("URL", "")[:50] + "..." if len(fields.get("URL", "")) > 50 else fields.get("URL", "")
            })
        return results
    
    # ============== IMA 笔记 ==============
    def read_ima_notes(self, limit=5):
        """从 IMA 读取笔记"""
        url = "https://ima.qq.com/openapi/note/v1/list_note_by_folder_id"
        data = {"folder_id": "", "cursor": "", "limit": limit}
        
        resp = requests.post(url, headers=IMA_HEADERS, json=data, timeout=10)
        result = resp.json()
        
        if "note_book_list" not in result:
            return []
        
        items = result.get("note_book_list", [])
        results = []
        for item in items:
            info = item.get("basic_info", {}).get("basic_info", {})
            results.append({
                "source": "IMA 笔记",
                "doc_id": info.get("docid", ""),
                "title": info.get("title", ""),
                "summary": info.get("summary", "")[:100] + "..." if info.get("summary") else "",
                "create_time": datetime.fromtimestamp(int(info.get("create_time", 0))/1000).strftime("%Y-%m-%d %H:%M") if info.get("create_time") else "",
                "folder": info.get("folder_name", "未分类")
            })
        return results
    
    def get_ima_note_content(self, doc_id):
        """获取 IMA 笔记完整内容"""
        url = "https://ima.qq.com/openapi/note/v1/get_doc_content"
        data = {"doc_id": doc_id, "target_content_format": 0}  # 0=纯文本
        
        resp = requests.post(url, headers=IMA_HEADERS, json=data, timeout=10)
        result = resp.json()
        return result.get("content", "")
    
    # ============== 辅助方法 ==============
    def _extract_title(self, content):
        """从 Markdown 提取标题"""
        for line in content.split('\n')[:5]:
            if line.startswith('# '):
                return line.replace('# ', '')
        return "无标题"
    
    # ============== 统一接口 ==============
    def read_all_reports(self, limit_per_source=3):
        """从所有平台读取报告"""
        all_reports = []
        
        # GitHub (本地)
        all_reports.extend(self.read_local_reports(limit_per_source))
        
        # 飞书
        all_reports.extend(self.read_feishu_reports(limit_per_source))
        
        # IMA
        all_reports.extend(self.read_ima_notes(limit_per_source))
        
        return all_reports
    
    def read_all_crawler(self, limit_per_source=3):
        """从所有平台读取爬虫数据"""
        all_data = []
        
        # GitHub (本地)
        all_data.extend(self.read_local_crawler(limit_per_source))
        
        # 飞书
        all_data.extend(self.read_feishu_crawler(limit_per_source))
        
        return all_data


def main():
    reader = DataReader()
    
    print("="*60)
    print("储能数据三平台读取测试")
    print("="*60)
    
    # 读取报告
    print("\n📄 报告数据（各平台最新3条）:")
    print("-"*60)
    reports = reader.read_all_reports(3)
    for r in reports:
        print(f"\n来源: {r['source']}")
        if 'title' in r:
            print(f"标题: {r['title'][:50]}...")
        if 'filename' in r:
            print(f"文件: {r['filename']}")
        if 'modified' in r:
            print(f"修改: {r['modified']}")
        if 'folder' in r:
            print(f"分类: {r['folder']}")
    
    # 读取爬虫数据
    print("\n\n🕷️ 爬虫数据（各平台最新3条）:")
    print("-"*60)
    crawler_data = reader.read_all_crawler(3)
    for d in crawler_data:
        print(f"\n来源: {d['source']}")
        if 'fetch_time' in d:
            print(f"时间: {d['fetch_time']}")
        if 'total_count' in d:
            print(f"数量: {d['total_count']}条")
        if 'sources' in d:
            print(f"网站: {', '.join(d['sources'][:3])}")
        if 'title' in d:
            print(f"标题: {d['title'][:40]}...")
    
    print("\n" + "="*60)
    print(f"总计: {len(reports)} 条报告, {len(crawler_data)} 条爬虫数据")
    print("="*60)


if __name__ == "__main__":
    main()
