from datetime import date

import pandas as pd
import streamlit as st

import db
from utils import WARN_RATIO, budget_status, category_options, fmt_vnd, render_budget_lines


def page() -> None:
    st.title("🎯 Ngân sách")
    st.caption(
        f"Hạn mức áp dụng cho **mỗi tháng**. Ứng dụng cảnh báo khi đã chi ≥ {WARN_RATIO:.0%} "
        "và báo đỏ khi vượt. Để 0 nghĩa là không đặt ngân sách."
    )

    budgets = db.get_budgets()
    cats = category_options(db.EXPENSE)

    with st.form("budgets"):
        total = st.number_input(
            "Ngân sách tổng cho mọi khoản chi (₫/tháng)",
            min_value=0, step=100_000, value=budgets.get(None, 0),
        )
        st.markdown("**Ngân sách theo danh mục**")
        table = pd.DataFrame(
            {
                "category_id": list(cats),
                "Danh mục": list(cats.values()),
                "Hạn mức (₫/tháng)": [budgets.get(cid, 0) for cid in cats],
            }
        )
        edited = st.data_editor(
            table,
            hide_index=True, width="stretch",
            disabled=["Danh mục"],
            column_config={
                "category_id": None,  # ẩn cột
                "Hạn mức (₫/tháng)": st.column_config.NumberColumn(
                    min_value=0, step=100_000, format="localized"
                ),
            },
        )
        if st.form_submit_button("Lưu ngân sách", type="primary"):
            db.set_budget(None, int(total))
            for row in edited.itertuples(index=False):
                value = row[2]
                db.set_budget(int(row[0]), 0 if pd.isna(value) else int(value))
            st.toast("Đã lưu ngân sách", icon="✅")
            st.rerun()

    cat_sum = sum(v for k, v in budgets.items() if k is not None)
    if budgets.get(None) and cat_sum > budgets[None]:
        st.warning(
            f"Tổng ngân sách các danh mục ({fmt_vnd(cat_sum)}) lớn hơn ngân sách tổng "
            f"({fmt_vnd(budgets[None])})."
        )

    today = date.today()
    st.subheader(f"Tình hình tháng {today.month}/{today.year}")
    lines = budget_status(today.year, today.month)
    if lines:
        render_budget_lines(lines, today.year, today.month)
    else:
        st.info("Chưa có ngân sách nào.")
