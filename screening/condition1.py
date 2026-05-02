"""Condition 1: 5交易日内一根阳线同时上穿20日10日5日均线."""
import pandas as pd
from indicators.moving_averages import compute_mas, is_bullish, ma_breakthrough


def screen_condition1(hist_data: dict[str, pd.DataFrame], stock_names: dict[str, str]) -> pd.DataFrame:
    """Find stocks with a bullish MA triple-breakthrough in the last 5 trading days."""
    results = []
    for code, df in hist_data.items():
        if len(df) < 25:
            continue
        df = compute_mas(df, windows=(5, 10, 20))
        last5 = df.iloc[-5:]
        for _, row in last5.iterrows():
            if is_bullish(row) and ma_breakthrough(row, (5, 10, 20)):
                results.append({
                    "code": code,
                    "name": stock_names.get(code, ""),
                    "match_date": str(row["date"])[:10],
                    "close": round(float(row["close"]), 2),
                    "change_pct": round(float(row.get("change_pct", 0)), 2),
                    "condition": "条件1",
                })
                break
    return pd.DataFrame(results)
