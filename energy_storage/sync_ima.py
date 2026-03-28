#!/usr/bin/env python3
"""
储能数据同步到 IMA 笔记
- 将爬虫/API数据整理后写入 IMA
- 支持新建笔记或追加到已有笔记
"""

import json
import os
import urllib.request
import ssl
from datetime import datetime
from pathlib import Path

# IMA API 配置
IMA_CLIENTID = os.getenv("IMA_OPENAPI_CLIENTID", "ce839f70acfed5aaffb7eb06cea559fe")
IMA_APIKEY = os.getenv("IMA_OPENAPI_APIKEY", "cdCO7OyFhmlglo5TSZQQu1YKVE+dcvPU8UlCnjI5YWo2AhaIc37gsX61qiWIfifXo/3djbOqkw==")
IMA_BASE_URL = "https://ima.qq.com/openapi/note/v1"

DATA_DIR = Path(__file__).parent / "data"
CACHE_FILE = Path(__file__).parent / "cache" / "ima_sync_cache.json"

ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE


def ima_api(endpoint: str, body: dict) -> dict:
    """调用 IMA API"""
    url = f"{IMA_BASE_URL}/{endpoint}"
    headers = {
        "ima-openapi-clientid": IMA_CLIENTID,
        "ima-openapi-apikey": IMA_APIKEY,
        "Content-Type": "application/json"
    }
    
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode('utf-8'),
        headers=headers,
        method='POST'
    )
    
    try:
        with urllib.request.urlopen(req, timeout=30, context=ssl_context) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        print(f"  ✗ API 调用失败: {e}")
        return {"code": -1, "msg": str(e)}


def find_or_create_notebook(folder_name: str = "储能数据") -> str:
    """查找笔记本，返回 folder_id。如果找不到，返回 None（表示使用根目录）"""
    # 1. 列出所有笔记本
    result = ima_api("list_note_folder_by_cursor", {"cursor": "0", "limit": 20})
    
    if result.get("code") != 0:
        print(f"  ⚠️ 获取笔记本列表失败: {result.get('msg')}")
        return None
    
    folders = result.get("data", {}).get("note_book_folders", [])
    
    # 2. 查找目标笔记本
    for folder in folders:
        basic = folder.get("folder", {}).get("basic_info", {})
        if basic.get("name") == folder_name:
            folder_id = basic.get("folder_id")
            print(f"  ✓ 找到笔记本 '{folder_name}': {folder_id}")
            return folder_id
    
    # 3. 没找到，使用根目录（全部笔记）
    print(f"  ⚠️ 未找到笔记本 '{folder_name}'，将同步到「全部笔记」")
    return None


def find_today_note(folder_id: str, date_str: str) -> str:
    """查找今天的笔记，返回 doc_id"""
    cursor = ""
    
    while True:
        result = ima_api("list_note_by_folder_id", {
            "folder_id": folder_id,
            "cursor": cursor,
            "limit": 20
        })
        
        if result.get("code") != 0:
            break
        
        data = result.get("data", {})
        notes = data.get("note_book_list", [])
        
        for note in notes:
            basic = note.get("basic_info", {}).get("basic_info", {})
            title = basic.get("title", "")
            if date_str in title and "储能日报" in title:
                doc_id = basic.get("docid")
                print(f"  ✓ 找到今日笔记: {title}")
                return doc_id
        
        # 分页
        if data.get("is_end"):
            break
        cursor = data.get("next_cursor", "")
        if not cursor:
            break
    
    return None


def create_note(folder_id: str, title: str, content: str) -> str:
    """创建新笔记，返回 doc_id"""
    body = {
        "content_format": 1,
        "content": content
    }
    # 如果指定了 folder_id，则添加到指定笔记本，否则添加到全部笔记
    if folder_id:
        body["folder_id"] = folder_id
    
    result = ima_api("import_doc", body)
    
    if result.get("code") == 0:
        doc_id = result.get("data", {}).get("doc_id")
        print(f"  ✓ 创建笔记成功: {doc_id}")
        return doc_id
    else:
        print(f"  ✗ 创建笔记失败: {result.get('msg')}")
        return None


def append_to_note(doc_id: str, content: str) -> bool:
    """追加内容到已有笔记"""
    result = ima_api("append_doc", {
        "doc_id": doc_id,
        "content_format": 1,
        "content": content
    })
    
    if result.get("code") == 0:
        print(f"  ✓ 追加内容成功")
        return True
    else:
        print(f"  ✗ 追加内容失败: {result.get('msg')}")
        return False


