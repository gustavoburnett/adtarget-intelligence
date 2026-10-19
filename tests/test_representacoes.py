"""Status comercial não é um filtro financeiro nem um cadastro de metas."""
from types import SimpleNamespace
from dataclasses import replace

import pandas as pd
import pytest

from src.data import metrics, representacoes as rep
from tests.test_radar import frame, linha, avaliar, recorde


FONTE_TESTE = "fonte-sintetica-homologada"


@pytest.fixture(autouse=True)
def referencia_sintetica(monkeypatch):
    import hashlib
    monkeypatch.setattr(rep, "_FONTE_HOMOLOGADA_SHA256", hashlib.sha256(FONTE_TESTE.encode()).hexdigest())


def cadastro(*rows):
    return replace(rep.validar_representacoes([list(rep.COLUNAS), *rows]), validacao_concluida=True)


def registro(grupo="CATRACA LIVRE", status="ENCERRADA", data="2026-10-19", fonte="Confirmação do responsável", fim=""):
    return [grupo, status, data, fonte, fim]


def test_encerrada_sem_data_nao_suprime_outra_queda_e_nao_muda_fonte():
    dados = frame(linha("2025-01-01", 100, "CATRACA LIVRE"),
                  linha("2025-01-01", 100, "OUTRO"), linha("2026-01-01", 50, "OUTRO"))
    original = dados.copy(deep=True)
    antes = avaliar(dados)
    depois = avaliar(dados, representacoes=cadastro(registro()))
    assert antes.insights[0].entidade == "CATRACA LIVRE"
    assert [(i.entidade, i.tipo) for i in depois.insights] == [("OUTRO", "queda")]
    assert depois.insights[0].status_representacao == rep.NAO_INFORMADO
    pd.testing.assert_frame_equal(dados, original)


@pytest.mark.parametrize("status", ["ATIVA", "NÃO INFORMADO", "", "INDEFINIDO"])
def test_ativo_ou_nao_validado_mantem_alerta(status):
    dados = frame(linha("2025-01-01", 100, "CATRACA LIVRE"), linha("2026-01-01", 1, "OUTRO"))
    c = cadastro(registro(status=status))
    resultado = avaliar(dados, representacoes=c)
    assert resultado.insights[0].entidade == "CATRACA LIVRE"
    assert c.status("CATRACA LIVRE") == ("ATIVA" if status == "ATIVA" else rep.NAO_INFORMADO)


def test_sem_cadastro_mesmo_resultado_e_status_nao_informado():
    dados = frame(linha("2025-01-01", 100), linha("2026-01-01", 10))
    assert avaliar(dados) == avaliar(dados, representacoes=cadastro())
    assert cadastro().status("OUTRO") == rep.NAO_INFORMADO


@pytest.mark.parametrize("linhas", [
    [registro("MELODIA"), registro("RÁDIO MELODIA", "ATIVA")],
    [registro(), registro()],
    [registro(), registro(status="ATIVA"), registro()],
])
def test_duplicidade_inclusive_alias_invalida_identidade_inteira(linhas):
    c = cadastro(*linhas)
    assert c.status(linhas[0][0]) == rep.NAO_INFORMADO
    assert c.avisos


def test_alias_exato_normalizado_sem_correspondencia_por_semelhanca():
    c = cadastro(registro(" rádio melodia "), registro("CARREGA +"))
    assert c.status("MELODIA") == c.status("CARREGA+") == "ENCERRADA"
    assert c.status("CARREGA") == c.status("CARREGA  +") == rep.NAO_INFORMADO


@pytest.mark.parametrize("idx,valor", [(0, ""), (1, "SIM"), (2, ""), (2, "2026-02-30"), (2, 46314), (3, ""), (4, "2026-02-30"), (4, 0)])
def test_linha_invalida_nao_exclui_parceiro(idx, valor):
    row = registro(); row[idx] = valor
    c = cadastro(row)
    assert c.status("CATRACA LIVRE") == rep.NAO_INFORMADO
    assert c.avisos


@pytest.mark.parametrize("rows", [[], [["GRUPO"]], [list(rep.COLUNAS) + ["GRUPO"]]])
def test_cabecalho_invalido_explica_falha(rows):
    with pytest.raises(rep.ErroRepresentacoes):
        rep.validar_representacoes(rows)


def test_status_atual_nao_inventa_vigencia_historica():
    dados = frame(linha("2024-01-01", 100, "CATRACA LIVRE"), linha("2025-01-01", 10, "CATRACA LIVRE"))
    assert avaliar(dados, 2025).insights
    assert not avaliar(dados, 2025, representacoes=cadastro(registro())).insights


