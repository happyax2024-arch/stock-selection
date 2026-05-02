"""Condition 3: 一根阳线上穿20/10/5日均线, 非ST/科创板/北交所, 今日涨幅>2%."""
import pandas as pd
from indicators.moving_averages import compute_mas, is_bullish, ma_breakthrough
from data.universe import is_st_stock, is_star_board, is_bse_board


def screen_condition3(
    hist_data: dict[str, pd.DataFrame],
    stock_names: dict[str, str],
    spot_data: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Single-day MA triple-breakthrough with universe and increase filters."""
    # Build quick lookup for today's change if spot data is available
    today_changes = {}
    if spot_data is not None and not spot_data.empty:
        for _, row in spot_data.iterrows():
            code = str(row.get("code", ""))
            if code:
                today_changes[code] = float(row.get("change_pct", 0))

    results = []
    for code, df in hist_data.items():
        # Universe filter
        if is_star_board(code) or is_bse_board(code):
            continue
        # ST check: use name lookup
        name = stock_names.get(code, "")
        if "ST" in name.upper():
            continue

        if len(df) < 25:
            continue

        # Today's increase > 2%
        today_chg = today_changes.get(code)
        if today_chg is None:
            if "change_pct" in df.columns:
                today_chg = float(df.iloc[-1]["change_pct"])
            else:
                continue
        if today_chg <= 2:
            continue

        df = compute_mas(df, windows=(5, 10, 20))
        today = df.iloc[-1]
        if is_bullish(today) and ma_breakthrough(today, (5, 10, 20)):
            results.append({
                "code": code,
                "name": name,
                "date": str(today["date"])[:10],
                "close": round(float(today["close"]), 2),
                "change_pct": round(today_chg, 2),
                "condition": "条件3",
            })

    return pd.DataFrame(results)
