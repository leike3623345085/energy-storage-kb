#!/usr/bin/env python3
"""
XML 提示格式化系统 (XML Prompt Formatter)
=============================================
基于 GSD 方法的 XML 结构化提示，提高 AI 理解和执行精度

核心特性:
- 结构化任务定义
- 强类型约束
- 版本控制兼容
- 与现有 HARNESS 框架集成
"""

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime
from pathlib import Path
import json


@dataclass
class TaskConstraint:
    """任务约束"""
    name: str
    value: Any
    required: bool = True


@dataclass
class TaskContext:
    """任务上下文"""
    source_data: List[Dict] = field(default_factory=list)
    date: str = ""
    history: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)


class XMLPromptBuilder:
    """XML 提示构建器"""
    
    def __init__(self, task_type: str = "daily_report"):
        self.task_type = task_type
        self.root = ET.Element("task")
        self.root.set("version", "1.0")
        self.root.set("type", task_type)
        self.root.set("generated_at", datetime.now().isoformat())
    
    def add_objective(self, description: str, priority: str = "high"):
        """添加任务目标"""
        obj = ET.SubElement(self.root, "objective")
        obj.set("priority", priority)
        obj.text = description
        return self
    
    def add_context(self, context: TaskContext):
        """添加上下文信息"""
        ctx = ET.SubElement(self.root, "context")
        
        # 数据源
        if context.source_data:
            sources = ET.SubElement(ctx, "data_sources")
            sources.set("count", str(len(context.source_data)))
            for item in context.source_data[:5]:  # 只显示前5条样本
                source = ET.SubElement(sources, "source")
                source.set("title", item.get("title", "")[:50])
                source.set("type", item.get("source", "unknown"))
        
        # 日期
        if context.date:
            date_elem = ET.SubElement(ctx, "date")
            date_elem.text = context.date
        
        # 历史
        if context.history:
            hist = ET.SubElement(ctx, "history")
            for h in context.history[-3:]:  # 最近3条
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
        """添加约束条件"""
        cons = ET.SubElement(self.root, "constraints")
        
        for c in constraints:
            elem = ET.SubElement(cons, "constraint")
            elem.set("name", c.name)
            elem.set("required", "true" if c.required else "false")
            elem.text = str(c.value)
        
        return self
    
    def add_output_format(self, format_type: str, sections: List[str], 
                         style_guide: Optional[str] = None):
        """添加输出格式规范"""
        fmt = ET.SubElement(self.root, "output_format")
        fmt.set("type", format_type)
        
        # 必需的章节
        required = ET.SubElement(fmt, "required_sections")
        for section in sections:
            sec = ET.SubElement(required, "section")
            sec.text = section
        
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
    
    def build(self) -> str:
        """构建 XML 字符串"""
        ET.indent(self.root, space="  ")
        return ET.tostring(self.root, encoding="unicode")
    
    def to_prompt(self) -> str:
        """转换为可直接使用的提示文本"""
        xml_str = self.build()
        return f"""请根据以下结构化任务描述生成内容：

```xml
{xml_str}
```

请严格按照 XML 中定义的约束条件和输出格式执行任务。
"""