@pytest.mark.parametrize("valor", ["bruto", "liquido"])
@pytest.mark.parametrize("criterio", ["ganho", "veiculacao"])
def test_invariancia_financeira_e_recorde_consolidado(valor, criterio):
    dados = recorde().assign(GRUPO="CATRACA LIVRE")
    original = dados.copy(deep=True)
    antes = (metrics.ytd(dados, 2026, valor, criterio), metrics.vendas_detalhado(dados, valor),
             metrics.evolucao_mensal(dados, 2026, valor, criterio))
    estado = avaliar(dados, valor=valor, criterio_mes=criterio, representacoes=cadastro(registro()))
    depois = (metrics.ytd(dados, 2026, valor, criterio), metrics.vendas_detalhado(dados, valor),
              metrics.evolucao_mensal(dados, 2026, valor, criterio))
    assert antes == depois
    assert next(i for i in estado.insights if i.tipo == "destaque") == next(
        i for i in avaliar(dados, valor=valor, criterio_mes=criterio).insights if i.tipo == "destaque")
    pd.testing.assert_frame_equal(dados, original)


def test_loader_somente_leitura(monkeypatch):
    chamadas = []
    def get(**kwargs):
        chamadas.append(kwargs)
        return [list(rep.COLUNAS), registro()]
    aba = SimpleNamespace(get=get)
    planilha = SimpleNamespace(fetch_sheet_metadata=lambda **_: {"spreadsheetId": FONTE_TESTE}, worksheet=lambda nome: aba if nome == "REPRESENTACOES" else None)
    monkeypatch.setattr(rep.loader, "criar_cliente", lambda _: SimpleNamespace(open_by_key=lambda _: planilha))
    resultado = rep.load_representacoes("TEST", {})
    assert resultado.validacao_concluida
    assert resultado.status("CATRACA LIVRE") == "ENCERRADA"
    assert chamadas == [{"value_render_option": "UNFORMATTED_VALUE"}]


def test_falha_fonte_nao_expoe_resposta(monkeypatch):
    def falha(_):
        raise RuntimeError("SEGREDO")
    monkeypatch.setattr(rep.loader, "criar_cliente", falha)
    resultado = rep.load_representacoes("TEST", {})
    assert not resultado.validacao_concluida
    assert "alertas anteriores preservados" in resultado.avisos[0]
    assert "SEGREDO" not in repr(resultado)


@pytest.mark.parametrize("falha", [False, True])
def test_entrada_carrega_cadastro_preserva_alertas_na_falha_e_refresh(monkeypatch, falha):
    import streamlit as st
    from src.components import cards
    from tests.test_app_routing import run_app
    leituras = []
    estados = []
    def ler(*_):
        leituras.append(True)
        if falha:
            raise rep.ErroRepresentacoes("Fonte indisponível; alertas existentes preservados.")
        return cadastro(registro("G"))
    monkeypatch.setattr(rep, "load_representacoes", ler)
    monkeypatch.setattr(cards, "render_radar", estados.append)
    st.cache_data.clear()
    try:
        app, df = run_app(monkeypatch, "Performance Comercial")
        assert not app.exception
        assert len(leituras) == 1
        assert estados
        if falha:
            assert any("alertas existentes preservados" in c.value for c in app.caption)
        app.run(timeout=20)
        assert len(leituras) == (2 if falha else 1)
        app.button(key="masthead_refresh").click().run(timeout=20)
        assert not app.exception
        assert len(leituras) == (3 if falha else 2)  # falhas não ficam em cache
    finally:
        st.cache_data.clear()


def test_pagina_transmite_cadastro_ao_radar(monkeypatch):
    import streamlit as st
    from streamlit.testing.v1 import AppTest
    from src.components import cards
    dados = frame(linha("2025-01-01", 100, "CATRACA LIVRE"), linha("2026-01-01", 1, "OUTRO"))
    vistos = []
    monkeypatch.setattr(cards, "render_radar", vistos.append)
    app = AppTest.from_function(_pagina_com_cadastro, args=(dados,)).run(timeout=20)
    assert not app.exception
    assert vistos and not any(i.entidade == "CATRACA LIVRE" for i in vistos[0].insights)


def _pagina_com_cadastro(dados):
    from pages_content.performance_comercial import render
    from src.data.representacoes import CadastroRepresentacoes
    render(dados, carregar_representacoes=lambda: CadastroRepresentacoes({"CATRACA LIVRE": "ENCERRADA"}, validacao_concluida=True))


