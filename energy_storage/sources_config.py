# 储能行业数据源配置
# 更新日期: 2026-03-03

# ============ 直接搜索源（当前主要使用） ============
SEARCH_SOURCES = {
    "ofweek": {
        "name": "OFweek储能网/锂电",
        "base_url": "https://libattery.ofweek.com",
        "search_pattern": "site:ofweek.com 储能 OR 固态电池 OR 钠电池",
        "reliability": "高",
        "update_frequency": "每日"
    },
    "bjx": {
        "name": "北极星储能网",
        "base_url": "https://news.bjx.com.cn",
        "search_pattern": "site:bjx.com.cn 储能",
        "reliability": "高",
        "update_frequency": "每日"
    },
    "escn": {
        "name": "中国储能网",
        "base_url": "http://www.escn.com.cn",
        "reliability": "高",
        "update_frequency": "每日"
    },
    "gg": {
        "name": "高工储能",
        "base_url": "https://www.gg-lb.com",
        "reliability": "高",
        "update_frequency": "每日"
    }
}

# ============ 财经数据源 ============
FINANCE_SOURCES = {
    "eastmoney": {
        "name": "东方财富",
        "api_type": "REST API",
        "data_type": "股票行情、资金流向",
        "stocks": [
            {"code": "300750", "name": "宁德时代", "category": "动力电池"},
            {"code": "002594", "name": "比亚迪", "category": "整车+电池"},
            {"code": "300014", "name": "亿纬锂能", "category": "动力电池"},
            {"code": "002074", "name": "国轩高科", "category": "动力电池"},
            {"code": "300438", "name": "鹏辉能源", "category": "储能电池"},
            {"code": "300068", "name": "南都电源", "category": "储能系统"},
            {"code": "300274", "name": "阳光电源", "category": "储能变流器"},
            {"code": "002335", "name": "科华数据", "category": "储能系统"},
            {"code": "002518", "name": "科士达", "category": "储能设备"},
            {"code": "688063", "name": "派能科技", "category": "户用储能"},
        ]
    },
    "sina": {
        "name": "新浪财经",
        "url": "https://finance.sina.com.cn/stock/",
        "data_type": "新闻、公告、研报"
    }
}

# ============ 政策/官方数据源 ============
POLICY_SOURCES = {
    "ndrc": {
        "name": "国家发改委",
        "url": "https://www.ndrc.gov.cn",
        "type": "政策发布"
    },
    "nea": {
        "name": "国家能源局",
        "url": "https://www.nea.gov.cn",
        "type": "行业政策"
    },
    "miit": {
        "name": "工信部",
        "url": "https://www.miit.gov.cn",
        "type": "产业政策"
    }
}

# ============ 国际数据源 ============
INTERNATIONAL_SOURCES = {
    "energy_storage_news": {
        "name": "Energy Storage News",
        "url": "https://www.energy-storage.news",
        "region": "全球"
    },
    "pv_magazine": {
        "name": "PV Magazine",
        "url": "https://www.pv-magazine.com",
        "region": "全球"
    },
    "bloomberg_nef": {
        "name": "BloombergNEF",
        "url": "https://about.bnef.com",
        "region": "全球",
        "note": "付费订阅"
    }
}

# ============ 监控关键词 ============
MONITOR_KEYWORDS = {
    "核心技术": [
        "固态电池", "半固态电池", "钠离子电池", "钠电池",
        "液流电池", "全钒液流", "压缩空气储能", "飞轮储能",
        "储能系统", "储能电站", "储能电池", "储能变流器",
        "BMS", "EMS", "电池管理系统"
    ],
    "重点企业": [
        "宁德时代", "比亚迪", "亿纬锂能", "国轩高科",
        "鹏辉能源", "南都电源", "派能科技", "海辰储能",
        "中科海钠", "宁德时代", "弗迪电池", "蜂巢能源",
        "中创新航", "欣旺达", "瑞浦兰钧"
    ],
    "应用场景": [
        "大储", "工商业储能", "户用储能", "便携式储能",
        "光储充", "新能源配储", "独立储能", "共享储能",
        "调峰调频", "电力现货市场"
    ],
    "政策市场": [
        "储能政策", "储能电价", "储能补贴", "强制配储",
        "电力市场化", "容量电价", "辅助服务", "需求侧响应"
    ]
}

# ============ 监控频率配置 ============
MONITOR_SCHEDULE = {
    "search_monitor": "每4小时",  # 搜索监控
    "rss_monitor": "每2小时",     # RSS监控（如可用）
    "stock_monitor": "交易日 9:00/15:00",  # 股票行情
    "daily_report": "每天 18:00",  # 日报
    "weekly_report": "每周一 09:00"  # 周报
}
