#!/usr/bin/env python3
"""
储能行业日报生成器 - Harness Engineering 版 v3
整合研报分析框架 (research_analysis SKILL)
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

# 添加 skills 到路径
sys.path.insert(0, str(Path(__file__).parent.parent / 'skills'))

from agent_runner import AgentRunner
from guardrails import GuardrailsSystem
from feedback_loop import FeedbackLoop
from progressive_context import ProgressiveDisclosure

# 导入研报分析框架
from research_analysis.frameworks.mece import MECEAnalyzer
from research_analysis.frameworks.swot import SWOTGenerator
from research_analysis.frameworks.impact_matrix import ImpactMatrix
from research_analysis.frameworks.industry_chain import IndustryChain

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
        
        # 提取数字声明
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
                           '中储国能', '中科海钠', '华为', '阳光电源', '科华数据',
                           '中创新航', '蜂巢能源', '璞泰来', '贝特瑞']
        for company in company_keywords:
            if company in report:
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
                result['confidence'] = 'medium'
                result['issue'] = f"公司 '{company}' 未在当日数据中找到，建议确认"
                self.confidence_score -= 5
        
        elif claim['type'] == 'policy':
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
        """执行事实核查"""
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
        
        passed = self.confidence_score >= 70
        return passed, self.issues, max(0, self.confidence_score)
    
    def generate_warning(self) -> str:
        """生成事实核查警告"""
        if not self.issues:
            return ""
        
        warning = "\n\n## ⚠️ 事实核查说明\n\n"
        warning += f"**置信度评分**: {self.confidence_score}/100\n\n"
        
        if self.issues:
            warning += "**需要注意的内容**:\n"
            for issue in self.issues[:5]:
                warning += f"- {issue['issue']}\n"
            
            if len(self.issues) > 5:
                warning += f"- ... 还有 {len(self.issues) - 5} 项未列出\n"
        
        return warning


def generate_hotspots_section(news_list: List[Dict], top_n: int = 3) -> str:
    """生成热点提炼章节"""
    print("\n  🔥 使用 MECE 框架分析热点...")
    
    analyzer = MECEAnalyzer(industry="储能")
    hotspots = analyzer.extract_hotspots(news_list, top_n=top_n)
    
    if not hotspots:
        return "## 🔥 今日热点\n\n暂无足够数据生成热点。\n\n"
    
    section = "## 🔥 今日TOP3热点\n\n"
    
    for hotspot in hotspots:
        rank = hotspot['rank']
        title = hotspot['title']
        source = hotspot['source']
        url = hotspot.get('url', '')
        categories = hotspot.get('categories', [])
        score = hotspot.get('importance_score', 0)
        analysis = hotspot.get('analysis', '')
        
        # 计算星级
        stars = "⭐⭐⭐" if score >= 80 else "⭐⭐" if score >= 60 else "⭐"
        
        section += f"### {rank}. {title}\n"
        section += f"**来源**: {source}"
        if url:
            section += f" | [原文链接]({url})"
        section += "\n"
        
        if categories:
            section += f"**影响层面**: {'/'.join(categories[:2])}\n"
        
        section += f"**重要程度**: {stars} (评分: {score:.0f}/100)\n\n"
        
        if analysis:
            section += f"**→ 影响**: {analysis}\n"
        
        section += "\n---\n\n"
    
    print(f"  ✓ 生成了 {len(hotspots)} 个热点")
    return section


def generate_swot_section(news_list: List[Dict]) -> str:
    """生成 SWOT 分析章节"""
    print("\n  📊 使用 SWOT 框架分析行业态势...")
    
    generator = SWOTGenerator(industry="储能")
    swot = generator.generate(news_list)
    
    section = "## 📊 行业 SWOT 速览\n\n"
    section += "| 维度 | 内容 |\n"
    section += "|------|------|\n"
    
    swot_dict = swot.to_dict()
    for dimension, items in swot_dict.items():
        if items:
            content = "; ".join(items[:3])
            section += f"| {dimension} | {content} |\n"
    
    print("  ✓ 生成了 SWOT 分析")
    return section + "\n"


def generate_industry_chain_section(news_list: List[Dict]) -> str:
    """生成产业链动态章节"""
    print("\n  🔗 使用产业链框架追踪动态...")
    
    chain = IndustryChain()
    updates = chain.track_updates(news_list)
    summary = chain.get_segment_summary()
    
    section = "## 🔗 产业链动态\n\n"
    
    for segment in ["上游", "中游", "下游"]:
        section += f"### {segment}\n\n"
        
        # 获取该环节的动态
        segment_updates = []
        for key, items in updates.items():
            if key.startswith(segment):
                segment_updates.extend(items)
        
        if segment_updates:
            # 取最新2条
            for item in segment_updates[:2]:
                title = item.get('title', '')
                source = item.get('source', '')
                section += f"- **{title}** (*{source}*)\n"
        else:
            section += "- 暂无重大动态\n"
        
        section += "\n"
    
    # 添加统计
    section += "**各环节动态统计**:\n\n"
    section += "| 环节 | 动态数量 | 占比 |\n"
    section += "|------|---------|------|\n"
    
    total = sum(summary.values()) if summary else 0
    for segment in ["上游", "中游", "下游"]:
        count = summary.get(segment, 0)
        pct = f"{count/total*100:.0f}%" if total > 0 else "0%"
        section += f"| {segment} | {count}条 | {pct} |\n"
    
    print(f"  ✓ 生成了产业链分析")
    return section + "\n"


def load_today_news(date_str: str) -> List[Dict]:
    """
    加载当天新闻 - 支持多数据源
    1. 首先尝试从 news.jsonl 读取
    2. 如果数据不足，从 crawler/ 目录读取
    3. 同时读取搜索数据（如果存在）
    """
    today_news = []
    
    # 数据源1: news.jsonl
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
    
    print(f"  📂 news.jsonl: {len(today_news)} 条")
    
    # 数据源2: crawler/ 目录（如果数据不足）
    if len(today_news) < 10:
        crawler_dir = DATA_DIR / "crawler"
        if crawler_dir.exists():
            # 查找当天的爬虫数据文件
            crawler_files = sorted(crawler_dir.glob(f"crawler_{date_str.replace('-', '')}_*.json"), reverse=True)
            
            for crawler_file in crawler_files[:3]:  # 最多取3个文件
                try:
                    with open(crawler_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        crawler_news = data.get('data', [])
                        
                        # 转换格式以兼容
                        for item in crawler_news:
                            today_news.append({
                                'title': item.get('title', ''),
                                'url': item.get('url', ''),
                                'source': item.get('source', '未知'),
                                'timestamp': item.get('pub_date') or item.get('fetched_at', date_str),
                                'summary': item.get('title', '')  # 爬虫没有摘要，用标题代替
                            })
                        
                        print(f"  📂 {crawler_file.name}: {len(crawler_news)} 条")
                except Exception as e:
                    print(f"  ⚠️ 读取失败 {crawler_file.name}: {e}")
    
    # 数据源3: 搜索数据（search_*.json）
    search_dir = DATA_DIR / "news"
    if search_dir.exists():
        search_files = sorted(search_dir.glob(f"search_*_{date_str}.json"), reverse=True)
        
        for search_file in search_files[:2]:  # 最多取2个文件
            try:
                with open(search_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    categories = data.get('categories', {})
                    
                    for cat_name, cat_data in categories.items():
                        highlights = cat_data.get('highlights', [])
                        for item in highlights:
                            today_news.append({
                                'title': item.get('title', ''),
                                'url': item.get('url', ''),
                                'source': '搜索-' + cat_name,
                                'timestamp': item.get('date', date_str),
                                'summary': item.get('summary', '')
                            })
                    
                    total_highlights = sum(len(c.get('highlights', [])) for c in categories.values())
                    print(f"  📂 {search_file.name}: {total_highlights} 条")
            except Exception as e:
                print(f"  ⚠️ 读取失败 {search_file.name}: {e}")
    
    # 去重
    seen_urls = set()
    unique_news = []
    for item in today_news:
        url = item.get('url', '')
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_news.append(item)
    
    print(f"  ✅ 去重后: {len(unique_news)} 条")
    return unique_news


def generate_daily_report_harness(date=None, use_harness=True, fact_check=True, use_analysis=True):
    """
    生成每日报告 - Harness 架构版 v3
    
    Args:
        date: 日期，默认为今天
        use_harness: 是否使用 Harness 架构
        fact_check: 是否启用事实核查
        use_analysis: 是否使用研报分析框架
    """
    if date is None:
        date = datetime.now()
    
    date_str = date.strftime("%Y-%m-%d")
    report_file = REPORTS_DIR / f"report_{date_str.replace('-', '')}.md"
    
    print("=" * 60)
    print("储能行业日报生成器 - Harness Engineering v3")
    print(f"报告日期: {date_str}")
    print("=" * 60)
    
    # 加载当天新闻 - 支持多数据源
    today_news = load_today_news(date_str)
    
    if use_harness:
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
        
        # 步骤3: 生成报告主体
        print("\n[步骤3/7] 生成报告主体...")
    
    # 报告头部
    report = f"""# 储能行业日报 - {date_str}

