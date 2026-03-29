#!/usr/bin/env python3
"""
XML 提示格式化系统 v2 - 优化版 (XML Prompt Formatter v2)
==========================================================

优化点:
1. 智能内容分类 - 自动将新闻归类到不同章节
2. 模板继承 - 支持日报/周报/深度分析等不同模板
3. 元数据增强 - 提取关键词、情感分析、重要性评分
4. XML 验证 - 确保生成的 XML 格式正确
5. 提示压缩 - 超长内容自动摘要
"""

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime
from pathlib import Path
import json
import re
import hashlib


@dataclass
class NewsAnalysis:
    """新闻分析结果"""
    category: str
    keywords: List[str]
    sentiment: str  # positive/negative/neutral
    importance: int  # 1-100
    entities: List[str]  # 公司/机构名
    is_hot: bool


@dataclass
class TaskConstraint:
    """任务约束"""
    name: str
    value: Any
    required: bool = True
    validator: Optional[str] = None  # 验证规则


@dataclass
class TaskContext:
    """任务上下文"""
    source_data: List[Dict] = field(default_factory=list)
    date: str = ""
    history: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)
    analysis: Dict[str, NewsAnalysis] = field(default_factory=dict)


class NewsAnalyzer:
    """新闻内容分析器"""
    
    # 关键词词典
    CATEGORY_KEYWORDS = {
        "政策法规": ["政策", "法规", "标准", "规范", "规划", "指导意见", "通知", "办法"],
        "市场动态": ["招标", "中标", "市场", "价格", "装机", "容量", "MW", "GW", "亿元"],
        "项目进展": ["项目", "开工", "并网", "投运", "建成", "投产", "开工仪式"],
        "技术创新": ["技术", "电池", "创新", "突破", "研发", "专利", "固态", "钠离子", "液流"],
        "企业动态": ["企业", "公司", "合作", "签约", "战略", "投资", "融资", "宁德时代", "比亚迪"],
        "国际市场": ["海外", "国际", "出口", "进口", "国外", "欧洲", "美国", "日本"],
        "安全事故": ["事故", "爆炸", "起火", "安全", "召回", "隐患"]
    }
    
    COMPANY_NAMES = [
        "宁德时代", "比亚迪", "亿纬锂能", "国轩高科", "海辰储能", "中储国能",
        "中科海钠", "华为", "阳光电源", "科华数据", "中创新航", "蜂巢能源",
        "璞泰来", "贝特瑞", "南网储能", "国家电网"
    ]
    
    @classmethod
    def analyze(cls, news: Dict) -> NewsAnalysis:
        """分析单条新闻"""
        title = news.get("title", "")
        summary = news.get("summary", "")
        content = title + " " + summary
        
        # 分类
        category_scores = {}
        for cat, keywords in cls.CATEGORY_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in content)
            category_scores[cat] = score
        
        category = max(category_scores, key=category_scores.get)
        if category_scores[category] == 0:
            category = "其他"
        
        # 提取关键词
        keywords = []
        for cat_kws in cls.CATEGORY_KEYWORDS.values():
            for kw in cat_kws:
                if kw in content and kw not in keywords:
                    keywords.append(kw)
        keywords = keywords[:5]  # 最多5个
        
        # 情感分析
        positive_words = ["突破", "成功", "增长", "领先", "获奖", "利好", "支持"]
        negative_words = ["下降", "亏损", "事故", "爆炸", "起火", "召回", "下跌"]
        
        pos_count = sum(1 for w in positive_words if w in content)
        neg_count = sum(1 for w in negative_words if w in content)
        
        if pos_count > neg_count:
            sentiment = "positive"
        elif neg_count > pos_count:
            sentiment = "negative"
        else:
            sentiment = "neutral"
        
        # 重要性评分
        importance = 50  # 基础分
        if any(kw in content for kw in ["宁德时代", "比亚迪", "国家电网"]):
            importance += 20
        if any(kw in content for kw in ["GW", "亿元", "重大项目"]):
            importance += 15
        if "政策" in content or "标准" in content:
            importance += 10
        importance = min(100, importance)
        
        # 提取实体
        entities = [name for name in cls.COMPANY_NAMES if name in content]
        
        # 是否热点
        is_hot = importance >= 70 or category == "安全事故"
        
        return NewsAnalysis(
            category=category,
            keywords=keywords,
            sentiment=sentiment,
            importance=importance,
            entities=entities,
            is_hot=is_hot
        )
    
    @classmethod
    def analyze_batch(cls, news_list: List[Dict]) -> Tuple[Dict[str, NewsAnalysis], Dict]:
        """批量分析并返回统计"""
        analyses = {}
        for news in news_list:
            news_id = news.get("url", news.get("title", ""))[:50]
            analyses[news_id] = cls.analyze(news)
        
        # 统计
        stats = {
            "total": len(news_list),
            "by_category": {},
            "by_sentiment": {"positive": 0, "negative": 0, "neutral": 0},
            "hot_news": 0,
            "avg_importance": 0
        }
        
        total_importance = 0
        for analysis in analyses.values():
            stats["by_category"][analysis.category] = stats["by_category"].get(analysis.category, 0) + 1
            stats["by_sentiment"][analysis.sentiment] += 1
            if analysis.is_hot:
                stats["hot_news"] += 1
            total_importance += analysis.importance
        
        if analyses:
            stats["avg_importance"] = total_importance / len(analyses)
        
        return analyses, stats


