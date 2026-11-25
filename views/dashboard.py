from datetime import date

import streamlit as st

import db
from utils import (
    budget_status,
    category_options,
    fmt_vnd,
    month_bounds,
    month_picker,
    prev_month,
    render_budget_lines,
)


def _totals(start, end) -> tuple[int, int]:
    df = db.list_transactions(start, end)
    if df.empty:
        return 0, 0
    sums = df.groupby("type")["amount"].sum()
    return int(sums.get(db.INCOME, 0)), int(sums.get(db.EXPENSE, 0))


def quick_add() -> None:
    with st.expander("➕ Ghi nhanh một khoản", expanded=True):
        ctype = st.radio(
            "Loại", [db.EXPENSE, db.INCOME], format_func=db.TYPE_LABELS.get,
            horizontal=True, key="qa_type",
        )
        cats = category_options(ctype)
        with st.form("quick_add", clear_on_submit=True):
            c1, c2, c3 = st.columns([1, 1, 1])
            amount = c1.number_input("Số tiền (₫)", min_value=0, step=1000, value=0)
            cat_id = c2.selectbox("Danh mục", list(cats), format_func=cats.get)
            d = c3.date_input("Ngày", value=date.today(), format="DD/MM/YYYY")
            note = st.text_input("Ghi chú", placeholder="vd: Cơm trưa")
            if st.form_submit_button("Lưu", type="primary"):
                if amount <= 0:
                    st.error("Số tiền phải lớn hơn 0.")
                elif cat_id is None:
                    st.error("Chưa có danh mục, hãy tạo ở trang Danh mục.")
                else:
                    db.add_transaction(d, amount, ctype, cat_id, note)
                    st.toast(f"Đã lưu {db.TYPE_LABELS[ctype].lower()} {fmt_vnd(amount)}", icon="✅")


def page() -> None:
    st.title("📊 Tổng quan")
    year, month = month_picker("dash")
    start, end = month_bounds(year, month)

    income, expense = _totals(start, end)
    p_income, p_expense = _totals(*month_bounds(*prev_month(year, month)))

    c1, c2, c3 = st.columns(3)
    c1.metric("Tổng thu", fmt_vnd(income), delta=fmt_vnd(income - p_income) if p_income else None)
    c2.metric(
        "Tổng chi", fmt_vnd(expense),
        delta=fmt_vnd(expense - p_expense) if p_expense else None, delta_color="inverse",
    )
    c3.metric("Còn lại (thu − chi)", fmt_vnd(income - expense))
    if p_income or p_expense:
        st.caption("Mũi tên so với tháng trước.")

    quick_add()

    st.subheader("Ngân sách tháng này")
    lines = budget_status(year, month)
    if lines:
        render_budget_lines(lines, year, month)
    else:
        st.info("Chưa đặt ngân sách. Vào trang **Ngân sách** để đặt hạn mức chi tiêu.")

    st.subheader("Giao dịch gần đây")
    recent = db.list_transactions(start, end).head(10)
    if recent.empty:
        st.caption("Chưa có giao dịch nào trong tháng.")
    else:
        recent = recent.assign(
            loai=recent["type"].map(db.TYPE_LABELS),
            so_tien=recent["amount"].map(fmt_vnd),
        )
        st.dataframe(
            recent[["date", "loai", "category", "so_tien", "note"]],
            hide_index=True, width="stretch",
            column_config={
                "date": st.column_config.DateColumn("Ngày", format="DD/MM/YYYY"),
                "loai": "Loại", "category": "Danh mục", "so_tien": "Số tiền", "note": "Ghi chú",
            },
        )
