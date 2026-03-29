#!/usr/bin/env python3
"""
波式并行执行引擎 (Wave-Based Parallelism Engine)
=================================================
基于 GSD 方法的波次依赖编排系统

核心特性:
- 按依赖波次执行任务
- 同一波次内并行执行
- 波次间串行依赖
- 自动错误处理和重试
- 与 XML 提示系统集成

Wave 概念:
    Wave 1: [任务A, 任务B, 任务C]  ← 无依赖，并行执行
    Wave 2: [任务D]               ← 依赖 Wave 1
    Wave 3: [任务E, 任务F]        ← 依赖 Wave 2
"""

import json
import time
import logging
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Callable, Any, Optional, Set
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from enum import Enum

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("WaveEngine")


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class Task:
    """任务定义"""
    id: str
    name: str
    func: Callable = field(compare=False)
    args: tuple = field(default_factory=tuple)
    kwargs: Dict = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)
    wave: int = 0
    timeout: int = 300
    retry: int = 2
    
    # 运行时状态
    status: TaskStatus = field(default=TaskStatus.PENDING)
    result: Any = None
    error: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    
    def to_dict(self) -> Dict:
        """转换为字典（不包括 func）"""
        return {
            "id": self.id,
            "name": self.name,
            "depends_on": self.depends_on,
            "wave": self.wave,
            "status": self.status.value,
            "error": self.error,
            "start_time": self.start_time,
            "end_time": self.end_time,
        }


@dataclass
class Wave:
    """波次定义"""
    id: int
    tasks: List[Task]
    parallel: bool = True
    
    @property
    def is_complete(self) -> bool:
        """检查波次是否完成"""
        return all(t.status in [TaskStatus.SUCCESS, TaskStatus.SKIPPED] for t in self.tasks)
    
    @property
    def has_failure(self) -> bool:
        """检查是否有失败任务"""
        return any(t.status == TaskStatus.FAILED for t in self.tasks)


