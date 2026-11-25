"""Ứng dụng quản lý chi tiêu hàng ngày — chạy bằng: streamlit run app.py"""

import hmac
from pathlib import Path

import streamlit as st

import db
import routes
import ui
from views import budgets, categories, dashboard, reports, transactions

ASSETS = Path(__file__).parent / "assets"

st.set_page_config(page_title="Quản lý chi tiêu", page_icon="💰", layout="wide")
ui.inject_css()


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

    _, mid, _ = st.columns([1, 1.2, 1])
    with mid:
        st.markdown(
            '<div class="login-hero"><div class="logo">💰</div>'
            '<div class="title">Quản lý chi tiêu</div>'
            '<div class="sub">Nhập mật khẩu để tiếp tục</div></div>',
            unsafe_allow_html=True,
        )
        with st.form("login"):
            entered = st.text_input("Mật khẩu", type="password", label_visibility="collapsed",
                                    placeholder="Mật khẩu")
            if st.form_submit_button("Đăng nhập", type="primary", width="stretch"):
                if hmac.compare_digest(entered, password):
                    st.session_state["authenticated"] = True
                    st.rerun()
                st.error("Sai mật khẩu.")
    return False


if check_password():
    db.get_engine()  # tạo bảng + danh mục mặc định ở lần chạy đầu
    st.logo(str(ASSETS / "logo.svg"), icon_image=str(ASSETS / "icon.svg"), size="large")

    if not db.is_sqlite() and not _app_password():
        st.warning("App đang dùng CSDL online nhưng chưa đặt APP_PASSWORD — ai có link cũng xem được.")

    pages = [
        st.Page(dashboard.page, title="Tổng quan", icon=":material/space_dashboard:",
                url_path="tong-quan", default=True),
        st.Page(transactions.page, title="Thu chi", icon=":material/receipt_long:", url_path="thu-chi"),
        st.Page(reports.page, title="Báo cáo", icon=":material/insights:", url_path="bao-cao"),
        st.Page(budgets.page, title="Ngân sách", icon=":material/savings:", url_path="ngan-sach"),
        st.Page(categories.page, title="Danh mục", icon=":material/category:", url_path="danh-muc"),
    ]
    routes.PAGES.update({p.url_path: p for p in pages})
    nav = st.navigation(pages)

    with st.sidebar:
        st.caption(
            ":material/database: " + ("SQLite trên máy" if db.is_sqlite() else "Đồng bộ online")
        )
        if _app_password() and st.button("Đăng xuất", icon=":material/logout:"):
            st.session_state.clear()
            st.rerun()
    nav.run()
