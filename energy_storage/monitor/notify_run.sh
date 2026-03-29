#!/bin/bash
# 带企微通知的任务执行包装器
# 用法: notify_run.sh "任务名称" "实际命令"
# 示例: notify_run.sh "数据爬虫" "python3 crawl.py"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON="${SCRIPT_DIR}/../venv/bin/python3"
[ ! -f "$PYTHON" ] && PYTHON="python3"

TASK_NAME="${1:-未命名任务}"
shift  # 移除第一个参数，剩下的就是实际命令

if [ $# -eq 0 ]; then
    echo "用法: $0 \"任务名称\" 命令 [参数...]"
    exit 1
fi

# 生成任务ID
TASK_ID="${TASK_NAME}-$(date +%s)"
START_TIME=$(date +%s)
START_TIME_STR=$(date "+%H:%M:%S")

# 发送开始通知
$PYTHON "${SCRIPT_DIR}/wechat_notifier.py" internal_start "$TASK_NAME" "$TASK_ID" "$START_TIME_STR" 2>/dev/null || true

echo "[$START_TIME_STR] 🚀 开始执行: $TASK_NAME"
echo "命令: $@"
echo ""

# 执行实际命令，捕获输出
OUTPUT=$("$@" 2>&1)
EXIT_CODE=$?

END_TIME=$(date +%s)
END_TIME_STR=$(date "+%H:%M:%S")
DURATION=$((END_TIME - START_TIME))
DURATION_STR="${DURATION}s"
if [ $DURATION -ge 60 ]; then
    DURATION_STR="$((DURATION / 60))分$((DURATION % 60))秒"
fi

# 截断输出（企微限制）
OUTPUT_SHORT="${OUTPUT:0:500}"

# 根据结果发送通知
if [ $EXIT_CODE -eq 0 ]; then
    echo "[$END_TIME_STR] ✅ 执行成功 ($DURATION_STR)"
    $PYTHON "${SCRIPT_DIR}/wechat_notifier.py" internal_success "$TASK_NAME" "$DURATION_STR" "$OUTPUT_SHORT" 2>/dev/null || true
else
    echo "[$END_TIME_STR] ❌ 执行失败 ($DURATION_STR)"
    echo "错误: $OUTPUT"
    $PYTHON "${SCRIPT_DIR}/wechat_notifier.py" internal_error "$TASK_NAME" "$DURATION_STR" "$OUTPUT" 2>/dev/null || true
fi

exit $EXIT_CODE
