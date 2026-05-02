"""Condition 5: 5天跌幅15%-30%, 30天涨幅<30%, 业绩为正."""
import pandas as pd
from data.fetcher import get_earnings


def screen_condition5(
    hist_data: dict[str, pd.DataFrame],
    stock_names: dict[str, str],
    spot_data: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """5-day decline 15-30%, 30-day increase < 30%, positive earnings."""
    results = []
    for code, df in hist_data.items():
        if len(df) < 31:
            continue

        close_today = float(df["close"].iloc[-1])
        close_5d = float(df["close"].iloc[-6])
        close_30d = float(df["close"].iloc[-31])

        # 5-day decline: between -30% and -15%
        decline_5d = (close_today - close_5d) / close_5d * 100
        if not (-30 <= decline_5d <= -15):
            continue

        # 30-day increase < 30%
        increase_30d = (close_today - close_30d) / close_30d * 100
        if increase_30d >= 30:
            continue

        # Positive earnings
        earnings = get_earnings(code)
        if earnings is None or earnings <= 0:
            continue

        results.append({
            "code": code,
            "name": stock_names.get(code, ""),
            "decline_5d": round(decline_5d, 2),
            "increase_30d": round(increase_30d, 2),
            "net_profit_yi": round(float(earnings), 4),
            "condition": "条件5",
        })

    return pd.DataFrame(results)
