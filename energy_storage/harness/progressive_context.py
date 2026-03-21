#!/usr/bin/env python3
"""
Progressive Disclosure - 渐进式披露模块
根据任务复杂度分层加载上下文
"""

import json
import yaml
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum


class ContextLevel(Enum):
    """上下文层级"""
    SIMPLE = "simple"        # 简单任务
    COMPLEX = "complex"      # 复杂任务
    DIAGNOSTIC = "diagnostic"  # 诊断任务


@dataclass
class Context:
    """上下文数据"""
    level: ContextLevel
    data: Dict
    sources: List[str]
    loaded_at: str


class ContextLoader:
    """上下文加载器"""
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.cache = {}
    
    def _load_crawler_data(self, date: str) -> List[Dict]:
        """加载爬虫数据"""
        files = list((self.data_dir / 'crawler').glob(f'*{date}*.json'))
        data = []
        for f in files:
            try:
                with open(f) as fp:
                    items = json.load(fp)
                    if isinstance(items, list):
                        data.extend(items)
            except:
                pass
        return data
    
    def _load_news_data(self, date: str) -> List[Dict]:
        """加载搜索数据"""
        files = list((self.data_dir / 'news').glob(f'*{date}*.json'))
        data = []
        for f in files:
            try:
                with open(f) as fp:
                    items = json.load(fp)
                    if isinstance(items, list):
                        data.extend(items)
            except:
                pass
        return data
    
    def _load_stock_data(self, date: str) -> Optional[Dict]:
        """加载股票数据"""
        files = list((self.data_dir / 'stocks').glob(f'*{date}*.json'))
        if files:
            try:
                with open(files[0]) as fp:
                    return json.load(fp)
            except:
                pass
        return None
    
    def _load_historical_reports(self, days: int = 7) -> List[Dict]:
        """加载历史报告"""
        reports = []
        reports_dir = self.data_dir / 'reports'
        
        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).strftime('%Y%m%d')
            files = list(reports_dir.glob(f'*daily*{date}*.md'))
            for f in files[:1]:  # 每天只取一份
                try:
                    with open(f) as fp:
                        reports.append({
                            'date': date,
                            'content': fp.read()[:2000]  # 截取摘要
                        })
                except:
                    pass
        return reports
    
    def _load_error_history(self) -> List[Dict]:
        """加载错误历史"""
        error_log = Path(__file__).parent / 'error_log.jsonl'
        if not error_log.exists():
            return []
        
        errors = []
        with open(error_log) as f:
            for line in f:
                try:
                    errors.append(json.loads(line))
                except:
                    pass
        return errors[-20:]  # 最近20条
    
    def _load_system_logs(self, lines: int = 100) -> str:
        """加载系统日志"""
        logs = []
        # 爬虫日志
        crawler_log = self.data_dir.parent / 'logs' / 'crawler.log'
        if crawler_log.exists():
            with open(crawler_log) as f:
                logs.extend(f.readlines()[-lines:])
        return '\n'.join(logs)


