"""
2026 US Stock Watchlist
=======================

交易策略输入股票池，按行业板块分类。
来源: X友推荐、用户补充、涨幅榜

Version: 2026-watchlist-sector-v3
"""

# 来源说明
SOURCES = [
    "X友推荐美股2026潜力股名单",
    "用户补充10只（MU, AMD, CIEN, CLS, COHR, ALL, INCY, B, WLDN, ATI）",
    "用户新增涨幅榜（BKKT, RCAT, OKLO, UAMY, ONDS, NVTS, SNDX, EOSE, AEHR, APLD, ASTS, ACMR, IREN, OSCR, RKLB, MU, SOUN, NBIS）"
]

# 近期涨幅榜新增
DELTA_ADDITIONS = [
    {"ticker": "BKKT", "change_pct": 63},
    {"ticker": "RCAT", "change_pct": 49},
    {"ticker": "NVTS", "change_pct": 42},
    {"ticker": "SNDX", "change_pct": 40},
    {"ticker": "EOSE", "change_pct": 33},
    {"ticker": "AEHR", "change_pct": 32},
    {"ticker": "APLD", "change_pct": 30},
    {"ticker": "RKLB", "change_pct": 22},
    {"ticker": "SOUN", "change_pct": 19}
]

# =========================================
# 行业板块分类
# =========================================

SECTORS = {
    "Semiconductor_and_Hardware": {
        "description": "半导体/芯片/EDA/硬件",
        "tickers": ["NVDA", "AMD", "ASML", "MU", "INTC", "SNPS", "AAOI", "ACMR", "AEHR", "NVTS"],
    },
    
    "Optical_Networking_and_DataCenter": {
        "description": "光模块/网络通信/数据中心互联（AI算力网络）",
        "tickers": ["CIEN", "CLS", "COHR", "AAOI", "APLD"],
    },
    
    "AI_Infra_and_Software": {
        "description": "AI平台/企业软件/数据中心/机器人/算力基础设施/AI语音交互",
        "tickers": ["PLTR", "U", "PATH", "BBAI", "SYM", "TEM", "NBIS", "GUPS", "ELVA", "RR", "WLDN", "SOUN"],
    },
    
    "Space_and_eVTOL": {
        "description": "航天/卫星通信/飞行汽车/商业航天",
        "tickers": ["ACHR", "JOBY", "ASTS", "LUNR", "SIDU", "RDW", "SPCE", "RKLB", "RCAT"],
    },
    
    "Energy_and_Mining": {
        "description": "能源/矿业/稀土/核相关/资源品/储能",
        "tickers": ["CVX", "CCJ", "LEU", "SMR", "UUUU", "UAMY", "HYMC", "AG", "ALT", "NFE", "AREC", "HUT", "IREN", "WULF", "B", "OKLO", "EOSE"],
    },
    
    "Biotech_and_Healthcare": {
        "description": "生物医药/医疗健康/医疗技术",
        "tickers": ["LLY", "NVO", "CRML", "LEGN", "PRME", "OSCR", "HIMS", "TEN", "NNOX", "INCY", "SNDX"],
    },
    
    "Crypto_and_Blockchain": {
        "description": "加密交易/挖矿/区块链基础设施",
        "tickers": ["CIFR", "CLSK", "BTDR", "HUT", "IREN", "WULF", "BKKT"],
    },
    
    "Other_SpecialSituations": {
        "description": "特殊题材/小众赛道/难归类",
        "tickers": ["ARQQ", "ONDS", "OSS", "POET", "PPTA", "SPIR", "SUPX", "ZETA", "BE", "BEP", "MARA", "MSTR", "MCO", "SE", "KRKNF", "NVX", "PL", "RVPX"],
    },
    
    "ETFs_and_Leveraged_ETFs": {
        "description": "指数ETF/行业ETF/杠杆ETF",
        "tickers": ["QQQ", "SQQQ", "REMX", "VNM", "NKL", "GGLL"],
    },
}

# =========================================
# 重点股票投资论点
# =========================================

