"""Meta na Performance: integração offline, estado e regressão das visões atuais."""

import datetime as dt
import json
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from pages_content import performance_comercial
from src.data import cleaning, loader, metas, metas_loader
from src.data.loader import COL_ANO_ABA
from src.data.metas_schema import COLUNAS_METAS, ErroDeMetas


APP = Path(__file__).resolve().parents[1] / "app.py"
REF = dt.datetime(2026, 10, 6, 12)
_MESES = (
    "JANEIRO", "FEVEREIRO", "MARÇO", "ABRIL", "MAIO", "JUNHO",
    "JULHO", "AGOSTO", "SETEMBRO", "OUTUBRO", "NOVEMBRO", "DEZEMBRO",
)


class _AgoraFixo(dt.datetime):
    @classmethod
    def now(cls, tz=None):
        return REF if tz is None else REF.replace(tzinfo=dt.timezone.utc).astimezone(tz)


@pytest.fixture(autouse=True)
def _isolamento(monkeypatch):
    st.cache_data.clear()
    monkeypatch.setattr(performance_comercial, "_dt", SimpleNamespace(datetime=_AgoraFixo))
    data_local_original = metas.data_local
    monkeypatch.setattr(
        metas, "data_local", lambda referencia: REF.date() if referencia is None else data_local_original(referencia),
    )
    yield
    st.cache_data.clear()


def _fonte_vendas():
    linhas = []
    valores = {
        "G": {1: 100, 2: 200, 9: 500, 10: 30, 11: 40, 12: 50},
        "H": {1: 300, 9: 600, 10: 300, 11: 400, 12: 500},
    }
    for ano in (2024, 2025, 2026):
        for grupo, meses in valores.items():
            for mes, valor in meses.items():
                liquido = valor if ano == 2026 else valor / 2
                linhas.append({
                    **{coluna: "TESTE" for coluna in cleaning.COLUNAS_TEXTO},
                    cleaning.COL_GRUPO: grupo,
                    cleaning.COL_VEICULO: f"VEICULO {grupo}",
                    cleaning.COL_CLIENTE: f"CLIENTE {grupo}",
                    cleaning.COL_STATUS: "FATURADO",
                    cleaning.COL_PI: str(len(linhas) + 1),
                    cleaning.COL_MES_VEICULACAO: f"{_MESES[mes - 1]}/{ano}",
                    cleaning.COL_MES_GANHO: f"AGOSTO/{ano}",
                    cleaning.COL_VALOR_LIQUIDO: liquido,
                    cleaning.COL_VALOR_BRUTO: liquido * 10,
                    cleaning.COL_VENCIMENTO: "CONTRA APRESENT.",
                    cleaning.COL_NOTA_FISCAL: "NF TESTE",
                    COL_ANO_ABA: ano,
                })
    fora = dict(linhas[-1])
    fora.update({cleaning.COL_GRUPO: "FORA", cleaning.COL_VALOR_LIQUIDO: 4000,
                 cleaning.COL_VALOR_BRUTO: 40000})
    linhas.append(fora)
    cancelada = dict(linhas[-2])
    cancelada.update({cleaning.COL_GRUPO: "G", cleaning.COL_STATUS: "CANCELADO",
                     cleaning.COL_VALOR_LIQUIDO: 9000, cleaning.COL_VALOR_BRUTO: 90000})
    linhas.append(cancelada)
    return pd.DataFrame(linhas)


def _plano():
    return pd.DataFrame([
        ["GRUPO", grupo, "", 2026, mes, valor, "SIM", 1,
         "2026-01-01T00:00:00-03:00", "Teste offline"]
        for grupo, valor in (("G", 100), ("H", 200)) for mes in range(1, 13)
    ], columns=COLUNAS_METAS)


def _render_pagina(vendas, plano, erro):
    from pages_content.performance_comercial import render

    def ler_metas():
        if erro is not None:
            raise erro
        return plano

    render(vendas, carregar_metas=ler_metas)


def _pagina(*, aba="Vendas", plano=None, erro=None, ano=2026, grupos=None,
            valor="Valor Líquido", criterio="Mês (Veiculação)"):
    vendas = cleaning.limpar_dataframe(_fonte_vendas())
    app = AppTest.from_function(_render_pagina, args=(vendas, _plano() if plano is None else plano, erro))
    app.session_state["performance_evolucao_tab"] = aba
    app.session_state["perf_ano"] = ano
    app.session_state["perf_valor"] = valor
    app.session_state["perf_mes"] = criterio
    if grupos is not None:
        app.session_state[f"perf_fc_{cleaning.COL_GRUPO}_aplicado"] = grupos
    return app.run(timeout=20), vendas


