"""A-Share Stock Screening System - Main Entry Point."""
import datetime
import time
import streamlit as st
import pandas as pd

from config import MARKET_OPEN, MARKET_CLOSE
from data.fetcher import get_stock_list, get_spot_snapshot, get_daily_hist_batch
from data.universe import clear_st_cache
from screening.runner import run_screening
from ui.sidebar import render_sidebar
from ui.results_table import render_results
from ui.stock_detail import render_stock_detail
from ui.news_panel import render_news_panel
from ui.styles import apply_styles

st.set_page_config(
    page_title="A股在线选股系统",
    page_icon="📈",
    layout="wide",
)

apply_styles()


def main():
    st.title("A股在线选股系统")
    now = datetime.datetime.now()
    st.caption(f"数据时间: {now.strftime('%Y-%m-%d %H:%M:%S')} | 仅供学习研究, 不构成投资建议")

    # Sidebar condition selection
    selected_conditions, max_stocks = render_sidebar()

    # Main area tabs
    tab1, tab2 = st.tabs(["选股筛选", "实时新闻"])

    with tab1:
        if not selected_conditions:
            st.info("请在左侧选择至少一个选股条件，勾选后自动开始筛选")
        else:
            # Determine data requirements
            need_hist = any(c in selected_conditions for c in [1, 3, 4, 5])
            need_spot = any(c in selected_conditions for c in [2, 3])

            # Load data with progress
            progress_bar = st.progress(0, "加载市场数据...")
            status_text = st.empty()

            # Get stock list
            status_text.text("获取股票列表...")
            stock_list = get_stock_list()
            all_codes = stock_list["code"].tolist()[:max_stocks]
            stock_names = dict(zip(stock_list["code"], stock_list["name"]))
            st.session_state["stock_names"] = stock_names
            progress_bar.progress(0.1, f"股票列表: {len(all_codes)}/{len(stock_list)}只")

            # Get spot data
            spot_data = pd.DataFrame()
            if need_spot:
                status_text.text("获取实时行情...")
                try:
                    spot_data = get_spot_snapshot()
                    if not spot_data.empty:
                        for _, row in spot_data.iterrows():
                            code = str(row.get("code", ""))
                            name = str(row.get("name", ""))
                            if code and name:
                                stock_names[code] = name
                    st.session_state["spot_data"] = spot_data
                    progress_bar.progress(0.2, f"实时行情: {len(spot_data)}只")
                except Exception as e:
                    st.warning(f"获取实时行情失败: {e}")

            progress_bar.progress(0.3)
            clear_st_cache()

            # Get historical data
            hist_data = {}
            if need_hist:
                days_needed = 60
                if 4 in selected_conditions:
                    days_needed = 120

                total = len(all_codes)
                start_time = time.time()

                progress_bar.progress(0.35, f"准备获取 {total} 只股票日线数据...")
                status_text.text("首次加载较慢，后续使用缓存秒级完成")

                def update_progress(completed, total_count, code, cache_hits):
                    pct = 0.35 + (completed / total_count) * 0.55
                    elapsed = time.time() - start_time
                    if completed > 0 and elapsed > 2:
                        eta = elapsed / completed * (total_count - completed)
                        eta_str = f" | 预计剩余 {eta:.0f}秒" if eta > 2 else ""
                    else:
                        eta_str = ""
                    progress_bar.progress(
                        pct, f"日线数据: {completed}/{total_count} (缓存 {cache_hits})"
                    )
                    status_text.text(f"{code} ({completed}/{total_count}){eta_str}")

                hist_data = get_daily_hist_batch(
                    all_codes,
                    days=days_needed,
                    progress_cb=update_progress,
                )

                elapsed = time.time() - start_time
                progress_bar.progress(0.9, f"日线数据: {len(hist_data)}只有效数据 ({elapsed:.0f}秒)")
                status_text.text("")

            status_text.text("正在筛选...")
            progress_bar.progress(0.95, "执行筛选条件...")

            # Run screening
            if "results" not in st.session_state:
                st.session_state["results"] = pd.DataFrame()

            results = run_screening(
                selected_conditions=selected_conditions,
                hist_data=hist_data,
                stock_names=stock_names,
                spot_data=spot_data if not spot_data.empty else None,
            )
            st.session_state["results"] = results

            progress_bar.progress(1.0, "完成!")
            status_text.empty()
            time.sleep(0.3)
            progress_bar.empty()

            # Display results
            st.subheader("筛选结果")
            selected_code, selected_name = render_results(results)

            # Show stock detail if a stock is selected
            if selected_code:
                render_stock_detail(selected_code, selected_name)

    with tab2:
        render_news_panel()


if __name__ == "__main__":
    main()
