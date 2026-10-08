"""Proteção do CSV, com registros sintéticos e sem dados ou fonte reais."""

import csv
import datetime as dt
from decimal import Decimal
import io

import pandas as pd
import pyarrow as pa
import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from pages_content import analitico_comercial
from src.data import cleaning
from src.data.csv_export import gerar_csv_seguro
from tests.test_performance_meta import _fonte_vendas


def _linhas(conteudo):
    return list(csv.reader(io.StringIO(conteudo.decode("utf-8-sig"))))


@pytest.mark.parametrize("texto", [
    "=1+1", "+SUM(A1:A2)", "-1+2", "@SUM(A1:A2)",
    "   =1+1", "\t+1+2", "\n-1+2", "\r\n@SUM(A1:A2)",
    '"=1+1', ' \t" \n"+1+2',
    '=HYPERLINK("https://example.invalid","TESTE")',
    "=1+1\nSEGUNDA LINHA", "@ação; ç, á\tfinal",
    "\u00a0=1+1", "\u2003+1+2", "\ufeff-1+2", "\x00@SUM(A1:A2)",
    "\x1b=1+1", "\x7f+1+2",
])
def test_prefixos_de_risco_sao_texto_no_csv_serializado(texto):
    original = pd.DataFrame({"CLIENTE": [texto], "VALOR PI LIQUIDO": [-123.45]})
    copia = original.copy(deep=True)
    conteudo = gerar_csv_seguro(original)
    assert conteudo.startswith(b"\xef\xbb\xbf")
    assert _linhas(conteudo) == [
        ["CLIENTE", "VALOR PI LIQUIDO"], ["'" + texto, "-123.45"],
    ]
    pd.testing.assert_frame_equal(original, copia)


@pytest.mark.parametrize("texto", [
    "CLIENTE DE TESTE", "CARREGA+", "PI-001", "RÁDIO · TESTE",
    'TEXTO "COM ASPAS"', "PRIMEIRA LINHA\nSEGUNDA LINHA", "A,B;C\tD",
    "' =1+1", "", "   ", "\tTEXTO COMUM", '"TEXTO COMUM"',
])
def test_textos_comuns_e_ja_neutralizados_preservados(texto):
    tabela = pd.DataFrame({"CLIENTE": [texto]})
    assert gerar_csv_seguro(tabela) == tabela.to_csv(index=False).encode("utf-8-sig")
    assert _linhas(gerar_csv_seguro(tabela)) == [["CLIENTE"], [texto]]


def test_financeiros_negativos_datas_nulos_e_dtypes_nao_sao_alterados():
    original = pd.DataFrame({
        "CLIENTE": ["=1+1", None, "CLIENTE"],
        "VALOR PI LIQUIDO": [-123.45, 0.0, 500.25],
        "VALOR PI BRUTO": [-200, 0, 1000],
        "PRECISAO": [Decimal("-123.4567"), Decimal("0.00"), Decimal("500.2500")],
        "INICIO": [dt.date(2026, 1, 2), None, dt.date(2026, 1, 3)],
        "DATA": pd.to_datetime(["2026-01-02", None, "2026-01-03"]),
        "OPCIONAL": pd.array([-1.5, pd.NA, 2.5], dtype="Float64"),
        "INTEIRO": pd.array([-123, pd.NA, 100], dtype="Int64"),
    }, index=pd.Index([4, 5, 6], name="ORIGEM"))
    # Um índice não padrão não deve alterar a ordem nem aparecer no CSV.
    copia = original.copy(deep=True)
    antes = _linhas(original.to_csv(index=False).encode("utf-8-sig"))
    depois = _linhas(gerar_csv_seguro(original))
    assert depois[0] == antes[0]
    assert [linha[1:] for linha in depois[1:]] == [linha[1:] for linha in antes[1:]]
    assert depois[1][0] == "'=1+1"
    assert depois[1][1:5] == ["-123.45", "-200", "-123.4567", "2026-01-02"]
    pd.testing.assert_frame_equal(original, copia)


def test_mistos_categorias_e_dataframe_vazio():
    original = pd.DataFrame({
        "MISTO": ["=1+1", -5, None],
        "CATEGORIA": pd.Categorical(["+TESTE", "COMUM", None]),
    })
    copia = original.copy(deep=True)
    assert _linhas(gerar_csv_seguro(original)) == [
        ["MISTO", "CATEGORIA"], ["'=1+1", "'+TESTE"], ["-5", "COMUM"], ["", ""],
    ]
    pd.testing.assert_frame_equal(original, copia)
    vazia = original.iloc[:0]
    assert gerar_csv_seguro(vazia) == vazia.to_csv(index=False).encode("utf-8-sig")


def _render_pagina(tabela):
    from pages_content.analitico_comercial import render

    render(tabela)


def test_pagina_protege_downloads_preservando_aparencia_filtros_e_valores(monkeypatch):
    vendas = cleaning.limpar_dataframe(_fonte_vendas())
    alvo = vendas[cleaning.COL_MES_VEICULACAO_DATA].dt.year.eq(2026)
    vendas.loc[alvo, cleaning.COL_CLIENTE] = '=HYPERLINK("https://example.invalid","TESTE")'
    vendas.loc[alvo, cleaning.COL_VALOR_LIQUIDO] = -123.45
    copia = vendas.copy(deep=True)
    downloads = []
    botao_original = st.download_button

    def capturar(label, data, **kwargs):
        downloads.append((label, data, kwargs))
        return botao_original(label, data, **kwargs)

    monkeypatch.setattr(analitico_comercial.st, "download_button", capturar)
    app = AppTest.from_function(_render_pagina, args=(vendas,))
    app.session_state["anfat_ano"] = 2026
    app.session_state["anfat_valor"] = "Valor Líquido"
    app.session_state["anfat_mes"] = "Mês (Veiculação)"
    app = app.run(timeout=20)
    assert not app.exception
    exibida = app.dataframe[-1].value
    visual = pa.ipc.open_stream(
        app.dataframe[-1].proto.arrow_data.styler.display_values,
    ).read_all().to_pandas()
    assert exibida[cleaning.COL_CLIENTE].str.startswith("'=").all()
    assert visual[cleaning.COL_CLIENTE].str.startswith("=").all()
    assert exibida[cleaning.COL_VALOR_LIQUIDO].eq(-123.45).all()
    assert len(downloads) == 1
    label, conteudo, opcoes = downloads[0]
    assert label == "Exportar CSV"
    assert opcoes["file_name"] == "analitico_comercial_2026.csv"
    assert opcoes["mime"] == "text/csv" and opcoes["key"] == "anfat_csv"
    esperado = vendas.loc[alvo, exibida.columns]
    assert conteudo == gerar_csv_seguro(esperado)
    pd.testing.assert_frame_equal(vendas, copia)
