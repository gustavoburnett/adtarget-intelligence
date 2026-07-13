"""Testes da formatação executiva e do card YTD de destaque (v0.5 Sprint 1).

Cobrem apenas as funções PURAS de cards.py (formatação e montagem do card);
a renderização Streamlit é validada pelo smoke test.
"""

import pytest

from src.components import cards


# ---------------------------------------------------------------------------
# Formatação executiva (Mi / mil / valor completo)
# ---------------------------------------------------------------------------

class TestFormatacaoExecutiva:
    @pytest.mark.parametrize("valor,esperado", [
        (12_500_000, "R$ 12,50 Mi"),
        (8_020_000, "R$ 8,02 Mi"),
        (1_000_000, "R$ 1,00 Mi"),
        (543_210, "R$ 543,21 mil"),
        (1_000, "R$ 1,00 mil"),
        (999.99, "R$ 999,99"),
        (0, "R$ 0,00"),
        (41_210_319, "R$ 41,21 Mi"),
    ])
    def test_faixas(self, valor, esperado):
        assert cards.formatar_moeda_executiva(valor) == esperado

    def test_nunca_usa_k(self):
        assert "K" not in cards.formatar_moeda_executiva(543_210)

    def test_arredonda_pelo_mais_proximo_nunca_trunca(self):
        assert cards.formatar_moeda_executiva(1_994_999) == "R$ 1,99 Mi"
        assert cards.formatar_moeda_executiva(1_995_000) == "R$ 2,00 Mi"
        assert cards.formatar_moeda_executiva(1_249) == "R$ 1,25 mil"

    def test_promocao_de_faixa_no_arredondamento(self):
        """999.995 arredondaria para '1.000,00 mil' — deve virar '1,00 Mi'."""
        assert cards.formatar_moeda_executiva(999_995) == "R$ 1,00 Mi"

    def test_valor_negativo(self):
        assert cards.formatar_moeda_executiva(-1_500_000) == "-R$ 1,50 Mi"

    def test_none_vira_sem_dados(self):
        assert cards.formatar_moeda_executiva(None) == cards.SEM_DADOS

    def test_valor_completo_permanece_disponivel(self):
        """Tooltips/tabelas/auditoria usam formatar_moeda (completo)."""
        assert cards.formatar_moeda(12_500_000) == "R$ 12.500.000,00"


# ---------------------------------------------------------------------------
# Card YTD de destaque: apenas fatos, 4 estados
# ---------------------------------------------------------------------------

def _resultado(atual, anterior, variacao, mes_limite=7):
    return {"atual": atual, "anterior": anterior,
            "variacao_pct": variacao, "mes_limite": mes_limite}


class TestMontarYtd:
    def test_crescimento(self):
        pecas = cards.montar_ytd(
            _resultado(12_500_000, 8_020_000, 55.9), ano=2026
        )
        assert pecas["estado"] == "ok"
        assert pecas["periodo"] == "Acumulado Jan–Jul/2026 vs Jan–Jul/2025"
        assert pecas["seta"] == "▲"
        assert pecas["cor"] == cards.COR_POSITIVO
        assert pecas["percentual"] == "55,9%"
        assert pecas["suporte"] == (
            "R$ 12,50 Mi este ano · R$ 8,02 Mi no mesmo período de 2025"
        )

    def test_queda_muda_apenas_cor_e_seta(self):
        cresce = cards.montar_ytd(_resultado(12e6, 8e6, 50.0), ano=2026)
        cai = cards.montar_ytd(_resultado(8e6, 12e6, -33.3), ano=2026)
        assert cai["seta"] == "▼" and cai["cor"] == cards.COR_NEGATIVO
        assert cai["percentual"] == "33,3%"  # uma casa decimal
        # mesma estrutura: mesmas chaves, mesmo formato de suporte
        assert set(cai) == set(cresce)
        assert "no mesmo período de 2025" in cai["suporte"]

    def test_sem_frase_interpretativa(self):
        for pecas in (
            cards.montar_ytd(_resultado(12e6, 8e6, 50.0), 2026),
            cards.montar_ytd(_resultado(8e6, 12e6, -33.3), 2026),
        ):
            texto = " ".join(pecas.values()).lower()
            assert "consistente" not in texto
            assert "recuo" not in texto
            assert "crescimento" not in texto

    def test_ano_encerrado_usa_jan_dez(self):
        pecas = cards.montar_ytd(
            _resultado(20e6, 16e6, 25.0, mes_limite=12), ano=2025
        )
        assert pecas["periodo"] == "Acumulado Jan–Dez/2025 vs Jan–Dez/2024"

    def test_sem_comparativo(self):
        pecas = cards.montar_ytd(_resultado(5e6, None, None), ano=2026)
        assert pecas["estado"] == "sem_comparativo"
        assert pecas["suporte"] == "Sem comparativo disponível para este ano."
        assert pecas["cor"] == cards.COR_NEUTRO
        assert "%" not in pecas["percentual"]  # nunca percentual quebrado

    def test_anterior_zero_nunca_divide(self):
        pecas = cards.montar_ytd(_resultado(5e6, 0.0, None), ano=2026)
        assert pecas["percentual"] == "—"
        assert pecas["cor"] == cards.COR_NEUTRO

    def test_recorte_sem_linhas(self):
        pecas = cards.montar_ytd(
            _resultado(0.0, None, None), ano=2026, sem_dados=True
        )
        assert pecas["estado"] == "sem_dados"
        assert pecas["suporte"] == "Sem dados no recorte selecionado."

    def test_variacao_zero_e_neutra(self):
        pecas = cards.montar_ytd(_resultado(8e6, 8e6, 0.0), ano=2026)
        assert pecas["percentual"] == "0,0%"
        assert pecas["cor"] == cards.COR_NEUTRO
        assert pecas["seta"] == ""