def _alternar(app, aba):
    # AppTest representa tabs como Block, sem setter. O estado público do
    # widget stateful permite testar os mesmos reruns, sem substituir st.tabs.
    app.session_state["performance_evolucao_tab"] = aba
    return app.run(timeout=20)


def _html(app):
    return "\n".join(elemento.value for elemento in app.markdown)


def _conteudo(app):
    return "\n".join(elemento.value for grupo in (app.markdown, app.caption, app.error, app.info) for elemento in grupo)


def _figuras(app):
    return [json.loads(elemento.proto.spec) for elemento in app.get("plotly_chart")]


def _figura_meta(app):
    return next(figura for figura in _figuras(app) if any(
        serie.get("name") == "Meta acumulada" for serie in figura["data"]
    ))


def _blocos_preservados(app):
    return [elemento.value for elemento in app.markdown if any(
        marcador in elemento.value
        for marcador in ('class="atg-kpi-row"', 'class="atg-radar-header"', 'class="atg-radar ', 'class="atg-card atg-rank"')
    )]


def _entrada(monkeypatch, *, aba="Vendas", erro=None, pagina="Performance Comercial"):
    fonte = _fonte_vendas()
    plano = _plano()
    leituras = {"vendas": 0, "metas": 0}

    def ler_vendas(*_):
        leituras["vendas"] += 1
        return fonte

    def ler_metas(*_):
        leituras["metas"] += 1
        if erro is not None:
            raise erro
        return plano

    monkeypatch.setattr(st, "secrets", {
        "spreadsheet_id": "TESTE_PERFORMANCE_META_OFFLINE",
        "gcp_service_account": {}, "dev_auditoria": True,
    })
    monkeypatch.setattr(loader, "load_all_sheets", ler_vendas)
    monkeypatch.setattr(metas_loader, "load_metas", ler_metas)
    app = AppTest.from_file(str(APP))
    app.session_state["autenticado"] = True
    app.session_state["nav_pagina"] = pagina
    app.session_state["perf_ano"] = 2026
    app.session_state["performance_evolucao_tab"] = aba
    app.run(timeout=20)
    return app, fonte, plano, leituras


def test_terceira_tab_preserva_nomes_ordem_e_duas_visoes_originais():
    app, _ = _pagina()
    assert not app.exception
    assert [aba.label for aba in app.tabs] == ["Vendas", "Ticket Médio", "Meta"]
    assert len(_figuras(app)) == 2
    assert not app.error


@pytest.mark.parametrize("aba", ["Vendas", "Ticket Médio"])
def test_visoes_originais_nao_avaliam_engine_metas(monkeypatch, aba):
    def proibido(*_, **__):
        raise AssertionError("A engine de metas não pertence às visões existentes")

    monkeypatch.setattr(metas, "avaliar_metas", proibido)
    monkeypatch.setattr(metas, "avaliar_pulso", proibido)
    app, _ = _pagina(aba=aba, erro=AssertionError("A fonte METAS não deve ser consultada"))
    assert not app.exception
    assert len(_figuras(app)) == 2


def test_meta_preserva_kpis_radar_rankings_e_graficos_das_visoes_originais():
    app, _ = _pagina()
    antes = _blocos_preservados(app)
    figuras_antes = _figuras(app)
    assert any('class="atg-kpi-row"' in bloco for bloco in antes)
    assert any('class="atg-radar-header"' in bloco for bloco in antes)
    assert any('class="atg-radar ' in bloco for bloco in antes)
    assert sum('class="atg-card atg-rank"' in bloco for bloco in antes) == 3
    _alternar(app, "Meta")
    assert not app.exception
    assert _blocos_preservados(app) == antes
    assert _figuras(app)[:2] == figuras_antes
    assert len(_figuras(app)) == 3
    _alternar(app, "Vendas")
    assert not app.exception
    assert _blocos_preservados(app) == antes
    assert _figuras(app) == figuras_antes
    _alternar(app, "Ticket Médio")
    assert not app.exception
    assert _blocos_preservados(app) == antes
    assert _figuras(app) == figuras_antes