STOCK_NOTES = {
    "MU": {
        "sector": "Semiconductor_and_Hardware",
        "change_pct": 20,
        "thesis": "HBM与闪存技术领先，FY2026Q1业绩大超预期，估值较行业折让，具备补涨空间。",
        "keywords": ["HBM", "DRAM", "NAND", "AI memory", "valuation discount"]
    },
    "ACMR": {
        "sector": "Semiconductor_and_Hardware",
        "change_pct": 24,
        "thesis": "半导体清洗/湿法设备厂商，受益先进制程与资本开支周期。",
        "keywords": ["semi equipment", "wafer cleaning", "capex cycle"]
    },
    "AEHR": {
        "sector": "Semiconductor_and_Hardware",
        "change_pct": 32,
        "thesis": "半导体测试设备相关（烧机/测试），受益SiC/功率半导体与车规测试需求。",
        "keywords": ["test equipment", "burn-in", "SiC", "power semis"]
    },
    "NVTS": {
        "sector": "Semiconductor_and_Hardware",
        "change_pct": 42,
        "thesis": "功率半导体（GaN）方向，受益数据中心电源、快充、汽车电子。",
        "keywords": ["GaN", "power semis", "data center power", "fast charging"]
    },
    "APLD": {
        "sector": "Optical_Networking_and_DataCenter",
        "change_pct": 30,
        "thesis": "AI数据中心/算力基础设施相关（高弹性），受益AI算力需求外溢与数据中心扩张。",
        "keywords": ["AI data center", "HPC", "compute infra", "colocation"]
    },
    "SOUN": {
        "sector": "AI_Infra_and_Software",
        "change_pct": 19,
        "thesis": "AI语音/对话交互赛道，受益车载、客服、语音助手等端侧应用扩张。",
        "keywords": ["voice AI", "conversational AI", "edge AI", "automotive"]
    },
    "RKLB": {
        "sector": "Space_and_eVTOL",
        "change_pct": 22,
        "thesis": "商业航天与发射服务，航天产业化加速背景下具备订单与产业链地位优势。",
        "keywords": ["space launch", "satellite", "commercial space"]
    },
    "RCAT": {
        "sector": "Space_and_eVTOL",
        "change_pct": 49,
        "thesis": "无人机/国防科技方向（偏航天军工链），订单驱动，题材属性强，高波动。",
        "keywords": ["drone", "defense tech", "UAV", "contracts"]
    },
    "OKLO": {
        "sector": "Energy_and_Mining",
        "change_pct": 48,
        "thesis": "小型核能/先进核裂变方向，属于能源结构转型+AI耗电增长共振赛道。",
        "keywords": ["nuclear", "SMR", "advanced fission", "AI power demand"]
    },
    "EOSE": {
        "sector": "Energy_and_Mining",
        "change_pct": 33,
        "thesis": "长时储能（LDES）方向，高赔率能源科技票，订单落地与政策驱动敏感。",
        "keywords": ["LDES", "energy storage", "grid storage"]
    },
    "SNDX": {
        "sector": "Biotech_and_Healthcare",
        "change_pct": 40,
        "thesis": "生物科技（肿瘤/创新药）方向，高风险高回报，核心看临床数据/获批节奏。",
        "keywords": ["biotech", "oncology", "clinical catalyst"]
    },
    "BKKT": {
        "sector": "Crypto_and_Blockchain",
        "change_pct": 63,
        "thesis": "加密交易/托管/支付相关平台型题材股，弹性极高，受情绪与市场周期影响显著。",
        "keywords": ["crypto platform", "custody", "trading", "sentiment-driven"]
    },
}


def get_all_tickers() -> list:
    """获取所有股票代码（去重）"""
    all_tickers = set()
    for sector in SECTORS.values():
        all_tickers.update(sector["tickers"])
    return sorted(list(all_tickers))


def get_sector_tickers(sector_name: str) -> list:
    """获取指定板块的股票"""
    return SECTORS.get(sector_name, {}).get("tickers", [])


def get_high_momentum_tickers(min_change_pct: float = 30) -> list:
    """获取高动量股票（涨幅超过指定阈值）"""
    return [
        t["ticker"] for t in DELTA_ADDITIONS 
        if t["change_pct"] >= min_change_pct
    ]


# =========================================
# 快速访问列表
# =========================================

# 所有股票
ALL_TICKERS = get_all_tickers()

# 高动量股票 (涨幅 >= 30%)
HIGH_MOMENTUM = get_high_momentum_tickers(30)

# 核心 AI 相关
AI_RELATED = (
    SECTORS["Semiconductor_and_Hardware"]["tickers"] +
    SECTORS["Optical_Networking_and_DataCenter"]["tickers"] +
    SECTORS["AI_Infra_and_Software"]["tickers"]
)

# 高波动题材股
HIGH_BETA = ["BKKT", "RCAT", "NVTS", "SNDX", "EOSE", "OKLO", "ONDS"]

if __name__ == "__main__":
    print(f"📊 2026 US Stock Watchlist")
    print(f"=" * 50)
    print(f"Total Stocks: {len(ALL_TICKERS)}")
    print(f"High Momentum: {HIGH_MOMENTUM}")
    print(f"\nSectors:")
    for name, sector in SECTORS.items():
        print(f"  {name}: {len(sector['tickers'])} stocks")