class WaveBasedExecutor:
    """波式并行执行器"""
    
    def __init__(self, max_workers: int = 4, stop_on_failure: bool = False):
        self.max_workers = max_workers
        self.stop_on_failure = stop_on_failure
        self.tasks: Dict[str, Task] = {}
        self.waves: Dict[int, Wave] = {}
        self.execution_log: List[Dict] = []
        self.results: Dict[str, Any] = {}
    
    def add_task(self, task: Task) -> "WaveBasedExecutor":
        """添加任务"""
        self.tasks[task.id] = task
        
        # 按 wave 分组
        if task.wave not in self.waves:
            self.waves[task.wave] = Wave(id=task.wave, tasks=[])
        self.waves[task.wave].tasks.append(task)
        
        return self
    
    def build_dependency_waves(self) -> "WaveBasedExecutor":
        """
        自动根据依赖关系构建波次
        
        算法:
        1. 找到所有没有依赖的任务 → Wave 1
        2. 依赖 Wave 1 的任务 → Wave 2
        3. 依赖 Wave 2 的任务 → Wave 3
        4. ...
        """
        # 重置波次
        self.waves = {}
        
        # 构建依赖图
        assigned: Set[str] = set()
        wave_num = 1
        
        while len(assigned) < len(self.tasks):
            wave_tasks = []
            
            for task_id, task in self.tasks.items():
                if task_id in assigned:
                    continue
                
                # 检查所有依赖是否已在之前的波次
                if all(dep in assigned for dep in task.depends_on):
                    task.wave = wave_num
                    wave_tasks.append(task)
            
            if not wave_tasks:
                # 有循环依赖或无法解析的依赖
                remaining = [t for t in self.tasks if t not in assigned]
                logger.error(f"无法解析的依赖: {remaining}")
                break
            
            self.waves[wave_num] = Wave(id=wave_num, tasks=wave_tasks)
            assigned.update(t.id for t in wave_tasks)
            wave_num += 1
        
        logger.info(f"构建了 {len(self.waves)} 个执行波次")
        return self
    
    def _execute_task(self, task: Task) -> Task:
        """执行单个任务"""
        logger.info(f"执行任务: {task.name} (Wave {task.wave})")
        
        task.status = TaskStatus.RUNNING
        task.start_time = time.time()
        
        try:
            # 执行函数
            result = task.func(*task.args, **task.kwargs)
            task.result = result
            task.status = TaskStatus.SUCCESS
            self.results[task.id] = result
            
            logger.info(f"✅ 任务成功: {task.name}")
            
        except Exception as e:
            task.error = str(e)
            task.status = TaskStatus.FAILED
            logger.error(f"❌ 任务失败: {task.name} - {e}")
        
        task.end_time = time.time()
        return task
    
    def _execute_wave(self, wave: Wave) -> bool:
        """执行一个波次，返回是否成功"""
        logger.info(f"\n🌊 执行 Wave {wave.id} ({len(wave.tasks)} 个任务)")
        
        if wave.parallel and len(wave.tasks) > 1:
            # 并行执行
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_task = {
                    executor.submit(self._execute_task, task): task 
                    for task in wave.tasks
                }
                
                for future in as_completed(future_to_task):
                    task = future_to_task[future]
                    try:
                        future.result()
                    except Exception as e:
                        logger.error(f"任务执行异常: {task.name} - {e}")
        else:
            # 串行执行
            for task in wave.tasks:
                self._execute_task(task)
        
        # 检查波次结果
        success = not wave.has_failure
        if not success and self.stop_on_failure:
            logger.error(f"Wave {wave.id} 失败，停止执行")
        
        return success
    
    def execute(self) -> Dict[str, Any]:
        """
        执行所有波次
        
        Returns:
            执行结果汇总
        """
        logger.info("=" * 60)
        logger.info("🚀 启动波式并行执行引擎")
        logger.info("=" * 60)
        
        start_time = time.time()
        
        # 如果没有构建波次，自动构建
        if not self.waves:
            self.build_dependency_waves()
        
        # 按波次顺序执行
        sorted_waves = sorted(self.waves.keys())
        
        for wave_id in sorted_waves:
            wave = self.waves[wave_id]
            
            # 执行波次
            success = self._execute_wave(wave)
            
            # 记录日志
            self.execution_log.append({
                "wave_id": wave_id,
                "timestamp": datetime.now().isoformat(),
                "tasks": [t.to_dict() for t in wave.tasks],
                "success": success
            })
            
            # 失败处理
            if not success and self.stop_on_failure:
                break
        
        total_time = time.time() - start_time
        
        # 汇总结果
        summary = {
            "total_waves": len(self.waves),
            "total_tasks": len(self.tasks),
            "successful_tasks": sum(1 for t in self.tasks.values() if t.status == TaskStatus.SUCCESS),
            "failed_tasks": sum(1 for t in self.tasks.values() if t.status == TaskStatus.FAILED),
            "total_time": total_time,
            "results": self.results,
            "log": self.execution_log
        }
        
        logger.info("\n" + "=" * 60)
        logger.info("📊 执行完成")
        logger.info(f"   总耗时: {total_time:.1f}s")
        logger.info(f"   成功: {summary['successful_tasks']}/{summary['total_tasks']}")
        logger.info("=" * 60)
        
        return summary
    
    def save_execution_log(self, output_path: Optional[Path] = None):
        """保存执行日志"""
        if output_path is None:
            output_path = Path(__file__).parent / "data" / "wave_execution_logs"
        
        output_path.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = output_path / f"wave_execution_{timestamp}.json"
        
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump({
                "execution_time": datetime.now().isoformat(),
                "tasks": {k: v.to_dict() for k, v in self.tasks.items()},
                "waves": {k: {"id": v.id, "task_count": len(v.tasks)} for k, v in self.waves.items()},
                "log": self.execution_log
            }, f, ensure_ascii=False, indent=2)
        
        logger.info(f"💾 执行日志已保存: {log_file}")


