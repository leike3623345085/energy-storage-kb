#!/usr/bin/env python3
"""
储能行业日报生成器 - Harness Engineering 版 v4.1 (优化版)
==========================================================
集成 GSD 方法论三大改进 v2：
1. XML 提示格式化 v2 (智能分析 + 模板继承)
2. 波式并行执行 v2 (可视化 + 智能重试)
3. 原子化 Git 提交 v2 (自动回滚 + 里程碑)

优化收益：
- 智能内容分析自动分类
- 实时进度可视化
- 自动回滚保障
- 里程碑自动标记
"""

import json
import os
import sys
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Any

sys.path.insert(0, str(Path(__file__).parent / 'harness'))
sys.path.insert(0, str(Path(__file__).parent))

# 导入 v2 版本
from xml_prompt_formatter_v2 import DailyReportXMLTemplate, TaskContext, NewsAnalyzer
from wave_based_executor_v2 import WaveBasedExecutorV2, Task as WaveTask, TaskStatus as WaveTaskStatus
from git_atomic_commit_v2 import GitAtomicCommitV2, TaskType, TaskStatus as GitTaskStatus, HarnessGitIntegrationV2

DATA_DIR = Path(__file__).parent / "data"
REPORTS_DIR = DATA_DIR / "reports"
NEWS_FILE = DATA_DIR / "news.jsonl"
CRAWLER_DIR = DATA_DIR / "crawler"


