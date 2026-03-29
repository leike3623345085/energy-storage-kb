# OpenClaw 架构优化实现方案

> 三项 P0 改进的具体实现

---

## 一、漂移检测 (Drift Detection)

### 实现原理
每步执行后，对比"预期结果"和"实际结果"的语义相似度

### 代码实现

```python
# harness/drift_detector.py
from difflib import SequenceMatcher
import json

class DriftDetector:
    def __init__(self, threshold=0.7):
        self.threshold = threshold
        self.history = []
    
    def check(self, task_description, actual_result, expected_keywords=None):
        """
        检测执行结果是否偏离预期
        
        Args:
            task_description: 任务描述
            actual_result: 实际执行结果
            expected_keywords: 预期应该包含的关键词列表
        
        Returns:
            is_drift: 是否漂移
            confidence: 置信度
            suggestion: 修正建议
        """
        # 方法1: 关键词检查
        if expected_keywords:
            missing = [kw for kw in expected_keywords if kw not in actual_result]
            if missing:
                return True, 0.5, f"缺少预期内容: {missing}"
        
        # 方法2: 语义相似度 (简化版)
        # 实际可用 sentence-transformers 计算 embedding 相似度
        similarity = self._semantic_similarity(task_description, actual_result)
        
        if similarity < self.threshold:
            return True, similarity, "结果与任务目标偏离"
        
        return False, similarity, None
    
    def _semantic_similarity(self, text1, text2):
        """简化版语义相似度"""
        return SequenceMatcher(None, text1, text2).ratio()


# 使用示例
from harness.drift_detector import DriftDetector

detector = DriftDetector(threshold=0.6)

# 任务执行后检查
result = execute_task("爬取储能行业新闻")
is_drift, confidence, suggestion = detector.check(
    task_description="爬取储能行业新闻",
    actual_result=result,
    expected_keywords=["储能", "新闻", "标题"]
)

if is_drift:
    print(f"⚠️ 检测到漂移 (置信度: {confidence:.2f})")
    print(f"建议: {suggestion}")
    # 自动重试或通知用户
```

### 集成到现有流程

修改 `self_healing_harness.py`，在执行后增加漂移检测步骤。

---

## 二、并行执行 (Parallel Spawn)

### 实现原理
利用 Python asyncio 或 threading 同时启动多个子任务

### 代码实现

```python
# harness/parallel_runner.py
import asyncio
import concurrent.futures
from typing import List, Dict, Any
import json

class ParallelRunner:
    """并行执行多个子任务"""
    
    def __init__(self, max_workers=5):
        self.max_workers = max_workers
    
    async def run_parallel(self, tasks: List[Dict]) -> List[Any]:
        """
        并行执行多个任务
        
        Args:
            tasks: [
                {"agent": "crawler", "task": "爬取A站点", "timeout": 300},
                {"agent": "crawler", "task": "爬取B站点", "timeout": 300},
                ...
            ]
        
        Returns:
            results: 每个任务的结果列表
        """
        # 创建异步任务
        async_tasks = [
            self._run_single_task(t) for t in tasks
        ]
        
        # 并行执行，等待全部完成
        results = await asyncio.gather(*async_tasks, return_exceptions=True)
        
        # 处理异常
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    "status": "failed",
                    "task": tasks[i],
                    "error": str(result)
                })
            else:
                processed_results.append({
                    "status": "success",
                    "task": tasks[i],
                    "result": result
                })
        
        return processed_results
    
    async def _run_single_task(self, task_config: Dict) -> Any:
        """执行单个子任务"""
        # 调用 OpenClaw 的 sessions_spawn
        # 这里需要封装成异步调用
        loop = asyncio.get_event_loop()
        
        result = await loop.run_in_executor(
            None,  # 使用默认线程池
            self._sync_spawn,
            task_config
        )
        
        return result
    
    def _sync_spawn(self, task_config: Dict) -> Any:
        """同步调用 sessions_spawn"""
        # 实际调用 OpenClaw API
        import subprocess
        import json
        
        cmd = [
            "openclaw", "sessions", "spawn",
            "--agent", task_config.get("agent", "default"),
            "--task", task_config["task"],
            "--timeout", str(task_config.get("timeout", 300))
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        return json.loads(result.stdout)


# 简化版 - 使用线程池
from concurrent.futures import ThreadPoolExecutor, as_completed

def parallel_spawn(tasks: List[Dict], max_workers=5) -> List[Any]:
    """
    并行执行多个子任务
    
    使用示例:
    tasks = [
        {"agent": "crawler", "task": "爬取北极星储能网"},
        {"agent": "crawler", "task": "爬取储能中国"},
        {"agent": "crawler", "task": "爬取OFweek储能"},
    ]
    results = parallel_spawn(tasks, max_workers=3)
    """
    results = [None] * len(tasks)
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任务
        future_to_index = {
            executor.submit(sessions_spawn_sync, task): i 
            for i, task in enumerate(tasks)
        }
        
        # 收集结果
        for future in as_completed(future_to_index):
            index = future_to_index[future]
            try:
                results[index] = future.result()
            except Exception as e:
                results[index] = {"error": str(e), "task": tasks[index]}
    
    return results


def sessions_spawn_sync(task_config: Dict) -> Any:
    """同步版本的 sessions_spawn"""
    # 这里调用实际的 OpenClaw API
    # 简化示意
    pass
```

