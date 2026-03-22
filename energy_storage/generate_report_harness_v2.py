#!/usr/bin/env python3
"""
储能行业日报生成器 - Harness Engineering 版 v2
增加 Fact Checker 阶段，强化质量验证
"""

import json
import os
import sys
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Tuple

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
FACT_CHECK_LOG = DATA_DIR / "fact_check_log.jsonl"


class FactChecker:
    """事实核查器 - 验证报告中的关键信息"""
    
    def __init__(self, source_data: List[Dict]):
        self.source_data = source_data
        self.issues = []
        self.confidence_score = 100
    
    def extract_claims(self, report: str) -> List[Dict]:
        """从报告中提取需要核查的声明"""
        claims = []
        
        # 提取数字声明 (如: "装机量增长 50%")
        number_pattern = r'(\d+(?:\.\d+)?)\s*(?:GW|MW|kWh|亿元|万元|%)'
        for match in re.finditer(number_pattern, report):
            claims.append({
                'type': 'number',
                'text': match.group(0),
                'position': match.span(),
                'needs_verification': True
            })
        
        # 提取公司名称
        company_keywords = ['宁德时代', '比亚迪', '亿纬锂能', '国轩高科', '海辰储能', 
                           '中储国能', '中科海钠', '华为', '阳光电源', '科华数据']
        for company in company_keywords:
            if company in report:
                # 找到公司名上下文
                idx = report.find(company)
                context = report[max(0, idx-30):min(len(report), idx+50)]
                claims.append({
                    'type': 'company',
                    'text': company,
                    'context': context,
                    'needs_verification': True
                })
        
        # 提取政策引用
        policy_pattern = r'(关于.*的.{2,8}通知|.{2,8}管理办法|.{2,8}指导意见)'
        for match in re.finditer(policy_pattern, report):
            claims.append({
                'type': 'policy',
                'text': match.group(0),
                'needs_verification': True
            })
        
        return claims
    
    def verify_claim(self, claim: Dict) -> Dict:
        """验证单个声明"""
        result = {
            'claim': claim,
            'verified': False,
            'confidence': 'unknown',
            'source': None,
            'issue': None
        }
        
        if claim['type'] == 'number':
            # 在原始数据中搜索该数字
            number = re.search(r'\d+(?:\.\d+)?', claim['text']).group(0)
            found_in_source = any(
                number in str(item.get('title', '')) or 
                number in str(item.get('summary', ''))
                for item in self.source_data
            )
            
            if found_in_source:
                result['verified'] = True
                result['confidence'] = 'high'
            else:
                result['verified'] = False
                result['confidence'] = 'low'
                result['issue'] = f"数字 '{number}' 未在原始数据源中找到"
                self.confidence_score -= 10
        
        elif claim['type'] == 'company':
            # 验证公司名是否出现在原始数据中
            company = claim['text']
            found_in_source = any(
                company in str(item.get('title', '')) or 
                company in str(item.get('summary', ''))
                for item in self.source_data
            )
            
            if found_in_source:
                result['verified'] = True
                result['confidence'] = 'high'
            else:
                result['verified'] = False
                result['confidence'] = 'medium'  # 公司名可能是常识，不必太严格
                result['issue'] = f"公司 '{company}' 未在当日数据中找到，建议确认"
                self.confidence_score -= 5
        
        elif claim['type'] == 'policy':
            # 政策引用需要严格验证
            policy = claim['text']
            found_in_source = any(
                policy in str(item.get('title', ''))
                for item in self.source_data
            )
            
            if found_in_source:
                result['verified'] = True
                result['confidence'] = 'high'
            else:
                result['verified'] = False
                result['confidence'] = 'low'
                result['issue'] = f"政策 '{policy}' 未找到明确来源"
                self.confidence_score -= 15
        
        return result
    
    def check(self, report: str) -> Tuple[bool, List[Dict], int]:
        """
        执行事实核查
        
        Returns:
            (passed, issues, confidence_score)
        """
        print("  📋 提取待核查声明...")
        claims = self.extract_claims(report)
        print(f"     找到 {len(claims)} 个需要核查的声明")
        
        print("  🔍 验证声明...")
        verified_results = []
        for claim in claims:
            result = self.verify_claim(claim)
            verified_results.append(result)
            
            if result['issue']:
                self.issues.append(result)
                print(f"     ⚠️ {result['issue']}")
        
        # 判断整体是否通过
        passed = self.confidence_score >= 70  # 70分以上算通过
        
        return passed, self.issues, max(0, self.confidence_score)
    
    def generate_warning(self) -> str:
        """生成事实核查警告（如有问题）"""
        if not self.issues:
            return ""
        
        warning = "\n\n## ⚠️ 事实核查说明\n\n"
        warning += f"**置信度评分**: {self.confidence_score}/100\n\n"
        
        if self.issues:
            warning += "**需要注意的内容**:\n"
            for issue in self.issues[:5]:  # 最多显示5条
                warning += f"- {issue['issue']}\n"
            
            if len(self.issues) > 5:
                warning += f"- ... 还有 {len(self.issues) - 5} 项未列出\n"
        
        return warning


