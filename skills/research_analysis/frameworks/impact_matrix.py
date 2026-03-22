"""
事件影响评估矩阵
基于影响程度和时间紧迫性进行优先级排序
"""

from typing import List, Dict, Any
from dataclasses import dataclass
from enum import Enum


class ImpactLevel(Enum):
    """影响程度"""
    HIGH = "高"
    MEDIUM = "中"
    LOW = "低"


class UrgencyLevel(Enum):
    """紧迫性"""
    HIGH = "高"  # 立即影响
    MEDIUM = "中"  # 近期影响
    LOW = "低"  # 长期影响


@dataclass
class ImpactAssessment:
    """影响评估结果"""
    title: str
    impact: ImpactLevel
    urgency: UrgencyLevel
    score: int  # 综合评分 0-100
    reason: str  # 评估理由
    recommendations: List[str]  # 建议关注方向


class ImpactMatrix:
    """
    事件影响评估矩阵
    
    评估维度：
    - 影响程度：对行业/市场的潜在影响大小
    - 紧迫性：需要关注的时间紧迫程度
    
    评分矩阵：
              紧迫性
           高    中    低
    高  |  100   85   70
影  中  |   85   70   55
响  低  |   70   55   40
    """
    
    # 影响程度评分矩阵
    SCORE_MATRIX = {
        (ImpactLevel.HIGH, UrgencyLevel.HIGH): 100,
        (ImpactLevel.HIGH, UrgencyLevel.MEDIUM): 85,
        (ImpactLevel.HIGH, UrgencyLevel.LOW): 70,
        (ImpactLevel.MEDIUM, UrgencyLevel.HIGH): 85,
        (ImpactLevel.MEDIUM, UrgencyLevel.MEDIUM): 70,
        (ImpactLevel.MEDIUM, UrgencyLevel.LOW): 55,
        (ImpactLevel.LOW, UrgencyLevel.HIGH): 70,
        (ImpactLevel.LOW, UrgencyLevel.MEDIUM): 55,
        (ImpactLevel.LOW, UrgencyLevel.LOW): 40,
    }
    
    # 高影响信号词
    HIGH_IMPACT_SIGNALS = {
        'policy': ['国家能源局', '发改委', '工信部', '六部门', '国务院', '国家标准'],
        'market': ['GW', 'GWh', '亿元', '增长', '突破', '创新高'],
        'technology': ['首座', '首台', '首套', '示范', '创新', '突破'],
        'company': ['宁德时代', '比亚迪', '特斯拉', 'Fluence']
    }
    
    # 高紧迫信号词
    HIGH_URGENCY_SIGNALS = {
        'immediate': ['即日起', '即日起实施', '紧急', '立即', '暂停'],
        'deadline': ['截止', '申报', '截止', '最后期限'],
        'deadline_units': ['月底', '年底', '日前']
    }
    
    def assess(self, news_item: Dict) -> ImpactAssessment:
        """
        评估单条资讯的影响
        
        Args:
            news_item: 资讯字典
            
        Returns:
            影响评估结果
        """
        title = news_item.get('title', '')
        source = news_item.get('source', '')
        
        # 评估影响程度
        impact = self._assess_impact(title, source)
        
        # 评估紧迫性
        urgency = self._assess_urgency(title)
        
        # 计算综合评分
        score = self.SCORE_MATRIX.get((impact, urgency), 50)
        
        # 生成评估理由
        reason = self._generate_reason(title, impact, urgency)
        
        # 生成关注建议
        recommendations = self._generate_recommendations(title, impact, urgency)
        
        return ImpactAssessment(
            title=title,
            impact=impact,
            urgency=urgency,
            score=score,
            reason=reason,
            recommendations=recommendations
        )
    
    def _assess_impact(self, title: str, source: str) -> ImpactLevel:
        """评估影响程度"""
        score = 0
        
        # 1. 政策层级评分
        if any(sig in title for sig in self.HIGH_IMPACT_SIGNALS['policy']):
            score += 40
        
        # 2. 数据规模评分
        if any(sig in title for sig in self.HIGH_IMPACT_SIGNALS['market']):
            score += 30
        
        # 3. 技术突破评分
        if any(sig in title for sig in self.HIGH_IMPACT_SIGNALS['technology']):
            score += 30
        
        # 4. 来源权威性评分
        authoritative = ['国家能源局', '工信部', '发改委', '北极星储能网', '中国储能网']
        if source in authoritative:
            score += 20
        
        # 5. 头部企业提及
        if any(sig in title for sig in self.HIGH_IMPACT_SIGNALS['company']):
            score += 15
        
        # 判定影响等级
        if score >= 60:
            return ImpactLevel.HIGH
        elif score >= 30:
            return ImpactLevel.MEDIUM
        else:
            return ImpactLevel.LOW
    
    def _assess_urgency(self, title: str) -> UrgencyLevel:
        """评估紧迫性"""
        # 高紧迫信号
        if any(sig in title for sig in self.HIGH_URGENCY_SIGNALS['immediate']):
            return UrgencyLevel.HIGH
        
        # 截止期限信号
        if any(sig in title for sig in self.HIGH_URGENCY_SIGNALS['deadline']):
            return UrgencyLevel.HIGH
        
        if any(sig in title for sig in self.HIGH_URGENCY_SIGNALS['deadline_units']):
            return UrgencyLevel.MEDIUM
        
        # 招标/中标类（有一定时效性）
        if any(kw in title for kw in ['招标', '中标', '启动', '开工']):
            return UrgencyLevel.MEDIUM
        
        # 其他默认为低
        return UrgencyLevel.LOW
    
    def _generate_reason(self, title: str, impact: ImpactLevel, urgency: UrgencyLevel) -> str:
        """生成评估理由"""
        reasons = []
        
        if impact == ImpactLevel.HIGH:
            if any(kw in title for kw in ['国家', '部门', '标准']):
                reasons.append("涉及政策/标准")
            if any(kw in title for kw in ['GW', 'GWh', '亿元']):
                reasons.append("规模数据显著")
            if any(kw in title for kw in ['首座', '首台', '首套']):
                reasons.append("具有标志性意义")
        
        if urgency == UrgencyLevel.HIGH:
            if any(kw in title for kw in ['即日起', '截止', '申报']):
                reasons.append("有时效性要求")
        
        if not reasons:
            reasons.append("常规行业动态")
        
        return "；".join(reasons)
    
    def _generate_recommendations(self, title: str, impact: ImpactLevel, urgency: UrgencyLevel) -> List[str]:
        """生成关注建议"""
        recommendations = []
        
        if impact == ImpactLevel.HIGH:
            recommendations.append("重点关注")
            
            if any(kw in title for kw in ['政策', '标准', '规范']):
                recommendations.append("跟踪政策细则")
            
            if any(kw in title for kw in ['招标', '中标']):
                recommendations.append("关注后续项目进展")
        
        if urgency == UrgencyLevel.HIGH:
            recommendations.append("近期内密切关注")
        
        if not recommendations:
            recommendations.append("常规关注")
        
        return recommendations
    
    def batch_assess(self, news_list: List[Dict]) -> List[ImpactAssessment]:
        """
        批量评估资讯列表
        
        Returns:
            按综合评分排序的评估结果列表
        """
        assessments = []
        for item in news_list:
            assessment = self.assess(item)
            assessments.append(assessment)
        
        # 按分数排序
        assessments.sort(key=lambda x: x.score, reverse=True)
        return assessments
    
    def get_priority_items(self, news_list: List[Dict], min_score: int = 70) -> List[ImpactAssessment]:
        """
        获取高优先级资讯
        
        Args:
            news_list: 资讯列表
            min_score: 最低分数门槛
            
        Returns:
            高优先级资讯列表
        """
        all_assessments = self.batch_assess(news_list)
        return [a for a in all_assessments if a.score >= min_score]


# 便捷函数
def quick_assess(news_item: Dict) -> Dict:
    """
    快速评估单条资讯
    
    Returns:
        评估结果字典
    """
    matrix = ImpactMatrix()
    result = matrix.assess(news_item)
    
    return {
        'title': result.title,
        'impact': result.impact.value,
        'urgency': result.urgency.value,
        'score': result.score,
        'reason': result.reason,
        'recommendations': result.recommendations
    }
