"""Condition 4: 连续三天上涨, 单日涨幅≤7%, 获利筹码>80%, 近两日换手率前100,
90交易日内≥3次涨停, 非ST, 上市>1个月."""
import pandas as pd
from indicators.candlestick import consecutive_rising, max_single_day_change
from indicators.limit_detector import count_limit_ups
from indicators.chip_distribution import compute_winner


def screen_condition4(
    hist_data: dict[str, pd.DataFrame],
    stock_names: dict[str, str],
    spot_data: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Multi-factor momentum + chip distribution screening."""
    if not hist_data:
        return pd.DataFrame()

    # Step 1: Quick filters
    candidates = []
    for code, df in hist_data.items():
        name = stock_names.get(code, "")
        if "ST" in name.upper():
            continue
        if len(df) < 90:
            continue

        # Three consecutive rising days
        if not consecutive_rising(df, days=3):
            continue

        # Single day increase <= 7%
        if max_single_day_change(df, days=3) > 7:
            continue

        # >= 3 limit-ups in 90 trading days
        zt_count = count_limit_ups(df, code, lookback=90)
        if zt_count < 3:
            continue

        candidates.append(code)

    if not candidates:
        return pd.DataFrame()

    # Step 2: Turnover ranking (top 100 in last 2 days)
    turnover_list = []
    for code in candidates:
        df = hist_data[code]
        if "turnover" in df.columns:
            avg_turnover = float(df.iloc[-2:]["turnover"].mean())
        else:
            avg_turnover = 0
        turnover_list.append((code, avg_turnover))

    turnover_list.sort(key=lambda x: x[1], reverse=True)
    top_100 = turnover_list[:100]
    top_codes = set(code for code, _ in top_100)

    # Step 3: Chip distribution filter (获利筹码 > 80%)
    results = []
    for code, avg_turnover in top_100:
        if code not in top_codes:
            continue
        try:
            winner_pct = compute_winner(hist_data[code])
            if winner_pct >= 80:
                results.append({
                    "code": code,
                    "name": stock_names.get(code, ""),
                    "winner_pct": round(winner_pct, 1),
                    "avg_turnover_2d": round(avg_turnover, 2),
                    "zt_count_90d": count_limit_ups(hist_data[code], code, 90),
                    "condition": "条件4",
                })
        except Exception:
            pass

    return pd.DataFrame(results)
