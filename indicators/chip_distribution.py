"""Chip distribution computation: WINNER(close) - profitable position percentage.

Primary: fengwo module (Windows, C-accelerated, matches 通达信 WINNER).
Fallback: simplified turnover-attenuation algorithm.
"""
import numpy as np
import pandas as pd


def compute_winner(df: pd.DataFrame) -> float:
    """Compute WINNER(close) - percentage of profitable positions at current close price.
    Returns value 0-100.
    """
    try:
        return _compute_winner_fengwo(df)
    except (ImportError, Exception):
        return _compute_winner_fallback(df)


def _compute_winner_fengwo(df: pd.DataFrame) -> float:
    """Use fengwo C module for accurate WINNER computation."""
    import fengwo
    turnrate = df["turnover"].fillna(3).values / 100.0
    close = float(df["close"].values[-1])
    winner = fengwo.WINNER(
        df["high"].values.astype(float),
        df["low"].values.astype(float),
        df["volume"].values.astype(float),
        turnrate.astype(float),
        close,
    )
    return winner * 100


def _compute_winner_fallback(df: pd.DataFrame) -> float:
    """Simplified chip distribution: build price-volume distribution with exponential decay.

    Uses last 60 trading days. Each day's volume is distributed across the price range,
    with older days receiving lower weight (0.95^days_ago).
    Returns percentage of chips below current close price.
    """
    n_days = min(len(df), 60)
    recent = df.iloc[-n_days:].copy()

    price_min = recent["low"].min()
    price_max = recent["high"].max()
    if price_max <= price_min:
        return 50.0

    bins = 200
    price_bins = np.linspace(price_min, price_max, bins + 1)
    chip_dist = np.zeros(bins)

    for i in range(n_days):
        row = recent.iloc[i]
        days_ago = n_days - i - 1
        decay = 0.95 ** days_ago

        low_idx = min(int((row["low"] - price_min) / (price_max - price_min) * bins), bins - 1)
        high_idx = max(int((row["high"] - price_min) / (price_max - price_min) * bins), low_idx + 1)
        high_idx = min(high_idx, bins)

        vol = float(row["volume"]) * decay
        span = high_idx - low_idx
        if span > 0:
            chip_dist[low_idx:high_idx] += vol / span

    if chip_dist.sum() == 0:
        return 50.0

    current_idx = int((float(recent["close"].iloc[-1]) - price_min) / (price_max - price_min) * bins)
    current_idx = min(max(current_idx, 0), bins - 1)
    return float(chip_dist[:current_idx + 1].sum() / chip_dist.sum() * 100)


def compute_winner_batch(hist_data: dict[str, pd.DataFrame], codes: list[str]) -> dict[str, float]:
    """Compute WINNER for a batch of stocks."""
    results = {}
    for code in codes:
        if code in hist_data and not hist_data[code].empty:
            try:
                results[code] = compute_winner(hist_data[code])
            except Exception:
                results[code] = 0.0
    return results
