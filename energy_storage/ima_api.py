#!/usr/bin/env python3
"""
IMA 知识库 + 笔记 完整 API 调用脚本
====================================
凭证配置（二选一）：
  方式 A：~/.config/ima/client_id + ~/.config/ima/api_key
  方式 B：环境变量 IMA_OPENAPI_CLIENTID + IMA_OPENAPI_APIKEY

用法示例：
  # ── 知识库 ──
  python3 ima_api.py search_kb --query ""              # 列出所有知识库
  python3 ima_api.py search_kb_content --kb-id "xxx" --query "关键词"  # 搜索知识库内容
  python3 ima_api.py list_kb --kb-id "xxx"             # 浏览知识库内容
  python3 ima_api.py add_url --kb-id "xxx" --url "https://example.com"  # 添加网页
  python3 ima_api.py upload_file --kb-id "xxx" --file "/path/to/file.pdf"  # 上传文件

  # ── 笔记 ──
  python3 ima_api.py search_note --query "会议纪要"    # 搜索笔记
  python3 ima_api.py list_notes                        # 列出所有笔记
  python3 ima_api.py get_note --doc-id "xxx"           # 读取笔记内容
  python3 ima_api.py create_note --content "# 标题\n\n正文"  # 新建笔记
  python3 ima_api.py append_note --doc-id "xxx" --content "追加内容"  # 追加到笔记
"""

import json, sys, os, argparse, urllib.request, urllib.error, mimetypes, time
from pathlib import Path

BASE_URL = "https://ima.qq.com"

# ─── 凭证加载 ───────────────────────────────────────────────

def load_credentials():
    client_id = os.environ.get("IMA_OPENAPI_CLIENTID", "")
    api_key = os.environ.get("IMA_OPENAPI_APIKEY", "")
    if not client_id:
        f = Path.home() / ".config" / "ima" / "client_id"
        if f.exists():
            client_id = f.read_text().strip()
    if not api_key:
        f = Path.home() / ".config" / "ima" / "api_key"
        if f.exists():
            api_key = f.read_text().strip()
    if not client_id or not api_key:
        print("❌ 缺少 IMA 凭证，请配置 ~/.config/ima/client_id 和 api_key")
        print("   或设置环境变量 IMA_OPENAPI_CLIENTID / IMA_OPENAPI_APIKEY")
        sys.exit(1)
    return client_id, api_key

CLIENT_ID, API_KEY = load_credentials()

# ─── 通用请求 ───────────────────────────────────────────────

