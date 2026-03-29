#!/usr/bin/env python3
"""
串行 vs 并行爬虫性能对比
========================
用于量化验证自动任务拆解的收益
"""

import time
import json
from pathlib import Path
from datetime import datetime
from crawler_parallel import ParallelCrawler, scrape_source, SOURCES_CONFIG


def crawl_sequential(source_keys: list) -> dict:
    """串行爬取（模拟当前实现）"""
    print("\n" + "="*60)
    print("【串行模式】逐个执行爬虫...")
    print("="*60)
    
    start = time.time()
    all_items = []
    results = []
    
    for key in source_keys:
        config = SOURCES_CONFIG[key]
        print(f"\n▶️ 开始: {config['name']}")
        
        result = scrape_source(key, config)
        results.append(result)
        
        status = "✅" if result.success else "⚠️"
        print(f"{status} {result.source} | {result.item_count}条 | {result.duration:.1f}s")
        
        if result.success:
            all_items.extend(result.items)
    
    # 去重
    seen = set()
    unique = [item for item in all_items if not (item["url"] in seen or seen.add(item["url"]))]
    
    return {
        "mode": "sequential",
        "total_duration": time.time() - start,
        "total_items": len(unique),
        "results": results,
    }


def crawl_parallel(source_keys: list, max_workers: int = 4) -> dict:
    """并行爬取"""
    print("\n" + "="*60)
    print(f"【并行模式】max_workers={max_workers}")
    print("="*60)
    
    crawler = ParallelCrawler(max_workers=max_workers)
    result = crawler.crawl(source_keys)
    
    return {
        "mode": "parallel",
        "total_duration": result["stats"]["total_duration"],
        "total_items": result["stats"]["total_items"],
        "results": result["results"],
    }


def main():
    """主函数 - 对比测试"""
    # 使用所有可用的数据源
    source_keys = ["bjx", "cnnes"]  # 目前只有这两个稳定可用
    
    print("\n" + "🧪 串行 vs 并行爬虫性能对比")
    print("=" * 60)
    print(f"数据源: {', '.join(source_keys)}")
    print(f"时间: {datetime.now()}")
    
    # 1. 串行测试
    seq_result = crawl_sequential(source_keys)
    
    # 2. 并行测试
    par_result = crawl_parallel(source_keys, max_workers=len(source_keys))
    
    # 3. 结果对比
    print("\n" + "="*60)
    print("📊 性能对比结果")
    print("="*60)
    
    print(f"\n{'指标':<20} {'串行':>12} {'并行':>12} {'提升':>12}")
    print("-" * 60)
    
    seq_time = seq_result["total_duration"]
    par_time = par_result["total_duration"]
    speedup = seq_time / par_time if par_time > 0 else 1
    
    print(f"{'总耗时':<20} {seq_time:>11.2f}s {par_time:>11.2f}s {speedup:>11.1f}x")
    print(f"{'获取条数':<20} {seq_result['total_items']:>11}条 {par_result['total_items']:>11}条 {'-':>12}")
    
    # 详细分解
    print("\n📋 各数据源耗时分解:")
    print("-" * 60)
    print(f"{'数据源':<15} {'串行耗时':>10} {'并行耗时':>10} {'状态':>10}")
    print("-" * 60)
    
    for s, p in zip(seq_result["results"], par_result["results"]):
        status = "✅" if p.get("success") else "❌"
        print(f"{s.source:<15} {s.duration:>9.2f}s {p.get('duration', 0):>9.2f}s {status:>10}")
    
    # 结论
    print("\n" + "="*60)
    print("🎯 结论")
    print("="*60)
    print(f"✅ 并行爬虫速度提升: {speedup:.1f}x")
    print(f"✅ 时间节省: {seq_time - par_time:.1f}秒 ({(1 - 1/speedup)*100:.0f}%)")
    print(f"✅ 数据完整性: {'一致' if seq_result['total_items'] == par_result['total_items'] else '有差异'}")
    
    if speedup >= 1.5:
        print(f"\n🚀 建议: 效率提升显著，建议在生产环境启用并行爬虫")
    else:
        print(f"\n⚠️ 建议: 提升有限，可能原因: 数据源少、网络延迟、反爬限制")
    
    # 保存详细结果
    output = {
        "test_time": datetime.now().isoformat(),
        "sources": source_keys,
        "sequential": {
            "duration": seq_result["total_duration"],
            "items": seq_result["total_items"],
        },
        "parallel": {
            "duration": par_result["total_duration"],
            "items": par_result["total_items"],
            "max_workers": len(source_keys),
        },
        "improvement": {
            "speedup": speedup,
            "time_saved": seq_time - par_time,
            "percentage": (1 - 1/speedup) * 100 if speedup > 0 else 0,
        }
    }
    
    output_file = Path(__file__).parent / "data" / "benchmark_parallel_crawler.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 详细结果保存: {output_file}")


if __name__ == "__main__":
    main()
