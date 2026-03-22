"""
MECE 分析框架实现
Mutually Exclusive, Collectively Exhaustive
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class MECECategory:
    """MECE 分类项"""
    name: str
    description: str
    keywords: List[str]
    items: List[Dict] = None
    
    def __post_init__(self):
        if self.items is None:
            self.items = []


class MECEAnalyzer:
    """
    MECE 分析器
    
    确保分析维度相互独立、完全穷尽
    """
    
    # 储能行业默认分类框架
    ENERGY_STORAGE_FRAMEWORK = {
        "政策监管": {
            "description": "国家政策、行业标准、监管动态",
            "keywords": ["政策", "标准", "监管", "规范", "通知", "意见", "规划", "目标"]
        },
        "市场动态": {
            "description": "市场规模、价格走势、供需关系",
            "keywords": ["市场", "规模", "价格", "招标", "中标", "装机", "容量", "MW", "GWh"]
        },
        "项目进展": {
            "description": "储能项目立项、建设、并网动态",
            "keywords": ["项目", "开工", "建成", "并网", "投运", "立项", "签约", "落地"]
        },
        "技术创新": {
            "description": "电池技术、系统集成、新兴技术",
            "keywords": ["技术", "电池", "锂电", "钠电", "固态", "液流", "压缩空气", "飞轮", "BMS", "PCS"]
        },
        "企业动态": {
            "description": "头部企业、投融资、合作并购",
            "keywords": ["企业", "公司", "投资", "融资", "合作", "签约", "中标", "财报"]
        },
        "国际市场": {
            "description": "海外市场、国际贸易、全球动态",
            "keywords": ["海外", "国际", "出口", "进口", "欧洲", "美国", "澳大利亚", "关税"]
        }
    }
    
    def __init__(self, industry: str = "储能", custom_framework: Dict = None):
        self.industry = industry
        self.framework = custom_framework or self._get_default_framework()
        self.categories = self._init_categories()
    
    def _get_default_framework(self) -> Dict:
        """获取默认分析框架"""
        if self.industry == "储能":
            return self.ENERGY_STORAGE_FRAMEWORK
        # 可扩展其他行业
        return self.ENERGY_STORAGE_FRAMEWORK
    
    def _init_categories(self) -> Dict[str, MECECategory]:
        """初始化分类对象"""
        categories = {}
        for name, config in self.framework.items():
            categories[name] = MECECategory(
                name=name,
                description=config["description"],
                keywords=config["keywords"]
            )
        return categories
    
    def classify(self, news_item: Dict) -> List[str]:
        """
        对单条资讯进行分类
        
        Returns:
            匹配的类别列表（可能属于多个类别）
        """
        title = news_item.get('title', '')
        summary = news_item.get('summary', '')
        content = f"{title} {summary}"
        
        matched_categories = []
        
        for cat_name, category in self.categories.items():
            for keyword in category.keywords:
                if keyword in content:
                    matched_categories.append(cat_name)
                    break
        
        # 如果没有匹配到任何类别，标记为"其他"
        if not matched_categories:
            matched_categories.append("其他")
        
        return matched_categories
    
    def analyze(self, news_list: List[Dict]) -> Dict[str, MECECategory]:
        """
        对资讯列表进行完整 MECE 分析
        
        Args:
            news_list: 资讯列表
            
        Returns:
            按类别组织的分析结果
        """
        # 清空之前的分析结果
        for cat in self.categories.values():
            cat.items = []
        
        # 分类每条资讯
        for item in news_list:
            categories = self.classify(item)
            for cat_name in categories:
                if cat_name in self.categories:
                    self.categories[cat_name].items.append(item)
                elif cat_name == "其他":
                    # 动态创建"其他"类别
                    if "其他" not in self.categories:
                        self.categories["其他"] = MECECategory(
                            name="其他",
                            description="未分类资讯",
                            keywords=[]
                        )
                    self.categories["其他"].items.append(item)
        
        return self.categories
    
    def extract_hotspots(self, news_list: List[Dict], top_n: int = 3) -> List[Dict]:
        """
        提取热点（综合重要性评分）
        
        评分维度：
        - 信息源权威性
        - 关键词热度
        - 时间新鲜度
        - 类别集中度
        
        Returns:
            热点列表，按重要性排序
        """
        # 先进行 MECE 分类
        self.analyze(news_list)
        
        # 计算每条资讯的重要性
        scored_items = []
        for item in news_list:
            score = self._calculate_importance(item)
            scored_items.append({
                'item': item,
                'score': score,
                'categories': self.classify(item)
            })
        
        # 按分数排序，取 top_n
        scored_items.sort(key=lambda x: x['score'], reverse=True)
        
        hotspots = []
        for i, si in enumerate(scored_items[:top_n], 1):
            hotspot = {
                'rank': i,
                'title': si['item'].get('title', ''),
                'source': si['item'].get('source', ''),
                'url': si['item'].get('url', ''),
                'categories': si['categories'],
                'importance_score': si['score'],
                'analysis': self._generate_hotspot_analysis(si['item'], si['categories'])
            }
            hotspots.append(hotspot)
        
        return hotspots
    
    def _calculate_importance(self, item: Dict) -> float:
        """计算资讯重要性分数"""
        score = 0.0
        title = item.get('title', '')
        source = item.get('source', '')
        
        # 1. 来源权威性评分 (0-30分)
        authoritative_sources = {
            '国家能源局': 30,
            '工信部': 30,
            '发改委': 28,
            '北极星储能网': 22,
            '中国储能网': 20,
            '高工储能': 18,
            'OFweek储能': 15
        }
        score += authoritative_sources.get(source, 10)
        
        # 2. 关键词热度评分 (0-40分)
        hot_keywords = {
            '装机': 10, '并网': 10, '中标': 8, '招标': 8,
            '政策': 8, '标准': 8, '规划': 8, '目标': 8,
            '宁德时代': 6, '比亚迪': 6, '亿纬锂能': 6,
            '钠电': 8, '固态': 8, '液流': 7, '压缩空气': 7,
            '虚拟电厂': 8, '构网型': 8
        }
        for kw, points in hot_keywords.items():
            if kw in title:
                score += points
        
        # 3. 数据含量评分 (0-20分)
        if any(unit in title for unit in ['GW', 'GWh', 'MW', 'MWh', '亿元', '%']):
            score += 15
        
        # 4. 时间加分 (0-10分)
        # 假设越新的信息越重要，由调用方处理时间因素
        score += 5
        
        return min(score, 100)  # 满分100
    
    def _generate_hotspot_analysis(self, item: Dict, categories: List[str]) -> str:
        """生成热点分析文本"""
        title = item.get('title', '')
        
        # 基于类别和分析对象生成分析
        analysis_parts = []
        
        # 判断影响对象
        if any(kw in title for kw in ['政策', '标准', '规范']):
            analysis_parts.append("政策层面")
        if any(kw in title for kw in ['招标', '中标', '项目', '装机']):
            analysis_parts.append("市场层面")
        if any(kw in title for kw in ['技术', '电池', 'BMS', 'PCS']):
            analysis_parts.append("技术层面")
        
        # 判断影响方向
        if any(kw in title for kw in ['增长', '上涨', '突破', '创新高']):
            impact = "利好"
        elif any(kw in title for kw in ['下降', '下跌', '风险', '挑战']):
            impact = "利空"
        else:
            impact = "中性"
        
        if analysis_parts:
            return f"影响{'/'.join(analysis_parts)}，信号：{impact}"
        else:
            return "行业动态，建议关注"
    
    def get_category_summary(self) -> Dict[str, int]:
        """获取各类别统计摘要"""
        return {
            name: len(cat.items)
            for name, cat in self.categories.items()
        }


# 便捷函数
def analyze_energy_storage(news_list: List[Dict], top_n: int = 3) -> Dict:
    """
    储能行业快速分析入口
    
    Args:
        news_list: 资讯列表
        top_n: 热点数量
        
    Returns:
        包含热点和分类统计的结果
    """
    analyzer = MECEAnalyzer(industry="储能")
    
    hotspots = analyzer.extract_hotspots(news_list, top_n)
    category_summary = analyzer.get_category_summary()
    
    return {
        'hotspots': hotspots,
        'category_summary': category_summary,
        'total_items': len(news_list)
    }
