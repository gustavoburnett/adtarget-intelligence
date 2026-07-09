"""Gate de senha única (documento 03).

- Senha em st.secrets["app_password"], fora do código e do versionamento
- st.session_state["autenticado"] inicia False
- Senha correta libera; incorreta mostra erro e não avança
- Roda no topo do app.py, antes de qualquer leitura de dado; se não
  autenticado, a execução para (st.stop())
- Sem perfil de usuário e sem logout no MVP (sessão dura enquanto a aba
  do navegador estiver aberta)
"""

from __future__ import annotations

import streamlit as st


def exigir_autenticacao() -> None:
    """Bloqueia a execução até a senha correta ser informada."""
    if "autenticado" not in st.session_state:
        st.session_state["autenticado"] = False

    if st.session_state["autenticado"]:
        return

    if "app_password" not in st.secrets:
        # Risco do documento 03: secrets ausentes geram mensagem amigável,
        # nunca stack trace
        st.error(
            "Senha do aplicativo não configurada. "
            "Defina `app_password` no arquivo .streamlit/secrets.toml "
            "(local) ou na interface de secrets do Streamlit Cloud."
        )
        st.stop()

    st.title("AdTarget Intelligence")
    st.caption("Acesso restrito — informe a senha para continuar.")

    with st.form("form_login"):
        senha = st.text_input("Senha", type="password")
        entrar = st.form_submit_button("Entrar")

    if entrar:
        if senha == st.secrets["app_password"]:
            st.session_state["autenticado"] = True
            st.rerun()
        else:
            st.error("Senha incorreta.")

    st.stop()
