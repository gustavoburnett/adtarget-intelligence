"""Design 1G: cópia nativa protegida, formatos pt-BR e base original intacta.

As provas usam dados sintéticos e o mesmo envelope Arrow/Styler do Streamlit.
O CSV nativo consome a cópia raw, enquanto a tela usa display_values.
"""

import datetime as dt
from decimal import Decimal
import io

import pandas as pd
import pyarrow as pa
import pytest
from streamlit.elements.lib.pandas_styler_utils import marshall_styler
from streamlit.proto.ArrowData_pb2 import ArrowData

from src.components.analitico_tables import configuracao_colunas, preparar_tabela
from src.data.cleaning import COL_VENCIMENTO_DATA
from src.data.csv_export import _neutralizar_formula, gerar_csv_seguro


COLUNAS = [
    "GRUPO", "VEICULO", "PI", "AGENCIA", "CLIENTE", "CAMPANHA",
    "MÊS (GANHO)", "MÊS (VEICULAÇÃO)", "INÍCIO", "FIM",
    "VALOR PI BRUTO", "VALOR PI LIQUIDO", "VENCIMENTO PI", "STATUS",
    "NOTA FISCAL", "EXECUTIVO",
]


def _exibida(styler):
    envelope = ArrowData()
    marshall_styler(envelope, styler, "tabela-teste")
    return pa.ipc.open_stream(envelope.styler.display_values).read_all().to_pandas()


def _fonte():
    tabela = pd.DataFrame({
        coluna: [f"{coluna} A", f"{coluna} B", ""] for coluna in COLUNAS
    })
    tabela["VALOR PI BRUTO"] = [5000.123456789, 0.0, -100.123456789]
    tabela["VALOR PI LIQUIDO"] = [1234.567890123, 0.0, -50.123456789]
    tabela["INÍCIO"] = pd.to_datetime(["2026-01-02", "2026-02-01 14:30:25", None], format="mixed")
    tabela["FIM"] = pd.to_datetime(["2026-01-31", "2026-02-28", None])
    tabela["VENCIMENTO PI"] = [46052, "CONTRA APRESENT.", "CONDIÇÃO MANUAL"]
    tabela[COL_VENCIMENTO_DATA] = pd.to_datetime(["2026-01-30", None, None])
    tabela.index = pd.Index([7, 7, 9], name="ORIGEM")
    return tabela


def test_16_campos_ordem_indices_e_csv_explicito_preservados():
    original = _fonte()
    copia = original.copy(deep=True)
    csv_antes = gerar_csv_seguro(original[COLUNAS])
    styler = preparar_tabela(original, colunas=COLUNAS)
    assert list(styler.data.columns) == COLUNAS
    assert styler.data.index.tolist() == [0, 1, 2]
    assert COL_VENCIMENTO_DATA not in styler.data
    pd.testing.assert_frame_equal(original, copia)
    assert gerar_csv_seguro(original[COLUNAS]) == csv_antes
    exibida = _exibida(styler)
    assert list(exibida.columns) == COLUNAS
    assert exibida["GRUPO"].tolist() == original["GRUPO"].tolist()


@pytest.mark.parametrize("texto", [
    "=1+1", "+SUM(A1:A2)", "-1+2", "@SUM(A1:A2)",
    "   =1+1", "\t+1+2", "\n-1+2", "\r\n@SUM(A1:A2)",
    '"=1+1', ' \t" \n"+1+2',
    '=HYPERLINK("https://example.invalid","TESTE")',
    "=1+1\nSEGUNDA LINHA", "@ação; ç, á\tfinal",
    "\u00a0=1+1", "\u2003+1+2", "\ufeff-1+2", "\x00@SUM(A1:A2)",
    "\x1b=1+1", "\x7f+1+2",
])
def test_envelope_nativo_seguro_e_display_original(texto):
    original = pd.DataFrame({"CLIENTE": [texto], "VALOR PI LIQUIDO": [-123.456789]})
    copia = original.copy(deep=True)
    styler = preparar_tabela(original)
    raw_arrow = pa.Table.from_pandas(styler.data, preserve_index=False)
    raw = raw_arrow.to_pandas()
    assert raw.iloc[0]["CLIENTE"] == _neutralizar_formula(texto)
    assert raw.iloc[0]["VALOR PI LIQUIDO"] == -123.456789
    assert _exibida(styler).iloc[0]["CLIENTE"] == texto
    pd.testing.assert_frame_equal(original, copia)


