"""Testes unitários do loader.py — 100% offline, com mocks de gspread.

Nenhum teste acessa rede ou depende de credenciais. Os fakes reproduzem o
contrato mínimo usado pelo loader: worksheet.title, worksheet.get(...),
planilha.worksheets() e cliente.open_by_key(...).
"""

import pandas as pd
import pytest

from src.data import loader
from src.data.cleaning import limpar_dataframe
from src.data.loader import (
    COL_ANO_ABA,
    COLUNAS_OBRIGATORIAS,
    ErroDeCarga,
    descobrir_abas_de_ano,
    load_all_sheets,
    validar_colunas,
)


# ---------------------------------------------------------------------------
# Fakes (contrato mínimo do gspread usado pelo loader)
# ---------------------------------------------------------------------------

class FakeWorksheet:
    def __init__(self, title: str, valores: list[list]):
        self.title = title
        self._valores = valores
        self.render_option_usado = None

    def get(self, value_render_option=None):
        self.render_option_usado = value_render_option
        return self._valores


class FakePlanilha:
    def __init__(self, abas: list[FakeWorksheet]):
        self._abas = abas

    def worksheets(self):
        return self._abas


class FakeCliente:
    def __init__(self, planilha: FakePlanilha):
        self._planilha = planilha
        self.chave_usada = None

    def open_by_key(self, chave: str):
        self.chave_usada = chave
        return self._planilha


def _linha_completa(pi, status="FATURADO", bruto=1000, liquido=800) -> list:
    """Linha na ordem exata de COLUNAS_OBRIGATORIAS."""
    por_coluna = {
        "PRAÇA": "BRASÍLIA",
        "EXECUTIVO": "EXEC 1",
        "GRUPO": "GRUPO A",
        "VEICULO": "VEIC A",
        "PI": pi,
        "AGENCIA": "AG1",
        "CLIENTE": "CLIENTE A",
        "CAMPANHA": "CAMP A",
        "MÊS (GANHO)": "JANEIRO/2025",
        "MÊS (VEICULAÇÃO)": "JANEIRO/2025",
        "INÍCIO": "",
        "FIM": "",
        "VALOR PI BRUTO": bruto,
        "VALOR PI LIQUIDO": liquido,
        "VENCIMENTO PI": "CONTRA APRESENT.",
        "STATUS": status,
        "NOTA FISCAL": "111",
        "DATA DE CRIAÇÃO": "",
        "OBSERVAÇÃO": "",
    }
    return [por_coluna[c] for c in COLUNAS_OBRIGATORIAS]


def _aba_valida(titulo: str, linhas: list[list]) -> FakeWorksheet:
    return FakeWorksheet(titulo, [list(COLUNAS_OBRIGATORIAS)] + linhas)


# ---------------------------------------------------------------------------
# Descoberta automática de abas de ano
# ---------------------------------------------------------------------------

class TestDescobertaDeAbas:
    def test_encontra_todas_as_abas_de_ano(self):
        planilha = FakePlanilha(
            [
                FakeWorksheet("2024", []),
                FakeWorksheet("2025", []),
                FakeWorksheet("2026", []),
            ]
        )
        abas = descobrir_abas_de_ano(planilha)
        assert [a.title for a in abas] == ["2024", "2025", "2026"]

    def test_ano_novo_descoberto_sem_mudanca_de_codigo(self):
        """Requisito do documento 03: quando a aba 2027 for criada,
        ela entra automaticamente."""
        planilha = FakePlanilha([FakeWorksheet("2026", []), FakeWorksheet("2027", [])])
        assert [a.title for a in descobrir_abas_de_ano(planilha)] == ["2026", "2027"]

    def test_ignora_abas_que_nao_sao_ano(self):
        planilha = FakePlanilha(
            [
                FakeWorksheet("2025", []),
                FakeWorksheet("Resumo", []),
                FakeWorksheet("Config", []),
                FakeWorksheet("Dados 2024", []),  # não é SÓ o ano
                FakeWorksheet("202", []),          # 3 dígitos
                FakeWorksheet("20255", []),        # 5 dígitos
            ]
        )
        assert [a.title for a in descobrir_abas_de_ano(planilha)] == ["2025"]


# ---------------------------------------------------------------------------
# Validação de colunas obrigatórias
# ---------------------------------------------------------------------------

