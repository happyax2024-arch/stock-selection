"""Limit-up/down detection with board-specific thresholds."""
import pandas as pd
from config import get_limit_threshold


def count_limit_ups(df: pd.DataFrame, code: str, lookback: int = 90) -> int:
    """Count limit-up occurrences in the last N trading days."""
    if len(df) < lookback:
        lookback = len(df)
    threshold = get_limit_threshold(code)
    recent = df.iloc[-lookback:]
    return len(recent[
        (recent["change_pct"] >= threshold - 0.5) &
        (recent["close"] >= recent["high"] * 0.995)
    ])


def has_limit_up_in_days(df: pd.DataFrame, code: str, days: int = 3) -> bool:
    """Check if there was a limit-up in the last N days."""
    if len(df) < days:
        return False
    threshold = get_limit_threshold(code)
    recent = df.iloc[-days:]
    return any(
        (recent["change_pct"] >= threshold - 0.5) &
        (recent["close"] >= recent["high"] * 0.995)
    )


def count_limit_ups_history(ztdf: pd.DataFrame, code_col: str = "代码", days: int = 90) -> dict[str, int]:
    """Build a lookup dict {code: count} of limit-ups from a limit-up history DataFrame."""
    if ztdf is None or ztdf.empty:
        return {}
    if code_col in ztdf.columns:
        return ztdf[code_col].value_counts().to_dict()
    return {}