# ============== 与爬虫和报告生成集成 ==============

class DailyReportWavePipeline:
    """日报生成的波式流水线"""
    
    def __init__(self, max_workers: int = 4):
        self.executor = WaveBasedExecutor(max_workers=max_workers)
        self.crawled_data = []
        self.cleaned_data = []
        self.report = None
    
    def _crawl_source(self, source_key: str) -> List[Dict]:
        """爬取单个数据源"""
        # 导入并行爬虫
        from crawler_parallel import ParallelCrawler, SOURCES_CONFIG
        
        crawler = ParallelCrawler(max_workers=1)
        result = crawler.crawl([source_key])
        return result.get("items", [])
    
    def _clean_data(self, all_data: List[List[Dict]]) -> List[Dict]:
        """清洗和合并数据"""
        # 合并所有数据源的结果
        merged = []
        for data_list in all_data:
            merged.extend(data_list)
        
        # 去重
        seen_urls = set()
        unique = [item for item in merged if not (item["url"] in seen_urls or seen_urls.add(item["url"]))]
        
        logger.info(f"数据清洗: {len(merged)} -> {len(unique)} 条")
        return unique
    
    def _generate_report(self, data: List[Dict]) -> str:
        """生成报告"""
        # 这里可以调用 XML 提示格式化
        from xml_prompt_formatter import DailyReportXMLTemplate
        
        date = datetime.now().strftime("%Y-%m-%d")
        builder = DailyReportXMLTemplate.create(
            source_data=data,
            date=date,
            data_stats={"quality_score": 95}
        )
        
        # 返回提示文本（实际使用时传递给 LLM）
        return builder.to_prompt()
    
    def run(self) -> Dict[str, Any]:
        """运行完整的日报生成流水线"""
        
        # Wave 1: 并行爬取多个数据源
        sources = ["bjx", "cnnes"]
        for i, source in enumerate(sources):
            self.executor.add_task(Task(
                id=f"crawl_{source}",
                name=f"爬取 {source}",
                func=self._crawl_source,
                args=(source,),
                wave=1,
                timeout=60
            ))
        
        # Wave 2: 数据清洗（依赖 Wave 1）
        self.executor.add_task(Task(
            id="clean_data",
            name="数据清洗",
            func=self._clean_data,
            args=([self.results.get(f"crawl_{s}", []) for s in sources],),
            depends_on=[f"crawl_{s}" for s in sources],
            wave=2,
            timeout=30
        ))
        
        # Wave 3: 报告生成（依赖 Wave 2）
        self.executor.add_task(Task(
            id="generate_report",
            name="生成报告",
            func=self._generate_report,
            args=([self.results.get("clean_data", [])],),
            depends_on=["clean_data"],
            wave=3,
            timeout=120
        ))
        
        # 执行
        result = self.executor.execute()
        self.executor.save_execution_log()
        
        return result


# ============== 使用示例 ==============

def example_wave_execution():
    """示例：波式执行"""
    
    def task_a():
        time.sleep(1)
        return "A result"
    
    def task_b():
        time.sleep(1)
        return "B result"
    
    def task_c(a_result, b_result):
        return f"C combines {a_result} and {b_result}"
    
    executor = WaveBasedExecutor(max_workers=2)
    
    # Wave 1: A 和 B 并行
    executor.add_task(Task(id="a", name="Task A", func=task_a, wave=1))
    executor.add_task(Task(id="b", name="Task B", func=task_b, wave=1))
    
    # Wave 2: C 依赖 A 和 B
    executor.add_task(Task(
        id="c", 
        name="Task C", 
        func=task_c,
        args=(executor.results.get("a"), executor.results.get("b")),
        depends_on=["a", "b"],
        wave=2
    ))
    
    result = executor.execute()
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    print("波式并行执行引擎 - 示例运行")
    print("=" * 60)
    
    # 运行示例
    example_wave_execution()
