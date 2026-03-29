#!/usr/bin/env python3
"""
GSD 方法论三大改进集成演示
=============================
演示 XML 提示格式化 + 波式并行 + 原子化 Git 提交的集成使用
"""

import sys
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from xml_prompt_formatter import DailyReportXMLTemplate, WaveBasedParallelTemplate
from wave_based_executor import WaveBasedExecutor, Task, TaskStatus as WaveTaskStatus
from git_atomic_commit import GitAtomicCommit, TaskType, TaskStatus as GitTaskStatus


def demo_xml_prompt():
    """演示 XML 提示格式化"""
    print("=" * 70)
    print("📝 演示 1: XML 提示格式化 (XML Prompt Formatter)")
    print("=" * 70)
    
    # 模拟数据源
    source_data = [
        {"title": "宁德时代发布新一代储能电池，能量密度提升20%", "source": "北极星储能网"},
        {"title": "菲律宾风光强制配建储能政策出台，装机不低于20%", "source": "储能中国网"},
        {"title": "贵州省首个构网型储能示范项目200MWh成功并网", "source": "高工储能"},
        {"title": "南网数字光伏及储能电站并网监测技术服务中标", "source": "OFweek储能"},
    ]
    
    # 创建 XML 提示
    date = datetime.now().strftime("%Y-%m-%d")
    builder = DailyReportXMLTemplate.create(
        source_data=source_data,
        date=date,
        data_stats={"quality_score": 95, "total_sources": 4}
    )
    
    prompt = builder.to_prompt()
    print("\n生成的 XML 提示（节选）:")
    print("-" * 70)
    # 只显示前 30 行
    lines = prompt.split('\n')[:30]
    print('\n'.join(lines))
    print("...")
    print("-" * 70)
    print(f"✅ XML 提示生成完成，共 {len(prompt)} 字符\n")
    
    return prompt


def demo_wave_execution():
    """演示波式并行执行"""
    print("=" * 70)
    print("🌊 演示 2: 波式并行执行 (Wave-Based Parallelism)")
    print("=" * 70)
    
    # 定义模拟任务
    results = {}
    
    def crawl_source_a():
        time.sleep(0.5)
        results['source_a'] = ["新闻A1", "新闻A2", "新闻A3"]
        return results['source_a']
    
    def crawl_source_b():
        time.sleep(0.5)
        results['source_b'] = ["新闻B1", "新闻B2"]
        return results['source_b']
    
    def crawl_source_c():
        time.sleep(0.5)
        results['source_c'] = ["新闻C1", "新闻C2", "新闻C3", "新闻C4"]
        return results['source_c']
    
    def clean_data():
        all_data = results.get('source_a', []) + results.get('source_b', []) + results.get('source_c', [])
        return list(set(all_data))  # 去重
    
    def generate_report():
        data = results.get('cleaned', [])
        return f"报告: 共 {len(data)} 条数据"
    
    # 创建执行器
    executor = WaveBasedExecutor(max_workers=3)
    
    # Wave 1: 并行爬取
    print("\n构建执行计划:")
    print("  Wave 1: [爬虫A, 爬虫B, 爬虫C]  ← 并行执行")
    executor.add_task(Task(id="crawl_a", name="北极星爬虫", func=crawl_source_a, wave=1))
    executor.add_task(Task(id="crawl_b", name="储能中国爬虫", func=crawl_source_b, wave=1))
    executor.add_task(Task(id="crawl_c", name="高工储能爬虫", func=crawl_source_c, wave=1))
    
    # Wave 2: 数据清洗（依赖 Wave 1）
    print("  Wave 2: [数据清洗]  ← 依赖 Wave 1")
    executor.add_task(Task(
        id="clean", 
        name="数据清洗", 
        func=clean_data,
        depends_on=["crawl_a", "crawl_b", "crawl_c"],
        wave=2
    ))
    
    # Wave 3: 报告生成（依赖 Wave 2）
    print("  Wave 3: [报告生成]  ← 依赖 Wave 2")
    executor.add_task(Task(
        id="report", 
        name="报告生成", 
        func=generate_report,
        depends_on=["clean"],
        wave=3
    ))
    
    # 执行
    print("\n开始执行...")
    result = executor.execute()
    
    print("\n执行结果:")
    print(f"  总波次数: {result['total_waves']}")
    print(f"  成功任务: {result['successful_tasks']}/{result['total_tasks']}")
    print(f"  总耗时: {result['total_time']:.2f}s")
    print(f"  并行效率提升: ~{result['total_waves'] * 0.5 / result['total_time']:.1f}x")
    
    return result