@pytest.mark.parametrize("grupos,valor,criterio", [
    (None, "Valor Líquido", "Mês (Veiculação)"),
    (["G"], "Valor Líquido", "Mês (Veiculação)"),
    (None, "Valor Bruto", "Mês (Veiculação)"),
    (None, "Valor Líquido", "Mês (Ganho)"),
    (["G"], "Valor Bruto", "Mês (Ganho)"),
    ([], "Valor Bruto", "Mês (Ganho)"),
])
def test_meta_fixa_consolidado_liquido_veiculacao_independentemente_dos_controles(
    grupos, valor, criterio,
):
    app, _ = _pagina(aba="Meta", grupos=grupos, valor=valor, criterio=criterio)
    assert not app.exception
    figura = _figura_meta(app)
    meta = next(serie for serie in figura["data"] if serie["name"] == "Meta acumulada")
    assert meta["y"][-1] == 3600
    assert any(serie["y"][-1] == 3020 for serie in figura["data"] if serie["name"] != "Meta acumulada")
    texto = _conteudo(app)
    assert "Meta · Valor Líquido · Mês de Veiculação · Consolidado AdTarget" in texto
    assert "controles acima continuam aplicados" not in texto
    padrao, _ = _pagina(aba="Meta")
    assert figura == _figura_meta(padrao)


@pytest.mark.parametrize("valor,criterio,grupos", [
    ("Valor Líquido", "Mês (Veiculação)", None),
    ("Valor Bruto", "Mês (Ganho)", ["G"]),
])
def test_meta_exibe_controles_nativos_somente_leitura_sem_mudar_estado_original(
    valor, criterio, grupos,
):
    app, _ = _pagina(aba="Meta", valor=valor, criterio=criterio, grupos=grupos)
    assert not app.exception
    for chave, fixo in (("performance_meta_valor", "Valor Líquido"),
                        ("performance_meta_mes", "Mês (Veiculação)")):
        controle = app.button_group(key=chave)
        assert controle.proto.disabled
        assert controle.value == fixo
    assert any(popover.proto.popover.disabled and
               popover.proto.popover.label == "Grupo · Consolidado AdTarget"
               for popover in app.get("popover"))
    assert app.button_group(key="perf_valor").value == valor
    assert app.button_group(key="perf_mes").value == criterio
    assert not app.button_group(key="perf_valor").proto.disabled
    assert not app.button_group(key="perf_mes").proto.disabled
    if grupos is not None:
        assert app.session_state[f"perf_fc_{cleaning.COL_GRUPO}_aplicado"] == grupos


def test_meta_compartilha_engine_e_entrega_base_completa_sem_mudar_fontes(monkeypatch):
    original_fechado, original_pulso = metas.avaliar_metas, metas.avaliar_pulso
    chamadas = []

    def fechado(vendas, plano, ano, **opcoes):
        chamadas.append(("fechado", vendas.copy(deep=True), plano.copy(deep=True), ano))
        return original_fechado(vendas, plano, ano, **opcoes)

    def pulso(vendas, plano, ano, **opcoes):
        chamadas.append(("pulso", vendas.copy(deep=True), plano.copy(deep=True), ano))
        return original_pulso(vendas, plano, ano, **opcoes)

    monkeypatch.setattr(metas, "avaliar_metas", fechado)
    monkeypatch.setattr(metas, "avaliar_pulso", pulso)
    plano = _plano()
    plano_antes = plano.copy(deep=True)
    app, vendas = _pagina(aba="Meta", plano=plano, grupos=["G"],
                         valor="Valor Bruto", criterio="Mês (Ganho)")
    assert not app.exception
    assert {tipo for tipo, *_ in chamadas} == {"fechado", "pulso"}
    for _, recebidas, metas_recebidas, ano in chamadas:
        pd.testing.assert_frame_equal(recebidas, vendas)
        pd.testing.assert_frame_equal(metas_recebidas, plano)
        assert ano == 2026
    pd.testing.assert_frame_equal(plano, plano_antes)


@pytest.mark.parametrize("destino", ["Vendas", "Ticket Médio"])
def test_retorno_preserva_estado_e_resposta_dos_controles(destino):
    app, _ = _pagina(aba=destino, grupos=["G"],
                     valor="Valor Bruto", criterio="Mês (Ganho)")
    antes = _figuras(app)
    blocos = _blocos_preservados(app)
    _alternar(app, "Meta")
    assert not app.exception
    assert app.session_state["perf_valor"] == "Valor Bruto"
    assert app.session_state["perf_mes"] == "Mês (Ganho)"
    assert app.session_state[f"perf_fc_{cleaning.COL_GRUPO}_aplicado"] == ["G"]
    _alternar(app, destino)
    assert not app.exception
    assert not app.button_group(key="perf_valor").proto.disabled
    assert not app.button_group(key="perf_mes").proto.disabled
    assert app.button_group(key="perf_valor").value == "Valor Bruto"
    assert app.button_group(key="perf_mes").value == "Mês (Ganho)"
    assert app.session_state[f"perf_fc_{cleaning.COL_GRUPO}_aplicado"] == ["G"]
    assert _figuras(app) == antes
    assert _blocos_preservados(app) == blocos
    app.button_group(key="perf_valor").set_value("Valor Líquido").run(timeout=20)
    assert not app.exception
    assert _figuras(app) != antes
    app.button_group(key="perf_mes").set_value("Mês (Veiculação)").run(timeout=20)
    assert not app.exception
    assert app.button_group(key="perf_mes").value == "Mês (Veiculação)"