class XMLPromptBuilder:
    """XML 提示构建器 v2"""
    
    def __init__(self, task_type: str = "daily_report", version: str = "2.0"):
        self.task_type = task_type
        self.version = version
        self.root = ET.Element("task")
        self.root.set("version", version)
        self.root.set("type", task_type)
        self.root.set("generated_at", datetime.now().isoformat())
        self.root.set("builder", "XMLPromptBuilder-v2")
    
    def add_objective(self, description: str, priority: str = "high", 
                     metrics: Optional[List[str]] = None):
        """添加任务目标（带评估指标）"""
        obj = ET.SubElement(self.root, "objective")
        obj.set("priority", priority)
        obj.text = description
        
        if metrics:
            metrics_elem = ET.SubElement(obj, "success_metrics")
            for m in metrics:
                metric = ET.SubElement(metrics_elem, "metric")
                metric.text = m
        
        return self
    
    def add_context(self, context: TaskContext, include_analysis: bool = True):
        """添加上下文信息（含智能分析）"""
        ctx = ET.SubElement(self.root, "context")
        
        # 数据分析
        if include_analysis and context.source_data:
            analyses, stats = NewsAnalyzer.analyze_batch(context.source_data)
            context.analysis = analyses
            
            # 分析摘要
            analysis_elem = ET.SubElement(ctx, "content_analysis")
            analysis_elem.set("total_items", str(stats["total"]))
            analysis_elem.set("hot_items", str(stats["hot_news"]))
            analysis_elem.set("avg_importance", f"{stats['avg_importance']:.1f}")
            
            # 分类分布
            cat_dist = ET.SubElement(analysis_elem, "category_distribution")
            for cat, count in sorted(stats["by_category"].items(), key=lambda x: -x[1]):
                cat_elem = ET.SubElement(cat_dist, "category")
                cat_elem.set("name", cat)
                cat_elem.set("count", str(count))
                cat_elem.set("percentage", f"{count/stats['total']*100:.1f}%")
            
            # 情感分布
            sent_dist = ET.SubElement(analysis_elem, "sentiment_distribution")
            for sent, count in stats["by_sentiment"].items():
                sent_elem = ET.SubElement(sent_dist, "sentiment")
                sent_elem.set("type", sent)
                sent_elem.set("count", str(count))
        
        # 数据源（按分类组织）
        if context.source_data:
            sources = ET.SubElement(ctx, "data_sources")
            sources.set("count", str(len(context.source_data)))
            
            # 按分类分组
            by_category = {}
            for item in context.source_data:
                item_id = item.get("url", item.get("title", ""))[:50]
                analysis = context.analysis.get(item_id)
                cat = analysis.category if analysis else "未分类"
                
                if cat not in by_category:
                    by_category[cat] = []
                by_category[cat].append((item, analysis))
            
            # 按分类输出
            for cat, items in sorted(by_category.items(), 
                                    key=lambda x: len(x[1]), reverse=True):
                cat_elem = ET.SubElement(sources, "category")
                cat_elem.set("name", cat)
                cat_elem.set("count", str(len(items)))
                
                # 每个分类只显示前 5 条
                for item, analysis in items[:5]:
                    src = ET.SubElement(cat_elem, "source")
                    src.set("title", item.get("title", "")[:60])
                    src.set("source_name", item.get("source", "未知"))
                    if analysis:
                        src.set("importance", str(analysis.importance))
                        src.set("sentiment", analysis.sentiment)
                        if analysis.entities:
                            src.set("entities", ", ".join(analysis.entities[:3]))
        
        # 日期
        if context.date:
            date_elem = ET.SubElement(ctx, "date")
            date_elem.text = context.date
        
        # 历史
        if context.history:
            hist = ET.SubElement(ctx, "history")
            for h in context.history[-3:]:
                item = ET.SubElement(hist, "item")
                item.text = h
        
        # 元数据
        if context.metadata:
            meta = ET.SubElement(ctx, "metadata")
            for k, v in context.metadata.items():
                m = ET.SubElement(meta, k)
                m.text = str(v)
        
        return self
    
    def add_constraints(self, constraints: List[TaskConstraint]):
        """添加约束条件（带验证规则）"""
        cons = ET.SubElement(self.root, "constraints")
        
        for c in constraints:
            elem = ET.SubElement(cons, "constraint")
            elem.set("name", c.name)
            elem.set("required", "true" if c.required else "false")
            if c.validator:
                elem.set("validator", c.validator)
            elem.text = str(c.value)
        
        return self
    
    def add_output_format(self, format_type: str, sections: List[Dict], 
                         style_guide: Optional[str] = None):
        """
        添加输出格式规范（增强版）
        
        sections: [{"name": "市场动态", "required": true, "max_items": 5}]
        """
        fmt = ET.SubElement(self.root, "output_format")
        fmt.set("type", format_type)
        
        # 必需的章节
        required = ET.SubElement(fmt, "required_sections")
        for section in sections:
            sec = ET.SubElement(required, "section")
            sec.set("name", section.get("name", ""))
            sec.set("required", "true" if section.get("required", True) else "false")
            if "max_items" in section:
                sec.set("max_items", str(section["max_items"]))
            if "min_items" in section:
                sec.set("min_items", str(section["min_items"]))
        
        # 风格指南
        if style_guide:
            style = ET.SubElement(fmt, "style_guide")
            style.text = style_guide
        
        return self
    
    def add_quality_criteria(self, criteria: Dict[str, Any]):
        """添加质量标准"""
        qc = ET.SubElement(self.root, "quality_criteria")
        
        for key, value in criteria.items():
            elem = ET.SubElement(qc, key)
            if isinstance(value, dict):
                for k, v in value.items():
                    sub = ET.SubElement(elem, k)
                    sub.text = str(v)
            else:
                elem.text = str(value)
        
        return self
    
    def add_examples(self, examples: List[Dict]):
        """添加示例（Few-shot）"""
        ex_elem = ET.SubElement(self.root, "examples")
        
        for ex in examples:
            example = ET.SubElement(ex_elem, "example")
            if "input" in ex:
                inp = ET.SubElement(example, "input")
                inp.text = ex["input"]
            if "output" in ex:
                out = ET.SubElement(example, "output")
                out.text = ex["output"]
        
        return self
    
    def build(self) -> str:
        """构建 XML 字符串"""
        ET.indent(self.root, space="  ")
        return ET.tostring(self.root, encoding="unicode")
    
    def validate(self) -> Tuple[bool, Optional[str]]:
        """验证 XML 格式"""
        try:
            xml_str = self.build()
            ET.fromstring(xml_str)
            return True, None
        except ET.ParseError as e:
            return False, str(e)
    
    def to_prompt(self, include_xml: bool = True, include_instructions: bool = True) -> str:
        """
        转换为可直接使用的提示文本
        
        Args:
            include_xml: 是否包含 XML 内容
            include_instructions: 是否包含系统指令
        """
        xml_str = self.build()
        
        # 验证 XML
        is_valid, error = self.validate()
        if not is_valid:
            return f"[XML 验证失败: {error}]\n\n{xml_str[:500]}"
        
        parts = []
        
        if include_instructions:
            parts.append("你是一位专业的储能行业分析师。请根据以下结构化任务描述生成高质量的行业日报。")
            parts.append("")
            parts.append("重要提示:")
            parts.append("- 严格遵循 XML 中定义的输出格式和章节要求")
            parts.append("- 基于提供的数据源，提炼关键信息")
            parts.append("- 确保内容准确、客观、专业")
            parts.append("")
        
        if include_xml:
            parts.append("```xml")
            parts.append(xml_str)
            parts.append("```")
        
        if include_instructions:
            parts.append("")
            parts.append("输出要求:")
            parts.append("1. 使用 Markdown 格式")
            parts.append("2. 每个章节内容充实，不要留空")
            parts.append("3. 关键数据和公司名加粗")
            parts.append("4. 添加适当的 emoji 增强可读性")
        
        return "\n".join(parts)
    
    def save(self, output_path: Path):
        """保存 XML 到文件"""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(self.build())


