#!/usr/bin/env python3
"""
储能行业日报生成器 - 增强版
每条信息标注来源和获取时间
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
REPORTS_DIR = DATA_DIR / "reports"

def load_news_with_metadata():
    """加载新闻数据，保留元数据"""
    all_news = []
    
    # 加载爬虫数据
    crawler_dir = DATA_DIR / "crawler"
    if crawler_dir.exists():
        for f in sorted(crawler_dir.glob("*.json"), reverse=True)[:3]:
            try:
                with open(f, 'r', encoding='utf-8') as file:
                    data = json.load(file)
                    if isinstance(data, dict) and "data" in data:
                        for item in data["data"]:
                            item['_fetch_time'] = data.get('fetch_time', '')
                            item['_data_source'] = '网站爬虫'
                            all_news.append(item)
            except:
                pass
    
    # 加载搜索数据
    for f in sorted(DATA_DIR.glob("news_*.json"), reverse=True)[:2]:
        try:
            with open(f, 'r', encoding='utf-8') as file:
                data = json.load(file)
                if isinstance(data, dict):
                    if "results" in data:
                        for item in data["results"]:
                            item['_fetch_time'] = data.get('timestamp', '')
                            item['_data_source'] = 'Kimi搜索'
                            all_news.append(item)
                    elif "data" in data:
                        for item in data["data"]:
                            item['_fetch_time'] = data.get('fetch_time', '')
                            item['_data_source'] = data.get('sources', ['搜索'])[0]
                            all_news.append(item)
        except:
            pass
    
    return all_news

def format_source(item):
    """格式化来源信息"""
    source = item.get('source', '未知来源')
    url = item.get('url', '')
    fetch_time = item.get('_fetch_time', '')
    data_source = item.get('_data_source', '')
    
    # 简化时间显示
    if fetch_time:
        try:
            dt = datetime.fromisoformat(fetch_time.replace('Z', '+00:00'))
            fetch_time = dt.strftime('%m-%d %H:%M')
        except:
            pass
    
    return f"[{source}] [{fetch_time}]"

def generate_daily_report_enhanced(date=None):
    """生成增强版日报"""
    if date is None:
        date = datetime.now()
    
    date_str = date.strftime("%Y%m%d")
    report_file = REPORTS_DIR / f"report_{date_str}.md"
    
    # 加载新闻
    news_list = load_news_with_metadata()
    
    if not news_list:
        print("⚠️ 未找到新闻数据")
        return None
    
    # 去重（基于URL）
    seen_urls = set()
    unique_news = []
    for item in news_list:
        url = item.get('url', '')
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_news.append(item)
    
    # 分类
    categories = {
        "政策监管": [],
        "市场动态": [],
        "技术前沿": [],
        "企业资讯": [],
        "项目进展": [],
        "国际市场": []
    }
    
    for item in unique_news:
        title = item.get('title', '')
        
        # 简单分类逻辑
        if any(kw in title for kw in ['政策', '法规', '监管', '能源局', '发改委']):
            categories["政策监管"].append(item)
        elif any(kw in title for kw in ['市场', '招标', '中标', '价格', '营收']):
            categories["市场动态"].append(item)
        elif any(kw in title for kw in ['技术', '电池', '固态', '钠电', '储能系统']):
            categories["技术前沿"].append(item)
        elif any(kw in title for kw in ['企业', '公司', '签署', '合作', '年报']):
            categories["企业资讯"].append(item)
        elif any(kw in title for kw in ['项目', '电站', '并网', '开工']):
            categories["项目进展"].append(item)
        elif any(kw in title for kw in ['美国', '欧洲', '澳大利亚', '国际']):
            categories["国际市场"].append(item)
        else:
            # 默认分类
            categories["市场动态"].append(item)
    
    # 生成报告
    report = f"""# 储能行业日报 - {date.strftime('%Y年%m月%d日')}

> **数据时间范围**：{(date - timedelta(days=1)).strftime('%Y-%m-%d')} 18:00 至 {date.strftime('%Y-%m-%d')} 18:00  
> **统计资讯数量**：{len(unique_news)} 条  
> **报告生成时间**：{datetime.now().strftime('%Y-%m-%d %H:%M')}

---

## 📊 数据说明

| 字段 | 说明 |
|------|------|
| **来源** | 信息原始出处 |
| **获取时间** | 系统采集时间 |
| **[爬虫]** | 直接抓取自网站 |
| **[搜索]** | 通过搜索引擎获取 |

---

"""
    
    # 写入分类内容
    for cat_name, items in categories.items():
        if items:
            report += f"## {cat_name}\n\n"
            for i, item in enumerate(items[:10], 1):  # 每类最多10条
                title = item.get('title', '无标题')
                url = item.get('url', '')
                source_info = format_source(item)
                
                report += f"{i}. **{title}**\n"
                report += f"   - 📎 {source_info}\n"
                if url:
                    report += f"   - 🔗 [{url[:60]}...]({url})\n"
                report += "\n"
    
    # 添加数据来源汇总
    report += """---

## 📡 数据来源汇总

| 数据源 | 类型 | 说明 |
|--------|------|------|
| 中国储能网 | 网站爬虫 | 行业协会官方平台 |
| 北极星储能网 | 网站爬虫 | 电力能源门户 |
| OFweek储能 | 网站爬虫 | 高科技产业媒体 |
| 高工储能 | 网站爬虫 | 锂电产业链研究 |
| Kimi Search | 搜索引擎 | 全网最新资讯补充 |

---

*本报告由 OpenClaw 自动生成*  
*数据采集时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
    
    # 保存报告
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"✅ 增强版日报已生成: {report_file}")
    print(f"   统计资讯: {len(unique_news)} 条")
    return report_file

def main():
    """主函数"""
    print("=" * 60)
    print("储能行业日报生成器 - 增强版（带来源标注）")
    print(f"运行时间: {datetime.now()}")
    print("=" * 60)
    
    report_file = generate_daily_report_enhanced()
    
    if report_file:
        print(f"\n报告路径: {report_file}")
        return 0
    else:
        return 1

if __name__ == "__main__":
    sys.exit(main())
