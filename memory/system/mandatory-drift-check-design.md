# 任务执行后强制审查机制设计

> 确保每次任务完成后强制执行漂移检测验证

---

## 一、强制审查架构

```
┌─────────────────────────────────────────────────────────────┐
│  任务执行 (Agent/Task)                                       │
└─────────────────────────────────────────────────────────────┘
                              ↓ 强制触发
┌─────────────────────────────────────────────────────────────┐
│  漂移检测 (Drift Detection) - 不可跳过                      │
│  ├─ 关键词检测                                              │
│  ├─ 语义偏离检测                                            │
│  └─ 格式检测                                                │
└─────────────────────────────────────────────────────────────┘
                              ↓ 自动路由
┌─────────────────────────────────────────────────────────────┐
│  结果处理                                                    │
│  ├─ 通过 → 记录日志 → 继续下一步                            │
│  └─ 漂移 → 触发修复 → 通知人工                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 二、四层强制保障机制

### 第1层：配置强制 (Configuration Enforcement)

```yaml
# harness_config.yaml
drift_detection:
  # 强制启用，不可禁用
  enabled: true
  enforce_mode: "strict"  # strict|warn|off
  
  # 跳过后果
  skip_penalty:
    log_level: "error"
    alert_channels: ["wechat", "email"]
    block_task: true  # 检测到漂移时阻止任务继续
  
  # 强制审查清单
  mandatory_checks:
    - keyword      # 必须检查关键词
    - semantic     # 必须检查语义
    - format       # 如有格式要求必须检查
```

### 第2层：代码强制 (Code Enforcement)

```python
# harness/agent_runner.py

class AgentRunner:
    def execute_workflow(self, workflow_name: str, **params) -> TaskResult:
        """
        执行工作流 - 强制漂移检测版本
        """
        # ... 前面代码 ...
        
        for step in steps:
            # 执行步骤
            result = self._execute_step(step, **params)
            
            # ===== 强制漂移检测 =====
            # 1. 无法跳过的检测
            drift_result = self._mandatory_drift_check(
                step=step,
                result=result,
                workflow_name=workflow_name
            )
            
            # 2. 检测结果强制处理
            if drift_result.is_drift:
                # 强制记录
                self._force_record_drift(drift_result)
                
                # 根据严重程度强制处理
                if drift_result.confidence > 0.8:
                    # 高置信度漂移：强制阻断
                    result = self._force_block_and_alert(
                        step, drift_result
                    )
                else:
                    # 低置信度漂移：强制修复尝试
                    result = self._force_retry_with_correction(
                        step, drift_result
                    )
            
            # 3. 强制验证检测已执行
            self._verify_drift_check_executed(step, drift_result)
        
        return result
    
    def _mandatory_drift_check(self, step, result, workflow_name):
        """强制漂移检测 - 不可跳过"""
        # 即使配置了禁用，严格模式下仍然执行
        return self.drift_detector.check(
            task_description=step.get('description', ''),
            actual_result=str(result.get('output', '')),
            expected_keywords=self._get_mandatory_keywords(workflow_name),
            expected_format=step.get('expected_format'),
            check_types=["keyword", "semantic", "format"]  # 强制全量检测
        )
```

### 第3层：流程强制 (Process Enforcement)

```python
# harness/task_executor.py

class MandatoryTaskExecutor:
    """
    强制审查任务执行器
    包装所有任务执行，确保漂移检测
    """
    
    def execute(self, task_func, *args, **kwargs):
        """
        执行任务并强制审查
        """
        # 1. 前置检查：确认漂移检测器可用
        if not self.drift_detector.enabled:
            raise RuntimeError(
                "漂移检测未启用，任务无法执行。"
                "请在 harness_config.yaml 中启用 drift_detection.enabled"
            )
        
        # 2. 执行任务
        result = task_func(*args, **kwargs)
        
        # 3. 强制漂移检测
        drift_check = self._perform_mandatory_check(
            task_name=task_func.__name__,
            result=result
        )
        
        # 4. 强制结果验证
        if not drift_check:
            raise TaskValidationError("漂移检测未返回结果，任务终止")
        
        # 5. 漂移处理
        if drift_check.is_drift:
            result = self._handle_mandatory_drift(
                result, drift_check
            )
        
        # 6. 强制审计记录
        self._create_audit_record(task_func, result, drift_check)
        
        return result
```

### 第4层：监控强制 (Monitoring Enforcement)

```python
# harness/drift_monitor.py

class DriftMonitor:
    """
    漂移检测监控器
    确保每次检测都被记录和审查
    """
    
    def __init__(self):
        self.unverified_tasks = set()  # 未验证任务跟踪
    
    def register_task(self, task_id: str):
        """注册任务，等待验证"""
        self.unverified_tasks.add(task_id)
    
    def verify_check_completed(self, task_id: str, drift_result: DriftCheckResult):
        """验证检测已完成"""
        if task_id in self.unverified_tasks:
            self.unverified_tasks.remove(task_id)
        
        # 记录到不可篡改的日志
        self._append_to_audit_log({
            'task_id': task_id,
            'timestamp': datetime.now().isoformat(),
            'drift_detected': drift_result.is_drift,
            'confidence': drift_result.confidence,
            'check_type': drift_result.check_type,
            'verified': True  # 已验证标记
        })
    
    def scan_unverified_tasks(self):
        """扫描未验证任务（定时任务）"""
        for task_id in self.unverified_tasks:
            # 发送告警
            self.alert_system.send(
                level="critical",
                message=f"任务 {task_id} 未完成漂移检测验证！"
            )
            
            # 自动补救：强制重新检测
            self.force_recheck(task_id)
