"""Central data gateway: AKShare data fetching.

Uses Sina data sources primarily (more stable from mainland China).
Falls back to Eastmoney where Sina equivalents aren't available.
"""
import time
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

from config import CACHE_DIR, CACHE_TTL
from data.cache import CacheManager

cache = CacheManager(CACHE_DIR, CACHE_TTL)
_fetch_lock = threading.Lock()


def get_stock_list() -> pd.DataFrame:
    """Get full A-share stock list (code + name) from Sina."""
    cached = cache.get("stock_list", "all")
    if cached is not None:
        return cached

    import akshare as ak
    df = ak.stock_info_a_code_name()
    df = df.rename(columns={"code": "code", "name": "name"})
    df["code"] = df["code"].astype(str).str.zfill(6)
    cache.set("stock_list", "all", df)
    return df


def get_spot_snapshot() -> pd.DataFrame:
    """Get real-time market snapshot from Sina (real-time during trading hours)."""
    cached = cache.get("spot_snapshot", "all")
    if cached is not None:
        return cached

    import akshare as ak
    try:
        df = ak.stock_zh_a_spot()
        if df is not None and not df.empty:
            col_map = {
                "代码": "code", "名称": "name",
                "最新价": "price", "涨跌幅": "change_pct",
                "涨跌额": "change_amount", "成交量": "volume",
                "成交额": "amount",
                "最高": "high", "最低": "low",
                "今开": "open", "昨收": "prev_close",
                "买入": "bid", "卖出": "ask",
            }
            existing = {k: v for k, v in col_map.items() if k in df.columns}
            df = df.rename(columns=existing)
            # Normalize code: strip exchange prefix (sz/sh/bj) and pad to 6 digits
            df["code"] = df["code"].astype(str).str.replace(r'^(sz|sh|bj)', '', regex=True).str.zfill(6)
            # Add missing columns as NaN
            for col in ["turnover", "pe", "market_cap", "circ_market_cap", "amplitude"]:
                if col not in df.columns:
                    df[col] = None
            cache.set("spot_snapshot", "all", df)
            return df
    except Exception:
        pass

    # Fallback: try Eastmoney version
    try:
        df = ak.stock_zh_a_spot_em()
        if df is not None and not df.empty:
            col_map = {
                "代码": "code", "名称": "name",
                "最新价": "price", "涨跌幅": "change_pct",
                "涨跌额": "change_amount", "成交量": "volume",
                "成交额": "amount", "振幅": "amplitude",
                "换手率": "turnover", "市盈率-动态": "pe",
                "最高": "high", "最低": "low",
                "今开": "open", "昨收": "prev_close",
                "总市值": "market_cap",
            }
            existing = {k: v for k, v in col_map.items() if k in df.columns}
            df = df.rename(columns=existing)
            df["code"] = df["code"].astype(str).str.zfill(6)
            cache.set("spot_snapshot", "all", df)
            return df
    except Exception:
        pass
    return pd.DataFrame()


def _to_sina_code(code: str) -> str:
    """Convert 6-digit code to Sina format (sz000001, sh600001, bj8xxxxx)."""
    code = str(code).zfill(6)
    if code.startswith(("60", "68")):
        return f"sh{code}"
    elif code.startswith(("8", "4")):
        return f"bj{code}"
    else:
        return f"sz{code}"


