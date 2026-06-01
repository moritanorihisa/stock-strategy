"""
認証モジュール
Streamlit の secrets.toml でユーザー情報を管理する簡易ログイン。
コードにパスワードを直書きしない設計。
"""

import hmac
import streamlit as st


def _check_credentials(username: str, password: str) -> bool:
    """
    secrets.toml の [users] セクションと照合する。

    secrets.toml の形式:
        [users]
        alice = "password_hash_or_plain"
        bob   = "another_password"
    """
    users: dict = st.secrets.get("users", {})
    stored = users.get(username)
    if stored is None:
        return False
    # タイミング攻撃対策のため hmac.compare_digest を使用
    return hmac.compare_digest(str(stored), password)


def login_wall() -> bool:
    """
    未ログイン時にログイン画面を表示してブロックする。
    ログイン済みなら True を返す。

    使い方:
        if not login_wall():
            st.stop()
    """
    if st.session_state.get("authenticated"):
        return True

    st.title("🔐 ログイン")
    st.caption("このツールは限定公開です。アカウントをお持ちの方のみ利用できます。")

    with st.form("login_form"):
        username = st.text_input("ユーザー名")
        password = st.text_input("パスワード", type="password")
        submitted = st.form_submit_button("ログイン", use_container_width=True)

    if submitted:
        if _check_credentials(username, password):
            st.session_state["authenticated"] = True
            st.session_state["username"] = username
            st.rerun()
        else:
            st.error("ユーザー名またはパスワードが違います")

    return False


def logout_button():
    """サイドバーにログアウトボタンを表示する。"""
    with st.sidebar:
        st.caption(f"ログイン中: {st.session_state.get('username', '')}")
        if st.button("ログアウト", use_container_width=True):
            st.session_state.clear()
            st.rerun()
