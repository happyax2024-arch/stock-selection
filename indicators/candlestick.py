"""Candlestick pattern detection."""
import pandas as pd


def is_bullish(row) -> bool:
    return row["close"] > row["open"]


def is_bearish(row) -> bool:
    return row["close"] < row["open"]


def consecutive_rising(df: pd.DataFrame, days: int = 3) -> bool:
    """Check if the last N days are all rising (each day close > open AND close > prev close)."""
    if len(df) < days:
        return False
    last_n = df.iloc[-days:]
    for i in range(len(last_n)):
        if not is_bullish(last_n.iloc[i]):
            return False
        if i > 0 and last_n.iloc[i]["close"] <= last_n.iloc[i - 1]["close"]:
            return False
    return True


def max_single_day_change(df: pd.DataFrame, days: int = 3) -> float:
    """Get the maximum absolute daily change % in the last N days."""
    if len(df) < days:
        return float("inf")
    return df.iloc[-days:]["change_pct"].abs().max()
