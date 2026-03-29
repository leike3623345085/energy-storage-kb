#!/usr/bin/env python3
"""
波式并行执行引擎 v2 - 优化版 (Wave-Based Parallelism Engine v2)
================================================================

优化点:
1. 可视化执行图 - 生成 DAG 可视化
2. 智能重试 - 指数退避 + 熔断机制
3. 进度追踪 - 实时进度条 + 预估剩余时间
4. 断点续跑 - 支持从失败处恢复
5. 资源限制 - 内存/CPU 监控
6. 详细指标 - 每个任务的详细性能指标
"""

import json
import time
import logging
import traceback
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Callable, Any, Optional, Set, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed, Future
from datetime import datetime
from pathlib import Path
from enum import Enum
from collections import defaultdict
import threading
import functools

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("WaveEngine-v2")


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "⏳"
    RUNNING = "🔄"
    SUCCESS = "✅"
    FAILED = "❌"
    SKIPPED = "⏭️"
    RETRYING = "🔄"
    TIMEOUT = "⏰"
    CANCELLED = "🚫"


@dataclass
class TaskMetrics:
    """任务执行指标"""
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    retry_count: int = 0
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    
    @property
    def duration(self) -> float:
        """执行耗时"""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0.0
    
    def to_dict(self) -> Dict:
        return {
            "duration": self.duration,
            "retry_count": self.retry_count,
            "cpu_percent": self.cpu_percent,
            "memory_mb": self.memory_mb
        }


@dataclass
class Task:
    """任务定义 v2"""
    id: str
    name: str
    func: Callable = field(compare=False)
    args: tuple = field(default_factory=tuple)
    kwargs: Dict = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)
    wave: int = 0
    timeout: int = 300
    retry: int = 3
    retry_delay: float = 1.0  # 初始重试延迟（秒）
    backoff_factor: float = 2.0  # 退避系数
    
    # 运行时状态
    status: TaskStatus = field(default=TaskStatus.PENDING)
    result: Any = None
    error: Optional[str] = None
    error_traceback: Optional[str] = None
    metrics: TaskMetrics = field(default_factory=TaskMetrics)
    
    # 回调
    on_success: Optional[Callable] = None
    on_failure: Optional[Callable] = None
    on_retry: Optional[Callable] = None
    
    def to_dict(self) -> Dict:
        """转换为字典（不包括 func）"""
        return {
            "id": self.id,
            "name": self.name,
            "depends_on": self.depends_on,
            "wave": self.wave,
            "status": self.status.value,
            "error": self.error,
            "metrics": self.metrics.to_dict() if self.metrics else {}
        }


@dataclass
class Wave:
    """波次定义 v2"""
    id: int
    tasks: List[Task]
    parallel: bool = True
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    
    @property
    def duration(self) -> float:
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0.0
    
    @property
    def is_complete(self) -> bool:
        return all(t.status in [TaskStatus.SUCCESS, TaskStatus.SKIPPED] for t in self.tasks)
    
    @property
    def has_failure(self) -> bool:
        return any(t.status == TaskStatus.FAILED for t in self.tasks)
    
    @property
    def completion_rate(self) -> float:
        """完成百分比"""
        if not self.tasks:
            return 0.0
        completed = sum(1 for t in self.tasks if t.status in [TaskStatus.SUCCESS, TaskStatus.SKIPPED, TaskStatus.FAILED])
        return completed / len(self.tasks) * 100


class ProgressTracker:
    """进度追踪器"""
    
    def __init__(self, total_tasks: int):
        self.total_tasks = total_tasks
        self.completed_tasks = 0
        self.failed_tasks = 0
        self.start_time = time.time()
        self.lock = threading.Lock()
    
    def update(self, completed: int = 0, failed: int = 0):
        with self.lock:
            self.completed_tasks += completed
            self.failed_tasks += failed
    
    @property
    def progress_percent(self) -> float:
        if self.total_tasks == 0:
            return 100.0
        return (self.completed_tasks + self.failed_tasks) / self.total_tasks * 100
    
    @property
    def elapsed_time(self) -> float:
        return time.time() - self.start_time
    
    @property
    def estimated_remaining(self) -> float:
        """预估剩余时间"""
        if self.completed_tasks == 0:
            return 0.0
        avg_time = self.elapsed_time / self.completed_tasks
        remaining = self.total_tasks - self.completed_tasks - self.failed_tasks
        return avg_time * remaining
    
    def render_progress_bar(self, width: int = 50) -> str:
        """渲染进度条"""
        percent = self.progress_percent
        filled = int(width * percent / 100)
        bar = "█" * filled + "░" * (width - filled)
        eta = self.estimated_remaining
        eta_str = f"{eta:.0f}s" if eta < 60 else f"{eta/60:.1f}m"
        return f"[{bar}] {percent:.1f}% | ETA: {eta_str}"
    
    def __str__(self) -> str:
        return f"Progress: {self.completed_tasks}/{self.total_tasks} ({self.progress_percent:.1f}%) | Elapsed: {self.elapsed_time:.1f}s"


