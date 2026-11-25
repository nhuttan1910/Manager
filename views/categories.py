import streamlit as st
from sqlalchemy.exc import IntegrityError

import db
import ui


def _section(ctype: str) -> None:
    label = db.TYPE_LABELS[ctype].lower()
    df = db.list_categories(ctype)

    with st.form(f"add_cat_{ctype}", clear_on_submit=True, border=False):
        c1, c2 = st.columns([4, 1], vertical_alignment="bottom")
        name = c1.text_input(f"Thêm danh mục {label}", placeholder=f"Tên danh mục {label} mới")
        if c2.form_submit_button("Thêm", width="stretch", type="primary",
                                 icon=":material/add:") and name.strip():
            try:
                db.add_category(name, ctype)
                st.rerun()
            except IntegrityError:
                st.error("Danh mục này đã tồn tại.")

    st.write("")
    for row in df.itertuples():
        cid = int(row.id)
        used = db.category_usage(cid)
        c0, c1, c2, c3 = st.columns([0.35, 4, 1, 1], vertical_alignment="center")
        c0.markdown(f"<div style='font-size:1.4rem;text-align:center'>{ui.icon_for(row.name, ctype)}</div>",
                    unsafe_allow_html=True)
        new_name = c1.text_input("Tên", value=row.name, key=f"cat_{cid}",
                                 label_visibility="collapsed")
        if c2.button("Lưu", key=f"ren_{cid}", width="stretch", icon=":material/edit:",
                     disabled=not new_name.strip() or new_name.strip() == row.name,
                     help="Sửa tên ở ô bên trái rồi bấm Lưu"):
            try:
                db.rename_category(cid, new_name)
                st.rerun()
            except IntegrityError:
                st.error("Tên này đã được dùng.")
        if c3.button("Xóa", key=f"del_{cid}", width="stretch", icon=":material/delete:",
                     disabled=used > 0,
                     help=f"Đang có {used} giao dịch, không xóa được" if used else "Xóa danh mục"):
            db.delete_category(cid)
            st.rerun()


def page() -> None:
    ui.page_header("Danh mục", "Thêm, đổi tên hoặc xóa danh mục thu chi")
    with st.container(border=True):
        tab_exp, tab_inc = st.tabs(["💸 Danh mục chi", "💰 Danh mục thu"])
        with tab_exp:
            _section(db.EXPENSE)
        with tab_inc:
            _section(db.INCOME)