class DailyReportXMLTemplate:
    """日报生成的 XML 模板 v2"""
    
    @staticmethod
    def create(source_data: List[Dict], date: str, 
               data_stats: Dict = None) -> XMLPromptBuilder:
        """创建日报生成的 XML 提示"""
        
        builder = XMLPromptBuilder("daily_report", version="2.0")
        
        # 1. 任务目标
        builder.add_objective(
            description=f"基于 {len(source_data)} 条储能行业资讯，生成 {date} 的行业日报",
            priority="high",
            metrics=[
                "信息覆盖率 > 90%",
                "关键数据准确率 = 100%",
                "内容可读性评分 > 80/100"
            ]
        )
        
        # 2. 上下文（含智能分析）
        context = TaskContext(
            source_data=source_data,
            date=date,
            history=[],
            metadata={
                "total_items": len(source_data),
                "sources": list(set(item.get("source", "") for item in source_data)),
                "data_quality_score": data_stats.get("quality_score", 90) if data_stats else 90,
                "report_type": "daily",
                "target_audience": "储能行业从业者、投资者、政策制定者"
            }
        )
        builder.add_context(context, include_analysis=True)
        
        # 3. 约束条件
        constraints = [
            TaskConstraint("format", "markdown", True, "regex:^markdown|html|pdf$"),
            TaskConstraint("language", "中文", True),
            TaskConstraint("tone", "专业、客观、简洁", True),
            TaskConstraint("max_length", "4000", False, "range:1000-10000"),
            TaskConstraint("include_data_sources", "true", True),
            TaskConstraint("fact_check_required", "true", True),
        ]
        builder.add_constraints(constraints)
        
        # 4. 输出格式（增强版）
        sections = [
            {"name": "📊 市场动态", "required": True, "min_items": 3, "max_items": 8},
            {"name": "⚡ 技术进展", "required": True, "min_items": 2, "max_items": 6},
            {"name": "📜 政策动态", "required": True, "min_items": 2, "max_items": 5},
            {"name": "📈 行情数据", "required": False, "max_items": 3},
            {"name": "🔥 今日热点", "required": True, "min_items": 3, "max_items": 5},
            {"name": "📋 详细资讯", "required": True, "min_items": 10, "max_items": 20},
        ]
        builder.add_output_format(
            format_type="markdown",
            sections=sections,
            style_guide="""
使用 emoji 增强可读性
每个要点控制在 100 字以内
关键数据加粗 (**数据**)
公司名称加粗 (**公司名**)
添加原文链接引用
使用表格展示对比数据
            """.strip()
        )
        
        # 5. 质量标准
        builder.add_quality_criteria({
            "fact_accuracy": {"required": "true", "min_score": 0.95},
            "data_completeness": {"required_sections": 5, "tolerance": 1},
            "source_citation": {"required": "true", "format": "文末标注", "min_sources": 3},
            "readability": {"target_audience": "专业", "level": "高级"},
            "originality": {"plagiarism_threshold": "0%", "paraphrase_required": "true"}
        })
        
        # 6. 添加示例（Few-shot）
        examples = [
            {
                "input": "宁德时代发布新一代储能电池",
                "output": "**宁德时代**发布新一代储能电池，能量密度提升 **20%**，循环寿命超过 **12000 次**"
            },
            {
                "input": "菲律宾强制配建储能政策",
                "output": "**菲律宾**出台风光强制配建储能政策，配储比例不低于装机容量的 **20%**"
            }
        ]
        builder.add_examples(examples)
        
        return builder


