# 储能行业监控配置
# 核心定位: 新型电力系统稳定器 - 解决风光间歇性，实现削峰填谷
# 更新日期: 2026-03-07

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

# 关键词监控 - 按核心定位分类
KEYWORDS = {
    # 核心使命
    "新型电力系统": [
        "新型电力系统", "新能源并网", "风光消纳", "可再生能源并网",
        "电网稳定性", "电力平衡", "削峰填谷"
    ],
    
    # 储能系统集成
    "储能系统集成": [
        "储能系统集成", "大型储能", "独立储能", "共享储能",
        "压缩空气储能", "飞轮储能", "储热", "储冷", "氢能储能"
    ],
    
    # 电池技术
    "电池技术": [
        "锂电池", "磷酸铁锂", "钠离子电池", "钠电池",
        "液流电池", "全钒液流", "固态电池", "半固态电池"
    ],
    
    # PCS与电力电子
    "PCS": [
        "储能变流器", "PCS", "逆变器", "构网型储能", "grid-forming",
        "高压直挂", "级联式储能"
    ],
    
    # 消防与安全
    "储能消防": [
        "储能消防", "储能安全", "电池热失控", "pack级消防", "全氟己酮"
    ],
    
    # 运维
    "运维": [
        "储能运维", "BMS", "EMS", "电池管理系统", "能量管理系统", "智能运维"
    ],
    
    # 虚拟电厂
    "虚拟电厂": [
        "虚拟电厂", "VPP", "聚合商", "源网荷储", "微电网", "车网互动", "V2G"
    ],
    
    # 政策与市场
    "政策市场": [
        "储能政策", "储能标准", "储能调度", "电力现货市场", "容量电价", "辅助服务"
    ]
}

# 重点企业监控
FOCUS_COMPANIES = [
    "宁德时代", "比亚迪", "亿纬锂能", "国轩高科",
    "鹏辉能源", "南都电源", "派能科技", "海辰储能",
    "阳光电源", "科华数据", "上能电气", "南网科技"
]

# 报告生成时间 (每天)
REPORT_TIME = "18:00"

# 监控频率 (分钟)
MONITOR_INTERVAL_MINUTES = 30
