# IMA 笔记打通步骤

> 将储能监控系统数据自动同步到 IMA 个人笔记

---

## 第一步：获取 IMA API 凭证

### 1.1 访问 IMA 开放平台
- 打开网址：https://ima.qq.com/opensource/ima-openapi/
- 使用微信扫码登录

### 1.2 创建应用
1. 点击「创建应用」
2. 填写应用信息：
   - 应用名称：储能监控系统
   - 应用描述：自动同步储能行业数据到 IMA 笔记
3. 提交审核（通常即时通过）

### 1.3 获取凭证
创建成功后，记录以下信息：
- **ClientID**: `ce839f70acfed5aaffb7eb06cea559fe`
- **API Key**: `cdCO7OyFhmlglo5TSZQQu1YKVE+dcvPU8UlCnjI5YWo2AhaIc37gsX61qiWIfifXo/3djbOqkw==`
- **Base URL**: `https://ima.qq.com/openapi/note/v1`

---

## 第二步：配置同步脚本

### 2.1 脚本位置
```
/root/.openclaw/workspace/energy_storage/sync_ima.py
```

### 2.2 修改配置（如需要）
编辑脚本开头的配置部分：

```python
# IMA API 配置
IMA_CLIENTID = os.getenv("IMA_OPENAPI_CLIENTID", "你的ClientID")
IMA_APIKEY = os.getenv("IMA_OPENAPI_APIKEY", "你的APIKey")
IMA_BASE_URL = "https://ima.qq.com/openapi/note/v1"

# 目标笔记本名称（如果不存在会同步到「全部笔记」）
FOLDER_NAME = "储能数据"
```

### 2.3 创建目标笔记本
1. 打开 IMA 客户端/网页版
2. 创建笔记本，命名为「储能数据」
3. 脚本会自动识别并同步到这个笔记本

---

## 第三步：测试同步

### 3.1 手动运行测试
```bash
cd /root/.openclaw/workspace/energy_storage
python3 sync_ima.py
```

### 3.2 预期输出
```
============================================================
储能数据同步到 IMA
运行时间: 2026-03-29 01:30:00
============================================================

[1/4] 查找笔记本...
  ✓ 找到笔记本 '储能数据': xxxxxxxx

[2/4] 加载数据...
  ✓ 爬虫数据: 20 条
  ✓ API数据: 5 条

[3/4] 格式化内容...
  ✓ 内容长度: 3500 字符

[4/4] 写入 IMA...
  ✓ 创建笔记成功: xxxxxxxx

============================================================
同步完成
============================================================
```

### 3.3 在 IMA 中验证
1. 打开 IMA 客户端
2. 进入「储能数据」笔记本
3. 查看是否出现「储能日报 20260329」笔记

---

## 第四步：设置定时任务

### 4.1 添加 cron 任务
```bash
openclaw cron add
```

配置示例：
```json
{
  "name": "储能数据 IMA 同步",
  "schedule": {"kind": "cron", "expr": "0 */4 * * *", "tz": "Asia/Shanghai"},
  "payload": {
    "kind": "agentTurn",
    "message": "运行储能数据 IMA 同步任务：cd /root/.openclaw/workspace/energy_storage && python3 sync_ima.py"
  },
  "sessionTarget": "isolated",
  "enabled": true
}
```

### 4.2 或者直接添加到现有任务
储能系统的爬虫任务已经配置了 IMA 同步，每4小时自动运行一次。

---

## 第五步：故障排查

### 5.1 常见问题

**问题1：找不到笔记本**
- 解决：在 IMA 中手动创建「储能数据」笔记本

**问题2：API 调用失败**
- 检查 ClientID 和 API Key 是否正确
- 检查网络连接
- 查看日志：`sync_ima.log`

**问题3：数据为空**
- 确认爬虫已正常运行
- 检查数据目录：`energy_storage/data/crawler/`

### 5.2 查看日志
```bash
tail -f /root/.openclaw/workspace/energy_storage/sync_ima.log
```

### 5.3 手动重新同步
```bash
cd /root/.openclaw/workspace/energy_storage
python3 sync_ima.py --force
```

---

## API 接口说明

### 支持的接口

| 接口 | 功能 | 端点 |
|------|------|------|
| list_note_folder_by_cursor | 列出笔记本 | note/v1/list_note_folder_by_cursor |
| list_note_by_folder_id | 列出笔记 | note/v1/list_note_by_folder_id |
| import_doc | 创建笔记 | note/v1/import_doc |
| append_doc | 追加内容 | note/v1/append_doc |

### 请求头格式
```
ima-openapi-clientid: {ClientID}
ima-openapi-apikey: {APIKey}
Content-Type: application/json
```

---

## 当前配置状态

✅ **已完成配置**
- ClientID: ce839f70acfed5aaffb7eb06cea559fe
- API Key: 已配置
- 同步频率: 每4小时
- 目标笔记本: 储能数据
- 最后同步: 2026-03-29

**同步内容**：
- 网站爬虫数据（北极星储能网、储能中国等）
- API监控数据（新浪财经行情）
- 自动生成「储能日报」格式笔记

---

**配置文件位置**: `energy_storage/sync_ima.py`  
**日志位置**: `energy_storage/sync_ima.log`