### 使用示例

```python
# 并行爬取多个网站
tasks = [
    {"agent": "crawler", "task": "爬取北极星储能网", "timeout": 120},
    {"agent": "crawler", "task": "爬取储能中国", "timeout": 120},
    {"agent": "crawler", "task": "爬取OFweek储能", "timeout": 120},
    {"agent": "crawler", "task": "爬取高工储能", "timeout": 120},
]

# 原来需要 4×2 = 8 分钟，现在只需要 2 分钟
results = parallel_spawn(tasks, max_workers=4)
```

---

## 三、自动任务拆解 (Auto Decomposition)

### 实现原理
用 LLM 评估任务复杂度，自动拆解为子任务

### 代码实现

```python
# harness/task_decomposer.py
import json
from typing import List, Dict

class TaskDecomposer:
    """自动任务拆解器"""
    
    COMPLEXITY_PROMPT = """
分析以下任务的复杂度，判断是否需要拆解为子任务。

任务: {task}

评估维度:
1. 步骤数量: 是否需要多步骤完成？
2. 工具调用: 是否需要多种工具？
3. 时间估计: 预计执行时间超过5分钟？
4. 失败风险: 是否存在多个可能的失败点？

输出JSON格式:
{{
    "complexity": "simple|medium|complex",
    "need_decompose": true|false,
    "reason": "拆解原因",
    "subtasks": [
        {{
            "id": "1",
            "description": "子任务描述",
            "agent": "使用的agent",
            "dependencies": [],  # 依赖的前置任务id
            "estimated_time": 120  # 预计秒数
        }}
    ]
}}
"""
    
    def __init__(self):
        self.min_complexity_threshold = "medium"  # 超过此复杂度需要拆解
    
    def analyze(self, task: str) -> Dict:
        """
        分析任务，决定是否需要拆解
        
        Returns:
            {
                "need_decompose": bool,
                "subtasks": List[Dict],
                "execution_plan": str
            }
        """
        # 简单规则判断（无需LLM）
        quick_check = self._quick_complexity_check(task)
        
        if quick_check == "simple":
            return {
                "need_decompose": False,
                "subtasks": [{"description": task}],
                "reason": "简单任务，直接执行"
            }
        
        # 复杂任务，使用LLM拆解
        return self._llm_decompose(task)
    
    def _quick_complexity_check(self, task: str) -> str:
        """快速复杂度检查"""
        indicators = {
            "simple": ["查询", "查看", "简单", "单个"],
            "complex": ["分析", "生成", "并", "和", "同时", "全流程", "系统"]
        }
        
        task_lower = task.lower()
        
        # 复杂指标匹配
        if any(kw in task_lower for kw in indicators["complex"]):
            return "complex"
        
        # 简单指标匹配
        if any(kw in task_lower for kw in indicators["simple"]):
            return "simple"
        
        return "medium"
    
    def _llm_decompose(self, task: str) -> Dict:
        """使用LLM拆解任务"""
        # 这里调用 LLM API 进行分析
        # 简化示意
        
        # 储能报告生成的示例拆解
        if "储能" in task and ("报告" in task or "分析" in task):
            return {
                "need_decompose": True,
                "reason": "任务涉及数据收集、分析、报告生成多个环节",
                "subtasks": [
                    {
                        "id": "1",
                        "description": "收集储能行业数据（爬虫+API）",
                        "agent": "crawler",
                        "dependencies": [],
                        "estimated_time": 180
                    },
                    {
                        "id": "2",
                        "description": "分析数据并提取关键信息",
                        "agent": "analyzer",
                        "dependencies": ["1"],
                        "estimated_time": 120
                    },
                    {
                        "id": "3",
                        "description": "生成分析报告",
                        "agent": "reporter",
                        "dependencies": ["2"],
                        "estimated_time": 180
                    }
                ]
            }
        
        # 默认不拆解
        return {
            "need_decompose": False,
            "subtasks": [{"description": task}],
            "reason": "未识别为复杂任务"
        }
    
    def execute_with_auto_decompose(self, task: str) -> Any:
        """
        自动拆解并执行任务
        
        这是对外提供的主接口
        """
        analysis = self.analyze(task)
        
        if not analysis["need_decompose"]:
            # 简单任务，直接执行
            return self._execute_single(task)
        
        # 复杂任务，拆解后并行/串行执行
        subtasks = analysis["subtasks"]
        
        # 按依赖关系排序
        sorted_tasks = self._sort_by_dependencies(subtasks)
        
        # 执行并收集结果
        results = self._execute_subtasks(sorted_tasks)
        
        return {
            "status": "completed",
            "task": task,
            "decomposition": analysis,
            "results": results
        }
    
    def _sort_by_dependencies(self, subtasks: List[Dict]) -> List[Dict]:
        """按依赖关系排序子任务"""
        # 拓扑排序实现
        # 简化版：假设依赖是线性的
        return sorted(subtasks, key=lambda x: int(x["id"]))
    
    def _execute_subtasks(self, subtasks: List[Dict]) -> List[Any]:
        """执行子任务列表"""
        results = []
        
        for subtask in subtasks:
            # 检查依赖是否完成
            deps = subtask.get("dependencies", [])
            # ... 检查逻辑
            
            # 执行子任务
            result = self._execute_single(subtask["description"])
            results.append(result)
        
        return results
    
    def _execute_single(self, task: str) -> Any:
        """执行单个子任务"""
        # 调用 OpenClaw 执行
        pass


# 使用示例
decomposer = TaskDecomposer()

# 自动判断并执行
result = decomposer.execute_with_auto_decompose(
    "帮我分析今天的储能行业动态并生成报告"
)

# 输出:
# {
#   "status": "completed",
#   "task": "帮我分析今天的储能行业动态并生成报告",
#   "decomposition": {
#     "need_decompose": True,
#     "reason": "任务涉及数据收集、分析、报告生成多个环节",
#     "subtasks": [...]
#   },
#   "results": [...]
# }
```

