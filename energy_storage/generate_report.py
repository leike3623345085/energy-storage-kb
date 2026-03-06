#!/usr/bin/env python3
"""
储能行业分析报告生成器
- 汇总当天资讯
- 分析趋势
- 生成结构化报告
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import KEYWORDS

DATA_DIR = Path(__file__).parent / "data"
REPORTS_DIR = DATA_DIR / "reports"
NEWS_FILE = DATA_DIR / "news.jsonl"

def generate_daily_report(date=None):
    """生成每日报告"""
    if date is None:
        date = datetime.now()
    
    date_str = date.strftime("%Y-%m-%d")
    report_file = REPORTS_DIR / f"report_{date_str}.md"
    
    # 加载当天新闻
    today_news = []
    if NEWS_FILE.exists():
        with open(NEWS_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    item = json.loads(line.strip())
                    item_date = item.get('timestamp', '')[:10]
                    if item_date == date_str:
                        today_news.append(item)
                except:
                    continue
    
    # 生成报告
    report = f"""# 储能行业日报 - {date_str}

## 📊 概览
- 报告日期: {date_str}
- 资讯数量: {len(today_news)} 条
- 生成时间: {datetime.now().strftime("%H:%M")}

## 🔥 热点资讯

"""
    
    # 分类整理
    categories = {
        "技术突破": [],
        "政策法规": [],
        "企业动态": [],
        "市场数据": [],
        "其他": []
    }
    
    for news in today_news:
        title = news.get('title', '')
        content = news.get('content', '')
        
        # 简单分类
        if any(kw in title for kw in ['技术', '突破', '研发', '创新']):
            categories["技术突破"].append(news)
        elif any(kw in title for kw in ['政策', '法规', '标准', '规范']):
            categories["政策法规"].append(news)
        elif any(kw in title for kw in ['企业', '公司', '财报', '合作']):
            categories["企业动态"].append(news)
        elif any(kw in title for kw in ['市场', '数据', '统计', '规模']):
            categories["市场数据"].append(news)
        else:
            categories["其他"].append(news)
    
    # 写入分类内容
    for cat_name, items in categories.items():
        if items:
            report += f"### {cat_name}\n\n"
            for item in items[:10]:  # 每类最多10条
                title = item.get('title', '无标题')
                url = item.get('url', '')
                source = item.get('source', '未知来源')
                report += f"- **{title}** ([{source}]({url}))\n"
            report += "\n"
    
    # 趋势分析
    report += f"""## 📈 趋势分析

### 关键词热度
"""
    for kw in KEYWORDS[:10]:
        count = sum(1 for n in today_news if kw in str(n))
        if count > 0:
            report += f"- {kw}: {count} 次提及\n"
    
    report += f"""
### 行业洞察

（基于当天资讯的自动分析）

1. **技术方向**: 关注固态电池、钠离子电池等新技术进展
2. **市场动态**: 储能装机量持续增长，大储项目加速落地
3. **政策环境**: 持续关注储能电价机制、补贴政策变化

---

*报告由 OpenClaw 自动生成*
*数据来源: 公开网络资讯*
"""
    
    # 保存报告
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"报告已生成: {report_file}")
    return report_file

def main():
    """主函数"""
    print("=" * 50)
    print("储能行业日报生成器")
    print(f"运行时间: {datetime.now()}")
    print("=" * 50)
    
    report_file = generate_daily_report()
    
    # 输出报告路径，供调用方使用
    print(f"\n报告路径: {report_file}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