def get_daily_hist(code: str, days: int = 120) -> pd.DataFrame:
    """Get daily OHLCV history for a single stock. Tries Sina first, then Eastmoney."""
    cached = cache.get("hist_daily", f"{code}:{days}")
    if cached is not None:
        return cached

    import akshare as ak

    # Try Sina source first
    try:
        sina_code = _to_sina_code(code)
        df = ak.stock_zh_a_daily(
            symbol=sina_code, adjust="qfq",
        )
        if df is not None and not df.empty:
            col_map = {
                "date": "date", "open": "open", "high": "high",
                "low": "low", "close": "close", "volume": "volume",
                "amount": "amount",
            }
            existing = {k: v for k, v in col_map.items() if k in df.columns}
            df = df.rename(columns=existing)
            # Sina daily may not have turnover and change_pct; compute if missing
            if "change_pct" not in df.columns:
                df["change_pct"] = df["close"].pct_change() * 100
            if "turnover" not in df.columns:
                df["turnover"] = 0.0
            df["date"] = pd.to_datetime(df["date"])
            needed_cols = ["date", "open", "high", "low", "close", "volume", "amount", "turnover", "change_pct"]
            df = df[[c for c in needed_cols if c in df.columns]]
            df = df.sort_values("date").tail(days).reset_index(drop=True)
            if len(df) >= 20:
                cache.set("hist_daily", f"{code}:{days}", df)
                return df
    except Exception:
        pass

    # Fallback: Eastmoney
    try:
        df = ak.stock_zh_a_hist(
            symbol=code, period="daily",
            start_date="20200101", end_date="20991231",
            adjust="qfq",
        )
        if df is not None and not df.empty:
            col_map = {
                "日期": "date", "开盘": "open", "最高": "high",
                "最低": "low", "收盘": "close", "成交量": "volume",
                "成交额": "amount", "振幅": "amplitude",
                "涨跌幅": "change_pct", "涨跌额": "change_amount",
                "换手率": "turnover",
            }
            existing = {k: v for k, v in col_map.items() if k in df.columns}
            df = df.rename(columns=existing)
            df["date"] = pd.to_datetime(df["date"])
            needed_cols = ["date", "open", "high", "low", "close", "volume", "amount", "turnover", "change_pct"]
            df = df[[c for c in needed_cols if c in df.columns]]
            df = df.sort_values("date").tail(days).reset_index(drop=True)
            cache.set("hist_daily", f"{code}:{days}", df)
            return df
    except Exception:
        pass
    return pd.DataFrame()


def get_daily_hist_batch(codes: list[str], days: int = 120, progress_cb=None) -> dict[str, pd.DataFrame]:
    """Get daily history for multiple stocks with parallel cache reads, serialized API calls.

    Progress callbacks fire from the main thread (via as_completed loop), not from workers,
    so Streamlit widgets update reliably.
    """
    result = {}
    total = len(codes)
    fetch_lock = threading.Lock()  # Protects AKShare calls (py_mini_racer is not thread-safe)
    cache_hits = [0]

    def fetch_one(code: str) -> tuple[str, pd.DataFrame, bool]:
        # Check cache first (no lock needed — read-only)
        cached = cache.get("hist_daily", f"{code}:{days}")
        if cached is not None:
            return code, cached, True  # True = cache hit

        # Serialize AKShare API calls to avoid py_mini_racer crash
        with fetch_lock:
            df = get_daily_hist(code, days)

        return code, df, False  # False = API fetch

    max_workers = min(8, total)
    completed = 0
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fetch_one, code): code for code in codes}
        for future in as_completed(futures):
            try:
                code, df, from_cache = future.result(timeout=60)
                completed += 1
                if from_cache:
                    cache_hits[0] += 1
                if not df.empty:
                    result[code] = df
                # Fire progress from main thread — safe for Streamlit widgets
                if progress_cb:
                    progress_cb(completed, total, code, cache_hits[0])
            except Exception:
                completed += 1
                if progress_cb:
                    progress_cb(completed, total, "", cache_hits[0])

    return result


def get_earnings(code: str) -> float | None:
    """Get latest net profit for a stock. Returns net profit in 亿元 or None."""
    import akshare as ak
    cached = cache.get("earnings", code)
    if cached is not None:
        val = cached.iloc[0, 0] if not cached.empty else None
        return val

    try:
        df = ak.stock_yjkb_em(date="最新报告期")
        if df is not None and not df.empty:
            row = df[df["股票代码"].astype(str).str.zfill(6) == code]
            if not row.empty:
                profit = float(row["净利润"].iloc[0])
                result_df = pd.DataFrame({"profit": [profit]})
                cache.set("earnings", code, result_df)
                return profit
    except Exception:
        pass
    return None