class ProgressiveDisclosure:
    """渐进式披露系统"""
    
    def __init__(self, config_path: Optional[Path] = None, data_dir: Optional[Path] = None):
        if config_path is None:
            config_path = Path(__file__).parent / 'harness_config.yaml'
        
        with open(config_path) as f:
            self.config = yaml.safe_load(f)
        
        if data_dir is None:
            data_dir = Path('/root/.openclaw/workspace/energy_storage/data')
        
        self.loader = ContextLoader(data_dir)
        self.disclosure_config = self.config.get('components', {}).get('progressive_disclosure', {})
    
    def load_context(self, task_type: str, **kwargs) -> Context:
        """
        根据任务类型加载相应层级的上下文
        
        Args:
            task_type: 任务类型 (daily_report, weekly_report, crawler_monitor, diagnostic)
            **kwargs: 额外参数
            
        Returns:
            Context 对象
        """
        if task_type == 'daily_report':
            return self._load_simple_context(**kwargs)
        elif task_type == 'weekly_report':
            return self._load_complex_context(**kwargs)
        elif task_type in ['crawler_monitor', 'diagnostic']:
            return self._load_diagnostic_context(**kwargs)
        else:
            return self._load_simple_context(**kwargs)
    
    def _load_simple_context(self, date: Optional[str] = None) -> Context:
        """
        简单上下文 - 当日数据 + 基础模板
        用于：单日报生成
        """
        if date is None:
            date = datetime.now().strftime('%Y%m%d')
        
        data = {
            'date': date,
            'crawler_data': self.loader._load_crawler_data(date),
            'news_data': self.loader._load_news_data(date),
            'stock_data': self.loader._load_stock_data(date),
            'template': self._load_template('daily_report')
        }
        
        return Context(
            level=ContextLevel.SIMPLE,
            data=data,
            sources=[
                f'crawler/{date}',
                f'news/{date}',
                f'stocks/{date}',
                'templates/daily_report'
            ],
            loaded_at=datetime.now().isoformat()
        )
    
    def _load_complex_context(self, start_date: Optional[str] = None) -> Context:
        """
        复杂上下文 - 7天数据 + 历史对比 + 趋势分析
        用于：周报生成
        """
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=7)).strftime('%Y%m%d')
        
        end_date = datetime.now().strftime('%Y%m%d')
        
        # 收集7天数据
        week_data = []
        for i in range(7):
            date = (datetime.now() - timedelta(days=i)).strftime('%Y%m%d')
            day_data = {
                'date': date,
                'crawler': self.loader._load_crawler_data(date),
                'news': self.loader._load_news_data(date)
            }
            week_data.append(day_data)
        
        data = {
            'period': f'{start_date} - {end_date}',
            'week_data': week_data,
            'historical_reports': self.loader._load_historical_reports(days=14),
            'template': self._load_template('weekly_report')
        }
        
        return Context(
            level=ContextLevel.COMPLEX,
            data=data,
            sources=[
                'crawler/week',
                'news/week',
                'reports/historical',
                'templates/weekly_report'
            ],
            loaded_at=datetime.now().isoformat()
        )
    
    def _load_diagnostic_context(self, component: str = 'crawler') -> Context:
        """
        诊断上下文 - 日志 + 错误历史 + 修复方案库
        用于：异常处理、故障诊断
        """
        data = {
            'component': component,
            'system_logs': self.loader._load_system_logs(),
            'error_history': self.loader._load_error_history(),
            'repair_manual': self._load_repair_manual(component),
            'current_status': self._check_component_status(component)
        }
        
        return Context(
            level=ContextLevel.DIAGNOSTIC,
            data=data,
            sources=[
                'logs/system',
                'logs/errors',
                f'manuals/{component}',
                'status/current'
            ],
            loaded_at=datetime.now().isoformat()
        )
    
    def _load_template(self, template_name: str) -> str:
        """加载模板"""
        template_file = Path(__file__).parent / 'templates' / f'{template_name}.md'
        if template_file.exists():
            with open(template_file) as f:
                return f.read()
        return ""
    
    def _load_repair_manual(self, component: str) -> Dict:
        """加载修复手册"""
        manual_file = Path(__file__).parent / 'manuals' / f'{component}.json'
        if manual_file.exists():
            with open(manual_file) as f:
                return json.load(f)
        return {}
    
    def _check_component_status(self, component: str) -> Dict:
        """检查组件状态"""
        # 简单的状态检查
        status = {'component': component, 'status': 'unknown'}
        
        if component == 'crawler':
            # 检查最近是否有爬虫数据
            today = datetime.now().strftime('%Y%m%d')
            files = list(self.loader.data_dir.glob(f'data/crawler/*{today}*'))
            status['status'] = 'healthy' if files else 'no_data'
        
        return status
    
    def get_context_summary(self, context: Context) -> str:
        """获取上下文摘要"""
        summaries = {
            ContextLevel.SIMPLE: f"简单上下文: {len(context.data.get('crawler_data', []))} 条爬虫数据",
            ContextLevel.COMPLEX: f"复杂上下文: 7天数据, {len(context.data.get('historical_reports', []))} 份历史报告",
            ContextLevel.DIAGNOSTIC: f"诊断上下文: {len(context.data.get('error_history', []))} 条错误记录"
        }
        return summaries.get(context.level, "未知上下文类型")


def main():
    """测试渐进式披露系统"""
    pd = ProgressiveDisclosure()
    
    # 测试简单上下文
    simple = pd.load_context('daily_report')
    print(f"[SIMPLE] {pd.get_context_summary(simple)}")
    print(f"  Sources: {', '.join(simple.sources)}")
    
    # 测试复杂上下文
    complex_ctx = pd.load_context('weekly_report')
    print(f"\n[COMPLEX] {pd.get_context_summary(complex_ctx)}")
    print(f"  Sources: {', '.join(complex_ctx.sources)}")
    
    # 测试诊断上下文
    diagnostic = pd.load_context('crawler_monitor')
    print(f"\n[DIAGNOSTIC] {pd.get_context_summary(diagnostic)}")
    print(f"  Sources: {', '.join(diagnostic.sources)}")


if __name__ == '__main__':
    main()
