"""Testes mínimos da FERRAMENTA TEMPORÁRIA de auditoria de Vendas.

Remover junto com src/data/auditoria.py ao fim da conciliação.
"""

import pandas as pd
import pytest

from src.data import auditoria
from src.data.cleaning import limpar_dataframe


def _linha(pi, status, ganho, liq, cliente="CLIENTE X", ano=2026):
    return {
        "PRAÇA": "BRASÍLIA", "EXECUTIVO": "E", "GRUPO": "G", "VEICULO": "V",
        "PI": pi, "AGENCIA": "A", "CLIENTE": cliente, "CAMPANHA": f"CAMP {pi}",
        "MÊS (GANHO)": ganho, "MÊS (VEICULAÇÃO)": ganho, "INÍCIO": "", "FIM": "",
        "VALOR PI BRUTO": liq * 1.25, "VALOR PI LIQUIDO": liq,
        "VENCIMENTO PI": "CONTRA APRESENT.", "STATUS": status,
        "NOTA FISCAL": "1", "DATA DE CRIAÇÃO": "", "OBSERVAÇÃO": "",
        "ANO_ABA": ano,
    }


@pytest.fixture
def df() -> pd.DataFrame:
    """Aba 2026 com 13.600 (soma total): 12.000 em Vendas do ano,
    500 cancelado, 400 status desconhecido, 700 com ganho em 2025.
    Mais 1.200 na aba 2025 com ganho em 2026 (conta no sistema)."""
    return limpar_dataframe(pd.DataFrame([
        _linha("1", "FATURADO", "JANEIRO/2026", 9000),
        _linha("2", "A VEICULAR", "MARÇO/2026", 3000),
        _linha("3", "CANCELADO", "ABRIL/2026", 500),
        _linha("4", "EM NEGOCIAÇÃO", "ABRIL/2026", 400),
        _linha("5", "CHECKING", "DEZEMBRO/2025", 700),
        _linha("6", "FATURADO", "JANEIRO/2026", 1200, ano=2025),
    ]))


class TestAuditoriaVendas:
    def test_totais(self, df):
        resultado = auditoria.auditar_vendas_ano(df, 2026)
        assert resultado["total_aba"] == pytest.approx(13600.0)
        # 9000 + 3000 (aba 2026) + 1200 (aba 2025, ganho 2026)
        assert resultado["vendas_sistema"] == pytest.approx(13200.0)
        assert resultado["diferenca"] == pytest.approx(400.0)

    def test_excluidas_com_motivos(self, df):
        resultado = auditoria.auditar_vendas_ano(df, 2026)
        excluidas = resultado["excluidas"].set_index("PI")
        assert len(excluidas) == 3
        assert "fora de todas as somas" in excluidas.loc["3", auditoria.COL_MOTIVO]
        assert "não reconhecido" in excluidas.loc["4", auditoria.COL_MOTIVO]
        assert "12/2025" in excluidas.loc["5", auditoria.COL_MOTIVO]
        assert resultado["total_excluidas"] == pytest.approx(1600.0)

    def test_linhas_de_outras_abas(self, df):
        resultado = auditoria.auditar_vendas_ano(df, 2026)
        assert len(resultado["outras_abas"]) == 1
        assert resultado["total_outras_abas"] == pytest.approx(1200.0)

    def test_conciliacao_fecha_em_zero(self, df):
        """A prova aritmética: exclusões + outras abas explicam a diferença."""
        resultado = auditoria.auditar_vendas_ano(df, 2026)
        assert resultado["residuo"] == pytest.approx(0.0, abs=0.01)

    def test_linha_em_vendas_nao_tem_motivo(self, df):
        linha_ok = df[df["PI"] == "1"].iloc[0]
        assert auditoria.classificar_exclusao(linha_ok, 2026) is None

    def test_ano_sem_aba(self, df):
        resultado = auditoria.auditar_vendas_ano(df, 2030)
        assert resultado["total_aba"] == 0.0
        assert resultado["excluidas"].empty
        assert resultado["residuo"] == pytest.approx(0.0)

    def test_auditoria_nao_altera_os_dados(self, df):
        copia = df.copy(deep=True)
        auditoria.auditar_vendas_ano(df, 2026)
        pd.testing.assert_frame_equal(df, copia)
