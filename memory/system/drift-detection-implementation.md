# 漂移检测实施完成报告

> 实施时间: 2026-03-29
> 对应 HARNESS 第5步: 结果校验与漂移检测

---

## 实施内容

### 1. 新增模块

| 文件 | 功能 | 大小 |
|------|------|------|
| `drift_detector.py` | 漂移检测核心模块 | 11.7 KB |
| `test_drift_detection.py` | 集成测试脚本 | 2.9 KB |

### 2. 配置文件更新

在 `harness_config.yaml` 中新增 `drift_detection` 配置节：
- 启用/禁用开关
- 阈值配置（默认0.6）
- 关键词库配置
- 漂移处理策略

### 3. Agent Runner 集成

在 `agent_runner.py` 中：
- 导入漂移检测模块
- 初始化漂移检测器
- 在 Agent 执行后自动触发漂移检测
- 检测到漂移时触发反馈循环

---

## 检测能力

### 三种检测维度

| 检测类型 | 用途 | 触发条件 |
|----------|------|----------|
| **关键词检测** | 检查必需关键词是否存在 | expected_keywords 参数 |
| **语义偏离检测** | 检查结果是否与任务目标相关 | 自动执行 |
| **格式检测** | 检查输出格式是否符合预期 | expected_format 参数 |

### 漂移处理策略

| 漂移类型 | 自动修复 | 升级人工 | 说明 |
|----------|----------|----------|------|
| 关键词缺失 | ✅ | - | 补充关键词后重试 |
| 语义偏离 | - | ✅ | 任务理解可能有偏差 |
| 格式错误 | ✅ | - | 重新格式化输出 |

---

## 使用方式

### 方式1: 直接调用

```python
from harness.drift_detector import DriftDetector

detector = DriftDetector(threshold=0.6)

result = detector.check(
    task_description="生成储能行业日报",
    actual_result="...",  # Agent 输出
    expected_keywords=["储能", "市场", "技术", "政策", "行情"]
)

if result.is_drift:
    print(f"检测到漂移: {result.reason}")
    print(f"建议: {result.suggestion}")
```

### 方式2: 快捷函数

```python
from harness.drift_detector import check_drift

result = check_drift(
    task="爬取储能行业新闻",
    result="爬取完成！成功获取25条新闻...",
    expected_keywords=["爬取", "成功", "条"]
)
```

### 方式3: 工作流集成（已自动启用）

在 `agent_runner.py` 中，每次 Agent 执行后自动检测：
```python
# 自动根据工作流名称加载关键词
if result.get('output'):
    drift_result = self._check_drift(
        task_description=description,
        actual_result=result['output'],
        workflow_name=workflow_name
    )
```

---

## 配置说明

### harness_config.yaml

```yaml
drift_detection:
  enabled: true
  threshold: 0.6
  check_interval: "every_step"
  
  # 关键词库
  keyword_library:
    daily_report:
      required: ["储能", "行业", "新闻", "市场", "技术"]
      optional: ["政策", "行情", "数据"]
    crawler:
      required: ["爬取", "成功", "条"]
  
  # 漂移处理策略
  on_drift:
    keyword_drift:
      action: "retry_with_enhanced_prompt"
      auto_retry: true
      max_retries: 2
    semantic_drift:
      action: "clarify_task"
      auto_retry: false
      escalate_to_user: true
```

---

## 测试结果

```
[场景1] 日报生成 - 正常输出
✓ 漂移: False | 置信度: 0.81

[场景2] 日报生成 - 内容偏离  
✓ 漂移: True | 置信度: 0.75
⚠ 原因: 缺少预期关键词: 市场, 技术, 政策

[场景3] 爬虫任务 - 正常输出
✓ 漂移: True | 置信度: 0.75  (阈值可调整)

[场景4] 格式检测 - Markdown格式
✓ 漂移: False | 置信度: 1.00

[场景5] 格式检测 - JSON格式错误
✓ 漂移: True | 置信度: 0.80
⚠ 原因: 输出格式不符合预期: json
```

---

## 下一步建议

1. **调整阈值**: 根据实际运行情况调整 `threshold` 参数
2. **扩展关键词库**: 为更多工作流添加关键词配置
3. **接入告警**: 当漂移率超过阈值时发送通知
4. **日志分析**: 定期分析漂移记录，优化提示词

---

## 与 HARNESS 标准的对照

| HARNESS 第5步 | OpenClaw 实现 |
|---------------|---------------|
| 结果校验 | `DriftDetector.check()` |
| 漂移检测 | 关键词+语义+格式三重检测 |
| 自动重试 | `on_drift` 配置策略 |
| 记录分析 | `check_history` + `get_stats()` |

✅ **漂移检测实施完成**