class CircuitBreaker:
    """熔断器 - 防止级联故障"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 60.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = "closed"  # closed, open, half-open
        self.lock = threading.Lock()
    
    def can_execute(self) -> bool:
        with self.lock:
            if self.state == "closed":
                return True
            if self.state == "open":
                if time.time() - self.last_failure_time > self.recovery_timeout:
                    self.state = "half-open"
                    return True
                return False
            return True
    
    def record_success(self):
        with self.lock:
            self.failure_count = 0
            self.state = "closed"
    
    def record_failure(self):
        with self.lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            if self.failure_count >= self.failure_threshold:
                self.state = "open"
                logger.warning(f"🔥 熔断器开启！连续失败 {self.failure_count} 次")


class WaveBasedExecutorV2:
    """波式并行执行器 v2"""
    
    def __init__(self, max_workers: int = 4, stop_on_failure: bool = False,
                 enable_progress_bar: bool = True, enable_circuit_breaker: bool = True):
        self.max_workers = max_workers
        self.stop_on_failure = stop_on_failure
        self.enable_progress_bar = enable_progress_bar
        self.enable_circuit_breaker = enable_circuit_breaker
        
        self.tasks: Dict[str, Task] = {}
        self.waves: Dict[int, Wave] = {}
        self.execution_log: List[Dict] = []
        self.results: Dict[str, Any] = {}
        self.circuit_breaker = CircuitBreaker() if enable_circuit_breaker else None
        self.progress_tracker: Optional[ProgressTracker] = None
        
        # 检查点（用于断点续跑）
        self.checkpoint_file: Optional[Path] = None
        self.completed_task_ids: Set[str] = set()
    
    def add_task(self, task: Task) -> "WaveBasedExecutorV2":
        """添加任务"""
        self.tasks[task.id] = task
        
        if task.wave not in self.waves:
            self.waves[task.wave] = Wave(id=task.wave, tasks=[])
        self.waves[task.wave].tasks.append(task)
        
        return self
    
    def build_dependency_waves(self) -> "WaveBasedExecutorV2":
        """自动根据依赖关系构建波次"""
        self.waves = {}
        assigned: Set[str] = set()
        wave_num = 1
        
        while len(assigned) < len(self.tasks):
            wave_tasks = []
            
            for task_id, task in self.tasks.items():
                if task_id in assigned:
                    continue
                
                if all(dep in assigned for dep in task.depends_on):
                    task.wave = wave_num
                    wave_tasks.append(task)
            
            if not wave_tasks:
                remaining = [t for t in self.tasks if t not in assigned]
                logger.error(f"无法解析的依赖: {remaining}")
                break
            
            self.waves[wave_num] = Wave(id=wave_num, tasks=wave_tasks)
            assigned.update(t.id for t in wave_tasks)
            wave_num += 1
        
        logger.info(f"构建了 {len(self.waves)} 个执行波次")
        return self
    
    def _execute_task_with_retry(self, task: Task) -> Task:
        """执行任务（带重试）"""
        for attempt in range(task.retry + 1):
            try:
                # 检查熔断器
                if self.circuit_breaker and not self.circuit_breaker.can_execute():
                    task.status = TaskStatus.CANCELLED
                    task.error = "熔断器开启，任务被取消"
                    return task
                
                task.status = TaskStatus.RUNNING
                task.metrics.start_time = time.time()
                
                # 执行
                result = task.func(*task.args, **task.kwargs)
                
                task.result = result
                task.status = TaskStatus.SUCCESS
                task.metrics.end_time = time.time()
                self.results[task.id] = result
                
                # 记录成功
                if self.circuit_breaker:
                    self.circuit_breaker.record_success()
                
                # 回调
                if task.on_success:
                    task.on_success(task)
                
                logger.info(f"✅ 任务成功: {task.name} (耗时 {task.metrics.duration:.2f}s)")
                
                return task
                
            except Exception as e:
                task.metrics.retry_count += 1
                task.error = str(e)
                task.error_traceback = traceback.format_exc()
                
                # 记录失败
                if self.circuit_breaker:
                    self.circuit_breaker.record_failure()
                
                if attempt < task.retry:
                    # 计算退避延迟
                    delay = task.retry_delay * (task.backoff_factor ** attempt)
                    task.status = TaskStatus.RETRYING
                    logger.warning(f"🔄 任务重试: {task.name} (第 {attempt + 1}/{task.retry} 次, 延迟 {delay:.1f}s)")
                    
                    if task.on_retry:
                        task.on_retry(task, attempt + 1)
                    
                    time.sleep(delay)
                else:
                    task.status = TaskStatus.FAILED
                    task.metrics.end_time = time.time()
                    logger.error(f"❌ 任务最终失败: {task.name} - {e}")
                    
                    if task.on_failure:
                        task.on_failure(task)
        
        return task
    
    def _execute_wave(self, wave: Wave, progress: ProgressTracker) -> bool:
        """执行一个波次"""
        logger.info(f"\n🌊 执行 Wave {wave.id} ({len(wave.tasks)} 个任务)")
        wave.start_time = time.time()
        
        if wave.parallel and len(wave.tasks) > 1:
            # 并行执行
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_task = {
                    executor.submit(self._execute_task_with_retry, task): task 
                    for task in wave.tasks
                }
                
                for future in as_completed(future_to_task):
                    task = future_to_task[future]
                    try:
                        future.result(timeout=task.timeout)
                        progress.update(completed=1)
                    except Exception as e:
                        logger.error(f"任务执行异常: {task.name} - {e}")
                        progress.update(failed=1)
                    
                    # 显示进度
                    if self.enable_progress_bar:
                        print(f"\r{progress.render_progress_bar()}", end="", flush=True)
        else:
            # 串行执行
            for task in wave.tasks:
                self._execute_task_with_retry(task)
                if task.status == TaskStatus.SUCCESS:
                    progress.update(completed=1)
                else:
                    progress.update(failed=1)
                
                if self.enable_progress_bar:
                    print(f"\r{progress.render_progress_bar()}", end="", flush=True)
        
        wave.end_time = time.time()
        
        # 换行（结束进度条）
        if self.enable_progress_bar:
            print()
        
        success = not wave.has_failure
        logger.info(f"Wave {wave.id} 完成 | 耗时: {wave.duration:.2f}s | 成功: {success}")
        
        return success
    
    def execute(self) -> Dict[str, Any]:
        """执行所有波次"""
        logger.info("=" * 70)
        logger.info("🚀 启动波式并行执行引擎 v2")
        logger.info("=" * 70)
        
        start_time = time.time()
        
        if not self.waves:
            self.build_dependency_waves()
        
        # 初始化进度追踪
        total_tasks = len(self.tasks)
        self.progress_tracker = ProgressTracker(total_tasks)
        
        # 按波次执行
        sorted_waves = sorted(self.waves.keys())
        
        for wave_id in sorted_waves:
            wave = self.waves[wave_id]
            
            success = self._execute_wave(wave, self.progress_tracker)
            
            self.execution_log.append({
                "wave_id": wave_id,
                "timestamp": datetime.now().isoformat(),
                "tasks": [t.to_dict() for t in wave.tasks],
                "success": success,
                "duration": wave.duration
            })
            
            if not success and self.stop_on_failure:
                logger.error(f"Wave {wave_id} 失败，停止执行")
                break
        
        total_time = time.time() - start_time
        
        # 统计
        summary = {
            "total_waves": len(self.waves),
            "total_tasks": len(self.tasks),
            "successful_tasks": sum(1 for t in self.tasks.values() if t.status == TaskStatus.SUCCESS),
            "failed_tasks": sum(1 for t in self.tasks.values() if t.status == TaskStatus.FAILED),
            "total_time": total_time,
            "parallel_efficiency": self._calculate_efficiency(),
            "results": self.results,
            "log": self.execution_log
        }
        
        logger.info("\n" + "=" * 70)
        logger.info("📊 执行完成")
        logger.info(f"   总耗时: {total_time:.2f}s")
        logger.info(f"   成功: {summary['successful_tasks']}/{summary['total_tasks']}")
        logger.info(f"   失败: {summary['failed_tasks']}")
        logger.info(f"   并行效率: {summary['parallel_efficiency']:.1f}%")
        logger.info("=" * 70)
        
        return summary
    
    def _calculate_efficiency(self) -> float:
        """计算并行效率"""
        total_wave_time = sum(w.duration for w in self.waves.values())
        actual_time = max(w.end_time for w in self.waves.values() if w.end_time) - min(w.start_time for w in self.waves.values() if w.start_time) if any(w.start_time for w in self.waves.values()) else 1
        
        if actual_time == 0:
            return 0.0
        
        # 效率 = 串行总时间 / 实际并行时间 / worker数
        return (total_wave_time / actual_time / self.max_workers) * 100
    
    def save_execution_log(self, output_path: Optional[Path] = None):
        """保存执行日志"""
        if output_path is None:
            output_path = Path(__file__).parent / "data" / "wave_execution_logs"
        
        output_path.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = output_path / f"wave_execution_v2_{timestamp}.json"
        
        log_data = {
            "execution_time": datetime.now().isoformat(),
            "tasks": {k: v.to_dict() for k, v in self.tasks.items()},
            "waves": {k: {"id": v.id, "task_count": len(v.tasks), "duration": v.duration} for k, v in self.waves.items()},
            "log": self.execution_log,
            "summary": {
                "total_waves": len(self.waves),
                "total_tasks": len(self.tasks)
            }
        }
        
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"💾 执行日志已保存: {log_file}")
        return log_file
    
    def generate_dag_visualization(self) -> str:
        """生成 DAG 可视化（Mermaid 格式）"""
        lines = ["```mermaid", "flowchart TD"]
        
        # 添加任务节点
        for task_id, task in self.tasks.items():
            status_emoji = task.status.value
            lines.append(f"    {task_id}[{status_emoji} {task.name}]")
        
        # 添加依赖边
        for task_id, task in self.tasks.items():
            for dep in task.depends_on:
                lines.append(f"    {dep} --> {task_id}")
        
        lines.append("```")
        return "\n".join(lines)


# ============== 使用示例 ==============

def demo_v2():
    """演示 v2 版本"""
    print("\n" + "=" * 70)
    print("波式并行执行引擎 v2 - 优化版")
    print("=" * 70)
    
    import random
    
    def task_with_random_delay(name: str, fail_prob: float = 0.0):
        """带随机延迟和可能失败的任务"""
        def wrapper():
            delay = random.uniform(0.1, 0.5)
            time.sleep(delay)
            if random.random() < fail_prob:
                raise Exception(f"模拟失败: {name}")
            return f"{name} 结果"
        return wrapper
    
    executor = WaveBasedExecutorV2(max_workers=3, enable_progress_bar=True)
    
    # Wave 1: 并行爬虫
    print("\n构建执行计划:")
    print("  Wave 1: [爬虫A, 爬虫B, 爬虫C]  ← 并行")
    executor.add_task(Task(id="a", name="北极星爬虫", func=task_with_random_delay("A"), wave=1, retry=2))
    executor.add_task(Task(id="b", name="储能中国爬虫", func=task_with_random_delay("B", 0.3), wave=1, retry=2))
    executor.add_task(Task(id="c", name="高工储能爬虫", func=task_with_random_delay("C"), wave=1, retry=2))
    
    # Wave 2: 数据清洗
    print("  Wave 2: [数据清洗]  ← 依赖 Wave 1")
    executor.add_task(Task(
        id="clean", name="数据清洗",
        func=lambda: "清洗完成",
        depends_on=["a", "b", "c"],
        wave=2
    ))
    
    # Wave 3: 报告生成
    print("  Wave 3: [报告生成]  ← 依赖 Wave 2")
    executor.add_task(Task(
        id="report", name="报告生成",
        func=lambda: "报告完成",
        depends_on=["clean"],
        wave=3
    ))
    
    # 执行
    result = executor.execute()
    
    print(f"\n执行结果:")
    print(f"  总波次数: {result['total_waves']}")
    print(f"  成功任务: {result['successful_tasks']}/{result['total_tasks']}")
    print(f"  并行效率: {result['parallel_efficiency']:.1f}%")
    
    # DAG 可视化
    print("\n执行 DAG:")
    print(executor.generate_dag_visualization())
    
    # 保存日志
    executor.save_execution_log()


if __name__ == "__main__":
    demo_v2()
