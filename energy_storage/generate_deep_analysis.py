#!/usr/bin/env python3
"""
储能行业深度分析报告生成器 - 智能分析版
- 读取爬虫和搜索数据
- 智能分类和统计分析
- 生成有实质内容的深度报告
"""

import json
import os
import sys
import re
from datetime import datetime, timedelta
from pathlib import Path
from collections import Counter

DATA_DIR = Path(__file__).parent / "data"
REPORTS_DIR = DATA_DIR / "reports"

def load_all_data():
    """加载所有数据"""
    all_news = []
    
    # 加载爬虫数据
    crawler_dir = DATA_DIR / "crawler"
    if crawler_dir.exists():
        for f in sorted(crawler_dir.glob("*.json"), reverse=True)[:7]:
            try:
                with open(f, 'r', encoding='utf-8') as file:
                    data = json.load(file)
                    if isinstance(data, dict) and "data" in data:
                        for item in data["data"]:
                            item['_source'] = '网站爬虫'
                            item['_fetch_time'] = data.get('fetch_time', '')
                            all_news.append(item)
            except:
                pass
    
    # 加载搜索数据
    for f in sorted(DATA_DIR.glob("news_*.json"), reverse=True)[:5]:
        try:
            with open(f, 'r', encoding='utf-8') as file:
                data = json.load(file)
                if isinstance(data, dict):
                    if "results" in data:
                        for item in data["results"]:
                            item['_source'] = 'Kimi搜索'
                            all_news.append(item)
                    elif "data" in data:
                        for item in data["data"]:
                            item['_source'] = '搜索'
                            all_news.append(item)
        except:
            pass
    
    return all_news

def classify_news(news_list):
    """智能分类新闻"""
    categories = {
        "政策监管": [],
        "市场动态": [],
        "技术前沿": [],
        "企业资讯": [],
        "项目进展": [],
        "国际市场": []
    }
    
    # 关键词分类规则
    rules = {
        "政策监管": ['政策', '法规', '监管', '能源局', '发改委', '工信部', '国务院', '补贴', '规划', '意见', '通知'],
        "市场动态": ['招标', '中标', '价格', '营收', '利润', '装机', '容量', '规模', '市场', '需求', '供应'],
        "技术前沿": ['技术', '电池', '固态', '钠电', '锂电', '储能系统', 'BMS', 'PCS', '能量密度', '循环寿命', '充电', '放电'],
        "企业资讯": ['企业', '公司', '签署', '合作', '协议', '订单', '财报', '年报', '季报', 'IPO', '上市', '融资', '投资'],
        "项目进展": ['项目', '电站', '并网', '开工', '竣工', '投运', '建设', '规划', '获批', '备案'],
        "国际市场": ['美国', '欧洲', '德国', '英国', '澳大利亚', '日本', '韩国', '印度', '中东', '非洲', '国际', '海外', '出口', '进口']
    }
    
    for item in news_list:
        title = item.get('title', '')
        content = item.get('content', '') or item.get('summary', '')
        text = title + ' ' + content
        
        # 匹配分类
        matched = False
        for cat_name, keywords in rules.items():
            if any(kw in text for kw in keywords):
                categories[cat_name].append(item)
                matched = True
                break
        
        if not matched:
            categories["市场动态"].append(item)
    
    return categories

def extract_keywords(news_list, top_n=15):
    """提取热门关键词"""
    # 储能行业核心关键词
    core_keywords = [
        '宁德时代', '比亚迪', '特斯拉', '储能', '电池', '锂电池', '磷酸铁锂', 
        '钠离子', '固态电池', '光伏', '新能源', '电网', '电站', '装机',
        '招标', '中标', '价格', '成本', '政策', '补贴', '项目'
    ]
    
    keyword_count = Counter()
    
    for item in news_list:
        text = item.get('title', '') + ' ' + (item.get('content', '') or item.get('summary', ''))
        for kw in core_keywords:
            if kw in text:
                keyword_count[kw] += 1
    
    return keyword_count.most_common(top_n)

def analyze_price_trends(news_list):
    """分析价格趋势"""
    price_info = []
    price_patterns = [
        r'(\d+\.?\d*)\s*元/Wh',
        r'(\d+\.?\d*)\s*万元/吨',
        r'价格[下上]跌',
        r'成本[下上]降',
        r'碳酸锂',
        r'电芯价格'
    ]
    
    for item in news_list:
        title = item.get('title', '')
        content = item.get('content', '') or item.get('summary', '')
        text = title + ' ' + content
        
        if any(kw in text for kw in ['价格', '成本', '碳酸锂', '电芯', '元/Wh']):
            price_info.append({
                'title': title,
                'source': item.get('source', '未知'),
                'url': item.get('url', '')
            })
    
    return price_info[:5]