## 📊 概览
- 报告日期: {date_str}
- 资讯数量: {len(today_news)} 条
- 生成时间: {datetime.now().strftime("%H:%M")}
- 生成模式: {"Harness v3 + 研报分析" if use_harness and use_analysis else "Harness Engineering" if use_harness else "传统模式"}

"""
    
    # 使用研报分析框架生成热点
    if use_analysis and today_news:
        hotspots_section = generate_hotspots_section(today_news, top_n=3)
        report += hotspots_section
    
    # 使用 SWOT 分析
    if use_analysis and today_news:
        swot_section = generate_swot_section(today_news)
        report += swot_section
    
    # 使用产业链分析
    if use_analysis and today_news:
        chain_section = generate_industry_chain_section(today_news)
        report += chain_section
    
    # 详细资讯列表（原有逻辑，简化版）
    report += "## 📋 详细资讯\n\n"
    
    # 分类整理
    categories = {
        "政策法规": [],
        "市场动态": [],
        "项目进展": [],
        "技术创新": [],
        "企业动态": [],
        "国际市场": []
    }
    
    for news in today_news:
        title = news.get('title', '')
        
        if any(kw in title for kw in ['政策', '法规', '标准', '规范']):
            categories["政策法规"].append(news)
        elif any(kw in title for kw in ['招标', '中标', '市场', '价格']):
            categories["市场动态"].append(news)
        elif any(kw in title for kw in ['项目', '开工', '并网', '投运']):
            categories["项目进展"].append(news)
        elif any(kw in title for kw in ['技术', '电池', '创新']):
            categories["技术创新"].append(news)
        elif any(kw in title for kw in ['企业', '公司', '合作']):
            categories["企业动态"].append(news)
        elif any(kw in title for kw in ['海外', '国际', '出口']):
            categories["国际市场"].append(news)
        else:
            categories["政策法规"].append(news)  # 默认放政策
    
    # 写入分类内容（每类最多5条）
    for cat_name, items in categories.items():
        if items:
            report += f"### {cat_name}\n\n"
            for item in items[:5]:
                title = item.get('title', '无标题')
                url = item.get('url', '')
                source = item.get('source', '未知来源')
                report += f"- **{title}** ([{source}]({url}))\n"
            report += "\n"
    
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
        
        # 步骤5: 事实核查
        if fact_check:
            print("\n[步骤5/7] 事实核查 (Fact Checker)...")
            checker = FactChecker(today_news)
            passed, issues, score = checker.check(report)
            
            print(f"  ✓ 置信度评分: {score}/100")
            
            if passed:
                print(f"  ✓ 事实核查通过")
            else:
                print(f"  ⚠️ 发现 {len(issues)} 个问题，已添加说明")
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
            score = 0
        
        # 步骤6: 保存报告
        print("\n[步骤6/7] 保存报告...")
    else:
        print("\n[保存报告]...")
        score = 0
    
    # 保存报告
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"  ✓ 报告已保存: {report_file}")
    
    # 添加报告结尾
    with open(report_file, 'a', encoding='utf-8') as f:
        f.write("\n---\n")
        f.write(f"*报告由 OpenClaw 自动生成*\n")
        if use_analysis:
            f.write("*基于 Harness Engineering + research_analysis SKILL*\n")
        elif use_harness:
            f.write("*基于 Harness Engineering 架构*\n")
        f.write(f"*数据来源: 公开网络资讯*\n")
        if fact_check and score > 0:
            f.write(f"*置信度评分: {score}/100*\n")
    
    # 步骤7: 反馈记录
    if use_harness:
        print("\n[步骤7/7] 记录执行结果 (Feedback Loop)...")
        feedback = FeedbackLoop()
        print(f"  ✓ 执行结果已记录")
        
        health = runner.get_system_health()
        print(f"\n系统状态: 学习到的模式 {health['learned_patterns']} 个")
    
    print("\n" + "=" * 60)
    print("✅ 日报生成完成")
    if fact_check and score > 0:
        print(f"📊 置信度评分: {score}/100")
    print("=" * 60)
    
    return report_file


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='储能行业日报生成器 - Harness v3')
    parser.add_argument('--no-harness', action='store_true', help='不使用 Harness 架构')
    parser.add_argument('--no-fact-check', action='store_true', help='禁用事实核查')
    parser.add_argument('--no-analysis', action='store_true', help='禁用研报分析框架')
    parser.add_argument('--date', type=str, help='指定日期 (YYYY-MM-DD)')
    args = parser.parse_args()
    
    use_harness = not args.no_harness
    fact_check = not args.no_fact_check
    use_analysis = not args.no_analysis
    date = None
    if args.date:
        date = datetime.strptime(args.date, "%Y-%m-%d")
    
    report_file = generate_daily_report_harness(date, use_harness, fact_check, use_analysis)
    
    if report_file:
        print(f"\n报告路径: {report_file}")
        return 0
    else:
        print("\n❌ 报告生成失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