@pytest.mark.parametrize("ano", [2024, 2025])
def test_meta_respeita_ano_sem_inventar_metas_para_anos_sem_plano(ano):
    app, _ = _pagina(aba="Meta", ano=ano)
    assert not app.exception
    assert f"Não há metas cadastradas para {ano}" in _conteudo(app)
    assert len(_figuras(app)) == 2
    app.button_group(key="perf_ano").set_value(2026).run(timeout=20)
    assert not app.exception and len(_figuras(app)) == 3
    _alternar(app, "Vendas")
    assert not app.exception and len(_figuras(app)) == 2


@pytest.mark.parametrize("categoria", ["fonte", "estrutura", "validacao"])
def test_erro_de_metas_fica_isolado_da_performance_e_das_visoes_existentes(categoria):
    erro = ErroDeMetas("CONTEUDO_SENSIVEL_NAO_EXIBIR", categoria)
    app, _ = _pagina(aba="Meta", erro=erro)
    assert not app.exception
    assert len(app.error) == 1
    assert "CONTEUDO_SENSIVEL_NAO_EXIBIR" not in _conteudo(app)
    assert len(_figuras(app)) == 2
    assert _blocos_preservados(app)
    _alternar(app, "Ticket Médio")
    assert not app.exception and not app.error
    assert len(_figuras(app)) == 2


def test_schema_invalido_na_meta_nao_interrompe_kpis_radar_rankings():
    plano = _plano()
    plano.loc[0, "VALOR_META"] = -1
    app, _ = _pagina(aba="Meta", plano=plano)
    assert not app.exception
    assert len(app.error) == 1
    assert len(_figuras(app)) == 2
    assert _blocos_preservados(app)


@pytest.mark.parametrize("aba", ["Vendas", "Ticket Médio"])
def test_entrada_real_nao_consulta_metas_nas_visoes_originais(monkeypatch, aba):
    app, _, _, leituras = _entrada(monkeypatch, aba=aba)
    assert not app.exception
    assert leituras == {"vendas": 1, "metas": 0}
    assert [tab.label for tab in app.tabs] == ["Vendas", "Ticket Médio", "Meta"]


def test_entrada_ler_metas_ao_abrir_tab_e_reutilizar_cache_compartilhado(monkeypatch):
    app, _, _, leituras = _entrada(monkeypatch)
    assert not app.exception and leituras == {"vendas": 1, "metas": 0}
    _alternar(app, "Meta")
    assert not app.exception and leituras == {"vendas": 1, "metas": 1}
    _alternar(app, "Vendas")
    _alternar(app, "Meta")
    assert not app.exception and leituras == {"vendas": 1, "metas": 1}
    app.radio(key="nav_pagina").set_value("Metas e Resultados").run(timeout=20)
    assert not app.exception and leituras == {"vendas": 1, "metas": 1}


def test_entrada_falha_metas_nao_impede_retornar_ticket_ou_outra_pagina(monkeypatch):
    app, _, _, leituras = _entrada(
        monkeypatch, aba="Meta", erro=ErroDeMetas("SEGREDO_SINTETICO", "fonte"),
    )
    assert not app.exception and len(app.error) == 1
    assert "SEGREDO_SINTETICO" not in _conteudo(app)
    assert leituras == {"vendas": 1, "metas": 1}
    _alternar(app, "Ticket Médio")
    assert not app.exception and not app.error
    app.radio(key="nav_pagina").set_value("Analítico Comercial").run(timeout=20)
    assert not app.exception and not app.error
    assert leituras == {"vendas": 1, "metas": 1}


@pytest.mark.parametrize("pagina", ["Analítico Comercial", "Analítico Veículos", "🔧 Auditoria (dev)"])
def test_tab_meta_memorizada_nao_carrega_fonte_em_outros_destinos(monkeypatch, pagina):
    app, _, _, leituras = _entrada(monkeypatch, aba="Meta", pagina=pagina)
    assert not app.exception
    assert leituras == {"vendas": 1, "metas": 0}


def test_gate_de_autenticacao_permanece_anterior_as_fontes(monkeypatch):
    app, _, _, leituras = _entrada(monkeypatch)
    leituras.update(vendas=0, metas=0)
    st.cache_data.clear()
    app.session_state["autenticado"] = False
    app.session_state["performance_evolucao_tab"] = "Meta"
    app.run(timeout=20)
    assert not app.exception
    assert leituras == {"vendas": 0, "metas": 0}
