"""Design 1H: rankings nativos com números, dimensões e CSV seguro preservados."""

from decimal import Decimal

import pandas as pd
import pyarrow as pa
import pytest
from streamlit.elements.lib.pandas_styler_utils import marshall_styler
from streamlit.proto.ArrowData_pb2 import ArrowData

from src.components.veiculos_tables import (
    configuracao_colunas_ranking,
    preparar_ranking_dimensao,
    preparar_ranking_veiculos,
)
from src.data import metrics
from src.data.cleaning import (
    COL_AGENCIA, COL_CLIENTE, COL_GRUPO, COL_STATUS,
    COL_VALOR_BRUTO, COL_VALOR_LIQUIDO, COL_VEICULO,
)
from src.data.csv_export import _neutralizar_formula


COLUNAS = [
    "Veículo", "Vendas (Bruto)", "Vendas (Líquido)",
    "Ticket Médio", "Qtd PIs", "% do Total",
]
CORRESPONDENCIA = {
    "Vendas (Bruto)": "vendas_bruto",
    "Vendas (Líquido)": "vendas_liquido",
    "Ticket Médio": "ticket_medio",
    "Qtd PIs": "qtd_pis",
    "% do Total": "pct_do_total",
}


def _exibida(styler):
    envelope = ArrowData()
    marshall_styler(envelope, styler, "ranking-teste")
    return pa.ipc.open_stream(envelope.styler.display_values).read_all().to_pandas()


def _agregado():
    return pd.DataFrame({
        COL_GRUPO: ["DISNEY", "DISNEY", "TEADS", "OUTRO"],
        COL_VEICULO: ["DISNEY+", "ESPN", "TEADS", "TEADS"],
        "vendas_bruto": [9000.123456789, 100.567890123, -123.123456789, 0.0],
        "vendas_liquido": [8000.123456789, 80.567890123, -100.123456789, 0.0],
        "ticket_medio": [4000.0617283945, 80.567890123, -100.123456789, 0.0],
        "qtd_pis": [2, 1, 1, 1],
        "pct_do_total": [98.5, 1.5, -1.2, 0.0],
    })


def _base_comercial():
    return pd.DataFrame({
        COL_GRUPO: ["DISNEY", "DISNEY", "TEADS", "OUTRO", "DISNEY", "OUTRO"],
        COL_VEICULO: ["DISNEY+", "ESPN", "TEADS", "TEADS", "DISNEY+", "TEADS"],
        COL_AGENCIA: ["AGÊNCIA A", "AGÊNCIA B", "AGÊNCIA A", "AGÊNCIA A", "AGÊNCIA B", "AGÊNCIA A"],
        COL_CLIENTE: ["CLIENTE A", "CLIENTE B", "CLIENTE A", "CLIENTE B", "CLIENTE A", "CLIENTE B"],
        COL_STATUS: ["FATURADO", "A VEICULAR", "DIRETO", "CHECKING", "CANCELADO", "BONIFICADO"],
        COL_VALOR_BRUTO: [9000.123456789, 100.567890123, 7000.123456789, 900.01, 99000.0, 33000.0],
        COL_VALOR_LIQUIDO: [8000.123456789, 80.567890123, 6000.123456789, 700.01, 89000.0, 23000.0],
    })


def test_seis_colunas_ordem_e_numeros_sem_arredondamento_ou_mutacao():
    original = _agregado()
    original.index = [3, 3, 9, 7]
    copia = original.copy(deep=True)
    styler = preparar_ranking_veiculos(original)
    assert list(styler.data.columns) == COLUNAS
    for exibida, origem in CORRESPONDENCIA.items():
        pd.testing.assert_series_equal(
            styler.data[exibida], original[origem].reset_index(drop=True), check_names=False,
        )
    pd.testing.assert_frame_equal(original, copia)
    assert styler.data.index.tolist() == [0, 1, 2, 3]


def test_identificacao_sem_repeticao_nao_confunde_disney_ou_homonimos():
    styler = preparar_ranking_veiculos(_agregado())
    assert _exibida(styler)["Veículo"].tolist() == [
        "DISNEY — DISNEY+", "DISNEY — ESPN", "TEADS", "OUTRO — TEADS",
    ]
    assert len(styler.data) == 4


@pytest.mark.parametrize("coluna", ["Vendas (Bruto)", "Vendas (Líquido)", "Ticket Médio"])
def test_ordenacao_financeira_numerica_corrige_a_antiga_ordenacao_textual(coluna):
    original = _agregado()
    original[CORRESPONDENCIA[coluna]] = [9000.123456789, 10000.567890123, -123.123456789, 0.0]
    styler = preparar_ranking_veiculos(original)
    raw = pa.Table.from_pandas(styler.data, preserve_index=False).to_pandas()
    assert pd.api.types.is_numeric_dtype(raw[coluna])
    assert raw.sort_values(coluna).index.tolist() == [2, 3, 0, 1]
    # O ranking legado entregava strings e "R$ 10.000..." precedia "R$ 9.000...".
    exibida = _exibida(styler)
    assert exibida.sort_values(coluna).index.tolist() != raw.sort_values(coluna).index.tolist()