def load_crawler_data(date_str: str) -> list:
    """加载爬虫数据"""
    crawler_dir = DATA_DIR / "crawler"  # 修正目录名
    if not crawler_dir.exists():
        return []
    
    data_files = sorted(crawler_dir.glob(f"crawler_{date_str}*.json"), reverse=True)
    
    all_data = []
    for f in data_files[:3]:  # 最近3个文件
        try:
            with open(f, 'r', encoding='utf-8') as fp:
                data = json.load(fp)
                # 适配不同格式
                if isinstance(data, list):
                    all_data.extend(data)
                elif isinstance(data, dict):
                    all_data.extend(data.get("data", []))
        except Exception as e:
            print(f"  读取文件失败 {f}: {e}")
            pass
    
    return all_data


def load_api_data(date_str: str) -> list:
    """加载 API 数据"""
    api_dir = DATA_DIR / "api_data"
    if not api_dir.exists():
        return []
    
    data_files = sorted(api_dir.glob(f"*{date_str}*.json"), reverse=True)
    
    all_data = []
    for f in data_files[:2]:  # 最近2个文件
        try:
            with open(f, 'r', encoding='utf-8') as fp:
                data = json.load(fp)
                if isinstance(data, list):
                    all_data.extend(data)
                elif isinstance(data, dict):
                    all_data.extend(data.get("data", []))
        except Exception as e:
            print(f"  读取文件失败 {f}: {e}")
            pass
    
    return all_data


def format_content(date_str: str, crawler_data: list, api_data: list) -> str:
    """格式化笔记内容"""
    content = f"# 储能日报 {date_str}\n\n"
    content += f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
    
    # 数据统计
    total = len(crawler_data) + len(api_data)
    content += f"## 📊 数据概览\n\n"
    content += f"- 网站爬虫: {len(crawler_data)} 条\n"
    content += f"- API 监控: {len(api_data)} 条\n"
    content += f"- **总计: {total} 条**\n\n"
    
    # 爬虫数据
    if crawler_data:
        content += "## 🕷️ 网站监控\n\n"
        for item in crawler_data[:20]:  # 最多20条
            title = item.get("title", "无标题")
            source = item.get("source", "未知")
            url = item.get("url", "")
            content += f"### {title}\n"
            content += f"- 来源: {source}\n"
            if url:
                content += f"- 链接: {url}\n"
            content += "\n"
    
    # API 数据
    if api_data:
        content += "## 📡 API 监控\n\n"
        for item in api_data[:10]:  # 最多10条
            title = item.get("title", "无标题")
            source = item.get("source", "未知")
            content += f"- **{title}** ({source})\n"
        content += "\n"
    
    content += "---\n"
    content += "*本笔记由 OpenClaw 自动同步*\n"
    
    return content


def main():
    print("=" * 60)
    print("储能数据同步到 IMA")
    print(f"运行时间: {datetime.now()}")
    print("=" * 60)
    
    date_str = datetime.now().strftime("%Y%m%d")
    
    # 1. 查找笔记本
    print("\n[1/4] 查找笔记本...")
    folder_id = find_or_create_notebook("储能数据")
    if folder_id:
        print(f"  ✓ 将同步到指定笔记本")
    else:
        print(f"  → 将同步到「全部笔记」")
    
    # 2. 加载数据
    print("\n[2/4] 加载数据...")
    crawler_data = load_crawler_data(date_str)
    api_data = load_api_data(date_str)
    print(f"  ✓ 爬虫数据: {len(crawler_data)} 条")
    print(f"  ✓ API数据: {len(api_data)} 条")
    
    if not crawler_data and not api_data:
        print("  ⚠️ 无数据需要同步")
        return
    
    # 3. 格式化内容
    print("\n[3/4] 格式化内容...")
    content = format_content(date_str, crawler_data, api_data)
    print(f"  ✓ 内容长度: {len(content)} 字符")
    
    # 4. 写入 IMA
    print("\n[4/4] 写入 IMA...")
    doc_id = find_today_note(folder_id, date_str)
    
    if doc_id:
        # 追加到已有笔记
        append_content = f"\n\n## 更新 {datetime.now().strftime('%H:%M')}\n\n"
        append_content += f"新增数据 {len(crawler_data) + len(api_data)} 条\n\n"
        
        # 只追加摘要
        for item in crawler_data[:5]:
            append_content += f"- {item.get('title', '无标题')}\n"
        
        append_to_note(doc_id, append_content)
    else:
        # 创建新笔记
        title = f"储能日报 {date_str}"
        create_note(folder_id, title, content)
    
    print("\n" + "=" * 60)
    print("同步完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
