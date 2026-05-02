"""Moving average computation utilities."""
import pandas as pd


def compute_mas(df: pd.DataFrame, windows=(5, 10, 20, 60)) -> pd.DataFrame:
    """Add MA columns to a daily OHLCV DataFrame."""
    df = df.copy()
    for w in windows:
        df[f"MA{w}"] = df["close"].rolling(window=w, min_periods=w).mean()
    return df


def ma_breakthrough(row, ma_windows=(5, 10, 20)) -> bool:
    """Check if a single candle breaks above all specified MAs.
    A true breakthrough means open is below the minimum MA and close is above the maximum MA.
    """
    mas = [row.get(f"MA{w}") for w in ma_windows]
    if any(pd.isna(m) for m in mas):
        return False
    ma_min = min(mas)
    ma_max = max(mas)
    return row["open"] < ma_min and row["close"] > ma_max


def is_bullish(row) -> bool:
    """Check if a candle is bullish (close > open)."""
    return row["close"] > row["open"]


def find_ma_breakthrough(df: pd.DataFrame, lookback: int = 5, ma_windows=(5, 10, 20)) -> tuple:
    """Find if there's a bullish MA breakthrough in the last N days.
    Returns (found: bool, match_date: str or None, match_row or None).
    """
    df = compute_mas(df, windows=ma_windows)
    last_n = df.iloc[-lookback:]
    for idx, row in last_n.iterrows():
        if is_bullish(row) and ma_breakthrough(row, ma_windows):
            return True, row["date"], row
    return False, None, None
