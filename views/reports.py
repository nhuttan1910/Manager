from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st

import db
import ui
from utils import fmt_vnd, month_bounds

COLORS = {"Chi": ui.RED, "Thu": ui.GREEN}
HOVER_VND = "%{y:,.0f} ₫<extra>%{fullData.name}</extra>"
CHART_CFG = {"displayModeBar": False}


def _by_category(df: pd.DataFrame, ctype: str) -> None:
    sub = df[df["type"] == ctype]
    label = db.TYPE_LABELS[ctype]
    if sub.empty:
        st.caption(f"Không có khoản {label.lower()} nào.")
        return
    agg = sub.groupby("category", as_index=False)["amount"].sum().sort_values("amount", ascending=False)
    total = agg["amount"].sum()

    c1, c2 = st.columns([1, 1.2], gap="large", vertical_alignment="center")
    with c1:
        fig = px.pie(agg, names="category", values="amount", hole=0.6,
                     color_discrete_sequence=ui.CHART_COLORS)
        fig.update_traces(textinfo="percent", textposition="inside", sort=False,
                          hovertemplate="%{label}: %{value:,.0f} ₫ (%{percent})<extra></extra>")
        fig.add_annotation(text=f"<b>{fmt_vnd(total)}</b><br><span style='font-size:11px'>tổng {label.lower()}</span>",
                           showarrow=False, font=dict(size=14))
        ui.style_fig(fig, height=320).update_layout(showlegend=False)
        st.plotly_chart(fig, width="stretch", config=CHART_CFG)
    with c2:
        table = pd.DataFrame({
            "Danh mục": [f"{ui.icon_for(c, ctype)} {c}" for c in agg["category"]],
            "Số tiền": agg["amount"].map(fmt_vnd).values,
            "Tỷ lệ": (agg["amount"] / total).values,
        })
        st.dataframe(
            table, hide_index=True, width="stretch",
            column_config={"Tỷ lệ": st.column_config.ProgressColumn(
                format="percent", min_value=0, max_value=1, color="auto")},
        )


def _by_day(df: pd.DataFrame) -> None:
    daily = (
        df.assign(loai=df["type"].map(db.TYPE_LABELS))
        .groupby(["date", "loai"], as_index=False)["amount"].sum()
    )
    fig = px.bar(
        daily, x="date", y="amount", color="loai", barmode="group",
        color_discrete_map=COLORS, labels={"date": "", "amount": ""},
    )
    fig.update_traces(hovertemplate=HOVER_VND, marker_cornerradius=4)
    fig.update_xaxes(tickformat="%d/%m")
    st.plotly_chart(ui.style_fig(fig, height=340), width="stretch", config=CHART_CFG)


def _trend_12_months() -> None:
    today = date.today()
    y, m = today.year, today.month - 11
    if m <= 0:
        y, m = y - 1, m + 12
    df = db.list_transactions(date(y, m, 1), month_bounds(today.year, today.month)[1])
    if df.empty:
        st.caption("Chưa có dữ liệu 12 tháng gần đây.")
        return
    df["thang"] = pd.to_datetime(df["date"]).dt.to_period("M").dt.to_timestamp()
    monthly = (
        df.assign(loai=df["type"].map(db.TYPE_LABELS))
        .groupby(["thang", "loai"], as_index=False)["amount"].sum()
    )
    fig = px.bar(
        monthly, x="thang", y="amount", color="loai", barmode="group",
        color_discrete_map=COLORS, labels={"thang": "", "amount": ""},
    )
    fig.update_traces(hovertemplate=HOVER_VND, marker_cornerradius=4)

    # Đường số dư (thu − chi) mỗi tháng
    pivot = monthly.pivot(index="thang", columns="loai", values="amount").fillna(0)
    balance = pivot.get("Thu", 0) - pivot.get("Chi", 0)
    fig.add_scatter(x=balance.index, y=balance.values, name="Chênh lệch", mode="lines+markers",
                    line=dict(color=ui.BLUE, width=2.5), hovertemplate=HOVER_VND)
    fig.update_xaxes(tickformat="%m/%Y", dtick="M1")
    st.plotly_chart(ui.style_fig(fig, height=360), width="stretch", config=CHART_CFG)


def page() -> None:
    head, picker = st.columns([3, 2], vertical_alignment="bottom")
    with head:
        ui.page_header("Báo cáo", "Phân tích thu chi theo danh mục và thời gian")
    today = date.today()
    period = picker.date_input(
        "Khoảng thời gian", value=(today.replace(day=1), today), format="DD/MM/YYYY",
        label_visibility="collapsed",
    )
    if not isinstance(period, tuple) or len(period) != 2:
        st.info("Chọn đủ ngày bắt đầu và ngày kết thúc.")
        return
    start, end = period
    df = db.list_transactions(start, end)

    if df.empty:
        st.info("Không có giao dịch trong khoảng thời gian này.")
    else:
        inc = int(df.loc[df["type"] == db.INCOME, "amount"].sum())
        exp = int(df.loc[df["type"] == db.EXPENSE, "amount"].sum())
        days = (end - start).days + 1
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            ui.kpi_card("Tổng thu", inc, ui.GREEN, "💰")
        with c2:
            ui.kpi_card("Tổng chi", exp, ui.RED, "💸")
        with c3:
            ui.kpi_card("Chênh lệch", inc - exp, ui.BLUE if inc >= exp else ui.RED, "🏦")
        with c4:
            ui.kpi_card("Chi trung bình/ngày", round(exp / days), ui.ORANGE, "📅")
        st.write("")

        with st.container(border=True):
            tab_exp, tab_inc, tab_day = st.tabs(["💸 Chi theo danh mục", "💰 Thu theo danh mục", "📅 Theo ngày"])
            with tab_exp:
                _by_category(df, db.EXPENSE)
            with tab_inc:
                _by_category(df, db.INCOME)
            with tab_day:
                _by_day(df)

    with st.container(border=True):
        st.markdown("**📈 Xu hướng 12 tháng gần đây**")
        _trend_12_months()
