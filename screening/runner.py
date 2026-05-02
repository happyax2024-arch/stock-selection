"""Screening orchestrator: runs selected conditions and merges results."""
import pandas as pd
from screening.condition1 import screen_condition1
from screening.condition2 import screen_condition2
from screening.condition3 import screen_condition3
from screening.condition4 import screen_condition4
from screening.condition5 import screen_condition5


def run_screening(
    selected_conditions: list[int],
    hist_data: dict[str, pd.DataFrame],
    stock_names: dict[str, str],
    spot_data: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Run selected screening conditions and return combined results."""
    all_results = []

    screeners = {
        1: screen_condition1,
        2: screen_condition2,
        3: screen_condition3,
        4: screen_condition4,
        5: screen_condition5,
    }

    for cond_id in selected_conditions:
        screener = screeners.get(cond_id)
        if screener is None:
            continue
        try:
            if cond_id == 2:
                df = screener(spot_data, hist_data, stock_names)
            elif cond_id == 3:
                df = screener(hist_data, stock_names, spot_data)
            elif cond_id == 4:
                df = screener(hist_data, stock_names, spot_data)
            elif cond_id == 5:
                df = screener(hist_data, stock_names, spot_data)
            else:
                df = screener(hist_data, stock_names)

            if not df.empty:
                all_results.append(df)
        except Exception as e:
            import streamlit as st
            st.warning(f"条件{cond_id}执行出错: {e}")

    if not all_results:
        return pd.DataFrame()

    combined = pd.concat(all_results, ignore_index=True)
    return combined
