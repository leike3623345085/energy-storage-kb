# 记忆系统架构 v2 - OpenViking 分层方案

> 实施时间：2026-03-28
> 参考：OpenViking 三层记忆加载思想

---

## 核心改进

### 1. 三层摘要体系 (L0/L1/L2)

```
用户提问
    ↓
L0 快速判断 ───────────────────────┐
    ↓ 筛选出相关记忆                 │
L1 概览加载 ───────────────┐       │
    ↓ 确认相关后加载          │       │
L2 完整内容 ←───────────────┘       │
    ↓                               │
生成回答 ←──────────────────────────┘
```

| 层级 | 内容 | Token 数 | 用途 |
|------|------|----------|------|
| **L0** | 一句话摘要 | ~100 | 快速判断相关性 |
| **L1** | 章节概览 + 关键点 | ~2,000 | 规划阶段决策 |
| **L2** | 原始完整内容 | 按需 | 深入分析时读取 |

---

### 2. 目录语义边界

```
memory/
├── 2026-03-28.md           # 每日日志（原始素材）
├── system/                 # 项目专属技术
│   ├── energy-storage.md   # 储能系统
│   └── bank-workflow.md    # 银行工作流
├── lessons/                # 经验教训
│   └── energy-storage.md   # 储能问题记录
├── auto/                   # 自动归档
│   └── 2026-03-28_auto.md
└── index/                  # 【新增】分层索引
    └── memory_index.json   # L0/L1 摘要索引
```

**语义边界原则**：
- 同一目录下的内容通常相关
- 按项目/主题分层组织
- 目录名即语义标签

---

### 3. 检索审计系统

```
每次检索
    ↓
生成唯一ID (retrieval_id)
    ↓
记录：查询词、结果列表、时间戳
    ↓
保存到 retrieval_audit.jsonl
```

**用途**：
- 出了问题回放检索轨迹
- 分析哪些记忆经常被访问
- 优化搜索结果排序

---

## 新文件说明

| 文件 | 功能 | 更新频率 |
|------|------|----------|
| `summarizer.py` | 生成 L0/L1 摘要 | 每天 9:30 (cron) |
| `retrieval_audit.py` | 检索审计日志 | 每次检索时 |
| `context_loader.py` | 会话启动记忆回顾 | 每次会话 |
| `index/memory_index.json` | 分层索引存储 | 每天更新 |

---

## 使用示例

### 快速搜索（L0 层）
```bash
cd memory && python3 summarizer.py search 储能
```

### 智能分层搜索（L0→L1）
```python
from context_loader import smart_memory_search

result = smart_memory_search("储能配置", user_context="用户询问储能系统配置")
# 返回：检索ID + L1 详细摘要
```

### 查看检索审计
```bash
# 最近5次检索
cd memory && python3 retrieval_audit.py recent 5

# 查看具体检索轨迹
cd memory && python3 retrieval_audit.py trace 048041f0

# 检索统计
cd memory && python3 retrieval_audit.py stats
```

---

## 与 Harness 架构的关系

```
Harness Architecture
┌─────────────────────────────────────┐
│  Progressive Disclosure              │
│  (渐进式披露)                        │
│      ↓ 使用 OpenViking 三层加载      │
│  SIMPLE → COMPLEX → DIAGNOSTIC      │
│      ↓                              │
│  L0摘要 → L1概览 → L2完整           │
└─────────────────────────────────────┘
```

---

## 性能提升预期

| 指标 | 改进前 | 改进后 | 提升 |
|------|--------|--------|------|
| 记忆检索速度 | 全文搜索 | L0 快速筛选 | 5-10x |
| 上下文相关性 | 靠关键词 | 分层判断 | 更精准 |
| 问题可追溯性 | 无 | 检索审计 | 可回放 |
| 存储效率 | 原始文本 | L0+L1 索引 | 节省 80%+ |

---

## 下一步可优化

1. **向量相似度**：将 L0 摘要向量化，支持语义搜索
2. **记忆过期**：根据访问频率自动归档冷记忆
3. **用户画像**：区分静态事实 vs 动态上下文

---

_最后更新：2026-03-28_
