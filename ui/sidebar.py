"""Sidebar with condition selection checkboxes."""
import streamlit as st

CONDITION_DESCRIPTIONS = {
    1: "条件1: 5日内阳线上穿20/10/5日均线",
    2: "条件2: 竞价涨幅0~2%, 换手>0.2%, 金额>1000万, 3日无涨停",
    3: "条件3: 阳线上穿20/10/5日均线, 非ST/科创/北交, 涨幅>2%",
    4: "条件4: 连续3日上涨(≤7%), 获利筹码>80%, 换手前100, 90日≥3涨停",
    5: "条件5: 5日跌幅15~30%, 30日涨幅<30%, 业绩为正",
}


def render_sidebar() -> list[int]:
    """Render condition checkboxes in the sidebar and return selected condition IDs."""
    st.sidebar.header("选股条件")
    st.sidebar.caption("选择以下一个或多个条件进行筛选")

    selected = []
    for cond_id, desc in CONDITION_DESCRIPTIONS.items():
        if st.sidebar.checkbox(desc, key=f"cond_{cond_id}"):
            selected.append(cond_id)

    if not selected:
        st.sidebar.info("请至少选择一个选股条件")

    st.sidebar.divider()
    st.sidebar.header("筛选设置")

    max_stocks = st.sidebar.slider(
        "最大扫描股票数",
        min_value=100, max_value=5500, value=500, step=100,
        help="限制扫描的股票数量以加快速度。建议先用小数量测试，确认条件后再扩大范围。"
    )

    st.sidebar.divider()
    st.sidebar.header("数据管理")

    if st.sidebar.button("清除缓存", use_container_width=True):
        from data.fetcher import cache
        cache.invalidate()
        st.sidebar.success("缓存已清除")
        st.rerun()

    st.sidebar.caption(
        "数据来源: AKShare (东方财富)\n"
        "缓存策略: 日线4小时, 实时60秒\n"
        "仅限学习研究使用, 不构成投资建议"
    )

    return selected, max_stocks
