"""Login 2A: contratos de acesso preservados, sem secrets ou fontes reais.

AppTest prova o gate, rerun e remoção da apresentação de login. Teclado,
mostrar/ocultar senha e CSS efetivo são conferidos no navegador.
"""

from pathlib import Path
import re

import pandas as pd
import pytest
import streamlit as st
from streamlit.proto.TextInput_pb2 import TextInput
from streamlit.testing.v1 import AppTest

from pages_content import (
    analitico_comercial, analitico_veiculos, auditoria_vendas,
    metas_resultados, performance_comercial,
)
from src.data import cleaning, loader, metas_loader


APP = Path(__file__).resolve().parents[1] / "app.py"
SENHA_TESTE = "Senha_Apenas_Teste_2A "
MARCADOR_PROTEGIDO = "CONTEUDO_PROTEGIDO_OFFLINE_2A"
PAGINAS = {
    "Performance Comercial": performance_comercial,
    "Metas e Resultados": metas_resultados,
    "Analítico Comercial": analitico_comercial,
    "Analítico Veículos": analitico_veiculos,
    "🔧 Auditoria (dev)": auditoria_vendas,
}


@pytest.fixture(autouse=True)
def _cache_isolado():
    st.cache_data.clear()
    yield
    st.cache_data.clear()


def _pagina_gate():
    import streamlit as st
    from src.auth.gate import exigir_autenticacao

    exigir_autenticacao()
    st.session_state["_login_execucoes_protegidas"] = (
        st.session_state.get("_login_execucoes_protegidas", 0) + 1
    )
    st.write("CONTEUDO_PROTEGIDO_OFFLINE_2A")


def _gate(monkeypatch, *, secrets=None, autenticado=None):
    # Substitui o objeto inteiro antes de executar o app: nenhum arquivo
    # secrets.toml é aberto, mesclado ou consultado pelos testes.
    monkeypatch.setattr(st, "secrets", {"app_password": SENHA_TESTE}
                        if secrets is None else secrets)
    app = AppTest.from_function(_pagina_gate)
    if autenticado is not None:
        app.session_state["autenticado"] = autenticado
    return app.run(timeout=20)


def _enviar(app, senha):
    app.text_input[0].set_value(senha)
    return app.button[0].click().run(timeout=20)


def _corpo(app):
    return "\n".join(
        elemento.proto.body for elemento in app
        if elemento.type in {"markdown", "html"}
    )


def _cards_login(app):
    return [elemento for elemento in app
            if "design_login_card" in getattr(getattr(elemento, "proto", None), "id", "")]


def _sem_login(app):
    assert not app.exception
    assert app.session_state["autenticado"] is True
    assert not app.text_input
    assert not app.get("form")
    assert not _cards_login(app)
    # AppTest pode conservar folhas st.html no bloco event durante o rerun
    # interno. Elas ficam inativas sem os marcadores exclusivos do login.
    markup = re.sub(r'<style\b[^>]*>.*?</style>', '', _corpo(app), flags=re.S | re.I)
    assert "design_login" not in markup
    assert "atg-login-" not in markup


def _bloqueado(app):
    assert not app.exception
    assert app.session_state["autenticado"] is False
    assert MARCADOR_PROTEGIDO not in _corpo(app)


def test_sessao_nova_inicia_bloqueada_com_formulario_nativo():
    # O monkeypatch é explícito para manter o isolamento também neste teste.
    with pytest.MonkeyPatch.context() as monkeypatch:
        app = _gate(monkeypatch)
        _bloqueado(app)
        assert app.text_input[0].label == "Senha"
        assert app.text_input[0].proto.type == TextInput.PASSWORD
        assert app.text_input[0].form_id == "form_login"
        assert app.button[0].label == "Entrar"
        assert app.button[0].proto.form_id == "form_login"
        assert app.button[0].proto.is_form_submitter
        assert _cards_login(app)
        assert not app.error


def test_senha_correta_libera_conteudo_por_rerun_e_remove_login(monkeypatch):
    app = _gate(monkeypatch)
    _enviar(app, SENHA_TESTE)
    _sem_login(app)
    assert MARCADOR_PROTEGIDO in _corpo(app)
    assert app.session_state["_login_execucoes_protegidas"] == 1
    assert not app.error
    assert SENHA_TESTE not in _corpo(app)


@pytest.mark.parametrize("senha", ["SENHA_INCORRETA_OFFLINE", ""], ids=["incorreta", "vazia"])
def test_senha_incorreta_ou_vazia_nao_ultrapassa_stop(monkeypatch, senha):
    app = _gate(monkeypatch)
    _enviar(app, senha)
    _bloqueado(app)
    assert [erro.value for erro in app.error] == ["Senha incorreta."]
    assert _cards_login(app)
    assert "_login_execucoes_protegidas" not in app.session_state


@pytest.mark.parametrize("senha", [
    SENHA_TESTE.lower(), SENHA_TESTE.rstrip(), " " + SENHA_TESTE,
])
def test_comparacao_permanece_exata_sem_normalizar_senha(monkeypatch, senha):
    app = _gate(monkeypatch)
    _enviar(app, senha)
    _bloqueado(app)
    assert [erro.value for erro in app.error] == ["Senha incorreta."]


def test_informar_senha_correta_sem_submit_nao_autentica(monkeypatch):
    app = _gate(monkeypatch)
    app.text_input[0].set_value(SENHA_TESTE).run(timeout=20)
    _bloqueado(app)
    assert not app.error


