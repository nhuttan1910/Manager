import streamlit as st
from sqlalchemy.exc import IntegrityError

import db


def _section(ctype: str) -> None:
    label = db.TYPE_LABELS[ctype].lower()
    df = db.list_categories(ctype)

    with st.form(f"add_cat_{ctype}", clear_on_submit=True):
        c1, c2 = st.columns([3, 1])
        name = c1.text_input(f"Tên danh mục {label} mới", label_visibility="collapsed",
                             placeholder=f"Tên danh mục {label} mới")
        if c2.form_submit_button("Thêm", width="stretch") and name.strip():
            try:
                db.add_category(name, ctype)
                st.rerun()
            except IntegrityError:
                st.error("Danh mục này đã tồn tại.")

    for row in df.itertuples():
        cid = int(row.id)
        c1, c2, c3 = st.columns([4, 1, 1])
        new_name = c1.text_input("Tên", value=row.name, key=f"cat_{cid}",
                                 label_visibility="collapsed")
        if c2.button("Đổi tên", key=f"ren_{cid}", width="stretch",
                     disabled=not new_name.strip() or new_name.strip() == row.name):
            try:
                db.rename_category(cid, new_name)
                st.rerun()
            except IntegrityError:
                st.error("Tên này đã được dùng.")
        used = db.category_usage(cid)
        if c3.button("Xóa", key=f"del_{cid}", width="stretch", disabled=used > 0,
                     help=f"Đang có {used} giao dịch, không xóa được" if used else None):
            db.delete_category(cid)
            st.rerun()


def page() -> None:
    st.title("🗂️ Danh mục")
    tab_exp, tab_inc = st.tabs(["Danh mục chi", "Danh mục thu"])
    with tab_exp:
        _section(db.EXPENSE)
    with tab_inc:
        _section(db.INCOME)