class TestValidacaoDeColunas:
    def test_cabecalho_completo_passa(self):
        validar_colunas(list(COLUNAS_OBRIGATORIAS), "2025")  # não levanta

    def test_colunas_extras_nao_sao_erro(self):
        """Aba 2026 tem DATA FATURAMENTO e DIAS EM ABERTO a mais (doc 01)."""
        cabecalho = list(COLUNAS_OBRIGATORIAS) + ["DATA FATURAMENTO", "DIAS EM ABERTO"]
        validar_colunas(cabecalho, "2026")  # não levanta

    def test_ordem_das_colunas_nao_importa(self):
        validar_colunas(list(reversed(COLUNAS_OBRIGATORIAS)), "2025")  # não levanta

    def test_coluna_faltante_gera_erro_claro(self):
        cabecalho = [c for c in COLUNAS_OBRIGATORIAS if c not in ("STATUS", "VALOR PI LIQUIDO")]
        with pytest.raises(ErroDeCarga) as excecao:
            validar_colunas(cabecalho, "2025")
        mensagem = str(excecao.value)
        assert "2025" in mensagem            # identifica a aba
        assert "STATUS" in mensagem          # nomeia o que falta
        assert "VALOR PI LIQUIDO" in mensagem

    def test_erro_e_amigavel_nao_um_keyerror(self):
        """Risco do documento 03: coluna renomeada deve gerar mensagem clara,
        nunca a aplicação seguir com dado errado ou estourar KeyError."""
        with pytest.raises(ErroDeCarga):
            validar_colunas(["QUALQUER"], "2024")


# ---------------------------------------------------------------------------
# Conversão de aba em DataFrame (linhas curtas, vazias, tipos preservados)
# ---------------------------------------------------------------------------

class TestAbaParaDataframe:
    def test_leitura_usa_unformatted_value(self):
        aba = _aba_valida("2025", [_linha_completa(1001)])
        loader._aba_para_dataframe(aba)
        assert aba.render_option_usado == "UNFORMATTED_VALUE"

    def test_linha_curta_da_api_e_preenchida(self):
        """A API do Sheets omite células finais vazias; a linha curta deve
        ser completada até a largura do cabeçalho, sem deslocar colunas."""
        linha_curta = _linha_completa(1001)[:10]  # corta INÍCIO em diante
        aba = _aba_valida("2025", [linha_curta])
        df = loader._aba_para_dataframe(aba)
        assert len(df) == 1
        assert df.loc[0, "PI"] == 1001                 # colunas não deslocaram
        assert df.loc[0, "MÊS (GANHO)"] == "JANEIRO/2025"
        assert pd.isna(df.loc[0, "STATUS"])            # preenchido, não inventado

    def test_linha_mais_longa_que_cabecalho_e_truncada(self):
        linha = _linha_completa(1001) + ["SOBRA"]
        aba = _aba_valida("2025", [linha])
        df = loader._aba_para_dataframe(aba)
        assert list(df.columns) == list(COLUNAS_OBRIGATORIAS)

    def test_linhas_totalmente_vazias_sao_descartadas(self):
        aba = _aba_valida(
            "2025",
            [_linha_completa(1001), [""] * len(COLUNAS_OBRIGATORIAS)],
        )
        df = loader._aba_para_dataframe(aba)
        assert len(df) == 1

    def test_cabecalho_com_espacos_e_normalizado(self):
        cabecalho = [f" {c} " for c in COLUNAS_OBRIGATORIAS]
        aba = FakeWorksheet("2025", [cabecalho, _linha_completa(1001)])
        df = loader._aba_para_dataframe(aba)
        assert list(df.columns) == list(COLUNAS_OBRIGATORIAS)

    def test_aba_vazia_vira_dataframe_vazio(self):
        assert loader._aba_para_dataframe(FakeWorksheet("2025", [])).empty
        so_cabecalho = FakeWorksheet("2025", [list(COLUNAS_OBRIGATORIAS)])
        assert loader._aba_para_dataframe(so_cabecalho).empty

    def test_pi_bruto_preservado_sem_coercao(self):
        """O loader NÃO converte tipos: PI numérico continua número e PI
        texto continua texto. A conversão para texto é papel do cleaning."""
        aba = _aba_valida(
            "2025",
            [_linha_completa(12345), _linha_completa("01/2024")],
        )
        df = loader._aba_para_dataframe(aba)
        assert df.loc[0, "PI"] == 12345
        assert df.loc[1, "PI"] == "01/2024"

    def test_cabecalho_na_linha_2_com_primeira_linha_vazia(self):
        """CASO REAL: a primeira linha da planilha é vazia e o cabeçalho
        verdadeiro está na linha 2. O loader deve detectar automaticamente."""
        largura = len(COLUNAS_OBRIGATORIAS)
        aba = FakeWorksheet(
            "2025",
            [
                [""] * largura,                    # linha 1: vazia
                list(COLUNAS_OBRIGATORIAS),        # linha 2: cabeçalho real
                _linha_completa(1001),
                _linha_completa(1002),
            ],
        )
        df = loader._aba_para_dataframe(aba)
        assert list(df.columns) == list(COLUNAS_OBRIGATORIAS)
        assert len(df) == 2
        assert df.loc[0, "PI"] == 1001

    def test_varias_linhas_vazias_e_titulo_antes_do_cabecalho(self):
        """Linhas vazias E uma linha de título antes do cabeçalho: o
        cabeçalho é a primeira linha que contém todas as colunas."""
        largura = len(COLUNAS_OBRIGATORIAS)
        aba = FakeWorksheet(
            "2026",
            [
                [""] * largura,
                ["PLANILHA DE VENDAS ADTARGET"] + [""] * (largura - 1),
                [""] * largura,
                list(COLUNAS_OBRIGATORIAS),
                _linha_completa(2001),
            ],
        )
        df = loader._aba_para_dataframe(aba)
        assert len(df) == 1
        assert df.loc[0, "PI"] == 2001

    def test_cabecalho_incompleto_com_linha_vazia_antes_gera_erro_claro(self):
        """Sem nenhuma linha com o cabeçalho completo, o erro nomeia as
        colunas faltantes da primeira candidata não vazia."""
        cabecalho_quebrado = [c for c in COLUNAS_OBRIGATORIAS if c != "STATUS"]
        aba = FakeWorksheet(
            "2025",
            [[""] * len(COLUNAS_OBRIGATORIAS), cabecalho_quebrado],
        )
        with pytest.raises(ErroDeCarga, match="STATUS"):
            loader._aba_para_dataframe(aba)

    def test_aba_so_com_linhas_vazias_gera_erro_claro(self):
        aba = FakeWorksheet("2025", [[""] * 5, ["", "", ""]])
        with pytest.raises(ErroDeCarga, match="cabeçalho"):
            loader._aba_para_dataframe(aba)

    def test_pi_vira_texto_apos_cleaning(self):
        """Integração loader -> cleaning: PI sempre texto no dado final."""
        aba = _aba_valida(
            "2025",
            [_linha_completa(12345), _linha_completa("01/2024")],
        )
        df = limpar_dataframe(loader._aba_para_dataframe(aba))
        assert df["PI"].tolist() == ["12345", "01/2024"]