@pytest.mark.parametrize("secrets", [{}, {"spreadsheet_id": "FONTE_OFFLINE_2A"}])
def test_app_password_ausente_preserva_erro_amigavel_e_bloqueio(monkeypatch, secrets):
    app = _gate(monkeypatch, secrets=secrets)
    _bloqueado(app)
    assert len(app.error) == 1
    assert app.error[0].value == (
        "Senha do aplicativo não configurada. "
        "Defina `app_password` no arquivo .streamlit/secrets.toml "
        "(local) ou na interface de secrets do Streamlit Cloud."
    )
    assert not app.text_input
    assert "_login_execucoes_protegidas" not in app.session_state


class _SecretsNaoConsultaveis:
    def __contains__(self, chave):
        raise AssertionError("Sessão autenticada não deve consultar a senha")

    def __getitem__(self, chave):
        raise AssertionError("Sessão autenticada não deve ler a senha")


def test_sessao_autenticada_retorna_sem_consultar_secrets(monkeypatch):
    app = _gate(monkeypatch, secrets=_SecretsNaoConsultaveis(), autenticado=True)
    _sem_login(app)
    assert app.session_state["_login_execucoes_protegidas"] == 1
    assert "design_login" not in _corpo(app)


def test_rerun_preserva_sessao_e_estado_sem_recriar_login(monkeypatch):
    app = _gate(monkeypatch)
    app.session_state["perf_ano"] = 2025
    app.session_state["perf_fc_GRUPO_aplicado"] = ["GRUPO_OFFLINE"]
    _enviar(app, SENHA_TESTE)
    monkeypatch.setattr(st, "secrets", _SecretsNaoConsultaveis())
    app.run(timeout=20)
    _sem_login(app)
    assert app.session_state["_login_execucoes_protegidas"] == 2
    assert "design_login" not in _corpo(app)
    assert app.session_state["perf_ano"] == 2025
    assert app.session_state["perf_fc_GRUPO_aplicado"] == ["GRUPO_OFFLINE"]


def _entrada(monkeypatch, pagina):
    chamadas = {"vendas": 0, "metas": 0, "renders": []}
    secrets = {
        "app_password": SENHA_TESTE,
        "spreadsheet_id": "FONTE_OFFLINE_LOGIN_2A",
        "gcp_service_account": {}, "dev_auditoria": True,
    }

    def ler_vendas(*_):
        chamadas["vendas"] += 1
        return pd.DataFrame({"REGISTRO_SINTETICO": [1]})

    def ler_metas(*_):
        chamadas["metas"] += 1
        return pd.DataFrame()

    def pagina_protegida(nome):
        def render(*_, **__):
            chamadas["renders"].append(nome)
            st.write(MARCADOR_PROTEGIDO)
        return render

    monkeypatch.setattr(st, "secrets", secrets)
    monkeypatch.setattr(loader, "load_all_sheets", ler_vendas)
    monkeypatch.setattr(metas_loader, "load_metas", ler_metas)
    monkeypatch.setattr(cleaning, "limpar_dataframe", lambda df: df)
    for nome, modulo in PAGINAS.items():
        monkeypatch.setattr(modulo, "render", pagina_protegida(nome))
    app = AppTest.from_file(str(APP))
    app.session_state["nav_pagina"] = pagina
    return app.run(timeout=20), chamadas, secrets


@pytest.mark.parametrize("pagina", PAGINAS)
def test_gate_impede_fontes_e_render_em_todas_as_paginas(monkeypatch, pagina):
    app, chamadas, _ = _entrada(monkeypatch, pagina)
    _bloqueado(app)
    assert chamadas == {"vendas": 0, "metas": 0, "renders": []}
    assert not app.sidebar.radio
    _enviar(app, "INCORRETA_OFFLINE")
    app.run(timeout=20)
    _bloqueado(app)
    assert chamadas == {"vendas": 0, "metas": 0, "renders": []}


def test_navegacao_e_reexecucao_nao_contornam_gate_sem_autenticacao(monkeypatch):
    app, chamadas, _ = _entrada(monkeypatch, "Performance Comercial")
    for pagina in PAGINAS:
        app.session_state["nav_pagina"] = pagina
        app.run(timeout=20)
        _bloqueado(app)
        assert chamadas == {"vendas": 0, "metas": 0, "renders": []}
        assert not app.sidebar.radio


def test_login_completo_preserva_navegacao_fontes_e_protecao_apos_reexecucao(monkeypatch):
    app, chamadas, secrets = _entrada(monkeypatch, "Performance Comercial")
    _enviar(app, SENHA_TESTE)
    _sem_login(app)
    assert chamadas == {"vendas": 1, "metas": 0, "renders": ["Performance Comercial"]}
    secrets.pop("app_password")
    for pagina in PAGINAS:
        app.radio(key="nav_pagina").set_value(pagina).run(timeout=20)
        _sem_login(app)
        assert chamadas["renders"][-1] == pagina
    assert chamadas["vendas"] == chamadas["metas"] == 1

    # Reexecutar com o estado novamente bloqueado não usa nem dados em cache.
    st.cache_data.clear()
    chamadas.update(vendas=0, metas=0, renders=[])
    app.session_state["autenticado"] = False
    app.run(timeout=20)
    _bloqueado(app)
    assert chamadas == {"vendas": 0, "metas": 0, "renders": []}
    assert "Senha do aplicativo não configurada" in app.error[0].value
