"""
SWOT 分析框架实现
Strengths, Weaknesses, Opportunities, Threats
"""

from typing import List, Dict, Any
from dataclasses import dataclass, field


@dataclass
class SWOTAnalysis:
    """SWOT 分析结果"""
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    opportunities: List[str] = field(default_factory=list)
    threats: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, List[str]]:
        return {
            'S(优势)': self.strengths,
            'W(劣势)': self.weaknesses,
            'O(机会)': self.opportunities,
            'T(威胁)': self.threats
        }
    
    def to_markdown(self) -> str:
        """生成 Markdown 格式的 SWOT 分析"""
        md = "## 📊 SWOT 分析\n\n"
        
        md += "| 维度 | 内容 |\n"
        md += "|------|------|\n"
        
        for dimension, items in self.to_dict().items():
            if items:
                content = "<br>".join([f"• {item}" for item in items[:3]])
                md += f"| {dimension} | {content} |\n"
        
        return md


class SWOTGenerator:
    """
    SWOT 分析生成器
    
    基于资讯列表自动生成 SWOT 分析
    """
    
    # 信号词库
    SIGNAL_WORDS = {
        'strengths': {
            'positive': ['增长', '突破', '领先', '优势', '强', '高', '大', '成功', '创新'],
            'keywords': ['装机增长', '技术突破', '市场份额', '政策支持', '产业链完整']
        },
        'weaknesses': {
            'negative': ['下降', '下跌', '亏损', '压力', '弱', '低', '小', '困难', '挑战'],
            'keywords': ['价格竞争', '盈利压力', '技术瓶颈', '成本高', '产能过剩']
        },
        'opportunities': {
            'positive': ['机会', '潜力', '空间', '趋势', '新', '增长', '拓展'],
            'keywords': ['新场景', '政策支持', '技术迭代', '海外拓展', '降本空间']
        },
        'threats': {
            'negative': ['风险', '威胁', '不确定', '挑战', '限制', '制约'],
            'keywords': ['贸易壁垒', '关税', '原材料涨价', '技术替代', '政策变化']
        }
    }
    
    def __init__(self, industry: str = "储能"):
        self.industry = industry
        self.swot = SWOTAnalysis()
    
    def generate(self, news_list: List[Dict], market_data: Dict = None) -> SWOTAnalysis:
        """
        生成 SWOT 分析
        
        Args:
            news_list: 资讯列表
            market_data: 市场数据（可选）
            
        Returns:
            SWOT 分析结果
        """
        # 分析每条资讯
        for item in news_list:
            self._analyze_item(item)
        
        # 如果有市场数据，补充分析
        if market_data:
            self._analyze_market_data(market_data)
        
        # 去重并限制数量
        self._deduplicate_and_limit()
        
        return self.swot
    
    def _analyze_item(self, item: Dict):
        """分析单条资讯"""
        title = item.get('title', '')
        summary = item.get('summary', '')
        content = f"{title} {summary}"
        
        # 判断信号类型
        is_positive = any(word in content for word in ['增长', '突破', '上升', '上涨', '创新'])
        is_negative = any(word in content for word in ['下降', '下跌', '风险', '压力', '挑战'])
        
        # S - 优势（行业已有积极进展）
        if any(kw in content for kw in ['装机', '规模', '市场份额', '技术领先']):
            if is_positive:
                self.swot.strengths.append(title[:40] + "..." if len(title) > 40 else title)
        
        # W - 劣势（行业面临的挑战）
        if any(kw in content for kw in ['价格', '成本', '盈利', '竞争']):
            if is_negative:
                self.swot.weaknesses.append(title[:40] + "..." if len(title) > 40 else title)
        
        # O - 机会（未来的积极因素）
        if any(kw in content for kw in ['政策', '规划', '目标', '新场景', '潜力']):
            if is_positive:
                self.swot.opportunities.append(title[:40] + "..." if len(title) > 40 else title)
        
        # T - 威胁（未来的消极因素）
        if any(kw in content for kw in ['关税', '贸易', '风险', '不确定', '限制']):
            self.swot.threats.append(title[:40] + "..." if len(title) > 40 else title)
    
    def _analyze_market_data(self, market_data: Dict):
        """基于市场数据补充 SWOT"""
        # 装机量数据 -> S
        if 'installed_capacity' in market_data:
            growth = market_data.get('growth_rate', 0)
            if growth > 50:
                self.swot.strengths.append(f"装机量高速增长({growth}%)")
        
        # 价格数据 -> W
        if 'price_trend' in market_data:
            trend = market_data['price_trend']
            if trend == 'down':
                self.swot.weaknesses.append("价格持续下行，盈利承压")
        
        # 政策数量 -> O
        if 'policy_count' in market_data:
            count = market_data['policy_count']
            if count > 5:
                self.swot.opportunities.append(f"政策密集出台({count}项)")
        
        # 国际贸易数据 -> T
        if 'trade_risk' in market_data:
            if market_data['trade_risk']:
                self.swot.threats.append("国际贸易环境不确定性增加")
    
    def _deduplicate_and_limit(self, max_items: int = 3):
        """去重并限制每个维度的条目数"""
        for attr in ['strengths', 'weaknesses', 'opportunities', 'threats']:
            items = list(dict.fromkeys(getattr(self.swot, attr)))  # 去重
            setattr(self.swot, attr, items[:max_items])  # 限制数量
    
    def generate_quick_summary(self, news_list: List[Dict]) -> str:
        """
        生成 SWOT 速览文本（日报用）
        
        Returns:
            Markdown 格式的 SWOT 摘要
        """
        self.generate(news_list)
        
        lines = ["## 📊 行业 SWOT 速览\n"]
        
        swot_dict = self.swot.to_dict()
        for dimension, items in swot_dict.items():
            if items:
                lines.append(f"**{dimension}**:")
                for item in items[:2]:  # 每类最多2条
                    lines.append(f"  • {item}")
                lines.append("")
        
        return "\n".join(lines)


# 便捷函数
def quick_swot(news_list: List[Dict]) -> str:
    """
    快速生成 SWOT 分析文本
    
    Args:
        news_list: 资讯列表
        
    Returns:
        Markdown 格式的 SWOT 分析
    """
    generator = SWOTGenerator(industry="储能")
    return generator.generate_quick_summary(news_list)
