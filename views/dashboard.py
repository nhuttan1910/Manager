from datetime import date

import plotly.express as px
import streamlit as st

import db
import routes
import ui
from utils import (
    budget_status,
    category_options,
    days_left_in,
    fmt_vnd,
    month_bounds,
    month_picker,
    prev_month,
)


def _totals(df) -> tuple[int, int]:
    if df.empty:
        return 0, 0
    sums = df.groupby("type")["amount"].sum()
    return int(sums.get(db.INCOME, 0)), int(sums.get(db.EXPENSE, 0))


def quick_add() -> None:
    with st.container(border=True):
        st.markdown("**➕ Ghi nhanh**")
        ctype = st.segmented_control(
            "Loại", [db.EXPENSE, db.INCOME], default=db.EXPENSE,
            format_func=lambda t: "💸 Khoản chi" if t == db.EXPENSE else "💰 Khoản thu",
            key="qa_type", label_visibility="collapsed",
        ) or db.EXPENSE
        cats = category_options(ctype)
        with st.form("quick_add", clear_on_submit=True, border=False):
            c1, c2 = st.columns(2)
            amount = c1.number_input("Số tiền (₫)", min_value=0, step=1000, value=0)
            cat_id = c2.selectbox(
                "Danh mục", list(cats),
                format_func=lambda i: f"{ui.icon_for(cats[i], ctype)} {cats[i]}",
            )
            c3, c4 = st.columns([1, 2])
            d = c3.date_input("Ngày", value=date.today(), format="DD/MM/YYYY")
            note = c4.text_input("Ghi chú", placeholder="vd: Cơm trưa")
            if st.form_submit_button("Lưu giao dịch", type="primary", width="stretch"):
                if amount <= 0:
                    st.error("Số tiền phải lớn hơn 0.")
                elif cat_id is None:
                    st.error("Chưa có danh mục, hãy tạo ở trang Danh mục.")
                else:
                    db.add_transaction(d, amount, ctype, cat_id, note)
                    st.toast(f"Đã lưu {db.TYPE_LABELS[ctype].lower()} {fmt_vnd(amount)}", icon="✅")


def _expense_donut(df) -> None:
    exp = df[df["type"] == db.EXPENSE]
    if exp.empty:
        st.caption("Chưa có khoản chi.")
        return
    agg = exp.groupby("category", as_index=False)["amount"].sum().sort_values("amount", ascending=False)
    fig = px.pie(agg, names="category", values="amount", hole=0.62,
                 color_discrete_sequence=ui.CHART_COLORS)
    fig.update_traces(textinfo="none", hovertemplate="%{label}: %{value:,.0f} ₫ (%{percent})<extra></extra>",
                      sort=False)
    fig.add_annotation(text=f"<b>{fmt_vnd(agg['amount'].sum())}</b><br><span style='font-size:11px'>tổng chi</span>",
                       showarrow=False, font=dict(size=14))
    ui.style_fig(fig, height=280)
    fig.update_layout(showlegend=True, legend=dict(orientation="v", y=0.5, x=1.02, yanchor="middle"))
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


def page() -> None:
    head, picker = st.columns([3, 2], vertical_alignment="bottom")
    with picker:
        year, month = month_picker("dash")
    with head:
        ui.page_header("Tổng quan", f"Tình hình tài chính tháng {month}/{year}")

    start, end = month_bounds(year, month)
    df = db.list_transactions(start, end)
    income, expense = _totals(df)
    p_income, p_expense = _totals(db.list_transactions(*month_bounds(*prev_month(year, month))))
    has_prev = bool(p_income or p_expense)

    c1, c2, c3 = st.columns(3)
    with c1:
        ui.kpi_card("Tổng thu", income, ui.GREEN, "💰",
                    delta=income - p_income if has_prev else None)
    with c2:
        ui.kpi_card("Tổng chi", expense, ui.RED, "💸",
                    delta=expense - p_expense if has_prev else None, higher_is_good=False)
    with c3:
        ui.kpi_card("Còn lại", income - expense, ui.BLUE if income >= expense else ui.RED, "🏦")

    st.write("")
    left, right = st.columns([3, 2], gap="large")
    with left:
        quick_add()
        with st.container(border=True):
            st.markdown("**🧾 Giao dịch gần đây**")
            if df.empty:
                st.caption("Chưa có giao dịch nào trong tháng.")
            else:
                ui.tx_list(df.head(8))
                if len(df) > 8:
                    st.page_link(routes.PAGES["thu-chi"], label=f"Xem tất cả {len(df)} giao dịch →")

    with right:
        with st.container(border=True):
            st.markdown("**🎯 Ngân sách**")
            lines = budget_status(year, month, df[df["type"] == db.EXPENSE])
            if lines:
                ui.budget_cards(lines, days_left_in(year, month))
            else:
                st.caption("Chưa đặt ngân sách.")
                st.page_link(routes.PAGES["ngan-sach"], label="Đặt ngân sách →")
        with st.container(border=True):
            st.markdown("**🍩 Chi theo danh mục**")
            _expense_donut(df)