class DailyReportXMLTemplate:
    """日报生成的 XML 模板"""
    
    @staticmethod
    def create(source_data: List[Dict], date: str, 
               data_stats: Dict = None) -> XMLPromptBuilder:
        """创建日报生成的 XML 提示"""
        
        builder = XMLPromptBuilder("daily_report")
        
        # 1. 任务目标
        builder.add_objective(
            description=f"基于 {len(source_data)} 条储能行业资讯，生成 {date} 的行业日报",
            priority="high"
        )
        
        # 2. 上下文
        context = TaskContext(
            source_data=source_data,
            date=date,
            history=[],
            metadata={
                "total_items": len(source_data),
                "sources": list(set(item.get("source", "") for item in source_data)),
                "data_quality_score": data_stats.get("quality_score", 90) if data_stats else 90
            }
        )
        builder.add_context(context)
        
        # 3. 约束条件
        constraints = [
            TaskConstraint("format", "markdown", True),
            TaskConstraint("language", "中文", True),
            TaskConstraint("tone", "专业、客观", True),
            TaskConstraint("max_length", "3000", False),
            TaskConstraint("include_data_sources", "true", True),
        ]
        builder.add_constraints(constraints)
        
        # 4. 输出格式
        builder.add_output_format(
            format_type="markdown",
            sections=[
                "📊 市场动态",
                "⚡ 技术进展", 
                "📜 政策动态",
                "📈 行情数据",
                "🔥 今日热点"
            ],
            style_guide="使用 emoji 增强可读性，每个要点控制在 100 字以内，关键数据加粗"
        )
        
        # 5. 质量标准
        builder.add_quality_criteria({
            "fact_accuracy": {"required": "true", "min_score": 0.9},
            "data_completeness": {"required_sections": 5, "tolerance": 1},
            "source_citation": {"required": "true", "format": "文末标注"},
            "readability": {"target_audience": "金融分析师", "level": "专业"}
        })
        
        return builder


class WaveBasedParallelTemplate:
    """波式并行性任务的 XML 模板"""
    
    @staticmethod
    def create(waves: List[List[Dict]]) -> XMLPromptBuilder:
        """
        创建波式并行任务的 XML 提示
        
        Args:
            waves: 每个波次包含的任务列表
                   [[wave1_tasks...], [wave2_tasks...], ...]
        """
        builder = XMLPromptBuilder("wave_based_parallel")
        
        # 任务目标
        builder.add_objective(
            description=f"执行 {len(waves)} 个波次的并行任务编排",
            priority="high"
        )
        
        # 波次定义
        waves_elem = ET.SubElement(builder.root, "execution_waves")
        
        for i, wave_tasks in enumerate(waves, 1):
            wave = ET.SubElement(waves_elem, "wave")
            wave.set("id", str(i))
            wave.set("parallel", "true")
            wave.set("task_count", str(len(wave_tasks)))
            
            for task in wave_tasks:
                task_elem = ET.SubElement(wave, "task")
                task_elem.set("name", task.get("name", ""))
                task_elem.set("type", task.get("type", ""))
                if "depends_on" in task:
                    task_elem.set("depends_on", str(task["depends_on"]))
        
        # 约束
        constraints = [
            TaskConstraint("max_parallel", "4", True),
            TaskConstraint("timeout_per_task", "300", True),
            TaskConstraint("retry_on_failure", "true", True),
            TaskConstraint("aggregate_results", "true", True),
        ]
        builder.add_constraints(constraints)
        
        return builder


# ============== 使用示例 ==============

def example_daily_report():
    """日报生成示例"""
    # 模拟数据源
    source_data = [
        {"title": "宁德时代发布新一代储能电池", "source": "北极星储能网"},
        {"title": "储能行业政策解读", "source": "储能中国网"},
    ]
    
    # 创建 XML 提示
    builder = DailyReportXMLTemplate.create(
        source_data=source_data,
        date="2026-03-29",
        data_stats={"quality_score": 95}
    )
    
    prompt = builder.to_prompt()
    print(prompt)
    return prompt


def example_wave_parallel():
    """波式并行示例"""
    waves = [
        # Wave 1: 爬虫（无依赖，并行）
        [
            {"name": "crawl_bjx", "type": "crawler"},
            {"name": "crawl_cnnes", "type": "crawler"},
            {"name": "crawl_ofweek", "type": "crawler"},
        ],
        # Wave 2: 数据清洗（依赖 Wave 1）
        [
            {"name": "clean_data", "type": "processor", "depends_on": 1},
        ],
        # Wave 3: 报告生成（依赖 Wave 2）
        [
            {"name": "generate_report", "type": "generator", "depends_on": 2},
        ]
    ]
    
    builder = WaveBasedParallelTemplate.create(waves)
    print(builder.build())


if __name__ == "__main__":
    print("=" * 60)
    print("示例 1: 日报生成 XML 提示")
    print("=" * 60)
    example_daily_report()
    
    print("\n" + "=" * 60)
    print("示例 2: 波式并行 XML 提示")
    print("=" * 60)
    example_wave_parallel()
