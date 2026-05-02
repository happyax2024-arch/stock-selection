"""Condition 2: 竞价涨幅0-2%, 竞价换手率>0.2%, 竞价金额>1000万, 近3日不涨停."""
import pandas as pd
from indicators.limit_detector import has_limit_up_in_days


def screen_condition2(
    spot_data: pd.DataFrame,
    hist_data: dict[str, pd.DataFrame],
    stock_names: dict[str, str],
) -> pd.DataFrame:
    """
    Filter stocks by call auction metrics:
    - Auction increase: 0% to 2% (calculated from open vs prev_close as proxy)
    - Auction turnover rate > 0.2%
    - Auction amount > 10 million CNY
    - No limit-up in last 3 trading days
    """
    if spot_data is None or spot_data.empty:
        return pd.DataFrame()

    results = []
    for _, row in spot_data.iterrows():
        code = str(row.get("code", ""))
        name = str(row.get("name", ""))
        if not code:
            continue

        open_p = row.get("open")
        prev_close = row.get("prev_close")
        turnover = row.get("turnover")
        amount = row.get("amount")

        if pd.isna(open_p) or pd.isna(prev_close) or prev_close == 0:
            continue

        auction_increase = (float(open_p) - float(prev_close)) / float(prev_close) * 100

        if not (0 <= auction_increase < 2):
            continue

        # Auction turnover: use early turnover as proxy
        auction_turnover = float(turnover) if not pd.isna(turnover) else 0
        if auction_turnover <= 0.2:
            continue

        # Auction amount in CNY (amount field is already in yuan from Eastmoney)
        auction_amount = float(amount) if not pd.isna(amount) else 0
        if auction_amount <= 10_000_000:
            continue

        # No limit-up in last 3 days
        if code in hist_data and has_limit_up_in_days(hist_data[code], code, days=3):
            continue

        results.append({
            "code": code,
            "name": stock_names.get(code, name),
            "auction_increase": round(auction_increase, 2),
            "auction_turnover": round(auction_turnover, 2),
            "auction_amount_wan": round(auction_amount / 10000, 2),
            "condition": "条件2",
        })

    return pd.DataFrame(results)