```

---

## 三、自动化审查流水线

### 1. 实时审查 (Real-time Review)

```python
# 每次任务执行时的实时审查
class RealTimeReviewer:
    def review(self, drift_result: DriftCheckResult):
        review_record = {
            'timestamp': datetime.now().isoformat(),
            'result': drift_result.to_dict(),
            'action_taken': None,
            'reviewer': 'system'
        }
        
        if drift_result.is_drift:
            # 自动决定处理方式
            if drift_result.confidence > 0.9:
                review_record['action_taken'] = 'auto_reject'
                review_record['escalation'] = 'human_required'
            elif drift_result.confidence > 0.7:
                review_record['action_taken'] = 'auto_retry'
            else:
                review_record['action_taken'] = 'log_and_continue'
        
        # 保存审查记录
        self.save_review(review_record)
        return review_record
```

### 2. 批量审查 (Batch Review)

```python
# 定时批量审查所有漂移记录
class BatchReviewer:
    def daily_review(self):
        """每日审查所有漂移记录"""
        yesterday_records = self.get_records_since(
            datetime.now() - timedelta(days=1)
        )
        
        review_report = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'total_checks': len(yesterday_records),
            'drift_count': sum(1 for r in yesterday_records if r['is_drift']),
            'high_confidence_drifts': [],
            'trends': self.analyze_trends(yesterday_records),
            'recommendations': []
        }
        
        # 生成建议
        if review_report['drift_rate'] > 0.3:
            review_report['recommendations'].append(
                "漂移率过高，建议检查提示词质量"
            )
        
        # 发送审查报告
        self.send_report(review_report)
```

### 3. 强制修复流程 (Mandatory Fix Flow)

```
检测到漂移
    ↓
置信度评估
    ├─ > 0.9: 强制阻断 + 立即人工介入
    ├─ 0.7-0.9: 强制自动修复(最多2次)
    └─ < 0.7: 记录日志 + 标记观察
    ↓
修复尝试
    ↓
修复后强制重新检测
    ↓
验证通过? 
    ├─ 是: 继续任务
    └─ 否: 升级人工处理
```

---

## 四、不可跳过机制

### 代码层面防止跳过

```python
# 使用装饰器强制检测
from functools import wraps

def mandatory_drift_check(expected_keywords=None, expected_format=None):
    """强制漂移检测装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 执行任务
            result = func(*args, **kwargs)
            
            # 强制检测 - 无法通过参数跳过
            detector = DriftDetector()
            drift_result = detector.check(
                task_description=func.__doc__ or func.__name__,
                actual_result=str(result),
                expected_keywords=expected_keywords,
                expected_format=expected_format
            )
            
            # 附加检测结果到返回值
            if isinstance(result, dict):
                result['_drift_check'] = drift_result.to_dict()
            
            return result
        return wrapper
    return decorator

# 使用示例
@mandatory_drift_check(
    expected_keywords=["储能", "市场", "技术"],
    expected_format="markdown"
)
def generate_daily_report():
    """生成储能行业日报"""
    # ... 生成逻辑 ...
    return report_content
```

### 审计追踪

```python
# 所有检测结果写入不可篡改的审计日志
class AuditLogger:
    def log_drift_check(self, task_id, drift_result):
        record = {
            'task_id': task_id,
            'timestamp': datetime.now().isoformat(),
            'drift_hash': self._hash_drift_result(drift_result),
            'signature': self._sign_record(record),  # 数字签名防篡改
        }
        
        # 写入只追加日志文件
        with open('drift_audit.log', 'a') as f:
            f.write(json.dumps(record) + '\n')
```

---

## 五、实施建议

### 第一阶段：立即可做（今天）

1. **修改 agent_runner.py**
   - 移除 `enabled` 检查，改为强制启用
   - 在 `execute_workflow` 中强制调用漂移检测

2. **添加不可跳过的装饰器**
   - 为所有关键任务函数添加 `@mandatory_drift_check`

3. **配置告警**
   - 检测到漂移时立即发送企微/邮件通知

### 第二阶段：本周完成

1. **实施自动修复流程**
   - 根据置信度自动决定处理方式

2. **建立审计日志**
   - 所有检测结果记录到只追加日志

3. **定时审查任务**
   - 每日生成漂移检测报告

### 第三阶段：下周完成

1. **监控仪表盘**
   - 可视化展示漂移趋势

2. **质量门禁**
   - 漂移率超过阈值时阻止部署

---

## 六、配置示例

```yaml
# harness_config.yaml - 强制审查配置
drift_detection:
  enabled: true
  enforce_mode: "strict"  # strict = 不可跳过
  
  mandatory_checks:
    all_tasks: true       # 所有任务都检测
    skip_allowed: false   # 不允许跳过
  
  auto_fix:
    enabled: true
    max_retries: 2
    confidence_threshold: 0.7
  
  escalation:
    high_confidence:      # > 0.9
      action: block_and_alert
      channels: [wechat, email]
    medium_confidence:    # 0.7-0.9
      action: auto_retry
      notify: true
    low_confidence:       # < 0.7
      action: log_only
  
  audit:
    enabled: true
    log_file: "drift_audit.log"
    daily_report: true
    report_time: "09:00"
```

---

**下一步**: 要我立即实施第一层和第二层的强制机制吗？
