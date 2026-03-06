#!/bin/bash
# 定时任务执行脚本 - 带重试机制
# 用法: ./run_with_retry.sh "任务名称" "命令"

TASK_NAME=$1
shift
COMMAND="$@"

MAX_RETRIES=5
RETRY_DELAY=60

echo "=========================================="
echo "任务: $TASK_NAME"
echo "时间: $(date)"
echo "命令: $COMMAND"
echo "=========================================="

for i in $(seq 0 $MAX_RETRIES); do
    if [ $i -eq 0 ]; then
        echo "第1次执行..."
    else
        echo "第$((i+1))次执行 (重试)..."
    fi
    
    # 执行命令
    eval $COMMAND
    
    if [ $? -eq 0 ]; then
        echo "✅ $TASK_NAME 执行成功"
        exit 0
    else
        echo "❌ $TASK_NAME 第$((i+1))次执行失败"
        
        if [ $i -lt $MAX_RETRIES ]; then
            echo "⏳ ${RETRY_DELAY}秒后重试..."
            sleep $RETRY_DELAY
        fi
    fi
done

# 所有重试都失败
echo "🚨 $TASK_NAME 连续$((MAX_RETRIES+1))次执行失败"

# 发送企业微信通知
cd /root/.openclaw/workspace/energy_storage
python3 -c "
from wechat_bot import send_alert
send_alert(
    title='🚨 定时任务执行失败',
    content='任务: $TASK_NAME\n时间: $(date +%Y-%m-%d %H:%M)\n状态: 连续$((MAX_RETRIES+1))次失败\n\n请检查系统。',
    priority='critical'
)
"

exit 1