---

## 四、整合方案

### 三层架构整合

```python
# harness/harness_v4.py

class HarnessV4:
    """
    整合三项改进的 Harness v4
    """
    
    def __init__(self):
        self.decomposer = TaskDecomposer()
        self.parallel_runner = ParallelRunner()
        self.drift_detector = DriftDetector()
    
    async def execute(self, task: str) -> Any:
        """
        完整执行流程：
        1. 自动拆解
        2. 并行执行
        3. 漂移检测
        """
        # 1. 自动拆解
        analysis = self.decomposer.analyze(task)
        
        if not analysis["need_decompose"]:
            return await self._execute_single(task)
        
        # 2. 并行执行子任务
        subtasks = analysis["subtasks"]
        results = await self.parallel_runner.run_parallel(subtasks)
        
        # 3. 汇总结果并检测漂移
        final_result = self._aggregate_results(results)
        
        is_drift, confidence, suggestion = self.drift_detector.check(
            task_description=task,
            actual_result=final_result
        )
        
        if is_drift:
            # 自动修复或通知
            return await self._handle_drift(task, final_result, suggestion)
        
        return final_result
```

---

## 五、实施建议

### 第一阶段（本周）：漂移检测
- 风险最低，改进效果明显
- 可以在现有 `self_healing_harness.py` 中直接集成

### 第二阶段（下周）：并行执行
- 提升多站点爬虫效率（4倍提升）
- 需要先封装 `sessions_spawn` 的异步调用

### 第三阶段（下下周）：自动拆解
- 最复杂的改进
- 需要设计好任务依赖关系图
- 可以从简单的规则判断开始，逐步引入LLM

### 预估收益

| 改进项 | 效率提升 | 稳定性提升 | 实施难度 |
|--------|----------|------------|----------|
| 漂移检测 | - | ⭐⭐⭐⭐⭐ | ⭐⭐ |
| 并行执行 | ⭐⭐⭐⭐⭐ | - | ⭐⭐⭐ |
| 自动拆解 | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |

**建议启动顺序**: 漂移检测 → 并行执行 → 自动拆解

要从哪一项开始？