def ima_api(path, payload):
    """调用 IMA OpenAPI，返回 data 字段"""
    url = f"{BASE_URL}{path}"
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={
        "Content-Type": "application/json",
        "ima-openapi-clientid": CLIENT_ID,
        "ima-openapi-apikey": API_KEY,
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        sys.exit(1)
    # 兼容 retcode / code 两种返回格式
    retcode = result.get("retcode", result.get("code", -1))
    errmsg = result.get("errmsg", result.get("msg", ""))
    if retcode not in (0, "0"):
        print(f"❌ API 错误 (code={retcode}): {errmsg}")
        sys.exit(1)
    return result.get("data", {})

# ─── 文件类型映射 ───────────────────────────────────────────

EXT_MEDIA_TYPE = {
    "pdf": 1, "doc": 3, "docx": 3, "ppt": 4, "pptx": 4,
    "xls": 5, "xlsx": 5, "csv": 5, "md": 7, "markdown": 7,
    "png": 9, "jpg": 9, "jpeg": 9, "webp": 9,
    "txt": 13, "xmind": 14, "mp3": 15, "m4a": 15, "wav": 15, "aac": 15,
}

EXT_CONTENT_TYPE = {
    "pdf": "application/pdf",
    "doc": "application/msword",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "ppt": "application/vnd.ms-powerpoint",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "xls": "application/vnd.ms-excel",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "csv": "text/csv",
    "md": "text/markdown", "markdown": "text/markdown",
    "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp",
    "txt": "text/plain",
    "xmind": "application/x-xmind",
    "mp3": "audio/mpeg", "m4a": "audio/x-m4a", "wav": "audio/wav", "aac": "audio/aac",
}

# ─── 知识库 API ─────────────────────────────────────────────

def search_kb(query, limit=20):
    """搜索知识库列表"""
    data = ima_api("/openapi/wiki/v1/search_knowledge_base", {
        "query": query, "cursor": "", "limit": limit
    })
    items = data.get("info_list", [])
    if not items:
        print("📭 没有找到知识库")
    for item in items:
        print(f"  📚 {item['name']}  (ID: {item['id']})")
    return items

def search_kb_content(kb_id, query):
    """搜索知识库内容"""
    data = ima_api("/openapi/wiki/v1/search_knowledge", {
        "query": query, "cursor": "", "knowledge_base_id": kb_id
    })
    items = data.get("info_list", [])
    if not items:
        print("📭 没有找到匹配内容")
    for item in items:
        title = item.get("title", "无标题")
        highlight = item.get("highlight_content", "")
        print(f"  📄 {title}")
        if highlight:
            print(f"     {highlight}")
    return items

def list_kb(kb_id, folder_id=None):
    """浏览知识库内容"""
    payload = {"cursor": "", "limit": 50, "knowledge_base_id": kb_id}
    if folder_id:
        payload["folder_id"] = folder_id
    data = ima_api("/openapi/wiki/v1/get_knowledge_list", payload)
    items = data.get("knowledge_list", [])
    if not items:
        print("📭 知识库为空")
    for item in items:
        if "folder_id" in item:
            # 文件夹
            print(f"  📁 {item['name']}  (文件夹, {item.get('file_number', 0)} 文件)")
        else:
            print(f"  📄 {item.get('title', '无标题')}  (ID: {item.get('media_id', '')})")
    return items

def add_url(kb_id, url, folder_id=None):
    """添加网页到知识库"""
    payload = {"knowledge_base_id": kb_id, "folder_id": folder_id or kb_id, "urls": [url]}
    data = ima_api("/openapi/wiki/v1/import_urls", payload)
    results = data.get("results", {})
    for u, r in results.items():
        if r.get("ret_code") == 0:
            print(f"✅ 添加成功: {u}  (media_id: {r.get('media_id', '')})")
        else:
            print(f"❌ 添加失败: {u}")
    return results

def _cos_sign(secret_id, secret_key, method, uri, host, content_type=""):
    """计算 COS 临时密钥签名（修正版）"""
    import hmac, hashlib
    start_time = int(time.time()) - 60
    end_time = start_time + 3600
    key_time = f"{start_time};{end_time}"
    
    # 1. SignKey
    sign_key = hmac.new(secret_key.encode("utf-8"), key_time.encode("utf-8"), hashlib.sha1).hexdigest()
    
    # 2. HttpString
    from urllib.parse import quote
    encoded_uri = quote(uri, safe="/")
    headers_to_sign = {"host": host.lower()}
    if content_type:
        headers_to_sign["content-type"] = quote(content_type, safe="")
    sorted_headers = sorted(headers_to_sign.items())
    http_headers = "&".join([f"{k}={v}" for k, v in sorted_headers])
    http_string = f"{method.lower()}\n{encoded_uri}\n\n{http_headers}\n"
    
    # 3. StringToSign
    http_string_hash = hashlib.sha1(http_string.encode("utf-8")).hexdigest()
    string_to_sign = f"sha1\n{key_time}\n{http_string_hash}\n"
    
    # 4. Signature
    signature = hmac.new(sign_key.encode("utf-8"), string_to_sign.encode("utf-8"), hashlib.sha1).hexdigest()
    
    # 5. Authorization
    header_list = ";".join([k for k, v in sorted_headers])
    auth = f"q-sign-algorithm=sha1&q-ak={secret_id}&q-sign-time={key_time}&q-key-time={key_time}&q-header-list={header_list}&q-url-param-list=&q-signature={signature}"
    return auth

def upload_file(kb_id, filepath, folder_id=None):
    """上传文件到知识库（create_media → COS upload → add_knowledge）"""
    filepath = Path(filepath)
    if not filepath.exists():
        print(f"❌ 文件不存在: {filepath}")
        sys.exit(1)

    file_name = filepath.name
    file_size = filepath.stat().st_size
    ext = filepath.suffix.lstrip(".").lower()
    media_type = EXT_MEDIA_TYPE.get(ext)
    content_type = EXT_CONTENT_TYPE.get(ext) or mimetypes.guess_type(str(filepath))[0] or "application/octet-stream"

    if not media_type:
        print(f"❌ 不支持的文件类型: .{ext}")
        sys.exit(1)

    # 文件大小检查
    size_limits = {5: 10*1024*1024, 13: 10*1024*1024, 14: 10*1024*1024, 7: 10*1024*1024, 9: 30*1024*1024}
    max_size = size_limits.get(media_type, 200*1024*1024)
    if file_size > max_size:
        print(f"❌ 文件过大 ({file_size/1024/1024:.1f}MB > {max_size/1024/1024:.0f}MB)")
        sys.exit(1)

    print(f"📤 上传文件: {file_name} ({file_size/1024:.1f}KB)")

    # Step 1: create_media
    media_data = ima_api("/openapi/wiki/v1/create_media", {
        "file_name": file_name, "file_size": file_size,
        "content_type": content_type, "knowledge_base_id": kb_id, "file_ext": ext
    })
    media_id = media_data.get("media_id", "")
    cos_cred = media_data.get("cos_credential", {})
    print(f"  ✅ 获取 media_id: {media_id}")

    # Step 2: COS 上传（使用临时密钥签名）
    cos_key = cos_cred.get("cos_key", "")
    bucket = cos_cred.get("bucket_name", "")
    region = cos_cred.get("region", "")
    cos_url = f"https://{bucket}.cos.{region}.myqcloud.com/{cos_key}"
    host = f"{bucket}.cos.{region}.myqcloud.com"
    
    # 计算签名
    auth = _cos_sign(cos_cred["secret_id"], cos_cred["secret_key"], "PUT", f"/{cos_key}", host, content_type)

    with open(filepath, "rb") as f:
        file_data = f.read()

    cos_req = urllib.request.Request(cos_url, data=file_data, method="PUT", headers={
        "Content-Type": content_type,
        "Host": host,
        "Authorization": auth,
        "x-cos-security-token": cos_cred.get("token", ""),
    })
    try:
        with urllib.request.urlopen(cos_req, timeout=120) as resp:
            if resp.status < 300:
                print(f"  ✅ COS 上传成功")
            else:
                print(f"  ❌ COS 上传失败: HTTP {resp.status}")
                sys.exit(1)
    except Exception as e:
        print(f"  ❌ COS 上传异常: {e}")
        sys.exit(1)

    # Step 3: add_knowledge
    add_data = ima_api("/openapi/wiki/v1/add_knowledge", {
        "media_type": media_type, "media_id": media_id,
        "title": file_name, "knowledge_base_id": kb_id,
        "file_info": {
            "cos_key": cos_key, "file_size": file_size,
            "last_modify_time": int(time.time()), "file_name": file_name
        }
    })
    print(f"  ✅ 文件已添加到知识库 (media_id: {add_data.get('media_id', '')})")
    return add_data

def add_note_to_kb(kb_id, doc_id, title, folder_id=None):
    """添加笔记到知识库"""
    payload = {
        "media_type": 11, "title": title, "knowledge_base_id": kb_id,
        "note_info": {"content_id": doc_id}
    }
    if folder_id:
        payload["folder_id"] = folder_id
    data = ima_api("/openapi/wiki/v1/add_knowledge", payload)
    print(f"✅ 笔记已添加到知识库 (media_id: {data.get('media_id', '')})")
    return data

# ─── 笔记 API ──────────────────────────────────────────────

def search_note(query, search_type=0):
    """搜索笔记 (0=标题, 1=正文)"""
    data = ima_api("/openapi/note/v1/search_note_book", {
        "query_info": {"title": query, "content": query},
        "search_type": search_type, "start": 0, "end": 20
    })
    docs = data.get("docs", [])
    if not docs:
        print("📭 没有找到笔记")
    for d in docs:
        basic = d.get("doc", {}).get("basic_info", {})
        title = basic.get("title", "无标题")
        doc_id = basic.get("docid", "")
        folder = basic.get("folder_name", "")
        print(f"  📝 {title}  (ID: {doc_id}, 笔记本: {folder})")
    return docs

def list_notes(folder_id=None):
    """列出笔记"""
    payload = {"cursor": "", "limit": 20}
    if folder_id:
        payload["folder_id"] = folder_id
    data = ima_api("/openapi/note/v1/list_note_by_folder_id", payload)
    notes = data.get("note_book_list", [])
    if not notes:
        print("📭 没有笔记")
    for n in notes:
        basic = n.get("basic_info", {}).get("basic_info", {})
        title = basic.get("title", "无标题")
        doc_id = basic.get("docid", "")
        modify = basic.get("modify_time", 0)
        try:
            modify_str = time.strftime("%Y-%m-%d %H:%M", time.localtime(int(modify) / 1000))
        except (ValueError, TypeError, OSError):
            modify_str = str(modify) if modify else "未知"
        print(f"  📝 {title}  (ID: {doc_id}, 更新: {modify_str})")
    return notes

def get_note(doc_id):
    """读取笔记内容"""
    data = ima_api("/openapi/note/v1/get_doc_content", {
        "doc_id": doc_id, "target_content_format": 0
    })
    content = data.get("content", "")
    print(content)
    return content

def create_note(content, folder_id=None):
    """新建笔记"""
    payload = {"content": content, "content_format": 1}
    if folder_id:
        payload["folder_id"] = folder_id
    data = ima_api("/openapi/note/v1/import_doc", payload)
    doc_id = data.get("doc_id", "")
    print(f"✅ 笔记创建成功 (ID: {doc_id})")
    return doc_id

def append_note(doc_id, content):
    """追加内容到笔记"""
    data = ima_api("/openapi/note/v1/append_doc", {
        "doc_id": doc_id, "content": content, "content_format": 1
    })
    print(f"✅ 追加成功 (ID: {data.get('doc_id', '')})")
    return data

# ─── CLI ────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description="IMA 知识库 + 笔记 API")
    sub = p.add_subparsers(dest="cmd")

    # 知识库命令
    kb_search = sub.add_parser("search_kb", help="搜索知识库列表")
    kb_search.add_argument("--query", "-q", required=True, help="搜索关键词（空字符串=列出全部）")
    kb_search.add_argument("--limit", type=int, default=20)

    kb_content = sub.add_parser("search_kb_content", help="搜索知识库内容")
    kb_content.add_argument("--kb-id", required=True, help="知识库 ID")
    kb_content.add_argument("--query", "-q", required=True, help="搜索关键词")

    kb_list = sub.add_parser("list_kb", help="浏览知识库内容")
    kb_list.add_argument("--kb-id", required=True, help="知识库 ID")
    kb_list.add_argument("--folder-id", help="文件夹 ID")

    kb_url = sub.add_parser("add_url", help="添加网页到知识库")
    kb_url.add_argument("--kb-id", required=True, help="知识库 ID")
    kb_url.add_argument("--url", "-u", required=True, help="网页 URL")
    kb_url.add_argument("--folder-id", help="文件夹 ID")

    kb_upload = sub.add_parser("upload_file", help="上传文件到知识库")
    kb_upload.add_argument("--kb-id", required=True, help="知识库 ID")
    kb_upload.add_argument("--file", "-f", required=True, help="文件路径")
    kb_upload.add_argument("--folder-id", help="文件夹 ID")

    kb_note = sub.add_parser("add_note_to_kb", help="添加笔记到知识库")
    kb_note.add_argument("--kb-id", required=True, help="知识库 ID")
    kb_note.add_argument("--doc-id", required=True, help="笔记 ID")
    kb_note.add_argument("--title", required=True, help="标题")
    kb_note.add_argument("--folder-id", help="文件夹 ID")

    # 笔记命令
    note_search = sub.add_parser("search_note", help="搜索笔记")
    note_search.add_argument("--query", "-q", required=True, help="搜索关键词")
    note_search.add_argument("--type", choices=["title", "content"], default="title")

    note_list = sub.add_parser("list_notes", help="列出笔记")
    note_list.add_argument("--folder-id", help="笔记本 ID")

    note_get = sub.add_parser("get_note", help="读取笔记内容")
    note_get.add_argument("--doc-id", required=True, help="笔记 ID")

    note_create = sub.add_parser("create_note", help="新建笔记")
    note_create.add_argument("--content", "-c", required=True, help="笔记内容（Markdown）")
    note_create.add_argument("--folder-id", help="笔记本 ID")

    note_append = sub.add_parser("append_note", help="追加内容到笔记")
    note_append.add_argument("--doc-id", required=True, help="笔记 ID")
    note_append.add_argument("--content", "-c", required=True, help="追加内容（Markdown）")

    args = p.parse_args()

    if args.cmd == "search_kb":
        search_kb(args.query, args.limit)
    elif args.cmd == "search_kb_content":
        search_kb_content(args.kb_id, args.query)
    elif args.cmd == "list_kb":
        list_kb(args.kb_id, args.folder_id)
    elif args.cmd == "add_url":
        add_url(args.kb_id, args.url, args.folder_id)
    elif args.cmd == "upload_file":
        upload_file(args.kb_id, args.file, args.folder_id)
    elif args.cmd == "add_note_to_kb":
        add_note_to_kb(args.kb_id, args.doc_id, args.title, args.folder_id)
    elif args.cmd == "search_note":
        search_note(args.query, 0 if args.type == "title" else 1)
    elif args.cmd == "list_notes":
        list_notes(args.folder_id)
    elif args.cmd == "get_note":
        get_note(args.doc_id)
    elif args.cmd == "create_note":
        create_note(args.content, args.folder_id)
    elif args.cmd == "append_note":
        append_note(args.doc_id, args.content)
    else:
        p.print_help()

if __name__ == "__main__":
    main()
