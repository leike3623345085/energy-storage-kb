#!/usr/bin/env python3
"""
储能爬虫自动验证套件
全自动闭环 - 验证环节
"""
import json
import time
import statistics
from datetime import datetime
from pathlib import Path

WORKSPACE = Path("/root/.openclaw/workspace/energy_storage")
DATA_DIR = WORKSPACE / "data/crawler"
LOG_FILE = WORKSPACE / "logs/validation.log"

# 验证阈值
THRESHOLDS = {
    "min_data_count": 50,          # 最少数据条数
    "max_runtime": 300,            # 最大执行时间（秒）
    "max_runtime_std": 30,         # 执行时间标准差
    "min_success_rate": 0.5,       # 最低站点成功率（4个站中至少成功2个）
    "max_consecutive_failures": 2  # 最大连续失败次数
}

def ensure_dirs():
    (WORKSPACE / "logs").mkdir(parents=True, exist_ok=True)

def run_crawler_test():
    """运行一次爬虫测试"""
    import subprocess
    
    start_time = time.time()
    result = subprocess.run(
        ["python3", "run_crawler_safe.py"],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
        timeout=THRESHOLDS["max_runtime"]
    )
    runtime = time.time() - start_time
    
    # 解析输出
    data_count = 0
    success_sites = 0
    total_sites = 6
    
    for line in result.stdout.split('\n'):
        if '条' in line and '✓' in line:
            try:
                count = int(line.split('获取')[1].split('条')[0].strip())
                data_count += count
                if count > 0:
                    success_sites += 1
            except:
                pass
    
    return {
        "return_code": result.returncode,
        "runtime": runtime,
        "data_count": data_count,
        "success_sites": success_sites,
        "total_sites": total_sites,
        "success_rate": success_sites / total_sites,
        "stdout": result.stdout[:500],
        "stderr": result.stderr[:500] if result.stderr else ""
    }

def validate_crawler(trials=3):
    """
    运行多次验证
    
    返回: {
        "passed": bool,
        "details": {...},
        "failures": [...]
    }
    """
    ensure_dirs()
    results = []
    failures = []
    
    for i in range(trials):
        print(f"验证运行 {i+1}/{trials}...")
        result = run_crawler_test()
        results.append(result)
        time.sleep(5)  # 间隔5秒
    
    # 分析结果
    runtimes = [r["runtime"] for r in results]
    data_counts = [r["data_count"] for r in results]
    return_codes = [r["return_code"] for r in results]
    
    # 检查各项指标
    checks = {
        "all_success": all(r == 0 for r in return_codes),
        "min_data": min(data_counts) >= THRESHOLDS["min_data_count"],
        "max_runtime": max(runtimes) <= THRESHOLDS["max_runtime"],
        "runtime_stable": statistics.stdev(runtimes) <= THRESHOLDS["max_runtime_std"] if len(runtimes) > 1 else True,
        "success_rate": all(r["success_rate"] >= THRESHOLDS["min_success_rate"] for r in results)
    }
    
    # 记录失败项
    for check, passed in checks.items():
        if not passed:
            failures.append({
                "check": check,
                "expected": THRESHOLDS.get(check.replace("all_", "").replace("min_", "").replace("max_", ""), True),
                "actual": {
                    "return_codes": return_codes,
                    "data_counts": data_counts,
                    "runtimes": runtimes,
                    "runtimes_std": statistics.stdev(runtimes) if len(runtimes) > 1 else 0
                }
            })
    
    passed = all(checks.values())
    
    report = {
        "timestamp": datetime.now().isoformat(),
        "passed": passed,
        "trials": trials,
        "checks": checks,
        "summary": {
            "avg_data_count": sum(data_counts) / len(data_counts),
            "avg_runtime": sum(runtimes) / len(runtimes),
            "runtime_std": statistics.stdev(runtimes) if len(runtimes) > 1 else 0,
            "success_rate": sum(1 for r in results if r["return_code"] == 0) / len(results)
        },
        "failures": failures,
        "raw_results": results
    }
    
    # 记录日志
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(json.dumps(report, ensure_ascii=False) + "\n")
    
    return report

def auto_deploy_check():
    """部署前自动检查"""
    print("=" * 50)
    print("储能爬虫自动验证")
    print("=" * 50)
    
    report = validate_crawler()
    
    if report["passed"]:
        print("\n✅ 验证通过")
        print(f"平均数据量: {report['summary']['avg_data_count']:.0f} 条")
        print(f"平均执行时间: {report['summary']['avg_runtime']:.1f} 秒")
        return True
    else:
        print("\n❌ 验证失败")
        for f in report["failures"]:
            print(f"  - {f['check']}: 未通过")
        return False

if __name__ == "__main__":
    success = auto_deploy_check()
    exit(0 if success else 1)
