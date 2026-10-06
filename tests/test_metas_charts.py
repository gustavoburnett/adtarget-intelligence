"""Apresentação dos contratos de metas em figuras, sem fonte real ou Streamlit."""

import datetime as dt
from dataclasses import replace
from decimal import Decimal

import pandas as pd
import pytest

from src.components import metas_charts
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

REF = dt.date(2026, 10, 5)


def _meta(mes, valor=100, **extras):
    linha = {
        "NIVEL_META": "GRUPO", "GRUPO": "G", "VEICULO": "",
        "ANO": 2026, "MES": mes, "VALOR_META": valor, "ATIVO": "SIM",
        "REVISAO": 1, "CRIADO_EM": "2026-01-01T00:00:00-03:00", "MOTIVO": "Teste",
    }
    linha.update(extras)
    return linha


def _venda(mes, valor=10, ano=2026):
    return {
        COL_GRUPO: "G", COL_VEICULO: "V", COL_STATUS: "FATURADO",
        COL_VALOR_LIQUIDO: valor, COL_VALOR_BRUTO: valor * 10,
        COL_MES_VEICULACAO_DATA: f"{ano}-{mes:02d}-01",
        COL_MES_GANHO_DATA: f"{ano}-{mes:02d}-01",
    }


def _resultados(*, referencia=REF, plano=None, vendas=None, ano=2026):
    plano_df = pd.DataFrame(
        plano if plano is not None else [_meta(mes) for mes in range(1, 13)],
        columns=COLUNAS_METAS,
    )
    vendas_df = pd.DataFrame(
        vendas if vendas is not None else [
            *[_venda(mes) for mes in range(1, 10)],
            _venda(10, 30), _venda(11, 40), _venda(12, 50),
            *[_venda(mes, 5, ano=2025) for mes in range(1, 13)],
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


def test_acumulada_preserva_meta_e_anterior_ate_dez_sem_estender_realizado():
    resultado, _ = _resultados()
    figura = metas_charts.evolucao_acumulada(resultado)
    meta = _serie(figura, "Meta acumulada")
    anterior = _serie(figura, "2025 · mesmo perímetro")
    realizado = _serie(figura, "Realizado 2026 · fechado")
    assert list(meta.x) == list(range(1, 13))
    assert list(meta.y) == [mes * 100 for mes in range(1, 13)]
    assert list(anterior.y) == [mes * 5 for mes in range(1, 13)]
    assert list(realizado.y) == [mes * 10 for mes in range(1, 10)] + [None] * 3
    assert not realizado.connectgaps


def test_acumulada_sem_mes_encerrado_nao_inventa_linha_realizada():
    resultado, _ = _resultados(referencia=dt.date(2026, 1, 15))
    figura = metas_charts.evolucao_acumulada(resultado)
    realizado = _serie(figura, "Realizado 2026 · fechado")
    assert list(realizado.y) == [None] * 12
    assert _serie(figura, "Meta acumulada").y[-1] == 1200
    assert not any("Realizado ·" in anotacao.text for anotacao in figura.layout.annotations)


def test_acumulada_ano_encerrado_exibe_todos_os_meses_sem_faixa_atual():
    resultado, _ = _resultados(referencia=dt.date(2027, 1, 1))
    figura = metas_charts.evolucao_acumulada(resultado)
    assert _serie(figura, "Realizado 2026 · fechado").y[-1] == 210
    assert not figura.layout.shapes
    assert list(figura.layout.xaxis.ticktext) == list(metas_charts._MESES)


def test_acumulada_base_anterior_ausente_e_lacuna_nao_zero():
    resultado, _ = _resultados(vendas=[_venda(1, 20)])
    figura = metas_charts.evolucao_acumulada(resultado)
    anterior = _serie(figura, "2025 · mesmo perímetro")
    assert list(anterior.y) == [None] * 12
    assert "sem base de comparação" in anterior.customdata[0]
    assert not any("2025 · R$" in anotacao.text for anotacao in figura.layout.annotations)


def test_acumulada_estilos_distintos_e_rotulos_diretos_sem_depender_so_de_cor():
    resultado, _ = _resultados()
    figura = metas_charts.evolucao_acumulada(resultado)
    assert [serie.line.dash for serie in figura.data] == ["dashdot", "dash", "solid"]
    realizado = _serie(figura, "Realizado 2026 · fechado")
    assert realizado.line.width > max(serie.line.width for serie in figura.data[:-1])
    assert realizado.line.color == COR_MARCA
    assert realizado.mode == "lines+markers"
    textos = " ".join(anotacao.text for anotacao in figura.layout.annotations)
    assert "Meta · R$ 1,20 mil" in textos
    assert "Realizado · R$ 90,00" in textos
    assert "2025 · R$ 60,00" in textos


def test_acumulada_mes_em_andamento_identificado_e_hover_futuro_sem_resultado():
    resultado, _ = _resultados()
    figura = metas_charts.evolucao_acumulada(resultado)
    assert figura.layout.xaxis.ticktext[9] == "<b>Out*</b>"
    assert figura.layout.shapes[0].x0 == 9.55
    hover = _serie(figura, "Meta acumulada").customdata[9]
    assert "OUTUBRO 2026" in hover
    assert "Mês em andamento" in hover
    assert "Meta acumulada: R$ 1.000,00" in hover
    assert "Realizado acumulado:" not in hover
    assert "Atingimento:" not in hover
    assert "YoY:" not in hover


def test_acumulada_hover_fechado_informa_comparativos_e_saldo():
    resultado, _ = _resultados()
    figura = metas_charts.evolucao_acumulada(resultado)
    hover = _serie(figura, "Realizado 2026 · fechado").customdata[8]
    for texto in (
        "SETEMBRO 2026", "Mês encerrado", "Realizado acumulado: R$ 90,00",
        "Meta acumulada: R$ 900,00", "Atingimento: 10,0%",
        "Déficit: R$ 810,00", "2025, mesmo perímetro: R$ 45,00", "YoY: +100,0%",
    ):
        assert texto in hover


def test_mensal_preserva_os_12_meses_e_a_carteira_em_andamento_e_futura():
    resultado, pulso = _resultados()
    figura = metas_charts.evolucao_mensal(resultado, pulso)
    meta = _serie(figura, "Meta")
    realizado = _serie(figura, "Realizado")
    ja_vendido = [serie for serie in figura.data if serie.name == "Já vendido"]
    assert list(meta.x) == list(range(1, 13))
    assert list(meta.y) == [100] * 12
    assert list(realizado.x) == list(range(1, 10))
    assert list(realizado.y) == [10] * 9
    assert [list(serie.x) for serie in ja_vendido] == [[10], [11, 12]]
    assert [list(serie.y) for serie in ja_vendido] == [[30], [40, 50]]
    assert sum(serie.showlegend for serie in ja_vendido) == 1


def test_mensal_hachura_e_contornos_indicam_estados_em_escala_de_cinza():
    resultado, pulso = _resultados()
    figura = metas_charts.evolucao_mensal(resultado, pulso)
    assert _serie(figura, "Meta").marker.pattern.shape == "/"
    assert figura.layout.barmode == "overlay"
    assert [shape.line.dash for shape in figura.layout.shapes] == (
        ["solid"] * 9 + ["dash", "dot", "dot"]
    )
    assert figura.layout.xaxis.ticktext[10:] == ("Nov°", "Dez°")
    assert "Em andamento" in figura.layout.annotations[0].text
    assert "Futuro" in figura.layout.annotations[0].text


def test_mensal_hover_fechado_usa_realizado_meta_atingimento_saldo_e_yoy():
    resultado, pulso = _resultados()
    figura = metas_charts.evolucao_mensal(resultado, pulso)
    hover = _serie(figura, "Realizado").customdata[-1]
    for texto in (
        "SETEMBRO 2026", "Realizado: R$ 10,00", "Meta: R$ 100,00",
        "Atingimento: 10,0%", "Déficit: R$ 90,00",
        "Setembro/2025: R$ 5,00", "YoY: +100,0%",
    ):
        assert texto in hover
    assert "Já vendido:" not in hover


@pytest.mark.parametrize("mes,estado,vendido,cobertura", [
    (10, "Mês em andamento", "30,00", "30,0%"),
    (11, "Mês futuro", "40,00", "40,0%"),
    (12, "Mês futuro", "50,00", "50,0%"),
])
def test_mensal_hover_aberto_usa_ja_vendido_sem_inventar_realizado(mes, estado, vendido, cobertura):
    resultado, pulso = _resultados()
    figura = metas_charts.evolucao_mensal(resultado, pulso)
    hover = _serie(figura, "Meta").customdata[mes - 1]
    assert estado in hover
    assert f"Já vendido: R$ {vendido}" in hover
    assert f"Cobertura atual: {cobertura}" in hover
    assert "Realizado:" not in hover
    assert "Atingimento:" not in hover
    assert "YoY:" not in hover
    assert "Déficit:" not in hover


def test_mensal_rotulos_permanentes_seletivos_sem_rotular_meta_ou_futuro():
    resultado, pulso = _resultados()
    figura = metas_charts.evolucao_mensal(resultado, pulso)
    assert len(_serie(figura, "Realizado").text) == 9
    assert sum(bool(texto) for texto in _serie(figura, "Realizado").text) == 1
    assert not _serie(figura, "Meta").text
    assert sum(
        bool(texto)
        for serie in figura.data if serie.name == "Já vendido"
        for texto in (serie.text or ())
    ) == 1
    assert all(
        not texto
        for serie in figura.data if serie.name == "Já vendido"
        for mes, texto in zip(serie.x, serie.text or ()) if mes > 10
    )


def test_mensal_rotula_maior_superacao_deficit_e_mes_atual_preservando_hover():
    resultado, pulso = _resultados(vendas=[
        *[
            _venda(mes, valor)
            for mes, valor in enumerate((12, 27, 18, 93, 70, 200, 6, 20, 85), start=1)
        ],
        _venda(10, 9999), _venda(11, 99999), _venda(12, 999999),
    ])
    figura = metas_charts.evolucao_mensal(resultado, pulso)
    realizado = _serie(figura, "Realizado")
    assert {
        mes for mes, texto in zip(realizado.x, realizado.text) if texto
    } == {6, 7}
    assert len(realizado.customdata) == 9
    assert all("Realizado:" in hover for hover in realizado.customdata)
    assert {
        mes
        for serie in figura.data if serie.name == "Já vendido"
        for mes, texto in zip(serie.x, serie.text or ()) if texto
    } == {10}
    assert len(_serie(figura, "Meta").customdata) == 12


def test_mensal_envelope_meta_e_barras_partem_de_zero_com_larguras_distintas():
    resultado, pulso = _resultados()
    figura = metas_charts.evolucao_mensal(resultado, pulso)
    meta = _serie(figura, "Meta")
    assert meta.base == 0
    assert all(serie.base == 0 for serie in figura.data)
    assert all(serie.width < meta.width for serie in figura.data if serie.name != "Meta")
    assert figura.layout.barmode == "overlay"
    assert all(shape.y0 == 0 for shape in figura.layout.shapes)
    assert _serie(figura, "Realizado").y[0] == 10
    assert meta.y[0] == 100


def test_mensal_hover_aprovado_preservado_integralmente_nos_12_meses():
    resultado, pulso = _resultados()
    figura = metas_charts.evolucao_mensal(resultado, pulso)
    esperado = [
        (
            f"<b>{mes.upper()} 2026</b><br>Mês encerrado"
            "<br>Realizado: R$ 10,00<br>Meta: R$ 100,00"
            "<br>Atingimento: 10,0%<br>Déficit: R$ 90,00"
            f"<br>{mes}/2025: R$ 5,00<br>YoY: +100,0%"
        )
        for mes in (
            "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
            "Julho", "Agosto", "Setembro",
        )
    ] + [
        (
            f"<b>{mes} 2026</b><br>{estado}<br>Já vendido: R$ {valor},00"
            f"<br>Meta: R$ 100,00<br>Cobertura atual: {valor},0%"
        )
        for mes, estado, valor in (
            ("OUTUBRO", "Mês em andamento", "30"),
            ("NOVEMBRO", "Mês futuro", "40"),
            ("DEZEMBRO", "Mês futuro", "50"),
        )
    ]
    assert list(_serie(figura, "Meta").customdata) == esperado
    for serie in figura.data:
        assert list(serie.customdata) == [esperado[mes - 1] for mes in serie.x]


def test_mensal_superavit_mantem_referencia_de_meta_visivel_sobre_a_barra():
    resultado, pulso = _resultados(vendas=[_venda(1, 150)])
    figura = metas_charts.evolucao_mensal(resultado, pulso)
    realizado = _serie(figura, "Realizado")
    assert realizado.y[0] == 150
    assert figura.layout.shapes[0].y1 == 100
    assert figura.layout.shapes[0].layer == "above"
    assert realizado.y[0] > _serie(figura, "Meta").y[0]
    assert realizado.base == 0
    assert not any("excedente" in serie.name.lower() for serie in figura.data)
    assert "Superávit: R$ 50,00" in realizado.customdata[0]


@pytest.mark.parametrize("plano,mensagem", [
    ([_meta(1, 0)], "Meta ativa com valor zero"),
    ([_meta(1, 0, ATIVO="NAO")], "Sem meta ativa neste mês"),
    ([_meta(2)], "Sem meta cadastrada neste mês"),
])
def test_mensal_zero_inativo_e_ausencia_nao_inventam_percentual(plano, mensagem):
    resultado, pulso = _resultados(plano=plano)
    figura = metas_charts.evolucao_mensal(resultado, pulso)
    hover = _serie(figura, "Meta").customdata[0]
    assert mensagem in hover
    assert "Atingimento:" not in hover
    assert not any(shape.x0 == 0.68 for shape in figura.layout.shapes)


def test_mensal_base_yoy_ausente_nao_vira_comparativo_zero():
    resultado, pulso = _resultados(vendas=[_venda(1, 20)])
    figura = metas_charts.evolucao_mensal(resultado, pulso)
    hover = _serie(figura, "Realizado").customdata[0]
    assert "Janeiro/2025: sem base de comparação" in hover
    assert "YoY: sem base de comparação" in hover
    assert "+0,0%" not in hover


def test_mensal_valor_negativo_nao_e_suprimido_ou_convertido_em_zero():
    resultado, pulso = _resultados(vendas=[_venda(1, -12.345)])
    figura = metas_charts.evolucao_mensal(resultado, pulso)
    realizado = _serie(figura, "Realizado")
    assert realizado.y[0] == -12.345
    assert "Realizado: R$ -12,35" in realizado.customdata[0]
    assert "Déficit: R$ 112,35" in realizado.customdata[0]


@pytest.mark.parametrize("campo,valor", [
    ("ano", 2025),
    ("data_referencia", dt.date(2026, 10, 6)),
    ("meses_encerrados", 8),
    ("meses", ()),
])
def test_mensal_rejeita_mistura_de_anos_referencias_e_series(campo, valor):
    resultado, pulso = _resultados()
    with pytest.raises(ValueError, match="mesmo ano e referência"):
        metas_charts.evolucao_mensal(resultado, replace(pulso, **{campo: valor}))


def test_figuras_sao_responsivas_serializaveis_e_acumulada_e_protagonista():
    resultado, pulso = _resultados()
    acumulada = metas_charts.evolucao_acumulada(resultado)
    mensal = metas_charts.evolucao_mensal(resultado, pulso)
    assert acumulada.layout.height > mensal.layout.height
    for figura in (acumulada, mensal):
        assert figura.layout.autosize
        assert figura.layout.width is None
        assert figura.layout.xaxis.range == (0.5, 12.5)
        assert figura.to_json()
    assert resultado.realizado_ytd == Decimal(90)
    assert pulso.carteira_futura == Decimal(120)


def test_mensal_permite_rotulo_de_dezembro_na_borda_sem_alterar_acumulada():
    resultado, pulso = _resultados()
    mensal = metas_charts.evolucao_mensal(resultado, pulso)
    acumulada = metas_charts.evolucao_acumulada(resultado)
    assert mensal.layout.xaxis.ticklabeloverflow == "allow"
    assert mensal.layout.xaxis.tickvals[-1] == 12
    assert mensal.layout.xaxis.ticktext[-1] == "Dez°"
    assert acumulada.layout.xaxis.ticklabeloverflow is None
