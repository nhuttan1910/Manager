from datetime import date

import streamlit as st

import db
from utils import category_options, fmt_vnd


def _add_form() -> None:
    st.subheader("Thêm giao dịch")
    ctype = st.radio(
        "Loại", [db.EXPENSE, db.INCOME], format_func=db.TYPE_LABELS.get,
        horizontal=True, key="add_type",
    )
    cats = category_options(ctype)
    with st.form("add_tx", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        amount = c1.number_input("Số tiền (₫)", min_value=0, step=1000, value=0)
        cat_id = c2.selectbox("Danh mục", list(cats), format_func=cats.get)
        d = c3.date_input("Ngày", value=date.today(), format="DD/MM/YYYY")
        note = st.text_input("Ghi chú")
        if st.form_submit_button("Lưu", type="primary"):
            if amount <= 0:
                st.error("Số tiền phải lớn hơn 0.")
            elif cat_id is None:
                st.error("Chưa có danh mục, hãy tạo ở trang Danh mục.")
            else:
                db.add_transaction(d, amount, ctype, cat_id, note)
                st.toast(f"Đã lưu {fmt_vnd(amount)}", icon="✅")


def _edit_form(row) -> None:
    tx_id = int(row["id"])
    st.subheader(f"Sửa giao dịch #{tx_id}")
    types = [db.EXPENSE, db.INCOME]
    ctype = st.radio(
        "Loại", types, index=types.index(row["type"]), format_func=db.TYPE_LABELS.get,
        horizontal=True, key=f"edit_type_{tx_id}",
    )
    cats = category_options(ctype)
    ids = list(cats)
    cur = int(row["category_id"])
    with st.form(f"edit_tx_{tx_id}"):
        c1, c2, c3 = st.columns(3)
        amount = c1.number_input("Số tiền (₫)", min_value=0, step=1000, value=int(row["amount"]))
        cat_id = c2.selectbox(
            "Danh mục", ids, index=ids.index(cur) if cur in ids else 0, format_func=cats.get
        )
        d = c3.date_input("Ngày", value=row["date"], format="DD/MM/YYYY")
        note = st.text_input("Ghi chú", value=row["note"] or "")
        b1, b2, _ = st.columns([1, 1, 4])
        save = b1.form_submit_button("Cập nhật", type="primary")
        remove = b2.form_submit_button("🗑️ Xóa")
    if save:
        if amount <= 0:
            st.error("Số tiền phải lớn hơn 0.")
        else:
            db.update_transaction(tx_id, d, amount, ctype, cat_id, note)
            st.toast("Đã cập nhật", icon="✅")
            st.rerun()
    if remove:
        db.delete_transaction(tx_id)
        st.toast("Đã xóa", icon="🗑️")
        st.rerun()


def page() -> None:
    st.title("📝 Thu chi")
    _add_form()

    st.divider()
    st.subheader("Danh sách giao dịch")
    today = date.today()
    c1, c2, c3 = st.columns([2, 1, 2])
    period = c1.date_input(
        "Khoảng thời gian", value=(today.replace(day=1), today), format="DD/MM/YYYY"
    )
    type_filter = c2.selectbox(
        "Loại", [None, db.EXPENSE, db.INCOME],
        format_func=lambda t: "Tất cả" if t is None else db.TYPE_LABELS[t],
    )
    if type_filter:
        cats = category_options(type_filter)
    else:
        all_cats = db.list_categories()
        cats = {
            int(r.id): f"{r.name} ({db.TYPE_LABELS[r.type]})" for r in all_cats.itertuples()
        }
    cat_filter = c3.multiselect("Danh mục", list(cats), format_func=cats.get)

    if not isinstance(period, tuple) or len(period) != 2:
        st.info("Chọn đủ ngày bắt đầu và ngày kết thúc.")
        return
    df = db.list_transactions(period[0], period[1], type_filter, cat_filter or None)
    if df.empty:
        st.caption("Không có giao dịch nào.")
        return

    inc = int(df.loc[df["type"] == db.INCOME, "amount"].sum())
    exp = int(df.loc[df["type"] == db.EXPENSE, "amount"].sum())
    st.caption(f"{len(df)} giao dịch · Thu {fmt_vnd(inc)} · Chi {fmt_vnd(exp)}")

    view = df.assign(
        loai=df["type"].map(db.TYPE_LABELS),
        signed=df.apply(lambda r: r["amount"] if r["type"] == db.INCOME else -r["amount"], axis=1),
    )
    event = st.dataframe(
        view[["date", "loai", "category", "signed", "note"]],
        hide_index=True, width="stretch",
        on_select="rerun", selection_mode="single-row", key="tx_table",
        column_config={
            "date": st.column_config.DateColumn("Ngày", format="DD/MM/YYYY"),
            "loai": "Loại",
            "category": "Danh mục",
            "signed": st.column_config.NumberColumn("Số tiền (₫)", format="localized"),
            "note": "Ghi chú",
        },
    )
    st.caption("Bấm chọn một dòng để sửa hoặc xóa.")

    st.download_button(
        "⬇️ Tải CSV",
        df.drop(columns=["category_id"]).to_csv(index=False).encode("utf-8-sig"),
        file_name=f"thu_chi_{period[0]:%Y%m%d}_{period[1]:%Y%m%d}.csv",
        mime="text/csv",
    )

    rows = event.selection.rows
    if rows:
        _edit_form(df.iloc[rows[0]])
