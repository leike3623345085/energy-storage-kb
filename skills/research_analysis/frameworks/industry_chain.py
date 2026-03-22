"""
产业链分析框架
上游 → 中游 → 下游 全链条追踪
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class IndustryNode:
    """产业链节点"""
    name: str  # 节点名称
    segment: str  # 所属环节（上游/中游/下游）
    companies: List[str] = field(default_factory=list)  # 相关企业
    updates: List[Dict] = field(default_factory=list)  # 最新动态


class IndustryChain:
    """
    产业链分析器
    
    储能行业产业链：
    上游：原材料（锂、钴、正负极材料、电解液、隔膜）
    中游：电池/PCS（电芯、模组、BMS、PCS、系统集成）
    下游：应用端（发电侧、电网侧、用户侧、储能运营商）
    """
    
    # 储能行业产业链结构
    ENERGY_STORAGE_CHAIN = {
        "上游": {
            "原材料": ["锂矿", "钴矿", "镍矿", "石墨"],
            "正极材料": ["磷酸铁锂", "三元材料", "钴酸锂"],
            "负极材料": ["人造石墨", "天然石墨", "硅基负极"],
            "电解液": ["六氟磷酸锂", "溶剂"],
            "隔膜": ["湿法隔膜", "干法隔膜"],
            "其他材料": ["铜箔", "铝箔", "结构件"]
        },
        "中游": {
            "电芯": ["宁德时代", "比亚迪", "亿纬锂能", "国轩高科", "中创新航"],
            "BMS": ["特斯拉", "比亚迪", "宁德时代", "均胜电子"],
            "PCS": ["阳光电源", "华为", "科华数据", "上能电气"],
            "系统集成": ["Fluence", "特斯拉", "阳光电源", "海博思创"]
        },
        "下游": {
            "发电侧": ["新能源配储", "风光大基地"],
            "电网侧": ["独立储能", "调峰调频", "共享储能"],
            "用户侧": ["工商业储能", "户用储能", "微电网"],
            "运营商": ["电网公司", "发电集团", "第三方运营"]
        }
    }
    
    # 企业映射
    COMPANY_MAPPING = {
        # 电池企业
        "宁德时代": ("中游", "电芯"),
        "比亚迪": ("中游", "电芯"),
        "亿纬锂能": ("中游", "电芯"),
        "国轩高科": ("中游", "电芯"),
        "中创新航": ("中游", "电芯"),
        "海辰储能": ("中游", "电芯"),
        "蜂巢能源": ("中游", "电芯"),
        # PCS企业
        "阳光电源": ("中游", "PCS"),
        "华为": ("中游", "PCS"),
        "科华数据": ("中游", "PCS"),
        "上能电气": ("中游", "PCS"),
        # 系统集成
        "海博思创": ("中游", "系统集成"),
        # 材料企业
        "璞泰来": ("上游", "负极材料"),
        "贝特瑞": ("上游", "负极材料"),
        "当升科技": ("上游", "正极材料"),
    }
    
    def __init__(self, industry: str = "储能"):
        self.industry = industry
        self.chain_structure = self._get_chain_structure()
        self.updates = defaultdict(list)  # 按环节存储动态
    
    def _get_chain_structure(self) -> Dict:
        """获取产业链结构"""
        if self.industry == "储能":
            return self.ENERGY_STORAGE_CHAIN
        return {}
    
    def track_updates(self, news_list: List[Dict]) -> Dict[str, List[Dict]]:
        """
        追踪产业链各环节动态
        
        Args:
            news_list: 资讯列表
            
        Returns:
            按产业链环节分类的动态
        """
        for item in news_list:
            segment, node = self._identify_segment(item)
            if segment:
                key = f"{segment}-{node}" if node else segment
                self.updates[key].append(item)
        
        return dict(self.updates)
    
    def _identify_segment(self, news_item: Dict) -> tuple:
        """
        识别资讯所属产业链环节
        
        Returns:
            (环节, 节点) 元组，如果无法识别返回 (None, None)
        """
        title = news_item.get('title', '')
        
        # 1. 检查是否提及具体企业
        for company, (segment, node) in self.COMPANY_MAPPING.items():
            if company in title:
                return segment, node
        
        # 2. 检查关键词
        # 上游
        if any(kw in title for kw in ['锂矿', '钴', '正极', '负极', '电解液', '隔膜', '材料']):
            return "上游", "原材料"
        
        # 中游 - 电池
        if any(kw in title for kw in ['电芯', '电池', '宁德时代', '比亚迪', '锂电']):
            return "中游", "电芯"
        
        # 中游 - PCS
        if any(kw in title for kw in ['PCS', '变流器', '逆变器', '阳光电源']):
            return "中游", "PCS"
        
        # 中游 - 集成
        if any(kw in title for kw in ['系统集成', '储能系统', '储能柜']):
            return "中游", "系统集成"
        
        # 下游
        if any(kw in title for kw in ['新能源配储', '独立储能', '工商业储能', '户用储能']):
            return "下游", "应用端"
        
        return None, None
    
    def generate_chain_report(self) -> str:
        """
        生成产业链动态报告
        
        Returns:
            Markdown 格式的产业链报告
        """
        md = "## 🔗 产业链动态\n\n"
        
        for segment in ["上游", "中游", "下游"]:
            md += f"### {segment}\n\n"
            
            # 获取该环节的动态
            segment_updates = []
            for key, items in self.updates.items():
                if key.startswith(segment):
                    segment_updates.extend(items)
            
            if segment_updates:
                # 按时间排序，取最新3条
                segment_updates = segment_updates[:3]
                for item in segment_updates:
                    title = item.get('title', '')
                    source = item.get('source', '')
                    md += f"- **{title}** (*{source}*)\n"
            else:
                md += "- 暂无重大动态\n"
            
            md += "\n"
        
        return md
    
    def get_segment_summary(self) -> Dict[str, int]:
        """获取各环节动态统计"""
        summary = {"上游": 0, "中游": 0, "下游": 0}
        
        for key, items in self.updates.items():
            for segment in summary.keys():
                if key.startswith(segment):
                    summary[segment] += len(items)
        
        return summary


# 便捷函数
def analyze_industry_chain(news_list: List[Dict]) -> Dict:
    """
    快速分析产业链动态
    
    Args:
        news_list: 资讯列表
        
    Returns:
        包含产业链动态和统计的结果
    """
    chain = IndustryChain()
    updates = chain.track_updates(news_list)
    summary = chain.get_segment_summary()
    
    return {
        'updates': updates,
        'summary': summary,
        'report': chain.generate_chain_report()
    }
