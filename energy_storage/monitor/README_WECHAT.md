# 任务执行监控 - 企微通知版

最简单的方式：任务执行时自动推送企微消息。

## 配置

### 1. 设置企微机器人

```bash
export WECHAT_WEBHOOK="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxxxxx"
```

添加到 `~/.bashrc` 永久生效。

### 2. 测试通知

```bash
# 测试开始通知
python3 wechat_notifier.py test_start

# 测试成功通知  
python3 wechat_notifier.py test_success

# 测试失败通知
python3 wechat_notifier.py test_error
```

## 使用方法

### 方法1: 包装现有命令（推荐）

```bash
# 原命令
python3 crawl.py

# 加监控
./notify_run.sh "数据爬虫" python3 crawl.py
```

### 方法2: 在OpenClaw Cron中使用

把原有命令：
```yaml
payload:
  kind: agentTurn
  message: "执行储能数据爬虫"
```

改成：
```yaml
payload:
  kind: systemEvent
  # 通过脚本包装，自动发送通知
```

或在任务脚本开头结尾添加：
```python
from wechat_notifier import notify_task_start, notify_task_success, notify_task_error

task_name = "储能数据爬虫"
notify_task_start(task_name)

try:
    # 你的任务代码
    result = do_crawl()
    notify_task_success(task_name, "2分30秒", result)
except Exception as e:
    notify_task_error(task_name, str(e))
```

### 方法3: Python装饰器

```python
from wechat_notifier import monitored_task

@monitored_task("数据爬虫", "crawl-task-1")
def my_crawl():
    # 任务代码
    return "抓取成功"

# 自动发送开始/成功/失败通知
my_crawl()
```

## 消息示例

**开始执行**:
```
## ⏳ 任务开始执行
**任务名称**: 数据爬虫
**开始时间**: 14:30:25
---
正在执行中，请稍候...
```

**执行成功**:
```
## ✅ 任务执行成功
**任务名称**: 数据爬虫
**完成时间**: 14:32:55
**执行时长**: 2分30秒
状态: 成功
```

**执行失败**:
```
## ❌ 任务执行失败
**任务名称**: 数据爬虫
**失败时间**: 14:31:10
**执行时长**: 1分15秒
状态: 失败
**错误信息**:
```
连接超时，请检查网络配置
```
@all 请尽快处理
```

## 定时日报

添加 cron 任务，每天发送执行汇总：

```bash
# 每天18:00发送日报
0 18 * * * cd /root/.openclaw/workspace/energy_storage/monitor && python3 wechat_notifier.py daily
```

或通过 OpenClaw:
```bash
openclaw cron add --name "任务日报" --schedule "0 18 * * *" \
  --command "python3 wechat_notifier.py daily"
```