@pytest.mark.parametrize("identidade", [FONTE_TESTE, "outra-planilha", None, 123])
@pytest.mark.parametrize("anchor", ["ENCERRADA", "ATIVA", "NÃO INFORMADO", "AUSENTE", "DUPLICADA"])
def test_validacao_automatica_exige_metadados_e_registro_confirmado(monkeypatch, identidade, anchor):
    chamadas = []
    rows = [list(rep.COLUNAS)]
    if anchor != "AUSENTE":
        rows.append(registro(status="ENCERRADA" if anchor == "DUPLICADA" else anchor))
    if anchor == "DUPLICADA":
        rows.append(registro(status="ATIVA"))
    def metadata(**kwargs):
        chamadas.append(("metadata", kwargs))
        return {"spreadsheetId": identidade}
    def worksheet(nome):
        chamadas.append(("worksheet", nome))
        return SimpleNamespace(get=lambda **_: rows)
    planilha = SimpleNamespace(fetch_sheet_metadata=metadata, worksheet=worksheet)
    monkeypatch.setattr(rep.loader, "criar_cliente", lambda _: SimpleNamespace(open_by_key=lambda _: planilha))
    resultado = rep.load_representacoes("referencia-configurada", {})
    assert resultado.validacao_concluida == (identidade == FONTE_TESTE and anchor == "ENCERRADA")
    assert resultado.fonte_confirmada == (identidade == FONTE_TESTE)
    assert resultado.cadastro_acessivel == (identidade == FONTE_TESTE)
    if identidade != FONTE_TESTE:
        assert len(chamadas) == 1  # fonte incorreta nem consulta o cadastro
    if not resultado.validacao_concluida:
        assert resultado.avisos
        assert resultado.status("CATRACA LIVRE") == rep.NAO_INFORMADO
    assert chamadas[0] == ("metadata", {"params": {"fields": "spreadsheetId"}})


@pytest.mark.parametrize("etapa", ["metadados", "aba", "leitura", "estrutura"])
def test_falha_em_cada_etapa_preserva_alerta_sem_expor_contexto(monkeypatch, etapa):
    segredo = "CONTEUDO_CONFIDENCIAL_NAO_EXIBIR"
    def falha():
        raise RuntimeError(segredo)
    def metadata(**_):
        return falha() if etapa == "metadados" else {"spreadsheetId": FONTE_TESTE}
    def worksheet(_):
        if etapa == "aba": falha()
        return SimpleNamespace(get=lambda **_: falha() if etapa == "leitura" else [[segredo]])
    planilha = SimpleNamespace(fetch_sheet_metadata=metadata, worksheet=worksheet)
    monkeypatch.setattr(rep.loader, "criar_cliente", lambda _: SimpleNamespace(open_by_key=lambda _: planilha))
    resultado = rep.load_representacoes("ID_NAO_EXIBIR", {"private_key": segredo})
    dados = frame(linha("2025-01-01", 100, "CATRACA LIVRE"), linha("2026-01-01", 1, "OUTRO"))
    assert avaliar(dados, representacoes=resultado) == avaliar(dados)
    assert not resultado.validacao_concluida
    assert segredo not in repr(resultado) and "ID_NAO_EXIBIR" not in repr(resultado)


def test_radar_nao_aceita_cadastro_apenas_parseado_sem_validacao_da_fonte():
    nao_validado = rep.validar_representacoes([list(rep.COLUNAS), registro()])
    dados = frame(linha("2025-01-01", 100, "CATRACA LIVRE"), linha("2026-01-01", 1, "OUTRO"))
    assert avaliar(dados, representacoes=nao_validado) == avaliar(dados)


@pytest.mark.parametrize("falha", [False, True])
def test_cache_de_validacao_inclui_pendencias_e_atualizar_invalida(monkeypatch, falha):
    import streamlit as st
    from tests.test_app_routing import run_app
    leituras = []
    def metadata(**_):
        leituras.append(True)
        if falha: raise RuntimeError("SEGREDO")
        return {"spreadsheetId": FONTE_TESTE}
    planilha = SimpleNamespace(fetch_sheet_metadata=metadata, worksheet=lambda _: SimpleNamespace(
        get=lambda **_: [list(rep.COLUNAS), registro()]))
    monkeypatch.setattr(rep.loader, "criar_cliente", lambda _: SimpleNamespace(open_by_key=lambda _: planilha))
    st.cache_data.clear()
    try:
        app, _ = run_app(monkeypatch, "Performance Comercial")
        assert not app.exception
        assert len(leituras) == 1
        captions = " ".join(c.value for c in app.caption)
        assert ("Fonte confirmada" in captions) == (not falha)
        assert ("Validação de representações pendente" in captions) == falha
        assert "SEGREDO" not in captions and FONTE_TESTE not in captions
        app.run(timeout=20)
        assert len(leituras) == 1
        app.button(key="masthead_refresh").click().run(timeout=20)
        assert not app.exception
        assert len(leituras) == 2
    finally:
        st.cache_data.clear()
