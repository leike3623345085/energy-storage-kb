#!/usr/bin/env python3
"""
储能行业深度分析 Agent
使用AI进行专业分析，生成高质量研究报告
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 分析Agent工作目录
AGENT_DIR = Path(__file__).parent
DATA_DIR = Path(__file__).parent.parent / "data"
REPORTS_DIR = DATA_DIR / "reports"

def load_data(days=1):
    """加载最近N天的数据"""
    all_data = []
    
    # 加载爬虫数据
    crawler_dir = DATA_DIR / "crawler"
    if crawler_dir.exists():
        for f in sorted(crawler_dir.glob("*.json"), reverse=True)[:days*3]:
            try:
                with open(f, 'r', encoding='utf-8') as file:
                    data = json.load(file)
                    if isinstance(data, dict) and "data" in data:
                        all_data.extend(data["data"])
                    elif isinstance(data, list):
                        all_data.extend(data)
            except:
                pass
    
    # 加载搜索数据
    for f in sorted(DATA_DIR.glob("news_*.json"), reverse=True)[:days]:
        try:
            with open(f, 'r', encoding='utf-8') as file:
                data = json.load(file)
                if isinstance(data, dict) and "results" in data:
                    all_data.extend(data["results"])
        except:
            pass
    
    return all_data

def prepare_analysis_prompt(data, analysis_type="daily"):
    """准备分析提示词"""
    
    # 提取关键信息
    titles = [item.get("title", "") for item in data[:30]]
    sources = list(set(item.get("source", "") for item in data))
    
    # 统计关键词
    keywords_count = {}
    keywords = ["宁德时代", "比亚迪", "亿纬锂能", "固态电池", "钠电池", 
                "储能", "锂电池", "光伏", "电网", "政策"]
    for kw in keywords:
        count = sum(1 for t in titles if kw in t)
        if count > 0:
            keywords_count[kw] = count
    
    # 构建提示词
    prompt = f"""作为储能行业资深分析师，请对以下数据进行深度分析：

## 数据概况
- 分析时间范围：最近{len(data)}条资讯
- 数据来源：{', '.join(sources[:5])}
- 关键词统计：{json.dumps(keywords_count, ensure_ascii=False)}

## 原始数据（前20条标题）
"""
    
    for i, item in enumerate(data[:20], 1):
        title = item.get("title", "")
        source = item.get("source", "")
        prompt += f"{i}. [{source}] {title}\n"
    
    prompt += """
## 分析要求

请按以下框架生成专业分析报告：

1. **执行摘要**
   - 今日最重要的3个发现
   - 核心观点（用★标注重要程度）

2. **市场动态分析**
   - 市场规模/增速变化
   - 细分领域表现（大储/小储/工商业）
   - 区域市场特点（国内/海外）

3. **技术趋势研判**
   - 技术突破（固态/钠电/大电芯）
   - 产业化进度评估
   - 技术路线竞争格局

4. **竞争格局变化**
   - 重点企业动态（宁德时代/比亚迪/亿纬等）
   - 市场份额变化趋势
   - 新进入者/退出者

5. **政策环境影响**
   - 国内政策（补贴/并网/电价）
   - 国际政策（关税/碳关税/贸易）
   - 政策影响评估

6. **投资分析**
   - 投资机会（细分领域/企业）
   - 风险提示（技术/政策/市场）
   - 估值水平评估

7. **未来展望**
   - 短期（1个月）关注重点
   - 中期（6个月）趋势预测
   - 关键监测指标

## 输出要求
- 使用Markdown格式
- 数据要有依据，观点要有逻辑
- 重要结论用**加粗**标注
- 添加适当的emoji增强可读性
- 总字数控制在2000-3000字
"""
    
    return prompt

def save_analysis_report(content, report_type="deep_analysis"):
    """保存分析报告"""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    
    date_str = datetime.now().strftime("%Y%m%d")
    filename = f"{report_type}_{date_str}.md"
    filepath = REPORTS_DIR / filename
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return filepath

def main():
    """主函数"""
    print("=" * 60)
    print("储能行业深度分析 Agent")
    print(f"运行时间: {datetime.now()}")
    print("=" * 60)
    
    # 加载数据
    print("\n📊 加载数据...")
    data = load_data(days=1)
    print(f"   加载 {len(data)} 条资讯")
    
    if not data:
        print("❌ 无数据可分析")
        return 1
    
    # 准备分析提示词
    print("\n📝 准备分析...")
    prompt = prepare_analysis_prompt(data)
    
    # 保存提示词（供AI分析使用）
    prompt_file = AGENT_DIR / "analysis_prompt.txt"
    with open(prompt_file, 'w', encoding='utf-8') as f:
        f.write(prompt)
    
    print(f"   提示词已保存: {prompt_file}")
    print(f"\n✅ 数据准备完成，等待AI分析...")
    print(f"   请使用提示词调用AI生成深度分析报告")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
