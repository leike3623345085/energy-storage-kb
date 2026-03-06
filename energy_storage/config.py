# 储能行业监控配置
# 定义要监控的数据源

SOURCES = {
    # 中文资讯源
    "cn_energy_trend": {
        "name": "集邦新能源",
        "url": "https://newenergy.ofweek.com/",
        "type": "news",
        "category": "储能"
    },
    "cn_energy_storage": {
        "name": "中国储能网",
        "url": "http://www.escn.com.cn/",
        "type": "news",
        "category": "储能"
    },
    "cn_pv_info": {
        "name": "光伏资讯",
        "url": "https://www.pv-info.com/",
        "type": "news",
        "category": "光伏储能"
    },
    "cn_36kr_energy": {
        "name": "36氪新能源",
        "url": "https://36kr.com/search/articles/储能",
        "type": "news",
        "category": "储能"
    },
    
    # 国际资讯源
    "en_energy_storage_news": {
        "name": "Energy Storage News",
        "url": "https://www.energy-storage.news/",
        "type": "news",
        "category": "储能"
    },
    "en_pv_magazine": {
        "name": "PV Magazine",
        "url": "https://www.pv-magazine.com/",
        "type": "news",
        "category": "光伏储能"
    },
    "en_battery_news": {
        "name": "Battery News",
        "url": "https://www.batterypoweronline.com/",
        "type": "news",
        "category": "电池"
    }
}

# 关键词监控
KEYWORDS = [
    "储能", "电池", "锂电池", "钠电池", "固态电池",
    "储能电站", "储能系统", "储能技术",
    "宁德时代", "比亚迪", "亿纬锂能", "国轩高科",
    "energy storage", "battery", "lithium", 
    "solid state battery", "BESS", "grid storage"
]

# 报告生成时间 (每天)
REPORT_TIME = "18:00"

# 监控频率 (分钟)
MONITOR_INTERVAL_MINUTES = 30