def test_moeda_e_percentual_ptbr_ficam_apenas_no_display_arrow():
    original = _agregado()
    styler = preparar_ranking_veiculos(original)
    exibida = _exibida(styler)
    assert exibida["Vendas (Bruto)"].tolist() == ["R$ 9.000,12", "R$ 100,57", "R$ -123,12", "R$ 0,00"]
    assert exibida["Vendas (Líquido)"].tolist() == ["R$ 8.000,12", "R$ 80,57", "R$ -100,12", "R$ 0,00"]
    assert exibida["Ticket Médio"].tolist() == ["R$ 4.000,06", "R$ 80,57", "R$ -100,12", "R$ 0,00"]
    assert exibida["% do Total"].tolist() == ["98,5%", "1,5%", "-1,2%", "0,0%"]
    assert styler.data["% do Total"].tolist() == original["pct_do_total"].tolist()


@pytest.mark.parametrize("valor", ["liquido", "bruto"])
def test_motor_oficial_preserva_registros_somas_tickets_contagens_e_participacoes(valor):
    base = _base_comercial()
    original = metrics.agregado_por_grupo_veiculo(base, valor)
    copia = original.copy(deep=True)
    styler = preparar_ranking_veiculos(original)
    for exibida, origem in CORRESPONDENCIA.items():
        pd.testing.assert_series_equal(styler.data[exibida], original[origem], check_names=False)
    coluna = "Vendas (Líquido)" if valor == "liquido" else "Vendas (Bruto)"
    assert styler.data[coluna].sum() == metrics.vendas(base, valor)
    assert styler.data["Qtd PIs"].sum() == 4
    assert len(styler.data) == metrics.veiculos_ativos(base) == 4
    disney = original[original[COL_GRUPO] == "DISNEY"]
    assert len(disney) == 2
    assert set(disney[COL_VEICULO]) == {"DISNEY+", "ESPN"}
    pd.testing.assert_frame_equal(original, copia)


@pytest.mark.parametrize("coluna", [COL_AGENCIA, COL_CLIENTE])
@pytest.mark.parametrize("valor", ["liquido", "bruto"])
def test_rankings_dimensao_preservam_colunas_ordem_e_calculo_oficial(coluna, valor):
    base = _base_comercial()
    original = metrics.agregado_por_dimensao(base, coluna, valor).rename(
        columns={"valor": "Vendas", "qtd_pis": "Qtd PIs"},
    )
    copia = original.copy(deep=True)
    styler = preparar_ranking_dimensao(original)
    pd.testing.assert_frame_equal(styler.data, original)
    pd.testing.assert_frame_equal(original, copia)
    assert list(styler.data) == [coluna, "Vendas", "Qtd PIs"]
    assert styler.data["Vendas"].sum() == pytest.approx(metrics.vendas(base, valor), rel=0, abs=1e-9)
    assert styler.data["Qtd PIs"].sum() == 4


@pytest.mark.parametrize("texto", [
    "=1+1", "+SUM(A1:A2)", "-1+2", "@SUM(A1:A2)",
    "\t+1+2", "\r\n@SUM(A1:A2)", '\"=1+1',
    "\u00a0=1+1", "\ufeff-1+2", "\x00@SUM(A1:A2)",
])
def test_csv_nativo_protegido_e_display_original_no_ranking_veiculos(texto):
    original = _agregado().iloc[:1].copy()
    original[COL_GRUPO] = texto
    original[COL_VEICULO] = texto
    copia = original.copy(deep=True)
    styler = preparar_ranking_veiculos(original)
    raw = pa.Table.from_pandas(styler.data, preserve_index=False).to_pandas()
    assert raw.iloc[0]["Veículo"] == _neutralizar_formula(texto)
    assert _exibida(styler).iloc[0]["Veículo"] == texto
    assert raw.iloc[0]["Vendas (Bruto)"] == original.iloc[0]["vendas_bruto"]
    pd.testing.assert_frame_equal(original, copia)


@pytest.mark.parametrize("dimensao", [COL_AGENCIA, COL_CLIENTE])
def test_colisoes_de_neutralizacao_sao_restauradas_por_celula(dimensao):
    original = pd.DataFrame({
        dimensao: ["=1+1", "'=1+1", "@ação", "'@ação"],
        "Vendas": [9000.123456789, 100.567890123, -123.123456789, 0.0],
        "Qtd PIs": [1, 2, 3, 4],
    })
    copia = original.copy(deep=True)
    styler = preparar_ranking_dimensao(original)
    assert styler.data[dimensao].tolist() == ["'=1+1", "'=1+1", "'@ação", "'@ação"]
    assert _exibida(styler)[dimensao].tolist() == original[dimensao].tolist()
    pd.testing.assert_frame_equal(original, copia)


