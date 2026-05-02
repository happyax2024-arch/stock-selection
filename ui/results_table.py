"""Results table display with formatting, export, and stock selection."""
import io
import pandas as pd
import streamlit as st


def render_results(df: pd.DataFrame) -> tuple[str | None, str | None]:
    """Display screening results with formatting and export buttons.

    Returns (selected_code, selected_name) if a stock is selected, else (None, None).
    """
    if df.empty:
        st.warning("未找到符合条件的股票")
        return None, None

    # Summary
    condition_groups = df.groupby("condition")
    summary_parts = []
    for cond, group in condition_groups:
        summary_parts.append(f"{cond}: {len(group)}只")
    st.success(f"共筛选出 {len(df)} 只股票 ({', '.join(summary_parts)})")

    # Column formatting
    col_order = ["code", "name", "condition"]
    extra_cols = [c for c in df.columns if c not in col_order]
    display_df = df[col_order + extra_cols].copy()

    col_labels = {
        "code": "代码", "name": "名称", "condition": "条件",
        "match_date": "匹配日期", "date": "日期",
        "close": "收盘价", "change_pct": "涨跌幅%",
        "auction_increase": "竞价涨幅%",
        "auction_turnover": "竞价换手%",
        "auction_amount_wan": "竞价金额(万)",
        "winner_pct": "获利筹码%",
        "avg_turnover_2d": "近2日均换手%",
        "zt_count_90d": "90日涨停次数",
        "decline_5d": "5日跌幅%",
        "increase_30d": "30日涨幅%",
        "net_profit_yi": "净利润(亿)",
    }
    display_df = display_df.rename(columns={k: v for k, v in col_labels.items() if k in display_df.columns})

    # Display table
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "代码": st.column_config.TextColumn(width="small"),
            "名称": st.column_config.TextColumn(width="small"),
        },
    )

    # Stock selector for detail view
    st.divider()
    st.caption("选择一只股票查看详细信息")

    choices = [f"{row['code']} - {row['name']}" for _, row in df.iterrows()]
    selected = st.selectbox(
        "股票选择",
        options=["-- 请选择 --"] + choices,
        key="stock_selector",
        label_visibility="collapsed",
    )

    # Export buttons
    col1, col2, _ = st.columns([1, 1, 8])
    with col1:
        csv = df.to_csv(index=False, encoding="utf-8-sig")
        st.download_button(
            "导出CSV",
            data=csv,
            file_name="stock_screen_results.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with col2:
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="选股结果")
        st.download_button(
            "导出Excel",
            data=buffer.getvalue(),
            file_name="stock_screen_results.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

    if selected and selected != "-- 请选择 --":
        code = selected.split(" - ")[0]
        name = selected.split(" - ")[1]
        return code, name

    return None, None
