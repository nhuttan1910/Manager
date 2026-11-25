from datetime import date

import streamlit as st

import db
import ui
from utils import category_options, fmt_vnd

TYPE_FMT = {db.EXPENSE: "💸 Chi", db.INCOME: "💰 Thu"}


def _type_control(key: str, default: str) -> str:
    return st.segmented_control(
        "Loại", [db.EXPENSE, db.INCOME], default=default, format_func=TYPE_FMT.get,
        key=key, label_visibility="collapsed", width="stretch",
    ) or default


def _cat_select(container, cats: dict, ctype: str, index: int = 0):
    ids = list(cats)
    return container.selectbox(
        "Danh mục", ids, index=index if ids else None,
        format_func=lambda i: f"{ui.icon_for(cats[i], ctype)} {cats[i]}",
    )


def _reset_selection() -> None:
    st.session_state["tx_table_ver"] = st.session_state.get("tx_table_ver", 0) + 1


def _add_form() -> None:
    st.markdown("**➕ Thêm giao dịch**")
    ctype = _type_control("add_type", db.EXPENSE)
    cats = category_options(ctype)
    with st.form("add_tx", clear_on_submit=True, border=False):
        amount = st.number_input("Số tiền (₫)", min_value=0, step=1000, value=0)
        cat_id = _cat_select(st, cats, ctype)
        d = st.date_input("Ngày", value=date.today(), format="DD/MM/YYYY")
        note = st.text_input("Ghi chú", placeholder="vd: Cơm trưa")
        if st.form_submit_button("Lưu giao dịch", type="primary", width="stretch"):
            if amount <= 0:
                st.error("Số tiền phải lớn hơn 0.")
            elif cat_id is None:
                st.error("Chưa có danh mục, hãy tạo ở trang Danh mục.")
            else:
                db.add_transaction(d, amount, ctype, cat_id, note)
                st.toast(f"Đã lưu {fmt_vnd(amount)}", icon="✅")


def _edit_form(row) -> None:
    tx_id = int(row["id"])
    st.markdown(f"**✏️ Sửa giao dịch #{tx_id}**")
    ctype = _type_control(f"edit_type_{tx_id}", row["type"])
    cats = category_options(ctype)
    ids = list(cats)
    cur = int(row["category_id"])
    with st.form(f"edit_tx_{tx_id}", border=False):
        amount = st.number_input("Số tiền (₫)", min_value=0, step=1000, value=int(row["amount"]))
        cat_id = _cat_select(st, cats, ctype, ids.index(cur) if cur in ids else 0)
        d = st.date_input("Ngày", value=row["date"], format="DD/MM/YYYY")
        note = st.text_input("Ghi chú", value=row["note"] or "")
        save = st.form_submit_button("Cập nhật", type="primary", width="stretch",
                                     icon=":material/check:")
        b1, b2 = st.columns(2)
        cancel = b1.form_submit_button("Hủy", width="stretch")
        remove = b2.form_submit_button("Xóa", width="stretch", icon=":material/delete:")
    if save:
        if amount <= 0:
            st.error("Số tiền phải lớn hơn 0.")
            return
        db.update_transaction(tx_id, d, amount, ctype, cat_id, note)
        st.toast("Đã cập nhật", icon="✅")
    elif remove:
        db.delete_transaction(tx_id)
        st.toast("Đã xóa", icon="🗑️")
    if save or remove or cancel:
        _reset_selection()
        st.rerun()


def page() -> None:
    ui.page_header("Thu chi", "Ghi chép, tìm kiếm và chỉnh sửa giao dịch")
    left, right = st.columns([1, 2.3], gap="large")
    form_box = left.container(border=True)

    with right:
        with st.container(border=True):
            today = date.today()
            c1, c2, c3 = st.columns([1.6, 1, 1.6])
            period = c1.date_input(
                "Khoảng thời gian", value=(today.replace(day=1), today), format="DD/MM/YYYY"
            )
            type_filter = c2.selectbox(
                "Loại", [None, db.EXPENSE, db.INCOME],
                format_func=lambda t: "Tất cả" if t is None else TYPE_FMT[t],
            )
            if type_filter:
                cats = category_options(type_filter)
            else:
                cats = {
                    int(r.id): f"{r.name} ({db.TYPE_LABELS[r.type]})"
                    for r in db.list_categories().itertuples()
                }
            cat_filter = c3.multiselect("Danh mục", list(cats), format_func=cats.get,
                                        placeholder="Tất cả")

        selected = None
        if not isinstance(period, tuple) or len(period) != 2:
            st.info("Chọn đủ ngày bắt đầu và ngày kết thúc.")
        else:
            df = db.list_transactions(period[0], period[1], type_filter, cat_filter or None)
            if df.empty:
                st.info("Không có giao dịch nào trong khoảng này.")
            else:
                inc = int(df.loc[df["type"] == db.INCOME, "amount"].sum())
                exp = int(df.loc[df["type"] == db.EXPENSE, "amount"].sum())
                st.markdown(
                    f"**{len(df)}** giao dịch &nbsp;·&nbsp; Thu :green[**{fmt_vnd(inc)}**]"
                    f" &nbsp;·&nbsp; Chi :red[**{fmt_vnd(exp)}**]"
                )
                view = df.assign(
                    category=[f"{ui.icon_for(c, t)} {c}" for c, t in zip(df["category"], df["type"])],
                    signed=df["amount"].where(df["type"] == db.INCOME, -df["amount"]),
                )[["date", "category", "signed", "note"]]
                styled = view.style.format(
                    lambda v: ("+" if v > 0 else "−") + fmt_vnd(abs(v)), subset=["signed"]
                ).map(
                    lambda v: f"color: {ui.GREEN if v > 0 else ui.RED}; font-weight: 600",
                    subset=["signed"],
                )
                event = st.dataframe(
                    styled, hide_index=True, width="stretch", height=min(38 + 35 * len(df), 560),
                    on_select="rerun", selection_mode="single-row",
                    key=f"tx_table_{st.session_state.get('tx_table_ver', 0)}",
                    column_config={
                        "date": st.column_config.DateColumn("Ngày", format="DD/MM/YYYY", width="small"),
                        "category": "Danh mục",
                        "signed": "Số tiền",
                        "note": "Ghi chú",
                    },
                )
                c1, c2 = st.columns([3, 1], vertical_alignment="center")
                c1.caption("Bấm chọn một dòng để sửa hoặc xóa.")
                c2.download_button(
                    "Tải CSV", icon=":material/download:", width="stretch",
                    data=df.drop(columns=["category_id"]).to_csv(index=False).encode("utf-8-sig"),
                    file_name=f"thu_chi_{period[0]:%Y%m%d}_{period[1]:%Y%m%d}.csv",
                    mime="text/csv",
                )
                if event.selection.rows:
                    selected = df.iloc[event.selection.rows[0]]

    with form_box:
        if selected is not None:
            _edit_form(selected)
        else:
            _add_form()
