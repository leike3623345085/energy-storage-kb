#!/bin/bash
# 任务执行监控 - 企微通知版使用示例

# ========================================
# 配置企微机器人
# ========================================
# 方式1: 设置环境变量
# export WECHAT_WEBHOOK="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxxx"

# 方式2: 修改脚本中的默认配置

# ========================================
# 用法示例
# ========================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# 示例1: 测试通知
echo "测试企微通知..."
python3 "$SCRIPT_DIR/wechat_notifier.py" test_start
sleep 2
python3 "$SCRIPT_DIR/wechat_notifier.py" test_success

# 示例2: 包装现有命令
echo ""
echo "包装命令示例:"
echo "  原命令: ./my_script.sh"
echo "  监控版: $SCRIPT_DIR/wechat_notifier.py wrap \"数据同步\" ./my_script.sh"

# 示例3: 在Python脚本中使用
cat <> 'PYEOF'
# 在你的任务脚本中加入:
from wechat_notifier import notify_task_start, notify_task_success, notify_task_error
import time

task_name = "数据爬虫"
notify_task_start(task_name)

try:
    # 你的任务代码
    time.sleep(2)
    result = "抓取成功"
    
    notify_task_success(task_name, "2秒", result)
except Exception as e:
    notify_task_error(task_name, str(e))
PYEOF

echo ""
echo "========================================"
echo "  企微通知配置完成"
echo "========================================"
echo ""
echo "请设置环境变量:"
echo '  export WECHAT_WEBHOOK="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx"'
echo ""
echo "然后运行测试:"
echo "  python3 $SCRIPT_DIR/wechat_notifier.py test_start"
