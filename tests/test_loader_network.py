"""Falhas de fonte no loader de vendas, sem rede nem credenciais reais."""

from pathlib import Path
from types import SimpleNamespace

import pytest
import streamlit as st
from google.auth.exceptions import RefreshError, TransportError
from gspread.exceptions import APIError
from requests.exceptions import (
    ChunkedEncodingError, ConnectionError as ErroDeConexaoHTTP,
    ContentDecodingError, JSONDecodeError, Timeout,
)
from streamlit.testing.v1 import AppTest

from src.data import loader
from tests.test_loader import FakeCliente, FakePlanilha, _aba_valida, _linha_completa


DETALHE_PRIVADO = "DETALHE_SINTETICO_NAO_EXIBIR"
MENSAGENS = {
    "descoberta": (
        "Não foi possível consultar as abas da planilha de vendas. "
        "Tente atualizar novamente."
    ),
    "leitura": (
        "Não foi possível ler os dados da planilha de vendas. "
        "Tente atualizar novamente."
    ),
}
FALHAS_ESPERADAS = [
    "api", "http_conexao", "http_timeout", "http_resposta_interrompida",
    "http_resposta_invalida", "http_json_invalido", "transporte_google",
    "renovacao_google", "conexao", "timeout",
]


def _erro_esperado(tipo):
    if tipo == "http_json_invalido":
        return JSONDecodeError(DETALHE_PRIVADO, "<HTML_SINTETICO>", 0)
    if tipo == "api":
        resposta = SimpleNamespace(
            json=lambda: {
                "error": {
                    "code": 503, "message": DETALHE_PRIVADO,
                    "status": "UNAVAILABLE",
                }
            },
        )
        return APIError(resposta)
    classes = {
        "http_conexao": ErroDeConexaoHTTP,
        "http_timeout": Timeout,
        "http_resposta_interrompida": ChunkedEncodingError,
        "http_resposta_invalida": ContentDecodingError,
        "transporte_google": TransportError,
        "renovacao_google": RefreshError,
        "conexao": ConnectionError,
        "timeout": TimeoutError,
    }
    return classes[tipo](DETALHE_PRIVADO)


def _fonte_que_falha(monkeypatch, etapa, erro, *, com_aba_anterior=False):
    aba = _aba_valida("2026", [_linha_completa(1)])
    chamadas = []

    def falhar(*args, **kwargs):
        chamadas.append(etapa)
        raise erro

    abas = [aba]
    if com_aba_anterior:
        abas.insert(0, _aba_valida("2025", [_linha_completa(2)]))
    planilha = FakePlanilha(abas)
    if etapa == "descoberta":
        monkeypatch.setattr(planilha, "worksheets", falhar)
    else:
        monkeypatch.setattr(aba, "get", falhar)
    monkeypatch.setattr(loader, "criar_cliente", lambda credenciais: FakeCliente(planilha))
    return chamadas


@pytest.mark.parametrize("etapa", MENSAGENS)
@pytest.mark.parametrize("tipo", FALHAS_ESPERADAS)
def test_falha_esperada_tem_mensagem_segura_sem_retentativa(monkeypatch, etapa, tipo):
    erro = _erro_esperado(tipo)
    chamadas = _fonte_que_falha(monkeypatch, etapa, erro)

    with pytest.raises(loader.ErroDeCarga) as recebido:
        loader.load_all_sheets("FONTE_SINTETICA", {})

    assert str(recebido.value) == MENSAGENS[etapa]
    assert DETALHE_PRIVADO not in str(recebido.value)
    assert recebido.value.__cause__ is None
    assert recebido.value.__suppress_context__
    assert chamadas == [etapa]


@pytest.mark.parametrize("etapa", MENSAGENS)
@pytest.mark.parametrize("tipo", [TypeError, ValueError, KeyError, AttributeError, RuntimeError])
def test_erro_de_programacao_nao_e_mascarado(monkeypatch, etapa, tipo):
    erro = tipo("FALHA_DE_PROGRAMACAO_SINTETICA")
    _fonte_que_falha(monkeypatch, etapa, erro)

    with pytest.raises(tipo) as recebido:
        loader.load_all_sheets("FONTE_SINTETICA", {})

    assert recebido.value is erro


def test_falha_em_aba_posterior_nao_retorna_dados_parciais(monkeypatch):
    _fonte_que_falha(
        monkeypatch, "leitura", ConnectionError(DETALHE_PRIVADO),
        com_aba_anterior=True,
    )
    with pytest.raises(loader.ErroDeCarga, match="ler os dados"):
        loader.load_all_sheets("FONTE_SINTETICA", {})


@pytest.mark.parametrize("etapa", MENSAGENS)
def test_aplicacao_exibe_erro_amigavel_sem_traceback(monkeypatch, etapa):
    chamadas = _fonte_que_falha(monkeypatch, etapa, _erro_esperado("api"))
    monkeypatch.setattr(st, "secrets", {
        "spreadsheet_id": "FONTE_SINTETICA", "gcp_service_account": {},
    })
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
    app.session_state["autenticado"] = True
    app.run(timeout=20)

    assert not app.exception
    assert len(app.error) == 1
    assert app.error[0].value == MENSAGENS[etapa]
    assert DETALHE_PRIVADO not in app.error[0].value
    assert not app.radio
    assert chamadas == [etapa]
