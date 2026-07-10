"""Testes da normalização genérica (cleaning.py).

Cobrem as regras do documento 02 e os casos extremos reais encontrados na
planilha (documento 01): status com espaço no fim, PI com tipo misto,
VENCIMENTO PI misto (data x "CONTRA APRESENT."), texto com espaço final em
CLIENTE/VEICULO, meses em texto pt-BR e valores vazios.
"""

import datetime

import pandas as pd
import pytest

from src.data.cleaning import (
    COL_CONTRA_APRESENTACAO,
    COL_MES_GANHO_DATA,
    COL_MES_VEICULACAO_DATA,
    COL_VENCIMENTO_DATA,
    converter_mes_ano,
    converter_valor,
    desdobrar_vencimento,
    limpar_dataframe,
    normalizar_nota_fiscal,
    normalizar_pi,
    normalizar_status,
    normalizar_texto,
)


# ---------------------------------------------------------------------------
# Normalização de STATUS (caso real: "FATURADO " com espaço no fim)
# ---------------------------------------------------------------------------

class TestNormalizacaoStatus:
    def test_espaco_no_fim_unificado(self):
        assert normalizar_status("FATURADO ") == "FATURADO"
        assert normalizar_status(" CHECKING  ") == "CHECKING"

    def test_caixa_padronizada(self):
        assert normalizar_status("faturado") == "FATURADO"
        assert normalizar_status("Direto") == "DIRETO"

    def test_vazio_vira_string_vazia(self):
        """O campo STATUS é obrigatório na planilha; um branco vira "" e é
        capturado pelo alerta de status desconhecido (sem categoria interna)."""
        assert normalizar_status("") == ""
        assert normalizar_status("   ") == ""
        assert normalizar_status(None) == ""

    def test_status_desconhecido_nao_e_corrigido(self):
        # Detecção é papel do alerta 4 de qualidade, não da limpeza
        assert normalizar_status("EM NEGOCIAÇÃO") == "EM NEGOCIAÇÃO"


# ---------------------------------------------------------------------------
# Normalização de texto (casos reais: "SEBRAE ", "93 FM ")
# ---------------------------------------------------------------------------

class TestNormalizacaoTexto:
    def test_trim_cliente(self):
        assert normalizar_texto("SEBRAE ") == "SEBRAE"

    def test_trim_veiculo(self):
        assert normalizar_texto("93 FM ") == "93 FM"

    def test_nulo_vira_vazio(self):
        assert normalizar_texto(None) == ""
        assert normalizar_texto(float("nan")) == ""


# ---------------------------------------------------------------------------
# Conversão de "MÊS/ANO" para data (primeiro dia do mês)
# ---------------------------------------------------------------------------

class TestConversaoMesAno:
    def test_mes_valido(self):
        assert converter_mes_ano("JANEIRO/2024") == pd.Timestamp(2024, 1, 1)
        assert converter_mes_ano("DEZEMBRO/2025") == pd.Timestamp(2025, 12, 1)

    def test_marco_com_e_sem_acento(self):
        assert converter_mes_ano("MARÇO/2026") == pd.Timestamp(2026, 3, 1)
        assert converter_mes_ano("MARCO/2026") == pd.Timestamp(2026, 3, 1)

    def test_caixa_e_espacos(self):
        assert converter_mes_ano(" fevereiro/2025 ") == pd.Timestamp(2025, 2, 1)

    def test_invalido_vira_nat(self):
        assert pd.isna(converter_mes_ano(""))
        assert pd.isna(converter_mes_ano(None))
        assert pd.isna(converter_mes_ano("XYZ/2024"))
        assert pd.isna(converter_mes_ano("JANEIRO"))


# ---------------------------------------------------------------------------
# PI sempre como texto (caso real: número, texto "01/2024", data por engano)
# ---------------------------------------------------------------------------

class TestNormalizacaoPI:
    def test_numero_float_vira_texto_sem_decimal(self):
        assert normalizar_pi(12345.0) == "12345"

    def test_numero_int(self):
        assert normalizar_pi(9876) == "9876"

    def test_texto_preservado(self):
        assert normalizar_pi("01/2024") == "01/2024"

    def test_data_por_engano_vira_texto(self):
        resultado = normalizar_pi(datetime.date(2024, 1, 1))
        assert isinstance(resultado, str)
        assert "2024" in resultado

    def test_vazio(self):
        assert normalizar_pi(None) == ""


# ---------------------------------------------------------------------------
# VENCIMENTO PI: data OU "CONTRA APRESENT." (caso real, ~55% das linhas)
# ---------------------------------------------------------------------------

class TestVencimentoPI:
    def test_contra_apresentacao(self):
        data, flag = desdobrar_vencimento("CONTRA APRESENT.")
        assert pd.isna(data)
        assert flag is True

    def test_contra_apresentacao_variacao_de_grafia(self):
        data, flag = desdobrar_vencimento("contra apresent")
        assert flag is True

    def test_data_serial_google_sheets(self):
        # UNFORMATTED_VALUE devolve datas como serial (dias desde 30/12/1899)
        data, flag = desdobrar_vencimento(45000)
        assert data == pd.Timestamp(2023, 3, 15)
        assert flag is False

    def test_data_em_texto_br(self):
        data, flag = desdobrar_vencimento("15/03/2025")
        assert data == pd.Timestamp(2025, 3, 15)
        assert flag is False

    def test_vazio(self):
        data, flag = desdobrar_vencimento("")
        assert pd.isna(data)
        assert flag is False