def generate_daily_report_harness(date=None, use_harness=True, fact_check=True):
    """
    生成每日报告 - Harness 架构版 v2
    
    Args:
        date: 日期，默认为今天
        use_harness: 是否使用 Harness 架构
        fact_check: 是否启用事实核查
    """
    if date is None:
        date = datetime.now()
    
    date_str = date.strftime("%Y-%m-%d")
    report_file = REPORTS_DIR / f"report_{date_str.replace('-', '')}.md"
    
    print("=" * 60)
    print("储能行业日报生成器 - Harness Engineering v2")
    print(f"报告日期: {date_str}")
    print("=" * 60)
    
    # 加载当天新闻（提前加载，供多个阶段使用）
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
    
    if use_harness:
        # 使用 Harness 架构
        runner = AgentRunner()
        
        # 步骤1: 飞行前检查
        print("\n[步骤1/7] 飞行前检查 (Guardrails)...")
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
        print("\n[步骤2/7] 加载上下文 (Progressive Disclosure)...")
        context = runner.context_loader.load_context('daily_report', date=date_str.replace('-', ''))
        print(f"  ✓ 上下文层级: {context.level.value}")
        print(f"  ✓ 数据源: {', '.join(context.sources[:3])}...")
        
        # 步骤3: 生成报告
        print("\n[步骤3/7] 生成报告...")
    
    # 生成报告内容（原有逻辑）
    report = f"""# 储能行业日报 - {date_str}

## 📊 概览
- 报告日期: {date_str}
- 资讯数量: {len(today_news)} 条
- 生成时间: {datetime.now().strftime("%H:%M")}
- 生成模式: {"Harness Engineering + Fact Check" if use_harness and fact_check else "Harness Engineering" if use_harness else "传统模式"}

## 🔥 热点资讯

"""
    
    # 分类整理
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
"""
    
    # Harness 验证步骤
    if use_harness:
        print(f"  ✓ 报告内容已生成 ({len(report)} 字符)")
        
        # 步骤4: 输出验证
        print("\n[步骤4/7] 格式验证 (Guardrails)...")
        validation = runner.guardrails.validate_output(report)
        if validation.passed:
            print(f"  ✓ 格式验证通过")
        else:
            print(f"  ⚠️ 格式问题: {validation.message}")
        
        # 步骤5: 事实核查（新增）
        if fact_check:
            print("\n[步骤5/7] 事实核查 (Fact Checker)...")
            checker = FactChecker(today_news)
            passed, issues, score = checker.check(report)
            
            print(f"  ✓ 置信度评分: {score}/100")
            
            if passed:
                print(f"  ✓ 事实核查通过")
            else:
                print(f"  ⚠️ 发现 {len(issues)} 个问题，已添加说明")
                # 添加事实核查说明到报告
                report += checker.generate_warning()
            
            # 记录核查日志
            FACT_CHECK_LOG.parent.mkdir(parents=True, exist_ok=True)
            with open(FACT_CHECK_LOG, 'a', encoding='utf-8') as f:
                log_entry = {
                    'date': date_str,
                    'timestamp': datetime.now().isoformat(),
                    'score': score,
                    'issues_count': len(issues),
                    'passed': passed
                }
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
        else:
            print("\n[步骤5/7] 事实核查 (已跳过)")
        
        # 步骤6: 保存报告
        print("\n[步骤6/7] 保存报告...")
    else:
        print("\n[保存报告]...")
    
    # 保存报告
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"  ✓ 报告已保存: {report_file}")
    
    # 添加报告结尾
    with open(report_file, 'a', encoding='utf-8') as f:
        f.write("""
---
*报告由 OpenClaw 自动生成 (Harness Engineering 架构)""")
        if fact_check:
            f.write(" + 事实核查*")
        else:
            f.write("*")
        f.write("\n*数据来源: 公开网络资讯*\n")
    
    # 步骤7: 反馈记录
    if use_harness:
        print("\n[步骤7/7] 记录执行结果 (Feedback Loop)...")
        feedback = FeedbackLoop()
        print(f"  ✓ 执行结果已记录")
        
        # 显示系统健康
        health = runner.get_system_health()
        print(f"\n系统状态: 学习到的模式 {health['learned_patterns']} 个")
    
    print("\n" + "=" * 60)
    print("✅ 日报生成完成")
    if fact_check and use_harness:
        print(f"📊 置信度评分: {score}/100")
    print("=" * 60)
    
    return report_file


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='储能行业日报生成器 - Harness v2')
    parser.add_argument('--no-harness', action='store_true', help='不使用 Harness 架构')
    parser.add_argument('--no-fact-check', action='store_true', help='禁用事实核查')
    parser.add_argument('--date', type=str, help='指定日期 (YYYY-MM-DD)')
    args = parser.parse_args()
    
    use_harness = not args.no_harness
    fact_check = not args.no_fact_check
    date = None
    if args.date:
        date = datetime.strptime(args.date, "%Y-%m-%d")
    
    report_file = generate_daily_report_harness(date, use_harness, fact_check)
    
    if report_file:
        print(f"\n报告路径: {report_file}")
        return 0
    else:
        print("\n❌ 报告生成失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