def get_stock_detail(code: str, spot_data: pd.DataFrame | None = None) -> dict:
    """Get comprehensive stock detail info from available sources."""
    cached = cache.get("stock_detail", code)
    if cached is not None:
        return dict(zip(cached.iloc[:, 0], cached.iloc[:, 1]))

    info = {"股票代码": code}

    # Build from spot data (Sina real-time)
    if spot_data is not None and not spot_data.empty:
        row = spot_data[spot_data["code"].astype(str).str.zfill(6) == str(code).zfill(6)]
        if not row.empty:
            r = row.iloc[0]
            spot_fields = {
                "price": "最新价", "change_pct": "涨跌幅",
                "change_amount": "涨跌额", "volume": "成交量",
                "amount": "成交额", "high": "最高", "low": "最低",
                "open": "今开", "prev_close": "昨收",
                "bid": "买入", "ask": "卖出",
                "market_cap": "总市值", "pe": "市盈率-动态",
                "turnover": "换手率", "circ_market_cap": "流通市值",
            }
            for src, dest in spot_fields.items():
                val = r.get(src)
                if val is not None and str(val) not in ("", "nan", "None"):
                    info[dest] = val

    # Supplement with financial data for market cap/PE if missing
    if info.get("总市值") is None:
        try:
            fin = get_financial_summary(code)
            if fin is not None and not fin.empty:
                # Try to extract market cap from financial data
                pass
        except Exception:
            pass

    # Try AKShare individual info as supplement (may fail on some networks)
    import akshare as ak
    try:
        df = ak.stock_individual_info_em(symbol=code)
        if df is not None and not df.empty:
            em_info = dict(zip(df["item"], df["value"]))
            for k, v in em_info.items():
                if k not in info or info.get(k) in (None, "N/A", ""):
                    info[k] = v
    except Exception:
        pass

    # Default fields
    for key in ["最新价", "涨跌幅", "总市值", "流通市值", "市盈率-动态",
                "行业", "上市时间", "最高", "最低", "今开", "昨收",
                "成交量", "成交额", "换手率"]:
        info.setdefault(key, "N/A")

    if info:
        result_df = pd.DataFrame({"item": list(info.keys()), "value": [str(v) for v in info.values()]})
        cache.set("stock_detail", code, result_df)
    return info


def get_financial_summary(code: str) -> pd.DataFrame:
    """Get key financial indicators summary: revenue, profit, growth, ROE, EPS, etc."""
    import akshare as ak
    cached = cache.get("finance_summary", code)
    if cached is not None:
        return cached

    try:
        df = ak.stock_financial_abstract(symbol=code)
        if df is not None and not df.empty:
            # Filter to key indicators only
            key_items = [
                "归母净利润", "营业总收入", "扣非净利润",
                "营业利润", "利润总额",
                "基本每股收益", "稀释每股收益",
                "加权净资产收益率", "毛利率", "净利率",
                "资产负债率", "流动比率", "速动比率",
                "经营活动现金流净额",
            ]
            available = [i for i in key_items if i in df["指标"].values]
            filtered = df[df["指标"].isin(available)]
            # Keep only the most recent 10 quarters
            date_cols = ["选项", "指标"] + [c for c in df.columns if c not in ["选项", "指标"]][:10]
            filtered = filtered[[c for c in date_cols if c in filtered.columns]]
            cache.set("finance_summary", code, filtered)
            return filtered
    except Exception:
        pass
    return pd.DataFrame()


def get_financial_growth(code: str) -> pd.DataFrame:
    """Get YoY growth rates for key metrics. Uses financial abstract data."""
    cached = cache.get("finance_growth", code)
    if cached is not None:
        return cached

    # Try Eastmoney profit sheet first
    import akshare as ak
    try:
        df = ak.stock_profit_sheet_by_report_em(symbol=code)
        if df is not None and not df.empty:
            key_cols = [
                "报告期", "营业总收入", "营业总收入同比",
                "归母净利润", "归母净利润同比",
                "扣非净利润", "扣非净利润同比",
                "基本每股收益", "加权净资产收益率",
            ]
            available = [c for c in key_cols if c in df.columns]
            if available:
                result = df[available].head(12)
                cache.set("finance_growth", code, result)
                return result
    except Exception:
        pass

    # Fallback: derive from financial abstract
    try:
        abs_df = get_financial_summary(code)
        if abs_df is not None and not abs_df.empty:
            # Transpose: dates as rows, indicators as columns
            growth_df = abs_df.set_index("指标").T
            growth_df = growth_df.reset_index()
            growth_df = growth_df.rename(columns={"index": "报告期"})
            # Keep last 12 periods
            growth_df = growth_df.head(12)
            cache.set("finance_growth", code, growth_df)
            return growth_df
    except Exception:
        pass
    return pd.DataFrame()


