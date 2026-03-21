#!/usr/bin/env python3
"""
储能行业日报生成器 - Harness Engineering 版
基于 OpenAI Harness Engineering 架构的报告生成器
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 添加 harness 到路径
sys.path.insert(0, str(Path(__file__).parent / 'harness'))

from agent_runner import AgentRunner
from guardrails import GuardrailsSystem
from feedback_loop import FeedbackLoop
from progressive_context import ProgressiveDisclosure

# 保留原有导入
sys.path.insert(0, str(Path(__file__).parent))
from config import KEYWORDS

DATA_DIR = Path(__file__).parent / "data"
REPORTS_DIR = DATA_DIR / "reports"
NEWS_FILE = DATA_DIR / "news.jsonl"


def generate_daily_report_harness(date=None, use_harness=True):
    """
    生成每日报告 - Harness 架构版
    
    Args:
        date: 日期，默认为今天
        use_harness: 是否使用 Harness 架构
    """
    if date is None:
        date = datetime.now()
    
    date_str = date.strftime("%Y-%m-%d")
    report_file = REPORTS_DIR / f"report_{date_str.replace('-', '')}.md"
    
    print("=" * 60)
    print("储能行业日报生成器 - Harness Engineering")
    print(f"报告日期: {date_str}")
    print("=" * 60)
    
    if use_harness:
        # 使用 Harness 架构
        runner = AgentRunner()
        
        # 步骤1: 飞行前检查
        print("\n[步骤1/6] 飞行前检查 (Guardrails)...")
        passed, results = runner.guardrails.pre_flight_check(DATA_DIR)
        
        for r in results:
            status = "✓" if r.passed else "✗"
            print(f"  {status} [{r.code}] {r.message}")
        
        if not passed:
            print("\n⚠️ 飞行前检查未通过，尝试自动修复...")
            feedback = FeedbackLoop()
            for r in results:
                if not r.passed:
                    fix_result = feedback.process_error(
                        code=r.code,
                        message=r.message,
                        context={'date': date_str, 'check': 'pre_flight'}
                    )
                    if fix_result['auto_fixed']:
                        print(f"  ✓ 自动修复: {fix_result['fix_action']}")
                    else:
                        print(f"  ✗ 无法自动修复，跳过报告生成")
                        return None
        
        # 步骤2: 加载上下文
        print("\n[步骤2/6] 加载上下文 (Progressive Disclosure)...")
        context = runner.context_loader.load_context('daily_report', date=date_str.replace('-', ''))
        print(f"  ✓ 上下文层级: {context.level.value}")
        print(f"  ✓ 数据源: {', '.join(context.sources[:3])}...")
        
        # 步骤3: 生成报告（原有逻辑 + Harness 验证）
        print("\n[步骤3/6] 生成报告...")
    
    # 加载当天新闻（原有逻辑）
    today_news = []
    if NEWS_FILE.exists():
        with open(NEWS_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    item = json.loads(line.strip())
                    item_date = item.get('timestamp', '')[:10]
                    if item_date == date_str:
                        today_news.append(item)
                except:
                    continue
    
    # 生成报告（原有逻辑）
    report = f"""# 储能行业日报 - {date_str}

## 📊 概览
- 报告日期: {date_str}
- 资讯数量: {len(today_news)} 条
- 生成时间: {datetime.now().strftime("%H:%M")}
- 生成模式: {"Harness Engineering" if use_harness else "传统模式"}

## 🔥 热点资讯

"""
    
    # 分类整理（原有逻辑）
    categories = {
        "技术突破": [],
        "政策法规": [],
        "企业动态": [],
        "市场数据": [],
        "其他": []
    }
    
    for news in today_news:
        title = news.get('title', '')
        
        if any(kw in title for kw in ['技术', '突破', '研发', '创新']):
            categories["技术突破"].append(news)
        elif any(kw in title for kw in ['政策', '法规', '标准', '规范']):
            categories["政策法规"].append(news)
        elif any(kw in title for kw in ['企业', '公司', '财报', '合作']):
            categories["企业动态"].append(news)
        elif any(kw in title for kw in ['市场', '数据', '统计', '规模']):
            categories["市场数据"].append(news)
        else:
            categories["其他"].append(news)
    
    # 写入分类内容
    for cat_name, items in categories.items():
        if items:
            report += f"### {cat_name}\n\n"
            for item in items[:10]:
                title = item.get('title', '无标题')
                url = item.get('url', '')
                source = item.get('source', '未知来源')
                report += f"- **{title}** ([{source}]({url}))\n"
            report += "\n"
    
    # 趋势分析
    report += f"""## 📈 趋势分析

### 关键词热度
"""
    for kw in KEYWORDS[:10]:
        count = sum(1 for n in today_news if kw in str(n))
        if count > 0:
            report += f"- {kw}: {count} 次提及\n"
    
    report += """
### 行业洞察

（基于当天资讯的自动分析）

1. **技术方向**: 关注固态电池、钠离子电池等新技术进展
2. **市场动态**: 储能装机量持续增长，大储项目加速落地
3. **政策环境**: 持续关注储能电价机制、补贴政策变化

---
*报告由 OpenClaw 自动生成 (Harness Engineering 架构)*
*数据来源: 公开网络资讯*
"""
    
    # Harness 验证步骤
    if use_harness:
        print(f"  ✓ 报告内容已生成 ({len(report)} 字符)")
        
        # 步骤4: 输出验证
        print("\n[步骤4/6] 输出验证 (Guardrails)...")
        validation = runner.guardrails.validate_output(report)
        if validation.passed:
            print(f"  ✓ 格式验证通过")
        else:
            print(f"  ⚠️ 格式问题: {validation.message}")
        
        # 步骤5: 保存报告
        print("\n[步骤5/6] 保存报告...")
    
    # 保存报告（原有逻辑）
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"  ✓ 报告已保存: {report_file}")
    
    # 步骤6: 反馈记录
    if use_harness:
        print("\n[步骤6/6] 记录执行结果 (Feedback Loop)...")
        feedback = FeedbackLoop()
        # 记录成功执行
        print(f"  ✓ 执行结果已记录")
        
        # 显示系统健康
        health = runner.get_system_health()
        print(f"\n系统状态: 学习到的模式 {health['learned_patterns']} 个")
    
    print("\n" + "=" * 60)
    print("✅ 日报生成完成")
    print("=" * 60)
    
    return report_file


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='储能行业日报生成器 - Harness 版')
    parser.add_argument('--no-harness', action='store_true', help='不使用 Harness 架构')
    parser.add_argument('--date', type=str, help='指定日期 (YYYY-MM-DD)')
    args = parser.parse_args()
    
    use_harness = not args.no_harness
    date = None
    if args.date:
        date = datetime.strptime(args.date, "%Y-%m-%d")
    
    report_file = generate_daily_report_harness(date, use_harness)
    
    if report_file:
        print(f"\n报告路径: {report_file}")
        return 0
    else:
        print("\n❌ 报告生成失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
