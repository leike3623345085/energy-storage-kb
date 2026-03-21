#!/bin/bash
cd /root/.openclaw/workspace/energy_storage
python3 -u sync_daemon.py >> /tmp/sync_daemon.log 2>&1 &
echo $! > /tmp/sync_daemon.pid
echo "同步守护进程已启动，PID: $!"