# ---------------------------------------------------------------------------
# Valores monetários
# ---------------------------------------------------------------------------

class TestConversaoValor:
    def test_numero_puro(self):
        assert converter_valor(99879.98) == pytest.approx(99879.98)

    def test_celula_vazia_vira_zero(self):
        assert converter_valor("") == 0.0
        assert converter_valor(None) == 0.0

    def test_string_numerica(self):
        assert converter_valor("1500") == 1500.0


# ---------------------------------------------------------------------------
# Nota Fiscal
# ---------------------------------------------------------------------------

class TestNotaFiscal:
    def test_numero_float_sem_decimal(self):
        assert normalizar_nota_fiscal(456.0) == "456"

    def test_texto_sem_nf_preservado(self):
        # A semântica de "ausente" é papel do quality_checks, não da limpeza
        assert normalizar_nota_fiscal("sem nf ") == "SEM NF"

    def test_vazio(self):
        assert normalizar_nota_fiscal(None) == ""


# ---------------------------------------------------------------------------
# Pipeline completo de limpeza
# ---------------------------------------------------------------------------

def _df_bruto_minimo() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "PRAÇA": ["BRASÍLIA", "BRASÍLIA"],
            "EXECUTIVO": ["EXEC 1 ", "EXEC 2"],
            "GRUPO": ["MELODIA", "SISTEMA VERDES MARES "],
            "VEICULO": ["93 FM ", "DIÁRIO DO NORDESTE"],
            "PI": [12345.0, "01/2024"],
            "AGENCIA": ["AG1", "DIRETO "],
            "CLIENTE": ["SEBRAE ", "SECOM"],
            "CAMPANHA": ["ALWAYS ON", "CAMPANHA X "],
            "MÊS (GANHO)": ["JANEIRO/2025", "FEVEREIRO/2025"],
            "MÊS (VEICULAÇÃO)": ["JANEIRO/2025", "MARÇO/2025"],
            "INÍCIO": [45658, ""],
            "FIM": ["", ""],
            "VALOR PI BRUTO": [10000, ""],
            "VALOR PI LIQUIDO": [8000, ""],
            "VENCIMENTO PI": ["CONTRA APRESENT.", 45000],
            "STATUS": ["FATURADO ", ""],
            "NOTA FISCAL": [111.0, ""],
            "DATA DE CRIAÇÃO": ["", ""],
            "OBSERVAÇÃO": ["", ""],
            "ANO_ABA": [2025, 2025],
        }
    )


class TestLimparDataframe:
    def test_nao_altera_o_dataframe_original(self):
        bruto = _df_bruto_minimo()
        copia = bruto.copy(deep=True)
        limpar_dataframe(bruto)
        pd.testing.assert_frame_equal(bruto, copia)

    def test_colunas_derivadas_criadas(self):
        limpo = limpar_dataframe(_df_bruto_minimo())
        for coluna in (
            COL_MES_GANHO_DATA,
            COL_MES_VEICULACAO_DATA,
            COL_VENCIMENTO_DATA,
            COL_CONTRA_APRESENTACAO,
        ):
            assert coluna in limpo.columns

    def test_normalizacoes_aplicadas_em_conjunto(self):
        limpo = limpar_dataframe(_df_bruto_minimo())
        assert limpo.loc[0, "STATUS"] == "FATURADO"
        assert limpo.loc[1, "STATUS"] == ""
        assert limpo.loc[0, "VEICULO"] == "93 FM"
        assert limpo.loc[0, "CLIENTE"] == "SEBRAE"
        assert limpo.loc[0, "PI"] == "12345"
        assert limpo.loc[1, "PI"] == "01/2024"
        assert limpo.loc[0, COL_MES_GANHO_DATA] == pd.Timestamp(2025, 1, 1)
        assert limpo.loc[1, COL_MES_VEICULACAO_DATA] == pd.Timestamp(2025, 3, 1)
        assert bool(limpo.loc[0, COL_CONTRA_APRESENTACAO]) is True
        assert bool(limpo.loc[1, COL_CONTRA_APRESENTACAO]) is False
        assert limpo.loc[1, COL_VENCIMENTO_DATA] == pd.Timestamp(2023, 3, 15)
        # Valores vazios viram 0.0, nunca NaN (somas seguras)
        assert limpo.loc[1, "VALOR PI BRUTO"] == 0.0
        assert limpo.loc[1, "VALOR PI LIQUIDO"] == 0.0
        assert limpo.loc[0, "NOTA FISCAL"] == "111"

    def test_nenhuma_correcao_de_cadastro_especifico(self):
        """Decisão 17: a limpeza não corrige cadastro individual.

        Um veículo sob grupo "errado" permanece exatamente como veio;
        a detecção é papel do alerta 3 de quality_checks.
        """
        limpo = limpar_dataframe(_df_bruto_minimo())
        assert limpo.loc[0, "GRUPO"] == "MELODIA"
        assert limpo.loc[0, "VEICULO"] == "93 FM"