def test_restauracao_por_celula_nao_confunde_textos_iguais_apos_neutralizar():
    original = pd.DataFrame({"CLIENTE": ["=1+1", "'=1+1", "@teste", "'@teste"]})
    original.index = [8, 8, 8, 8]
    styler = preparar_tabela(original)
    assert styler.data["CLIENTE"].tolist() == ["'=1+1", "'=1+1", "'@teste", "'@teste"]
    assert _exibida(styler)["CLIENTE"].tolist() == original["CLIENTE"].tolist()


def test_ordenacao_textual_considera_apostrofo_apenas_na_copia():
    original = pd.DataFrame({"CLIENTE": ["=teste", "'texto", "COMUM"]})
    styler = preparar_tabela(original)
    assert original.sort_values("CLIENTE")["CLIENTE"].tolist() == ["'texto", "=teste", "COMUM"]
    assert styler.data.sort_values("CLIENTE")["CLIENTE"].tolist() == ["'=teste", "'texto", "COMUM"]
    assert _exibida(styler)["CLIENTE"].tolist() == original["CLIENTE"].tolist()


def test_moedas_numericas_precisao_ordenacao_zero_e_ausencia():
    original = pd.DataFrame({
        "VALOR PI BRUTO": pd.array([9000.123456789, 100.567890123, -123.123456789, 0, pd.NA], dtype="Float64"),
        "VALOR PI LIQUIDO": pd.array([9000.123456789, 100.567890123, -123.123456789, 0, pd.NA], dtype="Float64"),
    })
    styler = preparar_tabela(original)
    for coluna in original:
        pd.testing.assert_series_equal(styler.data[coluna], original[coluna])
        assert styler.data.sort_values(coluna).index.tolist() == [2, 3, 1, 0, 4]
        assert _exibida(styler)[coluna].tolist() == ["R$ 9.000,12", "R$ 100,57", "R$ -123,12", "R$ 0,00", "—"]
        config = configuracao_colunas(original)[coluna]
        assert config["type_config"]["type"] == "number"
        assert config["type_config"]["format"] is None
        assert config["type_config"]["step"] is None
        assert config["alignment"] == "right"


def test_decimal_e_inteiro_permanecem_numericos():
    original = pd.DataFrame({
        "VALOR PI LIQUIDO": [Decimal("-123.456789"), Decimal("0.000000")],
        "VALOR PI BRUTO": pd.array([-123, 0], dtype="Int64"),
    })
    styler = preparar_tabela(original)
    pd.testing.assert_frame_equal(styler.data, original)
    pa.Table.from_pandas(styler.data, preserve_index=False)
    assert _exibida(styler)["VALOR PI LIQUIDO"].tolist() == ["R$ -123,46", "R$ 0,00"]


@pytest.mark.parametrize("data,exibida", [
    (dt.date(2026, 1, 2), "02/01/2026"),
    (pd.Timestamp("2026-01-02"), "02/01/2026"),
    (pd.Timestamp("2026-01-02 14:30"), "02/01/2026 14:30"),
    (pd.Timestamp("2026-01-02 14:30:25"), "02/01/2026 14:30:25"),
    (pd.Timestamp("2026-01-02 14:30:25.123456789"), "02/01/2026 14:30:25.123456789"),
    (pd.Timestamp("2026-01-02 14:30:00", tz="America/Sao_Paulo"), "02/01/2026 14:30 -0300"),
    (pd.NaT, "—"),
])
def test_datas_ptbr_sem_perder_horas_precision_ou_original(data, exibida):
    original = pd.DataFrame({"INÍCIO": [data], "FIM": [data]})
    copia = original.copy(deep=True)
    styler = preparar_tabela(original)
    pd.testing.assert_frame_equal(styler.data, original)
    assert _exibida(styler)["INÍCIO"].tolist() == [exibida]
    assert _exibida(styler)["FIM"].tolist() == [exibida]
    pd.testing.assert_frame_equal(original, copia)


