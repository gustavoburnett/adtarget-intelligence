"""Google OIDC gate. Only Streamlit's validated identity is trusted.

Never accept query parameters, session_state or browser-supplied claims.
Authlib/Streamlit validate signature, issuer, audience, state and nonce.
The application adds Workspace authorization and expiry checks on every run.
"""
from __future__ import annotations

import math
import time
from collections.abc import Mapping

import streamlit as st

from src.components import login, shell

DOMAIN = "adtarget.com.br"
METADATA_URL = "https://accounts.google.com/.well-known/openid-configuration"


def identidade_autorizada(claims: Mapping, client_id: str, now: float | None = None) -> bool:
    """Authorize already cryptographically validated OIDC claims, never raw JWTs."""
    now = time.time() if now is None else now
    exp = claims.get("exp")
    return bool(
        client_id
        and claims.get("iss") in ("https://accounts.google.com", "accounts.google.com")
        and claims.get("aud") == client_id
        and isinstance(claims.get("sub"), str) and claims["sub"]
        and claims.get("hd") == DOMAIN
        and claims.get("email_verified") is True
        and isinstance(exp, (int, float)) and not isinstance(exp, bool)
        and math.isfinite(exp) and exp > now
    )


def _config():
    try:
        auth = st.secrets["auth"]
        google = auth["google"]
        if (google["server_metadata_url"] != METADATA_URL
                or not all(isinstance(v, str) and v.strip() for v in (
                    auth["redirect_uri"], auth["cookie_secret"],
                    google["client_id"], google["client_secret"]))):
            return None
        return google
    except (KeyError, TypeError, FileNotFoundError):
        return None


def encerrar_sessao() -> None:
    """Clear per-user state; native logout removes the signed identity cookie."""
    st.session_state.clear()
    st.logout()
    st.stop()


def exigir_autenticacao() -> None:
    """Stop before any commercial data is loaded, on every run and deep link."""
    # Legacy shared-password state cannot grant access.
    st.session_state.pop("autenticado", None)
    config = _config()
    if config and st.user.is_logged_in:
        if identidade_autorizada(st.user, config["client_id"]):
            return
        st.session_state.clear()

    st.html(shell.font_style())
    st.html(login.CSS_LOGIN)
    with st.container(key="design_login_stage"):
        with st.container(key="design_login_card"):
            st.markdown(login.header(), unsafe_allow_html=True)
            if not config:
                st.error("Login Google não configurado. Consulte as instruções de configuração OAuth.")
            elif st.user.is_logged_in:
                st.error("Conta não autorizada ou sessão expirada. Entre com sua conta corporativa AdTarget.")
                st.button("Sair e trocar de conta", on_click=encerrar_sessao, type="primary")
            else:
                st.button("Entrar com Google", on_click=st.login, args=("google",),
                          type="primary", width="stretch")
        st.markdown(login.EDITORIAL, unsafe_allow_html=True)
    st.stop()
