"""Real-time global news panel."""
import time
from datetime import datetime
import streamlit as st
import pandas as pd
from data.fetcher import get_global_news, cache

CHANNEL_COLORS = {
    "全球财经": "#e74c3c",
    "产经新闻": "#3498db",
    "公司新闻": "#2ecc71",
    "美股新闻": "#e67e22",
    "金融市场": "#9b59b6",
    "宏观经济": "#1abc9c",
}

CHANNEL_EMOJI = {
    "全球财经": "🌍",
    "产经新闻": "🏭",
    "公司新闻": "🏢",
    "美股新闻": "🇺🇸",
    "金融市场": "📊",
    "宏观经济": "📈",
}


def render_news_panel():
    """Render a real-time scrolling news panel in the main area."""
    st.subheader("实时全球新闻")

    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        available_channels = list(CHANNEL_COLORS.keys())
        channel_filter = st.multiselect(
            "频道筛选",
            options=available_channels,
            default=available_channels[:4],
            key="news_channel_filter",
            label_visibility="collapsed",
        )
    with col2:
        if st.button("刷新新闻", use_container_width=True, key="refresh_news_btn"):
            cache.invalidate("global_news")
            st.rerun()
    with col3:
        auto_refresh = st.checkbox("自动刷新", value=True, key="news_auto_refresh")

    # Fetch news (fast: ~1s with parallel Sina sources)
    with st.spinner("加载最新新闻..."):
        news_df = get_global_news(limit=60)

    if news_df.empty:
        st.warning("暂无新闻数据，请检查网络连接后点击刷新")
        return

    # Apply channel filter
    if channel_filter:
        news_df = news_df[news_df["channel"].isin(channel_filter)]

    if news_df.empty:
        st.info("所选频道暂无新闻，请调整频道筛选")
        return

    # Display news count
    st.caption(f"共 {len(news_df)} 条新闻 | 数据来源: 新浪财经")

    # News list
    for _, row in news_df.iterrows():
        title = str(row.get("title", ""))
        source = str(row.get("source", ""))
        news_time_raw = str(row.get("time", ""))
        # Sina ctime is a Unix timestamp; convert to readable datetime
        try:
            ts = float(news_time_raw)
            if ts > 1e12:  # milliseconds
                ts /= 1000
            news_time = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, OSError):
            news_time = news_time_raw[:19]
        summary = str(row.get("summary", ""))
        url = str(row.get("url", ""))
        channel = str(row.get("channel", ""))

        emoji = CHANNEL_EMOJI.get(channel, "📰")

        with st.expander(f"{emoji} 【{channel}】{title}", expanded=False):
            st.caption(f"来源: {source} | 时间: {news_time}")
            if summary and summary != "nan":
                st.markdown(summary)
            if url and url != "nan":
                st.link_button("查看原文", url)

    # Auto-refresh: invalidate cache every 60s to fetch fresh news on next render
    if auto_refresh:
        now = time.time()
        # Default to now so first load doesn't trigger immediate rerun
        last_refresh = st.session_state.get("news_last_refresh", now)
        if now - last_refresh >= 60:
            cache.invalidate("global_news")
            st.session_state["news_last_refresh"] = now
            st.rerun()
