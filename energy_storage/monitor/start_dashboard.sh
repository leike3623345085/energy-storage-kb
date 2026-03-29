#!/bin/bash
# 任务执行实时监控面板启动脚本

echo "========================================"
echo "  任务执行实时监控面板"
echo "========================================"
echo ""

# 检查依赖
echo "[1/4] 检查依赖..."
pip install flask flask-socketio -q 2>/dev/null || echo "依赖已安装"

# 初始化数据库
echo "[2/4] 初始化数据库..."
cd /root/.openclaw/workspace/energy_storage
python3 monitor/collector.py

# 启动监控面板
echo "[3/4] 启动监控面板..."
echo ""
echo "面板地址: http://localhost:5000"
echo ""

# 后台运行
nohup python3 monitor/dashboard_server.py > /tmp/task_monitor.log 2>&1 &
echo $! > /tmp/task_monitor.pid

echo "[4/4] 启动完成!"
echo ""
echo "查看日志: tail -f /tmp/task_monitor.log"
echo "停止服务: kill $(cat /tmp/task_monitor.pid)"
echo ""
