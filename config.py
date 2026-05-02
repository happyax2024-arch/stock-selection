"""Global configuration for the A-Share Stock Screening System."""
from pathlib import Path

# Project root
ROOT_DIR = Path(__file__).parent
CACHE_DIR = ROOT_DIR / "cache"

# Cache TTL in seconds
CACHE_TTL = {
    "stock_list": 604800,       # 7 days
    "hist_daily": 14400,        # 4 hours
    "spot_snapshot": 60,        # 60 seconds
    "earnings": 86400,          # 24 hours
    "zt_history": 3600,         # 1 hour
    "global_news": 60,          # 60 seconds
}

# Market hours (CST)
MARKET_OPEN = (9, 30)
MARKET_CLOSE = (15, 0)

# Eastmoney API
EM_SPOT_URL = "https://push2.eastmoney.com/api/qt/clist/get"
EM_KLINE_URL = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
EM_FIELDS = (
    "f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f14,f15,f16,f17,f18,f20,f21,f37,f38,f39,"
    "f40,f41,f45,f46,f48,f49,f50,f57,f58,f62,f66,f69,f72,f75,f78,f81,f84,f87,"
    "f117,f124,f128,f135,f136,f137,f138,f139,f140,f141,f152,f167,f168,f169,"
    "f170,f171,f184,f185,f186,f187,f188,f189,f190,f191,f192,f193,f204,f205"
)

# Board-specific limit-up thresholds
def get_limit_threshold(code: str) -> float:
    if code.startswith(('300', '301')):   # ChiNext
        return 20.0
    elif code.startswith('688'):          # STAR
        return 20.0
    elif code.startswith(('8', '4')):     # BSE
        return 30.0
    else:
        return 10.0                       # Main board
