# Harness Engineering for Energy Storage Monitoring
# 储能监控系统的驾驭工程架构

> **"人类掌舵，智能体执行"** —— Humans steer. Agents execute.

## 什么是 Harness Engineering？

**Harness Engineering（驾驭工程）** 是 OpenAI 在 2026年2月提出的 AI 软件开发新范式。

核心理念：**把 AI 当作一匹烈马，工程师建造"缰绳"（约束）和"跑道"（护栏）来驾驭它。**

### OpenAI 实验结果

| 指标 | 数值 |
|------|------|
| 团队规模 | 3人 → 7人 |
| 开发周期 | 5个月 |
| 代码量 | 100万行 |
| 手写代码 | **0行** |
| 效率提升 | **10倍** |

---

## 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                    Harness Architecture                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  Guardrails  │  │   Feedback   │  │ Progressive  │     │
│  │   (护栏)      │  │    Loop      │  │  Disclosure  │     │
│  │              │  │  (反馈循环)   │  │ (渐进式披露)  │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
│         │                  │                  │            │
│         └──────────────────┼──────────────────┘            │
│                            │                               │
│                    ┌───────┴───────┐                       │
│                    │  Agent Runner │                       │
│                    │   (执行器)     │                       │
│                    └───────┬───────┘                       │
│                            │                               │
│         ┌──────────────────┼──────────────────┐            │
│         ▼                  ▼                  ▼            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │Daily Report  │  │Crawler Monitor│  │Self Healing │     │
│  │   日报生成    │  │   爬虫监控    │  │   自愈系统   │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 核心组件

### 1. Guardrails（护栏）

**作用**：硬性约束，Agent 不可违背

```python
# 飞行前检查示例
passed, results = guardrails.pre_flight_check(data_dir)

# 检查项：
# - 数据量是否足够（爬虫≥20条，新闻≥10条）
# - 股票数据是否更新
# - 报告格式是否正确（必须包含4个章节）
# - 执行时间是否超时
```

**配置位置**：`harness_config.yaml` → `components.deterministic_constraints`

---

### 2. Feedback Loop（反馈循环）

**作用**：错误自动检测 → 分类 → 修复 → 记录 → 防止再犯

```python
# 错误处理流程
result = feedback.process_error(
    code="E001",
    message="爬虫数据不足",
    context={'date': '2026-03-21'}
)

# 结果：
# - 自动修复：重试爬虫
# - 记录错误：更新 learned_rules.json
# - 防止再犯：下次遇到自动处理
```

**错误类型库**：`harness_config.yaml` → `error_library`

---

### 3. Progressive Disclosure（渐进式披露）

**作用**：根据任务复杂度分层加载上下文

| 层级 | 任务类型 | 加载内容 |
|------|---------|---------|
| **SIMPLE** | 单日报生成 | 当日数据 + 基础模板 |
| **COMPLEX** | 周报生成 | 7天数据 + 历史对比 + 趋势分析 |
| **DIAGNOSTIC** | 异常处理 | 日志 + 错误历史 + 修复方案库 |

```python
# 加载上下文
context = context_loader.load_context('daily_report')
# 结果：Context(level=SIMPLE, sources=[...], data={...})
```

---

## 工作流定义

### 日报生成工作流

```yaml
workflow: daily_report
steps:
  1. pre_flight_check      # 数据质量检查（Guardrails）
  2. load_context          # 加载当日数据（Progressive Disclosure）
  3. generate_report       # Agent生成报告（Agent Executor）
  4. validate_output       # 输出格式验证（Guardrails）
  5. deliver               # 邮件发送（Delivery）
  6. feedback              # 记录执行结果（Feedback Loop）
```

### 爬虫监控工作流

```yaml
workflow: crawler_monitor
steps:
  1. check_health          # 检查爬虫状态（Application Legibility）
  2. diagnose              # 如失败，加载诊断上下文
  3. repair                # 自动修复或通知人工（Feedback Loop）
```

### 自愈系统工作流

```yaml
workflow: self_healing
steps:
  1. scan                  # 扫描系统状态
  2. detect_anomaly        # 异常检测（Guardrails）
  3. classify_issue        # 问题分类（Feedback Loop）
  4. auto_repair           # 自动修复
  5. update_rules          # 更新约束规则
```

---

## 使用方法

### 基础用法

```python
from harness.agent_runner import AgentRunner

# 初始化
runner = AgentRunner()

# 运行日报工作流
result = runner.run_daily_report()
print(f"Success: {result.success}")
print(f"Duration: {result.duration_seconds}s")

# 运行爬虫监控
result = runner.run_crawler_monitor()

# 运行自愈系统
result = runner.run_self_healing()
```

### 高级用法

```python
# 自定义工作流
result = runner.execute_workflow('daily_report', date='20260321')

# 检查系统健康
health = runner.get_system_health()
```

---

## 文件结构

```
harness/
├── README.md                    # 本文件
├── harness_config.yaml          # 主配置文件
├── guardrails.py               # 护栏系统
├── feedback_loop.py            # 反馈循环
├── progressive_context.py      # 渐进式披露
├── agent_runner.py             # Agent执行器
├── error_log.jsonl             # 错误日志（自动生成）
├── learned_rules.json          # 学习到的规则（自动生成）
├── templates/                  # 报告模板
│   ├── daily_report.md
│   └── weekly_report.md
└── manuals/                    # 修复手册
    ├── crawler.json
    └── sync.json
```

---

## 关键公式

> **自主权 = f(背压)**

约束和反馈越完善，能给 AI 的自主权越大。

---

## 三层工程范式演进

```
2024: Prompt Engineering (提示词工程)
       ↓ 怎么跟AI说话
       
2025: Context Engineering (上下文工程)
       ↓ 给AI看什么
       
2026: Harness Engineering (驾驭工程)
       ↓ 怎么让AI可靠工作
```

**关系**：Harness ⊃ Context ⊃ Prompt

---

## 性能目标

| 指标 | 目标 |
|------|------|
| 成功率 | ≥ 95% |
| 平均延迟 | ≤ 300s |
| 自动修复率 | ≥ 80% |
| 人工干预率 | ≤ 5% |

---

## 参考文献

- [OpenAI Blog: Harness engineering](https://openai.com/index/harness-engineering/)
- Martin Fowler: Exploring Generative AI
- Mitchell Hashimoto (HashiCorp)

---

**创建时间**: 2026-03-21  
**版本**: 1.0  
**作者**: AI Assistant