# ---------------------------------------------------------------------------
# load_all_sheets: concatenação com ANO_ABA (cliente mockado, sem rede)
# ---------------------------------------------------------------------------

class TestLoadAllSheets:
    def _com_planilha(self, monkeypatch, abas) -> pd.DataFrame:
        cliente = FakeCliente(FakePlanilha(abas))
        monkeypatch.setattr(loader, "criar_cliente", lambda credenciais: cliente)
        return load_all_sheets("id-fake", {})

    def test_concatena_abas_com_ano_aba(self, monkeypatch):
        df = self._com_planilha(
            monkeypatch,
            [
                _aba_valida("2025", [_linha_completa(1), _linha_completa(2)]),
                _aba_valida("2026", [_linha_completa(3)]),
            ],
        )
        assert len(df) == 3
        assert COL_ANO_ABA in df.columns
        assert df[COL_ANO_ABA].tolist() == [2025, 2025, 2026]
        assert df[COL_ANO_ABA].dtype.kind == "i"  # inteiro, não texto

    def test_aba_que_nao_e_ano_fica_de_fora(self, monkeypatch):
        df = self._com_planilha(
            monkeypatch,
            [
                _aba_valida("2025", [_linha_completa(1)]),
                _aba_valida("Resumo", [_linha_completa(99)]),
            ],
        )
        assert len(df) == 1
        assert df[COL_ANO_ABA].tolist() == [2025]

    def test_aba_de_ano_vazia_e_pulada(self, monkeypatch):
        df = self._com_planilha(
            monkeypatch,
            [
                _aba_valida("2024", []),
                _aba_valida("2025", [_linha_completa(1)]),
            ],
        )
        assert df[COL_ANO_ABA].tolist() == [2025]

    def test_sem_nenhuma_aba_de_ano_gera_erro_claro(self, monkeypatch):
        with pytest.raises(ErroDeCarga, match="aba de ano"):
            self._com_planilha(monkeypatch, [_aba_valida("Resumo", [])])

    def test_todas_as_abas_vazias_gera_erro_claro(self, monkeypatch):
        with pytest.raises(ErroDeCarga, match="vazias"):
            self._com_planilha(
                monkeypatch, [_aba_valida("2024", []), _aba_valida("2025", [])]
            )

    def test_coluna_faltante_em_uma_aba_interrompe_a_carga(self, monkeypatch):
        cabecalho_quebrado = [c for c in COLUNAS_OBRIGATORIAS if c != "STATUS"]
        aba_quebrada = FakeWorksheet(
            "2026", [cabecalho_quebrado, _linha_completa(1)[:-1]]
        )
        with pytest.raises(ErroDeCarga, match="STATUS"):
            self._com_planilha(
                monkeypatch,
                [_aba_valida("2025", [_linha_completa(1)]), aba_quebrada],
            )

    def test_planilha_inacessivel_gera_erro_amigavel(self, monkeypatch):
        class ClienteQueFalha:
            def open_by_key(self, chave):
                raise RuntimeError("403")

        monkeypatch.setattr(
            loader, "criar_cliente", lambda credenciais: ClienteQueFalha()
        )
        with pytest.raises(ErroDeCarga, match="spreadsheet_id"):
            load_all_sheets("id-fake", {})
