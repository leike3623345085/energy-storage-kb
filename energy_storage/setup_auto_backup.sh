#!/bin/bash
# 自动增量备份定时任务配置脚本

echo "🔄 配置自动增量备份..."

# 获取脚本路径
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE="/root/.openclaw/workspace"

# 测试备份脚本
echo "📋 测试备份脚本..."
cd "$WORKSPACE"

# 检查是否有变更需要备份
if git status --porcelain | grep -q .; then
    echo "✅ 检测到变更，测试提交..."
    
    # 配置git（如果还没配置）
    git config user.email "backup@energy-storage.local" 2>/dev/null || true
    git config user.name "Energy Storage Backup Bot" 2>/dev/null || true
    
    # 添加并提交（测试）
    git add -A
    git commit -m "test: 备份测试 $(date '+%Y-%m-%d %H:%M:%S')" || echo "没有变更需要提交"
    
    echo "✅ 测试完成"
else
    echo "ℹ️ 当前没有变更"
fi

echo ""
echo "📅 添加定时任务（每天23:50自动备份）..."

# 创建cron任务
# 注意：这里只是显示配置命令，实际需要用 openclaw cron add 添加
cat << 'EOF'

请运行以下命令添加定时任务：

openclaw cron add --name "储能数据自动备份" \
  --schedule "50 23 * * *" \
  --command "cd /root/.openclaw/workspace/energy_storage && python3 auto_backup.py" \
  --timeout 120

或者手动编辑 crontab：
50 23 * * * cd /root/.openclaw/workspace/energy_storage && /usr/bin/python3 auto_backup.py >> /root/.openclaw/workspace/energy_storage/logs/auto_backup.log 2>&1

EOF

echo ""
echo "✅ 配置完成！"
echo "   脚本位置: $SCRIPT_DIR/auto_backup.py"
echo "   备份时间: 每天 23:50"
echo "   目标仓库: https://github.com/leike3623345085/energy-storage-kb"