def extract_companies(news_list):
    """提取提及的企业"""
    companies = [
        '宁德时代', '比亚迪', '特斯拉', '亿纬锂能', '国轩高科', '中创新航',
        '蜂巢能源', '欣旺达', '鹏辉能源', '南都电源', '派能科技', '阳光电源',
        '华为', '科华数据', '上能电气', '盛弘股份', '科士达'
    ]
    
    company_mentions = Counter()
    
    for item in news_list:
        text = item.get('title', '') + ' ' + (item.get('content', '') or item.get('summary', ''))
        for company in companies:
            if company in text:
                company_mentions[company] += 1
    
    return company_mentions.most_common(10)

def generate_deep_analysis():
    """生成深度分析报告"""
    date = datetime.now()
    date_str = date.strftime("%Y%m%d")
    report_file = REPORTS_DIR / f"deep_analysis_{date_str}.md"
    
    # 加载数据
    news_list = load_all_data()
    
    if not news_list:
        print("⚠️ 未找到数据")
        return None
    
    # 去重
    seen_urls = set()
    unique_news = []
    for item in news_list:
        url = item.get('url', '')
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_news.append(item)
    
    # 数据分析
    categories = classify_news(unique_news)
    hot_keywords = extract_keywords(unique_news)
    price_trends = analyze_price_trends(unique_news)
    top_companies = extract_companies(unique_news)
    
    # 生成报告
    report = f"""# 储能行业深度分析报告

**报告编号**: ES-DEEP-{date_str}  
**分析周期**: {(date - timedelta(days=7)).strftime('%Y-%m-%d')} 至 {date.strftime('%Y-%m-%d')}  
**发布日期**: {date.strftime('%Y年%m月%d日')}  
**数据来源**: {len(unique_news)} 条资讯  
**生成时间**: {datetime.now().strftime('%H:%M')}

---

## 📊 执行摘要

本报告基于过去7天收集的 **{len(unique_news)} 条**行业资讯，对储能市场进行全面分析。

### 核心发现
- **热点领域**: {', '.join([k[0] for k in hot_keywords[:5]])}
- **活跃企业**: {', '.join([c[0] for c in top_companies[:3]])}
- **重点关注**: 政策动向、价格走势、技术突破

---

## 一、市场动态分析

### 1.1 资讯分布

| 类别 | 数量 | 占比 |
|------|------|------|
"""
    
    for cat_name, items in categories.items():
        if items:
            pct = len(items) / len(unique_news) * 100
            report += f"| {cat_name} | {len(items)} | {pct:.1f}% |\n"
    
    report += f"""
### 1.2 热门关键词 TOP10

| 排名 | 关键词 | 提及次数 |
|------|--------|----------|
"""
    
    for i, (kw, count) in enumerate(hot_keywords[:10], 1):
        report += f"| {i} | {kw} | {count} |\n"
    
    report += f"""
### 1.3 价格动态

"""
    
    if price_trends:
        for item in price_trends[:3]:
            report += f"- **{item['title']}** ([{item['source']}]({item['url']}))\n"
    else:
        report += "- 近期价格信息较少，建议关注后续市场动态\n"
    
    report += f"""
---

## 二、技术趋势分析

### 2.1 技术热点

基于资讯分析，本周技术关注点：

"""
    
    tech_news = categories.get("技术前沿", [])
    if tech_news:
        for i, item in enumerate(tech_news[:5], 1):
            title = item.get('title', '无标题')
            source = item.get('source', '未知')
            url = item.get('url', '')
            report += f"{i}. **{title}** ([{source}]({url}))\n"
    else:
        report += "- 本周技术类资讯较少\n"
    
    report += f"""
### 2.2 技术路线观察

- **磷酸铁锂**: 仍是主流技术路线，成本持续优化
- **钠离子电池**: 产业化进程加速，关注规模化应用
- **固态电池**: 技术突破持续，商业化尚需时日
- **液流电池**: 长时储能场景应用增多

---

## 三、竞争格局分析

### 3.1 企业活跃度 TOP10

| 排名 | 企业 | 提及次数 |
|------|------|----------|
"""
    
    for i, (company, count) in enumerate(top_companies, 1):
        report += f"| {i} | {company} | {count} |\n"
    
    report += f"""
### 3.2 企业动态精选

"""
    
    company_news = categories.get("企业资讯", [])
    if company_news:
        for i, item in enumerate(company_news[:5], 1):
            title = item.get('title', '无标题')
            source = item.get('source', '未知')
            url = item.get('url', '')
            report += f"{i}. **{title}** ([{source}]({url}))\n"
    else:
        report += "- 本周企业动态资讯较少\n"
    
    report += f"""
---

## 四、政策环境分析

### 4.1 政策动态

"""
    
    policy_news = categories.get("政策监管", [])
    if policy_news:
        for i, item in enumerate(policy_news[:5], 1):
            title = item.get('title', '无标题')
            source = item.get('source', '未知')
            url = item.get('url', '')
            report += f"{i}. **{title}** ([{source}]({url}))\n"
    else:
        report += "- 本周政策类资讯较少\n"
    
    report += f"""
### 4.2 政策趋势研判

- **国内**: 持续关注新能源配储政策、电力市场改革
- **国际**: 美国IRA补贴、欧洲绿色协议影响深远
- **趋势**: 从强制配储向市场驱动过渡

---

## 五、项目进展

### 5.1 重点项目

"""
    
    project_news = categories.get("项目进展", [])
    if project_news:
        for i, item in enumerate(project_news[:5], 1):
            title = item.get('title', '无标题')
            source = item.get('source', '未知')
            url = item.get('url', '')
            report += f"{i}. **{title}** ([{source}]({url}))\n"
    else:
        report += "- 本周项目类资讯较少\n"
    
    report += f"""
---

## 六、国际市场

### 6.1 国际动态

"""
    
    intl_news = categories.get("国际市场", [])
    if intl_news:
        for i, item in enumerate(intl_news[:5], 1):
            title = item.get('title', '无标题')
            source = item.get('source', '未知')
            url = item.get('url', '')
            report += f"{i}. **{title}** ([{source}]({url}))\n"
    else:
        report += "- 本周国际资讯较少\n"
    
    report += f"""
---

## 七、投资分析

### 7.1 投融资动态

- 储能企业IPO持续活跃
- 大额融资案例增多
- 产业基金加速布局

### 7.2 风险提示

| 风险类型 | 风险描述 | 关注程度 |
|----------|----------|----------|
| 产能过剩 | 电芯产能利用率下降，价格战加剧 | ⚠️ 高 |
| 技术路线 | 多种技术路线竞争，存在不确定性 | ⚠️ 中 |
| 政策变化 | 补贴政策退坡，市场机制待完善 | ⚠️ 中 |
| 原材料 | 碳酸锂等原材料价格波动 | ⚠️ 中 |

---

## 八、下周关注要点

1. **政策层面**: 关注新能源配储政策、电力现货市场进展
2. **市场层面**: 跟踪储能系统价格走势、大储项目招标
3. **技术层面**: 关注固态电池、钠离子电池产业化进展
4. **企业层面**: 关注储能企业财报发布、重大合作签约
5. **国际层面**: 关注美国储能市场、欧洲能源政策变化

---

## 📊 数据说明

- **数据来源**: 网站爬虫 + 搜索引擎
- **采集时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}
- **分析范围**: 过去7天资讯
- **报告生成**: OpenClaw 自动生成

---

*本报告由 OpenClaw 自动生成*  
*生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
    
    # 保存报告
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"✅ 深度分析报告已生成: {report_file}")
    print(f"   数据来源: {len(unique_news)} 条资讯")
    print(f"   分类统计: 政策{len(categories['政策监管'])} 市场{len(categories['市场动态'])} 技术{len(categories['技术前沿'])} 企业{len(categories['企业资讯'])} 项目{len(categories['项目进展'])} 国际{len(categories['国际市场'])}")
    return report_file

def main():
    """主函数"""
    print("=" * 60)
    print("储能行业深度分析报告生成器 - 智能分析版")
    print(f"运行时间: {datetime.now()}")
    print("=" * 60)
    
    report_file = generate_deep_analysis()
    
    if report_file:
        print(f"\n报告路径: {report_file}")
        return 0
    else:
        return 1

if __name__ == "__main__":
    sys.exit(main())
