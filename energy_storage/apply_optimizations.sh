#!/bin/bash
# energy_storage/apply_optimizations.sh
# 一键应用降本增效优化

echo "🚀 开始应用API调用优化..."

# 1. 备份当前cron
crontab -l > ~/cron_backup_$(date +%Y%m%d_%H%M).txt 2>/dev/null
echo "✅ 已备份当前cron配置"

# 2. 创建缓存目录
mkdir -p cache/analysis cache/content logs
echo "✅ 已创建缓存目录"

# 3. 安装新cron（需要确认）
echo ""
echo "📋 即将安装优化后的cron配置："
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
cat energy_storage/cron_optimized.txt
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
read -p "确认安装优化配置？(y/n) " confirm

if [ "$confirm" = "y" ]; then
    # 删除旧储能任务
    crontab -l 2>/dev/null | grep -v "energy_storage" > /tmp/cron_new.txt
    
    # 添加新配置
    cat energy_storage/cron_optimized.txt >> /tmp/cron_new.txt
    crontab /tmp/cron_new.txt
    
    echo "✅ 新cron配置已安装"
    echo ""
    echo "📊 优化效果预估："
    echo "  • AI调用频率：每小时4次 → 每4小时1次（-75%）"
    echo "  • 纯脚本任务：保持原频率（不消耗API）"
    echo "  • 预计节省Token：60-70%"
else
    echo "❌ 已取消安装"
fi

echo ""
echo "💡 其他优化建议："
echo "  1. 运行 'python3 energy_storage/setup_cache.py' 启用智能缓存"
echo "  2. 检查现有数据，避免重复分析"
echo "  3. 考虑非高峰时段运行重任务（凌晨2-6点）"
