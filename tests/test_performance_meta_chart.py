"""Resumo de metas da Performance, com contratos e valores sintéticos."""

import datetime as dt
from dataclasses import replace
from decimal import Decimal

import pandas as pd
import pytest

from src.components import charts, metas_charts
from src.components.cards import COR_MARCA
from src.data import metas
from src.data.cleaning import (
    COL_GRUPO,
    COL_MES_GANHO_DATA,
    COL_MES_VEICULACAO_DATA,
    COL_STATUS,
    COL_VALOR_BRUTO,
    COL_VALOR_LIQUIDO,
    COL_VEICULO,
)
from src.data.metas_schema import COLUNAS_METAS

REF = dt.date(2026, 10, 6)


def _meta(mes, ano=2026, valor=100):
    return {
        "NIVEL_META": "GRUPO", "GRUPO": "G", "VEICULO": "",
        "ANO": ano, "MES": mes, "VALOR_META": valor, "ATIVO": "SIM",
        "REVISAO": 1, "CRIADO_EM": "2026-01-01T00:00:00-03:00", "MOTIVO": "Teste",
    }


def _venda(mes, valor=10, ano=2026):
    return {
        COL_GRUPO: "G", COL_VEICULO: "V", COL_STATUS: "FATURADO",
        COL_VALOR_LIQUIDO: valor, COL_VALOR_BRUTO: valor * 10,
        COL_MES_VEICULACAO_DATA: f"{ano}-{mes:02d}-01",
        COL_MES_GANHO_DATA: f"{ano}-{mes:02d}-01",
    }


def _resultados(*, ano=2026, referencia=REF, vendas=None, plano=None):
    plano_df = pd.DataFrame(
        plano if plano is not None else [_meta(mes, ano) for mes in range(1, 13)],
        columns=COLUNAS_METAS,
    )
    vendas_df = pd.DataFrame(
        vendas if vendas is not None else [
            *[_venda(mes, ano=ano) for mes in range(1, 10)],
            _venda(10, 30, ano), _venda(11, 40, ano), _venda(12, 50, ano),
            *[_venda(mes, 5, ano - 1) for mes in range(1, 13)],
        ],
        columns=list(_venda(1)),
    )
    for coluna in (COL_MES_VEICULACAO_DATA, COL_MES_GANHO_DATA):
        vendas_df[coluna] = pd.to_datetime(vendas_df[coluna])
    return (
        metas.avaliar_metas(vendas_df, plano_df, ano, data_referencia=referencia),
        metas.avaliar_pulso(vendas_df, plano_df, ano, data_referencia=referencia),
    )


def _serie(figura, nome):
    return next(serie for serie in figura.data if serie.name == nome)


def test_meta_acumulada_inicia_em_janeiro_e_termina_na_meta_anual_da_engine():
    resultado, pulso = _resultados()
    figura = metas_charts.evolucao_performance_meta(resultado, pulso)
    meta = _serie(figura, "Meta acumulada")
    assert list(meta.x) == list(range(1, 13))
    assert list(meta.y) == [float(mes.meta_acumulada) for mes in resultado.meses]
    assert meta.y[-1] == float(resultado.meta_anual)
    assert meta.line.dash == "dashdot"


def test_realizado_conserva_acumulados_oficiais_e_termina_no_ultimo_fechado():
    resultado, pulso = _resultados()
    figura = metas_charts.evolucao_performance_meta(resultado, pulso)
    realizado = _serie(figura, "Realizado acumulado · fechado")
    assert list(realizado.y) == [mes * 10 for mes in range(1, 10)] + [None] * 3
    assert list(realizado.y[:9]) == [float(mes.realizado_acumulado) for mes in resultado.meses[:9]]
    assert realizado.line.dash == "solid"
    assert realizado.marker.symbol == "circle"
    assert not realizado.connectgaps


def test_carteira_acumulada_conecta_no_ultimo_fechado_e_reconcilia_total_anual():
    resultado, pulso = _resultados()
    figura = metas_charts.evolucao_performance_meta(resultado, pulso)
    carteira = _serie(figura, "Já vendido acumulado")
    assert list(carteira.x) == [9, 10, 11, 12]
    assert list(carteira.y) == [90, 120, 160, 210]
    assert carteira.y[0] == float(resultado.realizado_ytd)
    assert carteira.y[-1] == float(pulso.total_vendido_ano)
    assert carteira.line.dash == "dash"
    assert carteira.marker.symbol == "circle-open"
    assert carteira.marker.size[0] == 0
    assert carteira.line.color == COR_MARCA


