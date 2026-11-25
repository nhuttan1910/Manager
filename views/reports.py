from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st

import db
from utils import fmt_vnd, month_bounds

COLORS = {"Chi": "#e4572e", "Thu": "#29a96b"}
HOVER_VND = "%{y:,.0f} ₫"


def _style(fig):
    # Dấu chấm phân cách hàng nghìn kiểu Việt Nam
    fig.update_layout(separators=",.", margin=dict(t=40, l=10, r=10, b=10), legend_title_text="")
    return fig


def _by_category(df: pd.DataFrame, ctype: str) -> None:
    sub = df[df["type"] == ctype]
    label = db.TYPE_LABELS[ctype]
    if sub.empty:
        st.caption(f"Không có khoản {label.lower()} nào.")
        return
    agg = sub.groupby("category", as_index=False)["amount"].sum().sort_values("amount", ascending=False)
    fig = px.pie(agg, names="category", values="amount", hole=0.45, title=f"{label} theo danh mục")
    fig.update_traces(hovertemplate="%{label}: %{value:,.0f} ₫ (%{percent})<extra></extra>")
    st.plotly_chart(_style(fig), width="stretch")
    agg["Tỷ lệ"] = (agg["amount"] / agg["amount"].sum()).map("{:.1%}".format)
    agg["Số tiền"] = agg["amount"].map(fmt_vnd)
    st.dataframe(
        agg[["category", "Số tiền", "Tỷ lệ"]].rename(columns={"category": "Danh mục"}),
        hide_index=True, width="stretch",
    )


def _by_day(df: pd.DataFrame) -> None:
    daily = (
        df.assign(loai=df["type"].map(db.TYPE_LABELS))
        .groupby(["date", "loai"], as_index=False)["amount"].sum()
    )
    fig = px.bar(
        daily, x="date", y="amount", color="loai", barmode="group",
        color_discrete_map=COLORS, title="Thu chi theo ngày",
        labels={"date": "Ngày", "amount": "Số tiền (₫)"},
    )
    fig.update_traces(hovertemplate=HOVER_VND)
    fig.update_xaxes(tickformat="%d/%m")
    st.plotly_chart(_style(fig), width="stretch")


def _trend_12_months() -> None:
    today = date.today()
    y, m = today.year, today.month - 11
    if m <= 0:
        y, m = y - 1, m + 12
    start = date(y, m, 1)
    df = db.list_transactions(start, month_bounds(today.year, today.month)[1])
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
        color_discrete_map=COLORS, title="Xu hướng 12 tháng gần đây",
        labels={"thang": "Tháng", "amount": "Số tiền (₫)"},
    )
    fig.update_traces(hovertemplate=HOVER_VND)
    fig.update_xaxes(tickformat="%m/%Y", dtick="M1")
    st.plotly_chart(_style(fig), width="stretch")


def page() -> None:
    st.title("📈 Báo cáo")
    today = date.today()
    period = st.date_input(
        "Khoảng thời gian", value=(today.replace(day=1), today), format="DD/MM/YYYY"
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
        c1.metric("Tổng thu", fmt_vnd(inc))
        c2.metric("Tổng chi", fmt_vnd(exp))
        c3.metric("Chênh lệch", fmt_vnd(inc - exp))
        c4.metric("Chi trung bình/ngày", fmt_vnd(exp / days))

        tab_exp, tab_inc, tab_day = st.tabs(["Chi theo danh mục", "Thu theo danh mục", "Theo ngày"])
        with tab_exp:
            _by_category(df, db.EXPENSE)
        with tab_inc:
            _by_category(df, db.INCOME)
        with tab_day:
            _by_day(df)

    st.divider()
    _trend_12_months()
