"""
Authentication module - Quản lý đăng nhập cho Admin Dashboard.
Sử dụng Streamlit session_state để lưu trạng thái đăng nhập.
"""
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
from config import ADMIN_USERNAME, ADMIN_PASSWORD


def check_authentication() -> bool:
    """
    Kiểm tra trạng thái đăng nhập.
    Nếu chưa đăng nhập, hiển thị form login và trả về False.
    """
    if st.session_state.get("authenticated"):
        return True

    _show_login_form()
    return False


def _show_login_form():
    """Hiển thị form đăng nhập."""
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("## 🔐 Đăng nhập Admin")
        st.markdown("---")
        with st.form("login_form"):
            username = st.text_input("👤 Tên đăng nhập", placeholder="admin")
            password = st.text_input("🔑 Mật khẩu", type="password", placeholder="••••••••")
            submitted = st.form_submit_button("Đăng nhập", use_container_width=True)

            if submitted:
                if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
                    st.session_state["authenticated"] = True
                    st.session_state["username"] = username
                    st.rerun()
                else:
                    st.error("❌ Tên đăng nhập hoặc mật khẩu không đúng!")

        st.caption("💡 Demo: admin / admin123")


def logout():
    """Đăng xuất."""
    st.session_state["authenticated"] = False
    st.session_state.pop("username", None)
    st.rerun()


def get_username() -> str:
    return st.session_state.get("username", "admin")