def demo_git_atomic():
    """演示原子化 Git 提交"""
    print("\n" + "=" * 70)
    print("🔀 演示 3: 原子化 Git 提交 (Atomic Git Commit)")
    print("=" * 70)
    
    git = GitAtomicCommit()
    
    if not git.enabled:
        print("\n⚠️ 当前不是 Git 仓库，以下为模拟演示")
    
    # 模拟多个任务提交
    commits = []
    
    # 提交 1: 爬虫
    commit1 = git.commit_task_result(
        task_type=TaskType.CRAWL,
        task_name="北极星储能网爬虫",
        status=GitTaskStatus.SUCCESS,
        summary="成功获取 94 条新闻",
        details=[
            "新增数据 94 条",
            "去重后有效 94 条",
            "耗时: 0.5s"
        ],
        files=["data/crawler/bjx_20260329.json"],
        metadata={"source": "北极星", "items": 94, "duration": 0.5}
    )
    commits.append(("爬虫", commit1))
    
    # 提交 2: 数据清洗
    commit2 = git.commit_task_result(
        task_type=TaskType.CLEAN,
        task_name="数据清洗合并",
        status=GitTaskStatus.SUCCESS,
        summary="合并3个数据源，去重后 106 条",
        details=[
            "原始数据: 120 条",
            "去重后: 106 条",
            "数据源: 北极星/储能中国/高工"
        ],
        files=["data/cleaned/news_merged_20260329.json"],
        metadata={"sources": 3, "before": 120, "after": 106}
    )
    commits.append(("清洗", commit2))
    
    # 提交 3: 报告生成
    commit3 = git.commit_task_result(
        task_type=TaskType.GENERATE,
        task_name="储能日报生成",
        status=GitTaskStatus.SUCCESS,
        summary="生成 2026-03-29 日报，置信度 90/100",
        details=[
            "章节: 市场动态/技术进展/政策动态/行情数据/今日热点",
            "热点TOP3: 菲律宾政策/贵州项目/南网中标",
            "数据量: 196 条"
        ],
        files=["data/reports/report_20260329.md"],
        metadata={"date": "2026-03-29", "confidence": 90, "sections": 5}
    )
    commits.append(("报告", commit3))
    
    print("\n提交记录:")
    for name, commit_hash in commits:
        status = "✅" if commit_hash else "❌"
        print(f"  {status} [{name}] {commit_hash[:8] if commit_hash else 'N/A'}")
    
    # 统计
    stats = git.get_commit_stats()
    print("\n提交统计:")
    print(f"  总提交数: {stats['total_commits']}")
    print(f"  按类型: {stats['by_type']}")
    
    return commits


def demo_integration():
    """演示完整集成流程"""
    print("\n" + "=" * 70)
    print("🚀 演示 4: 完整集成流程 (XML + Wave + Git)")
    print("=" * 70)
    
    print("""
完整流程示意:

┌──────────────────────────────────────────────────────────────────────┐
│                        日报生成完整流程                               │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  1. XML 提示构建                                                      │
│     └─ DailyReportXMLTemplate.create()                               │
│        ├─ 任务目标: 生成日报                                          │
│        ├─ 上下文: 数据源/日期/历史                                    │
│        ├─ 约束: 格式/语言/质量要求                                    │
│        └─ 输出格式: 5个必需章节                                       │
│                                                                       │
│  2. 波式并行执行                                                      │
│     └─ WaveBasedExecutor.execute()                                   │
│        Wave 1: [爬虫A] [爬虫B] [爬虫C]  ← 并行 (3x 速度)              │
│           ↓                                                           │
│        Wave 2: [数据清洗]               ← 依赖 Wave 1                 │
│           ↓                                                           │
│        Wave 3: [报告生成]               ← 依赖 Wave 2                 │
│                                                                       │
│  3. 原子化 Git 提交                                                   │
│     └─ 每个任务完成自动提交                                           │
│        [CRAWL] 北极星爬虫 ✅                                          │
│        [CRAWL] 储能中国爬虫 ✅                                        │
│        [CRAWL] 高工储能爬虫 ✅                                        │
│        [CLEAN] 数据清洗合并 ✅                                        │
│        [GENERATE] 日报生成 ✅                                         │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘
""")
    
    print("✅ 集成演示完成！")
    print("\n改进收益汇总:")
    print("  1. XML 提示: 结构化输入，AI 理解更精确")
    print("  2. 波式并行: 50-70% 时间节省")
    print("  3. 原子提交: 任务级版本控制，可回滚")


def main():
    """主函数"""
    print("\n" + "=" * 70)
    print("  GSD 方法论三大改进集成演示")
    print("  XML Prompt + Wave Parallelism + Atomic Git Commit")
    print("=" * 70 + "\n")
    
    # 运行四个演示
    demo_xml_prompt()
    demo_wave_execution()
    demo_git_atomic()
    demo_integration()
    
    print("\n" + "=" * 70)
    print("  演示完成！")
    print("=" * 70)


if __name__ == "__main__":
    main()