class ParallelDataLoaderV2:
    """并行数据加载器 v2"""
    
    def __init__(self, git: HarnessGitIntegrationV2 = None):
        self.git = git
        self.loaded_data: Dict[str, List[Dict]] = {}
        self.stats = {"total": 0, "by_source": {}, "analysis": None}
    
    def load_from_jsonl(self) -> List[Dict]:
        """从 news.jsonl 加载"""
        data = []
        date_str = datetime.now().strftime("%Y-%m-%d")
        
        if NEWS_FILE.exists():
            with open(NEWS_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        item = json.loads(line.strip())
                        item_date = item.get('timestamp', '')[:10]
                        if item_date == date_str:
                            data.append(item)
                    except:
                        continue
        
        self.loaded_data['jsonl'] = data
        return data
    
    def load_from_crawler(self) -> List[Dict]:
        """从爬虫目录加载"""
        data = []
        date_str = datetime.now().strftime("%Y-%m-%d")
        
        if CRAWLER_DIR.exists():
            crawler_files = sorted(CRAWLER_DIR.glob(f"crawler_{date_str.replace('-', '')}_*.json"), reverse=True)
            
            for crawler_file in crawler_files[:3]:
                try:
                    with open(crawler_file, 'r', encoding='utf-8') as f:
                        crawler_data = json.load(f)
                        crawler_news = crawler_data.get('data', [])
                        
                        for item in crawler_news:
                            data.append({
                                'title': item.get('title', ''),
                                'url': item.get('url', ''),
                                'source': item.get('source', '未知'),
                                'timestamp': item.get('pub_date') or item.get('fetched_at', date_str),
                                'summary': item.get('title', ''),
                                'data_source': 'crawler'
                            })
                except:
                    continue
        
        self.loaded_data['crawler'] = data
        return data
    
    def load_from_search(self) -> List[Dict]:
        """从搜索数据加载"""
        data = []
        date_str = datetime.now().strftime("%Y-%m-%d")
        search_dir = DATA_DIR / "news"
        
        if search_dir.exists():
            search_files = sorted(search_dir.glob(f"search_*_{date_str}.json"), reverse=True)
            
            for search_file in search_files[:2]:
                try:
                    with open(search_file, 'r', encoding='utf-8') as f:
                        search_data = json.load(f)
                        categories = search_data.get('categories', {})
                        
                        for cat_name, cat_data in categories.items():
                            highlights = cat_data.get('highlights', [])
                            for item in highlights:
                                data.append({
                                    'title': item.get('title', ''),
                                    'url': item.get('url', ''),
                                    'source': '搜索-' + cat_name,
                                    'timestamp': item.get('date', date_str),
                                    'summary': item.get('summary', ''),
                                    'data_source': 'search'
                                })
                except:
                    continue
        
        self.loaded_data['search'] = data
        return data
    
    def parallel_load(self, use_git: bool = True) -> List[Dict]:
        """
        波式并行加载所有数据源 (v2)
        """
        print("  🌊 Wave 1: 并行加载数据源...")
        
        # 创建 v2 执行器
        executor = WaveBasedExecutorV2(max_workers=3, enable_progress_bar=True)
        
        # 添加并行加载任务
        executor.add_task(WaveTask(
            id="load_jsonl", name="加载 news.jsonl",
            func=self.load_from_jsonl, wave=1, timeout=30, retry=2
        ))
        executor.add_task(WaveTask(
            id="load_crawler", name="加载爬虫数据",
            func=self.load_from_crawler, wave=1, timeout=30, retry=2
        ))
        executor.add_task(WaveTask(
            id="load_search", name="加载搜索数据",
            func=self.load_from_search, wave=1, timeout=30, retry=2
        ))
        
        # 执行
        result = executor.execute()
        
        # 合并所有数据
        all_data = []
        seen_urls = set()
        
        for source_name, data in self.loaded_data.items():
            for item in data:
                url = item.get('url', '')
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    all_data.append(item)
            
            self.stats["by_source"][source_name] = len(data)
            print(f"    ✓ {source_name}: {len(data)} 条")
        
        self.stats["total"] = len(all_data)
        print(f"    ✓ 去重后: {len(all_data)} 条")
        
        # 智能分析
        if all_data:
            _, analysis_stats = NewsAnalyzer.analyze_batch(all_data)
            self.stats["analysis"] = analysis_stats
            print(f"    📊 智能分析: {analysis_stats['hot_news']} 热点 / {analysis_stats['avg_importance']:.1f} 平均重要性")
        
        # Git 提交
        if use_git and self.git:
            output_file = CRAWLER_DIR / f"merged_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump({"data": all_data, "stats": self.stats}, f, ensure_ascii=False, indent=2)
            
            self.git.git.commit_task_result(
                task_type=TaskType.CRAWL,
                task_name="数据加载与合并 v2",
                status=GitTaskStatus.SUCCESS,
                summary=f"并行加载 {len(self.stats['by_source'])} 个数据源，合并后 {len(all_data)} 条",
                details=[
                    f"数据源: {', '.join(self.stats['by_source'].keys())}",
                    f"原始总量: {sum(self.stats['by_source'].values())} 条",
                    f"去重后: {len(all_data)} 条",
                    f"并行效率: {result.get('parallel_efficiency', 0):.1f}%"
                ],
                files=[str(output_file)],
                metadata={
                    "sources": list(self.stats['by_source'].keys()),
                    "total_unique": len(all_data),
                    "parallel_efficiency": result.get('parallel_efficiency', 0)
                },
                change_set=self.git.current_change_set
            )
        
        # 保存执行日志
        executor.save_execution_log()
        
        return all_data


class XMLReportGeneratorV2:
    """基于 XML 提示的报告生成器 v2"""
    
    def __init__(self, git: HarnessGitIntegrationV2 = None):
        self.git = git
    
    def generate_report(self, news_list: List[Dict], date_str: str) -> str:
        """生成报告 - 基于 XML 提示 v2"""
        
        # 智能分析
        analyses, stats = NewsAnalyzer.analyze_batch(news_list)
        
        # 统计数据
        sources = list(set(item.get("source", "未知") for item in news_list))
        
        data_stats = {
            "quality_score": min(95, 70 + len(news_list) // 2),
            "total_sources": len(sources),
            "categories": stats["by_category"],
            "hot_news": stats["hot_news"],
            "avg_importance": stats["avg_importance"]
        }
        
        # 创建 XML 提示 v2
        builder = DailyReportXMLTemplate.create(
            source_data=news_list,
            date=date_str,
            data_stats=data_stats
        )
        
        # 验证
        is_valid, error = builder.validate()
        if not is_valid:
            print(f"  ⚠️ XML 验证失败: {error}")
        
        prompt = builder.to_prompt()
        
        # 保存 XML 提示
        xml_file = REPORTS_DIR / f"xml_prompt_v2_{date_str.replace('-', '')}.xml"
        xml_file.parent.mkdir(parents=True, exist_ok=True)
        builder.save(xml_file)
        
        # 生成报告内容（简化版，实际会发送给 LLM）
        categories = stats["by_category"]
        
        report = f"""# 储能行业日报 - {date_str}

## 📊 概览
- **报告日期**: {date_str}
- **资讯数量**: {len(news_list)} 条
- **生成时间**: {datetime.now().strftime("%H:%M")}
- **生成模式**: Harness v4.1 + GSD v2
- **置信度评分**: {data_stats['quality_score']}/100
- **热点数量**: {stats['hot_news']} 条

## 📊 分类统计

| 分类 | 数量 | 占比 |
|------|------|------|
"""
        
        for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
            pct = count / len(news_list) * 100 if news_list else 0
            report += f"| {cat} | {count} | {pct:.1f}% |\n"
        
        report += f"""
## 📊 市场动态

{categories.get('市场动态', 0)} 条市场相关资讯

## ⚡ 技术进展

{categories.get('技术创新', 0)} 条技术相关资讯

## 📜 政策动态

{categories.get('政策法规', 0)} 条政策相关资讯

## 🔥 今日热点 ({stats['hot_news']} 条)

"""
        
        # 添加热点（重要性 > 70）
        hot_news = [item for item in news_list 
                   if analyses.get(item.get('url', item.get('title', ''))[:50], type('obj', (object,), {'is_hot': False})()).is_hot]
        
        for i, news in enumerate(hot_news[:5], 1):
            title = news.get('title', '无标题')
            source = news.get('source', '未知')
            report += f"{i}. **{title}** ({source})\n"
        
        report += """
## 📋 详细资讯

"""
        
        for i, news in enumerate(news_list[:20], 1):
            title = news.get('title', '无标题')
            source = news.get('source', '未知')
            url = news.get('url', '')
            
            if url:
                report += f"{i}. **{title}** [{source}]({url})\n"
            else:
                report += f"{i}. **{title}** ({source})\n"
        
        report += """
---
*报告由 OpenClaw 自动生成 (Harness v4.1 + GSD v2)*
*数据来源: 公开网络资讯*
"""
        
        # Git 提交
        if self.git:
            report_file = REPORTS_DIR / f"report_{date_str.replace('-', '')}.md"
            report_file.parent.mkdir(parents=True, exist_ok=True)
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(report)
            
            self.git.git.commit_task_result(
                task_type=TaskType.GENERATE,
                task_name="储能日报生成 v2",
                status=GitTaskStatus.SUCCESS,
                summary=f"生成 {date_str} 日报，包含 {len(news_list)} 条资讯",
                details=[
                    f"资讯数量: {len(news_list)} 条",
                    f"热点数量: {stats['hot_news']} 条",
                    f"置信度: {data_stats['quality_score']}/100",
                    f"分类分布: {categories}"
                ],
                files=[str(report_file), str(xml_file)],
                metadata={
                    "date": date_str,
                    "news_count": len(news_list),
                    "hot_news": stats['hot_news'],
                    "categories": categories
                },
                change_set=self.git.current_change_set
            )
        
        return report


class ReportPipelineV41:
    """v4.1 报告生成流水线 - 集成 GSD 三大改进 v2"""
    
    def __init__(self):
        self.git = HarnessGitIntegrationV2()
        self.data_loader = ParallelDataLoaderV2(self.git)
        self.report_generator = XMLReportGeneratorV2(self.git)
    
    def run(self, date: Optional[datetime] = None) -> Tuple[str, Dict[str, Any]]:
        """执行完整流水线 v4.1"""
        if date is None:
            date = datetime.now()
        
        date_str = date.strftime("%Y-%m-%d")
        
        print("=" * 70)
        print("储能行业日报生成器 - Harness Engineering v4.1 (GSD v2 集成)")
        print(f"报告日期: {date_str}")
        print("=" * 70)
        
        # 开始变更集
        cs = self.git.start_pipeline(f"日报生成_{date_str}")
        
        start_time = datetime.now()
        
        # Wave 1: 并行加载数据
        print("\n[Wave 1] 并行数据加载 (v2)...")
        news_list = self.data_loader.parallel_load(use_git=True)
        
        # Wave 2: 数据清洗
        print("\n[Wave 2] 数据清洗...")
        cleaned_list = self._clean_data(news_list)
        print(f"  ✓ 清洗后: {len(cleaned_list)} 条")
        
        # Wave 3: 生成报告
        print("\n[Wave 3] 生成报告 (XML v2)...")
        report = self.report_generator.generate_report(cleaned_list, date_str)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # 保存报告
        report_file = REPORTS_DIR / f"report_{date_str.replace('-', '')}.md"
        report_file.parent.mkdir(parents=True, exist_ok=True)
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        # 结束流水线（自动打里程碑标签）
        self.git.end_pipeline(auto_tag=True)
        
        # 保存执行报告
        report_path = self.git.git.save_report()
        
        print("\n" + "=" * 70)
        print("✅ 日报生成完成 (Harness v4.1)")
        print(f"📊 数据量: {len(cleaned_list)} 条")
        print(f"⏱️  总耗时: {duration:.1f}s")
        print(f"📁 报告路径: {report_file}")
        print(f"💾 执行报告: {report_path}")
        print("=" * 70)
        
        stats = {
            "duration": duration,
            "news_count": len(cleaned_list),
            "sources": self.data_loader.stats["by_source"],
            "analysis": self.data_loader.stats.get("analysis"),
            "report_file": str(report_file)
        }
        
        return report, stats
    
    def _clean_data(self, news_list: List[Dict]) -> List[Dict]:
        """清洗数据"""
        seen_urls = set()
        unique = []
        
        for item in news_list:
            url = item.get('url', '')
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique.append(item)
            elif not url:
                title = item.get('title', '')
                if title and title not in seen_urls:
                    seen_urls.add(title)
                    unique.append(item)
        
        return unique


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='储能行业日报生成器 - Harness v4.1 (GSD v2)')
    parser.add_argument('--date', type=str, help='指定日期 (YYYY-MM-DD)')
    parser.add_argument('--no-git', action='store_true', help='禁用 Git 提交')
    args = parser.parse_args()
    
    date = None
    if args.date:
        date = datetime.strptime(args.date, "%%Y-%m-%d")
    
    pipeline = ReportPipelineV41()
    report, stats = pipeline.run(date)
    
    print(f"\n📊 执行统计:")
    print(f"  数据量: {stats['news_count']} 条")
    print(f"  数据源: {stats['sources']}")
    if stats.get('analysis'):
        print(f"  热点数: {stats['analysis']['hot_news']}")
        print(f"  平均重要性: {stats['analysis']['avg_importance']:.1f}")
    print(f"  耗时: {stats['duration']:.1f}s")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
