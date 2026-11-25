"""Ứng dụng quản lý chi tiêu hàng ngày — chạy bằng: streamlit run app.py"""

import hmac

import streamlit as st

import db
from views import budgets, categories, dashboard, reports, transactions

st.set_page_config(page_title="Quản lý chi tiêu", page_icon="💰", layout="wide")


def _app_password() -> str | None:
    try:
        return st.secrets.get("APP_PASSWORD")
    except Exception:
        return None


def check_password() -> bool:
    """Khóa app bằng mật khẩu nếu APP_PASSWORD được đặt trong Secrets."""
    password = _app_password()
    if not password or st.session_state.get("authenticated"):
        return True

    st.title("💰 Quản lý chi tiêu")
    with st.form("login"):
        entered = st.text_input("Mật khẩu", type="password")
        if st.form_submit_button("Đăng nhập", type="primary"):
            if hmac.compare_digest(entered, password):
                st.session_state["authenticated"] = True
                st.rerun()
            st.error("Sai mật khẩu.")
    return False


if check_password():
    db.get_engine()  # tạo bảng + danh mục mặc định ở lần chạy đầu

    if not db.is_sqlite() and not _app_password():
        st.warning("App đang dùng CSDL online nhưng chưa đặt APP_PASSWORD — ai có link cũng xem được.")

    nav = st.navigation(
        [
            st.Page(dashboard.page, title="Tổng quan", icon="📊", url_path="tong-quan", default=True),
            st.Page(transactions.page, title="Thu chi", icon="📝", url_path="thu-chi"),
            st.Page(reports.page, title="Báo cáo", icon="📈", url_path="bao-cao"),
            st.Page(budgets.page, title="Ngân sách", icon="🎯", url_path="ngan-sach"),
            st.Page(categories.page, title="Danh mục", icon="🗂️", url_path="danh-muc"),
        ]
    )
    with st.sidebar:
        st.caption("Dữ liệu: " + ("SQLite trên máy" if db.is_sqlite() else "Postgres online"))
        if _app_password() and st.button("Đăng xuất"):
            st.session_state.clear()
            st.rerun()
    nav.run()
