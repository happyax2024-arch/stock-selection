"""Stock detail view: company info, financials, earnings, and news."""
import streamlit as st
import pandas as pd
from data.fetcher import get_stock_detail, get_financial_summary, get_financial_growth, get_stock_news


def render_stock_detail(code: str, name: str):
    """Render comprehensive stock detail when a stock is selected from results."""
    st.divider()
    st.subheader(f"{name} ({code}) 详细信息")

    tab1, tab2, tab3, tab4 = st.tabs(["公司概况", "财务指标", "业绩增长", "相关新闻"])

    with tab1:
        _render_company_info(code, name)
    with tab2:
        _render_financial_summary(code)
    with tab3:
        _render_financial_growth(code)
    with tab4:
        _render_stock_news(code, name)


def _render_company_info(code: str, name: str):
    """Render basic company information."""
    import streamlit as st

    with st.spinner("加载公司信息..."):
        spot_data = st.session_state.get("spot_data")
        detail = get_stock_detail(code, spot_data)

    if not detail:
        st.info("暂无公司信息")
        return

    label_map = {
        "最新价": "最新价", "股票代码": "股票代码", "股票简称": "股票简称",
        "总股本": "总股本", "流通股": "流通股",
        "总市值": "总市值", "流通市值": "流通市值",
        "行业": "所属行业", "上市时间": "上市时间",
        "市盈率-动态": "动态市盈率", "市净率": "市净率",
    }

    cols = st.columns(4)
    row_items = [
        ("最新价", None), ("股票代码", code), ("股票简称", name),
        ("总市值", None), ("流通市值", None), ("行业", None),
        ("上市时间", None), ("总股本", None), ("流通股", None),
    ]

    for i, (key, fallback) in enumerate(row_items):
        label = label_map.get(key, key)
        val = detail.get(key, fallback)
        if val is None:
            val = detail.get(label, "N/A")
        val_str = str(val) if val is not None else "N/A"

        # Format large numbers
        if key in ("总市值", "流通市值") and val and str(val).replace(".", "").isdigit():
            val_num = float(val)
            if val_num > 1e12:
                val_str = f"{val_num / 1e12:.2f} 万亿"
            elif val_num > 1e8:
                val_str = f"{val_num / 1e8:.2f} 亿"
        if key in ("总股本", "流通股") and val and str(val).replace(".", "").isdigit():
            val_num = float(val)
            if val_num > 1e8:
                val_str = f"{val_num / 1e8:.2f} 亿股"

        cols[i % 4].metric(label, val_str)


def _render_financial_summary(code: str):
    """Render key financial indicators summary table."""
    with st.spinner("加载财务数据..."):
        df = get_financial_summary(code)

    if df.empty:
        st.info("暂无财务数据")
        return

    # Transpose: indicators as rows, dates as columns
    display = df.set_index("指标").T
    display.index.name = "报告期"

    # Format numbers
    def fmt_val(v):
        try:
            n = float(v)
            if abs(n) >= 1e8:
                return f"{n / 1e8:.2f}亿"
            elif abs(n) >= 1e4:
                return f"{n / 1e4:.2f}万"
            elif abs(n) < 1:
                return f"{n:.4f}"
            else:
                return f"{n:.2f}"
        except (ValueError, TypeError):
            return str(v) if v else "N/A"

    display = display.map(fmt_val)
    st.dataframe(display, use_container_width=True)


def _render_financial_growth(code: str):
    """Render revenue and profit growth trends."""
    with st.spinner("加载业绩增长数据..."):
        df = get_financial_growth(code)

    if df.empty:
        st.info("暂无业绩增长数据")
        return

    # Rename columns for display
    col_labels = {
        "报告期": "报告期",
        "营业总收入": "营收",
        "营业总收入同比": "营收同比%",
        "归母净利润": "归母净利润",
        "归母净利润同比": "净利润同比%",
        "扣非净利润": "扣非净利润",
        "扣非净利润同比": "扣非净利润同比%",
        "基本每股收益": "每股收益",
        "加权净资产收益率": "ROE%",
    }
    display = df.rename(columns={k: v for k, v in col_labels.items() if k in df.columns})
    st.dataframe(display, use_container_width=True, hide_index=True)


def _render_stock_news(code: str, name: str):
    """Render recent stock-related news."""
    with st.spinner("加载相关新闻..."):
        news_df = get_stock_news(code, limit=15)

    if news_df.empty:
        st.info("暂无相关新闻")
        return

    for _, row in news_df.iterrows():
        title = row.get("title", "")
        source = row.get("source", "")
        news_time = row.get("time", "")
        summary = row.get("summary", "")
        url = row.get("url", "")

        st.markdown(f"**{title}**")
        st.caption(f"{source} | {news_time}")
        if summary:
            st.caption(summary[:200] + "..." if len(str(summary)) > 200 else summary)
        if url:
            st.link_button("阅读原文", url)
        st.divider()
