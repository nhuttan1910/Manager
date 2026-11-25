from datetime import date

import pandas as pd
import streamlit as st

import db
import ui
from utils import WARN_RATIO, budget_status, category_options, days_left_in, fmt_vnd


def page() -> None:
    ui.page_header(
        "Ngân sách",
        f"Hạn mức chi mỗi tháng · cảnh báo khi dùng ≥ {WARN_RATIO:.0%}, báo đỏ khi vượt",
    )

    budgets = db.get_budgets()
    cats = category_options(db.EXPENSE)
    left, right = st.columns([1.2, 1], gap="large")

    with left, st.container(border=True):
        st.markdown("**⚙️ Đặt hạn mức**")
        with st.form("budgets", border=False):
            total = st.number_input(
                "🎯 Ngân sách tổng cho mọi khoản chi (₫/tháng)",
                min_value=0, step=100_000, value=budgets.get(None, 0),
                help="Để 0 nếu không muốn giới hạn tổng.",
            )
            table = pd.DataFrame(
                {
                    "category_id": list(cats),
                    "Danh mục": [f"{ui.icon_for(n)} {n}" for n in cats.values()],
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
                        min_value=0, step=100_000, format="localized",
                        help="Để 0 nếu không đặt ngân sách cho danh mục này",
                    ),
                },
            )
            if st.form_submit_button("Lưu ngân sách", type="primary", width="stretch",
                                     icon=":material/save:"):
                db.set_budget(None, int(total))
                for row in edited.itertuples(index=False):
                    value = row[2]
                    db.set_budget(int(row[0]), 0 if pd.isna(value) else int(value))
                st.toast("Đã lưu ngân sách", icon="✅")
                st.rerun()

    with right:
        cat_sum = sum(v for k, v in budgets.items() if k is not None)
        if budgets.get(None) and cat_sum > budgets[None]:
            st.warning(
                f"Tổng hạn mức các danh mục ({fmt_vnd(cat_sum)}) lớn hơn ngân sách tổng "
                f"({fmt_vnd(budgets[None])}).",
                icon=":material/warning:",
            )
        today = date.today()
        with st.container(border=True):
            st.markdown(f"**📊 Tình hình tháng {today.month}/{today.year}**")
            lines = budget_status(today.year, today.month)
            if lines:
                ui.budget_cards(lines, days_left_in(today.year, today.month))
            else:
                st.caption("Chưa có ngân sách nào. Nhập hạn mức ở bên trái rồi bấm Lưu.")