def test_acumulado_nao_arredonda_os_valores_mensais_da_carteira():
    resultado, pulso = _resultados(vendas=[
        _venda(1, 0.011), _venda(10, 0.004), _venda(11, 0.004), _venda(12, 0.004),
    ])
    figura = metas_charts.evolucao_performance_meta(resultado, pulso)
    carteira = _serie(figura, "Já vendido acumulado")
    assert list(carteira.y) == [0.011, 0.015, 0.019, 0.023]
    assert carteira.y[-1] == float(pulso.total_vendido_ano)
    assert "Total já vendido acumulado: R$ 0,02" in carteira.customdata[-1]


def test_hover_fechado_utiliza_indicadores_acumulados_da_engine():
    resultado, pulso = _resultados()
    figura = metas_charts.evolucao_performance_meta(resultado, pulso)
    hover = _serie(figura, "Realizado acumulado · fechado").customdata[8]
    for texto in (
        "SETEMBRO 2026", "Mês encerrado", "Meta acumulada: R$ 900,00",
        "Realizado acumulado: R$ 90,00", "Atingimento: 10,0%",
        "Déficit: R$ 810,00", "2025, mesmo perímetro: R$ 45,00", "YoY: +100,0%",
    ):
        assert texto in hover
    assert "Total já vendido acumulado:" not in hover


@pytest.mark.parametrize("mes,valor,estado,meta", [
    (10, "120,00", "Mês em andamento", "Meta acumulada: R$ 1.000,00"),
    (11, "160,00", "Mês futuro", "Meta acumulada planejada: R$ 1.100,00"),
    (12, "210,00", "Mês futuro", "Meta acumulada planejada: R$ 1.200,00"),
])
def test_hover_aberto_exibe_ja_vendido_sem_resultados_oficiais_futuros(mes, valor, estado, meta):
    resultado, pulso = _resultados()
    figura = metas_charts.evolucao_performance_meta(resultado, pulso)
    carteira = _serie(figura, "Já vendido acumulado")
    hover = carteira.customdata[list(carteira.x).index(mes)]
    assert meta in hover
    assert f"Total já vendido acumulado: R$ {valor}" in hover
    assert estado in hover
    assert "Realizado acumulado:" not in hover
    assert "Atingimento:" not in hover
    assert "Déficit:" not in hover
    assert "Superávit:" not in hover
    assert "YoY:" not in hover
    assert _serie(figura, "Meta acumulada").customdata[mes - 1] == hover


def test_anchor_da_carteira_preserva_semantica_realizada_do_ultimo_fechado():
    resultado, pulso = _resultados()
    figura = metas_charts.evolucao_performance_meta(resultado, pulso)
    carteira = _serie(figura, "Já vendido acumulado")
    realizado = _serie(figura, "Realizado acumulado · fechado")
    assert carteira.customdata[0] == realizado.customdata[8]
    assert "Realizado acumulado:" in carteira.customdata[0]


def test_mes_em_andamento_visivel_sem_esconder_vendas_futuras():
    resultado, pulso = _resultados()
    figura = metas_charts.evolucao_performance_meta(resultado, pulso)
    assert figura.layout.shapes[0].x0 == 9.55
    assert figura.layout.shapes[0].x1 == 10.45
    assert figura.layout.shapes[0].line.dash == "dash"
    textos = [anotacao.text for anotacao in figura.layout.annotations]
    assert "Mês em andamento" in textos
    assert not any("sem dado disponível" in texto for texto in textos)


def test_ano_encerrado_tem_realizado_completo_e_nao_tem_trecho_ja_vendido():
    resultado, pulso = _resultados(referencia=dt.date(2027, 1, 1))
    figura = metas_charts.evolucao_performance_meta(resultado, pulso)
    assert len(figura.data) == 2
    assert _serie(figura, "Realizado acumulado · fechado").y[-1] == 210
    assert not any(serie.name == "Já vendido acumulado" for serie in figura.data)
    assert not figura.layout.shapes


