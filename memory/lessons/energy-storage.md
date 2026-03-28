## 2026-03-28 飞书同步修复

### 问题
储能数据同步到飞书 Bitable 失败，错误信息：
```
field validation failed
字段错误: fields - fields is required
```

### 根本原因
飞书 Bitable 批量添加记录 API 的接口路径错误。
- ❌ 错误路径：`/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records`
- ✅ 正确路径：`/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_create`

### 修复
文件：`energy_storage/sync_batch.py`

1. 修改 `add_records` 方法中的 API URL，添加 `/batch_create` 后缀
2. 时间戳递增间隔从 1000ms 改为 100ms，确保主键唯一性

### 结果
- 成功同步 588 条记录到飞书
- 批量添加 API 正常工作

### 参考
- 飞书 API 文档：https://open.feishu.cn/document/server-docs/docs/bitable-v1/app-table-record/batch_create