class WeeklyReportXMLTemplate:
    """周报 XML 模板"""
    
    @staticmethod
    def create(weekly_data: List[Dict], week_range: str) -> XMLPromptBuilder:
        """创建周报 XML 提示"""
        builder = XMLPromptBuilder("weekly_report", version="2.0")
        
        builder.add_objective(
            description=f"生成 {week_range} 储能行业周报",
            priority="high",
            metrics=["周度趋势分析", "行业热点追踪", "数据对比"]
        )
        
        # 周报特有的章节
        sections = [
            {"name": "📈 本周概览", "required": True},
            {"name": "🔥 热点事件", "required": True, "max_items": 10},
            {"name": "📊 数据分析", "required": True},
            {"name": "🔮 趋势预测", "required": True},
            {"name": "📋 下周关注", "required": True},
        ]
        builder.add_output_format(
            format_type="markdown",
            sections=sections,
            style_guide="周报需包含数据对比和趋势分析"
        )
        
        return builder


# ============== 使用示例 ==============

def demo_v2():
    """演示 v2 版本"""
    print("=" * 70)
    print("XML 提示格式化 v2 - 智能分析版")
    print("=" * 70)
    
    # 模拟数据源
    source_data = [
        {"title": "宁德时代发布新一代储能电池，能量密度提升20%", "source": "北极星储能网", 
         "summary": "宁德时代发布新款储能电池", "url": "http://example.com/1"},
        {"title": "菲律宾风光强制配建储能政策出台，装机不低于20%", "source": "储能中国网",
         "summary": "菲律宾出台新政策", "url": "http://example.com/2"},
        {"title": "储能电池包闪爆！6·14爆炸事故调查报告全文公布", "source": "北极星储能网",
         "summary": "安全事故调查报告", "url": "http://example.com/3"},
        {"title": "贵州省首个构网型储能示范项目200MWh成功并网", "source": "高工储能",
         "summary": "项目成功并网", "url": "http://example.com/4"},
    ]
    
    # 创建 XML 提示
    date = datetime.now().strftime("%Y-%m-%d")
    builder = DailyReportXMLTemplate.create(
        source_data=source_data,
        date=date,
        data_stats={"quality_score": 95}
    )
    
    # 验证并生成提示
    is_valid, error = builder.validate()
    print(f"\nXML 验证: {'✅ 通过' if is_valid else '❌ 失败'}")
    if error:
        print(f"  错误: {error}")
    
    prompt = builder.to_prompt()
    print(f"\n生成的提示（节选）:")
    print("-" * 70)
    lines = prompt.split('\n')[:50]
    print('\n'.join(lines))
    print("...")
    print("-" * 70)
    print(f"✅ 总字符数: {len(prompt)}")
    
    # 分析统计
    _, stats = NewsAnalyzer.analyze_batch(source_data)
    print(f"\n智能分析结果:")
    print(f"  总条数: {stats['total']}")
    print(f"  热点数: {stats['hot_news']}")
    print(f"  平均重要性: {stats['avg_importance']:.1f}")
    print(f"  分类分布: {stats['by_category']}")
    print(f"  情感分布: {stats['by_sentiment']}")


if __name__ == "__main__":
    demo_v2()