@pytest.mark.parametrize("ano,referencia", [
    (2026, dt.date(2026, 1, 15)),
    (2027, REF),
])
def test_sem_fechados_so_mostra_carteira_sem_inventar_realizado(ano, referencia):
    resultado, pulso = _resultados(ano=ano, referencia=referencia)
    figura = metas_charts.evolucao_performance_meta(resultado, pulso)
    assert len(figura.data) == 2
    assert not any(serie.name == "Realizado acumulado · fechado" for serie in figura.data)
    carteira = _serie(figura, "Já vendido acumulado")
    assert list(carteira.x) == list(range(1, 13))
    assert carteira.y[0] == 10
    assert carteira.y[-1] == float(pulso.total_vendido_ano)


def test_meta_ativa_zero_nao_inventa_atingimento_e_carteira_continua_visivel():
    resultado, pulso = _resultados(plano=[_meta(mes, valor=0) for mes in range(1, 13)])
    figura = metas_charts.evolucao_performance_meta(resultado, pulso)
    assert list(_serie(figura, "Meta acumulada").y) == [0] * 12
    hover = _serie(figura, "Realizado acumulado · fechado").customdata[0]
    assert "Sem meta acumulada positiva" in hover
    assert "Atingimento:" not in hover
    assert _serie(figura, "Já vendido acumulado").y[-1] == 210


def test_sem_base_anterior_preserva_ausencia_comparativa_no_hover():
    resultado, pulso = _resultados(vendas=[_venda(1, 20)])
    figura = metas_charts.evolucao_performance_meta(resultado, pulso)
    hover = _serie(figura, "Realizado acumulado · fechado").customdata[0]
    assert "2025, mesmo perímetro: sem base de comparação" in hover
    assert "YoY: sem base de comparação" in hover


def test_valores_negativos_e_reducao_de_carteira_nao_sao_truncados():
    resultado, pulso = _resultados(vendas=[
        _venda(1, -10), _venda(10, -30), _venda(11, -40), _venda(12, -50),
    ])
    figura = metas_charts.evolucao_performance_meta(resultado, pulso)
    assert _serie(figura, "Realizado acumulado · fechado").y[0] == -10
    assert list(_serie(figura, "Já vendido acumulado").y) == [-10, -40, -80, -130]
    assert figura.layout.yaxis.range is None
    assert "Total já vendido acumulado: R$ -130,00" in _serie(figura, "Já vendido acumulado").customdata[-1]


@pytest.mark.parametrize("campo,valor", [
    ("ano", 2025),
    ("data_referencia", dt.date(2026, 10, 7)),
    ("meses_encerrados", 8),
    ("meses", ()),
])
def test_rejeita_snapshots_incompativeis_sem_fallback(campo, valor):
    resultado, pulso = _resultados()
    with pytest.raises(ValueError, match="mesmo snapshot"):
        metas_charts.evolucao_performance_meta(resultado, replace(pulso, **{campo: valor}))


@pytest.mark.parametrize("campo,valor", [
    ("estado_mes", "futuro"),
    ("meta_centavos", 20000),
    ("vendido", Decimal(11)),
])
def test_rejeita_meses_de_planos_ou_vendas_diferentes(campo, valor):
    resultado, pulso = _resultados()
    mes_diferente = replace(pulso.meses[0], **{campo: valor})
    misturado = replace(pulso, meses=(mes_diferente, *pulso.meses[1:]))
    with pytest.raises(ValueError, match="mesmo snapshot"):
        metas_charts.evolucao_performance_meta(resultado, misturado)


def test_figura_pura_preserva_contratos_e_dimensoes_nativas_da_performance(monkeypatch):
    resultado, pulso = _resultados()
    antes = repr(resultado), repr(pulso)

    def interface_proibida(*args, **kwargs):
        pytest.fail("A figura pura não deve renderizar Streamlit.")

    monkeypatch.setattr(charts.st, "plotly_chart", interface_proibida)
    figura = metas_charts.evolucao_performance_meta(resultado, pulso)
    assert (repr(resultado), repr(pulso)) == antes
    assert figura.layout.height == 392
    assert figura.layout.width is None
    assert figura.layout.autosize
    assert figura.layout.xaxis.range == (0.5, 12.5)
    assert list(figura.layout.xaxis.tickvals) == list(range(1, 13))
    assert figura.to_json()