def test_vencimento_misto_usa_derivado_sem_converter_condicoes_comerciais():
    original = pd.DataFrame({
        "VENCIMENTO PI": [46052, 46068.5, "CONTRA APRESENT.", "PRÓXIMO DIA ÚTIL", "", None, "=termo"],
        COL_VENCIMENTO_DATA: pd.to_datetime(["2026-01-30", "2026-02-15 12:00", None, "2026-03-01", None, None, None], format="mixed"),
    })
    copia = original.copy(deep=True)
    styler = preparar_tabela(original, colunas=["VENCIMENTO PI"])
    raw_arrow = pa.Table.from_pandas(styler.data, preserve_index=False)
    tipo = raw_arrow.schema.field("VENCIMENTO PI").type
    assert pa.types.is_string(tipo) or pa.types.is_large_string(tipo)
    assert _exibida(styler)["VENCIMENTO PI"].tolist() == [
        "30/01/2026", "15/02/2026 12:00", "CONTRA APRESENT.", "PRÓXIMO DIA ÚTIL", "", "—", "=termo",
    ]
    assert styler.data.iloc[-1]["VENCIMENTO PI"] == "'=termo"
    pd.testing.assert_frame_equal(original, copia)
    csv = pd.read_csv(io.BytesIO(gerar_csv_seguro(original[["VENCIMENTO PI"]])), keep_default_na=False)
    assert csv.iloc[0]["VENCIMENTO PI"] == "46052"
    assert csv.iloc[1]["VENCIMENTO PI"] == "46068.5"


def test_vencimento_sem_derivado_nao_inventa_datas():
    original = pd.DataFrame({"VENCIMENTO PI": [46052, 0, "30/01/2026", "=termo", None]})
    styler = preparar_tabela(original)
    assert _exibida(styler)["VENCIMENTO PI"].tolist() == ["46052", "0", "30/01/2026", "=termo", "—"]


def test_campo_textual_misto_arrow_preserva_zero_blank_e_ausencia():
    original = pd.DataFrame({"MÊS (GANHO)": [0, "", None, "CONTEÚDO INVÁLIDO", "=teste"]})
    copia = original.copy(deep=True)
    styler = preparar_tabela(original)
    pa.Table.from_pandas(styler.data, preserve_index=False)
    assert _exibida(styler)["MÊS (GANHO)"].tolist() == ["0", "", "—", "CONTEÚDO INVÁLIDO", "=teste"]
    pd.testing.assert_frame_equal(original, copia)


def test_tabela_vazia_preserva_colunas_e_configuracao():
    original = _fonte().iloc[:0]
    styler = preparar_tabela(original, colunas=COLUNAS)
    assert styler.data.empty
    assert list(styler.data.columns) == COLUNAS
    assert list(_exibida(styler).columns) == COLUNAS
    assert list(configuracao_colunas(original, colunas=COLUNAS)) == COLUNAS


def test_larguras_monetarias_nao_truncam_valores_extensos():
    original = pd.DataFrame({"VALOR PI LIQUIDO": [1234567890123.45]})
    config = configuracao_colunas(original)["VALOR PI LIQUIDO"]
    assert config["width"] >= len("R$ 1.234.567.890.123,45") * 8 + 40


def test_colunas_selecionadas_respeitam_ordem_do_chamador():
    original = _fonte()
    selecionadas = ["VALOR PI LIQUIDO", "GRUPO", "INÍCIO"]
    styler = preparar_tabela(original, colunas=selecionadas)
    assert list(styler.data.columns) == selecionadas
    assert list(configuracao_colunas(original, colunas=selecionadas)) == selecionadas


def test_protecao_tambem_se_aplica_a_campos_adicionais_textuais():
    original = pd.DataFrame({"OBSERVAÇÃO": ["+teste", "OBSERVAÇÃO NORMAL"], "NÚMERO": [-1.5, 0.0]})
    styler = preparar_tabela(original)
    assert styler.data["OBSERVAÇÃO"].tolist() == ["'+teste", "OBSERVAÇÃO NORMAL"]
    assert _exibida(styler)["OBSERVAÇÃO"].tolist() == original["OBSERVAÇÃO"].tolist()
    pd.testing.assert_series_equal(styler.data["NÚMERO"], original["NÚMERO"])
