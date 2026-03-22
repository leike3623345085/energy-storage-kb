"""
研报分析框架 - research_analysis SKILL

专业研报分析框架，提供 MECE、SWOT、产业链分析、影响评估等专业工具。
"""

__version__ = "1.0.0"
__author__ = "Kimi Claw"

from .frameworks.mece import MECEAnalyzer, analyze_energy_storage
from .frameworks.swot import SWOTGenerator, quick_swot
from .frameworks.impact_matrix import ImpactMatrix, quick_assess
from .frameworks.industry_chain import IndustryChain, analyze_industry_chain

__all__ = [
    'MECEAnalyzer',
    'analyze_energy_storage',
    'SWOTGenerator',
    'quick_swot',
    'ImpactMatrix',
    'quick_assess',
    'IndustryChain',
    'analyze_industry_chain',
]
