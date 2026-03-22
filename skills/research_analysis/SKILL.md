# research_analysis

专业研报分析框架 SKILL

提供标准化的行业研究分析方法，包括 MECE 分类、SWOT 分析、产业链梳理、事件影响评估等专业工具。

---

## 适用范围

- 行业日报/周报/月报生成
- 市场动态分析
- 政策影响评估
- 技术趋势追踪
- 企业动态监测

---

## 核心方法论

### 1. MECE 分析法
Mutually Exclusive, Collectively Exhaustive（相互独立，完全穷尽）

确保分析维度不重叠、不遗漏。

### 2. SWOT 分析
- **S**trengths（优势）
- **W**eaknesses（劣势）
- **O**pportunities（机会）
- **T**hreats（威胁）

### 3. 波特五力模型
- 现有竞争者
- 潜在进入者
- 替代品威胁
- 上游议价能力
- 下游议价能力

### 4. 产业链分析
上游 → 中游 → 下游的全链条梳理

### 5. 事件影响评估矩阵
基于影响程度和时间紧迫性进行优先级排序

---

## 使用方法

### 热点提炼（日报）

```python
from skills.research_analysis.frameworks.mece import MECEAnalyzer
from skills.research_analysis.frameworks.impact_matrix import ImpactMatrix

# 分析当日资讯
analyzer = MECEAnalyzer(industry="储能")
top3 = analyzer.extract_hotspots(news_list, top_n=3)

# 评估影响
matrix = ImpactMatrix()
for hotspot in top3:
    score = matrix.assess(hotspot)
    hotspot['impact_score'] = score
```

### SWOT 速览生成

```python
from skills.research_analysis.frameworks.swot import SWOTGenerator

swot = SWOTGenerator(industry="储能")
analysis = swot.generate(news_list, market_data)
```

### 产业链分析

```python
from skills.research_analysis.frameworks.industry_chain import IndustryChain

chain = IndustryChain()
updates = chain.track_updates(news_list)
```

---

## 输出模板

### 日报热点模板
见 `templates/daily_top3.md`

### 周报趋势模板
见 `templates/trend_week.md`

### 数据追踪模板
见 `templates/data_tracker.md`

---

## 行业适配

当前已适配：
- ✅ 储能行业
- 🔄 可扩展至其他行业

---

## 更新记录

| 日期 | 版本 | 更新内容 |
|------|------|---------|
| 2026-03-22 | 1.0.0 | 初始版本，基于专业研报框架创建 |

---

**参考框架**：
- 麦肯锡 MECE 分析法
- 波特五力模型
- SWOT 分析模型
- 产业链价值分析
