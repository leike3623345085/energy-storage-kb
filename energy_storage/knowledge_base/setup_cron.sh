#!/bin/bash
# 储能报告知识库归档 - 定时任务配置脚本
# 配置到 OpenClaw 定时任务，实现报告自动生成后自动归档

echo "========================================="
echo "储能报告知识库归档 - 定时任务配置"
echo "========================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}步骤1: 配置知识库空间${NC}"
echo "请先获取飞书知识库的空间ID和父节点token："
echo ""
echo "获取方法："
echo "1. 在飞书打开目标知识库"
echo "2. 复制URL，格式：https://xxx.feishu.cn/wiki/空间ID?node=节点token"
echo ""
echo "示例命令："
echo "  cd energy_storage/knowledge_base"
echo "  python3 kb_manager.py --setup \"空间ID\" \"父节点token\""
echo ""
read -p "配置完成后按Enter继续..."

echo ""
echo -e "${YELLOW}步骤2: 添加知识库归档定时任务${NC}"
echo ""

# 任务1: 日报归档
echo "添加任务: 日报知识库归档 (每天18:25)"
openclaw cron add \
  --name "kb_sync_daily_report" \
  --schedule "0 25 18 * * *" \
  --command "cd /root/.openclaw/workspace/energy_storage/knowledge_base && python3 auto_sync.py daily" \
  --agent main \
  --target isolated

echo ""

# 任务2: 深度分析归档
echo "添加任务: 深度分析知识库归档 (每天18:30)"
openclaw cron add \
  --name "kb_sync_deep_analysis" \
  --schedule "0 30 18 * * *" \
  --command "cd /root/.openclaw/workspace/energy_storage/knowledge_base && python3 auto_sync.py deep" \
  --agent main \
  --target isolated

echo ""

# 任务3: 批量处理同步队列（每4小时）
echo "添加任务: 知识库同步队列处理 (每4小时)"
openclaw cron add \
  --name "kb_sync_queue_processor" \
  --schedule "0 0 */4 * * *" \
  --command "cd /root/.openclaw/workspace/energy_storage/knowledge_base && python3 sync_to_feishu.py --process-pending" \
  --agent main \
  --target isolated

echo ""

# 任务4: 周报归档
echo "添加任务: 周报知识库归档 (每周一9:30)"
openclaw cron add \
  --name "kb_sync_weekly" \
  --schedule "0 30 9 * * 1" \
  --command "cd /root/.openclaw/workspace/energy_storage/knowledge_base && python3 auto_sync.py weekly" \
  --agent main \
  --target isolated

echo ""
echo -e "${GREEN}========================================="
echo "定时任务配置完成！"
echo "=========================================${NC}"
echo ""
echo "已添加的定时任务："
echo "  1. kb_sync_daily_report     - 每天18:25归档日报"
echo "  2. kb_sync_deep_analysis    - 每天18:30归档深度分析"
echo "  3. kb_sync_queue_processor  - 每4小时处理同步队列"
echo "  4. kb_sync_weekly          - 每周一9:30归档周报"
echo ""
echo "查看所有任务: openclaw cron list"
echo "查看同步状态: cd energy_storage/knowledge_base && python3 kb_manager.py --status"