def get_stock_news(code: str, limit: int = 20) -> pd.DataFrame:
    """Get recent news for a specific stock via Sina finance."""
    import requests
    cached = cache.get("stock_news", f"{code}:{limit}")
    if cached is not None:
        return cached

    items = []
    # Sina stock-specific news
    try:
        url = "https://feed.mix.sina.com.cn/api/roll/get"
        params = {
            "pageid": "154",
            "lid": "2513",
            "k": str(code),
            "num": str(limit),
            "page": "1",
        }
        resp = requests.get(url, params=params, timeout=15)
        data = resp.json()
        if data.get("result") and data["result"].get("data"):
            for item in data["result"]["data"]:
                items.append({
                    "title": item.get("title", ""),
                    "source": item.get("media_name", "新浪财经"),
                    "time": item.get("ctime", ""),
                    "url": item.get("url", ""),
                    "summary": item.get("intro", ""),
                })
    except Exception:
        pass

    # Fallback: Eastmoney stock news
    if not items:
        try:
            url = "https://push2his.eastmoney.com/api/qt/stock/news/get"
            params = {
                "secid": f"{'1' if code.startswith('6') else '0'}.{code}",
                "ut": "bd1d9ddb04089700cf9c1680336956b7",
                "size": str(limit),
                "page": "1",
            }
            resp = requests.get(url, params=params, timeout=15)
            data = resp.json()
            if data.get("data") and data["data"].get("list"):
                for item in data["data"]["list"]:
                    items.append({
                        "title": item.get("title", ""),
                        "source": item.get("source", "东方财富"),
                        "time": item.get("showTime", ""),
                        "url": item.get("url", ""),
                        "summary": item.get("digest", ""),
                    })
        except Exception:
            pass

    if items:
        df = pd.DataFrame(items)
        cache.set("stock_news", f"{code}:{limit}", df)
        return df
    return pd.DataFrame()


def get_global_news(limit: int = 30) -> pd.DataFrame:
    """Get latest global financial news from Sina (multi-channel, fast timeout)."""
    import requests
    cached = cache.get("global_news", f"all:{limit}")
    if cached is not None:
        return cached

    all_news = []
    # Only use verified-working Sina lids with short timeout (8s each)
    sina_sources = [
        ("2509", "全球财经"),
        ("2516", "产经新闻"),
        ("2514", "公司新闻"),
        ("2510", "美股新闻"),
    ]

    def _fetch_sina(lid: str, channel: str, count: int):
        items = []
        try:
            resp = requests.get(
                "https://feed.mix.sina.com.cn/api/roll/get",
                params={"pageid": "153", "lid": lid, "k": "", "num": str(count), "page": "1"},
                timeout=8,
            )
            data = resp.json()
            if data.get("result") and data["result"].get("data"):
                for item in data["result"]["data"]:
                    items.append({
                        "title": item.get("title", ""),
                        "source": item.get("media_name", "新浪财经"),
                        "time": item.get("ctime", ""),
                        "url": item.get("url", ""),
                        "summary": item.get("intro", ""),
                        "channel": channel,
                    })
        except Exception:
            pass
        return items

    # Fetch all channels in parallel
    per_source = limit // len(sina_sources) + 5
    with ThreadPoolExecutor(max_workers=len(sina_sources)) as executor:
        futures = {
            executor.submit(_fetch_sina, lid, channel, per_source): channel
            for lid, channel in sina_sources
        }
        for future in as_completed(futures):
            try:
                items = future.result(timeout=10)
                all_news.extend(items)
            except Exception:
                pass

    if all_news:
        df = pd.DataFrame(all_news).drop_duplicates(subset=["title"])
        df = df.sort_values("time", ascending=False).head(limit).reset_index(drop=True)
        cache.set("global_news", f"all:{limit}", df)
        return df
    return pd.DataFrame()