def test_nomes_compostos_tambem_protegidos_e_sem_truncamento_interno():
    original = _agregado().iloc[:1].copy()
    grupo = "=GRUPO " + "áéç " * 80
    veiculo = "VEÍCULO " + "中文日本語 " * 70
    original[COL_GRUPO] = grupo
    original[COL_VEICULO] = veiculo
    styler = preparar_ranking_veiculos(original)
    esperado = grupo + " — " + veiculo
    assert styler.data.iloc[0]["Veículo"] == "'" + esperado
    assert _exibida(styler).iloc[0]["Veículo"] == esperado


def test_zero_e_ausencia_sao_distintos_com_precisao_numerica_preservada():
    original = _agregado().iloc[:3].copy()
    for coluna in ("vendas_bruto", "vendas_liquido", "ticket_medio", "pct_do_total"):
        original[coluna] = pd.array([0.0, -123.456789012, pd.NA], dtype="Float64")
    styler = preparar_ranking_veiculos(original)
    for exibida, origem in CORRESPONDENCIA.items():
        pd.testing.assert_series_equal(styler.data[exibida], original[origem], check_names=False)
    assert _exibida(styler)["Vendas (Bruto)"].tolist() == ["R$ 0,00", "R$ -123,46", "—"]
    assert _exibida(styler)["% do Total"].tolist() == ["0,0%", "-123,5%", "—"]
    pa.Table.from_pandas(styler.data, preserve_index=False)


def test_decimal_e_contagem_nullable_nao_viram_texto():
    original = pd.DataFrame({
        COL_CLIENTE: ["CLIENTE A", "CLIENTE B"],
        "Vendas": [Decimal("123456789.123456789"), Decimal("0.000000000")],
        "Qtd PIs": pd.array([1, pd.NA], dtype="Int64"),
    })
    styler = preparar_ranking_dimensao(original)
    pd.testing.assert_frame_equal(styler.data, original)
    pa.Table.from_pandas(styler.data, preserve_index=False)
    assert _exibida(styler)["Vendas"].tolist() == ["R$ 123.456.789,12", "R$ 0,00"]


def test_configuracao_nativa_nao_sobrescreve_moeda_ou_limita_precisao():
    styler = preparar_ranking_veiculos(_agregado())
    configuracao = configuracao_colunas_ranking(styler.data)
    assert list(configuracao) == COLUNAS
    for coluna in CORRESPONDENCIA:
        campo = configuracao[coluna]
        assert campo["type_config"]["type"] == "number"
        assert campo["type_config"]["format"] is None
        assert campo["type_config"]["step"] is None
        assert campo["alignment"] == "right"
    assert configuracao["Veículo"]["type_config"]["type"] == "text"


def test_valores_monetarios_extensos_tem_largura_para_formato_completo():
    original = pd.DataFrame({COL_AGENCIA: ["A"], "Vendas": [1234567890123.45], "Qtd PIs": [1]})
    configuracao = configuracao_colunas_ranking(original)
    assert configuracao["Vendas"]["width"] >= len("R$ 1.234.567.890.123,45") * 8 + 40


@pytest.mark.parametrize("coluna", [COL_AGENCIA, COL_CLIENTE])
def test_ranking_dimensao_vazio_preserva_campos(coluna):
    original = pd.DataFrame(columns=[coluna, "Vendas", "Qtd PIs"])
    styler = preparar_ranking_dimensao(original)
    assert styler.data.empty
    assert list(styler.data) == list(original)
    assert list(_exibida(styler)) == list(original)
    assert list(configuracao_colunas_ranking(styler.data)) == list(original)


def test_ranking_veiculos_vazio_preserva_seis_campos():
    original = _agregado().iloc[:0]
    styler = preparar_ranking_veiculos(original)
    assert styler.data.empty
    assert list(styler.data) == COLUNAS
    assert list(_exibida(styler)) == COLUNAS
    assert list(configuracao_colunas_ranking(styler.data)) == COLUNAS


def test_ordenacao_textual_da_copia_neutralizada_tem_efeito_limitado_documentado():
    original = pd.DataFrame({
        COL_AGENCIA: ["=teste", "'texto", "COMUM"],
        "Vendas": [1000.0, 20.0, 300.0], "Qtd PIs": [1, 2, 3],
    })
    styler = preparar_ranking_dimensao(original)
    assert original.sort_values(COL_AGENCIA)[COL_AGENCIA].tolist() == ["'texto", "=teste", "COMUM"]
    assert styler.data.sort_values(COL_AGENCIA)[COL_AGENCIA].tolist() == ["'=teste", "'texto", "COMUM"]
    assert styler.data.sort_values("Vendas").index.tolist() == original.sort_values("Vendas").index.tolist()
    assert _exibida(styler)[COL_AGENCIA].tolist() == original[COL_AGENCIA].tolist()
