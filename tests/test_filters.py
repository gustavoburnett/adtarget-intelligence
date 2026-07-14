"""Testes do filtro compacto (Sprint 3A) — funções puras do componente.

O rascunho/aplicado e a interação do popover são validados no smoke test
e nas capturas de tela; aqui fica a lógica determinística: resumo do
campo recolhido, busca com realce e recorte do subconjunto buscado.
"""

import pytest

from src.components.filters import (
    filtrar_opcoes,
    realcar_busca,
    resumo_curto,
)

GRUPOS = ["DISNEY", "TEADS", "IG", "CANAL RURAL", "MELODIA"]


class TestResumoCurto:
    """Resumo inline do campo (Sprint 3B): o rótulo do filtro fica no
    próprio campo, então o resumo não repete o substantivo."""

    def test_todos(self):
        assert resumo_curto(GRUPOS, 5) == "Todos (5)"
        assert resumo_curto(["A", "B"], 2, genero="a") == "Todas (2)"

    def test_nenhum(self):
        assert resumo_curto([], 18) == "Nenhum"
        assert resumo_curto([], 18, genero="a") == "Nenhuma"

    def test_parcial_com_nomes(self):
        assert resumo_curto(["DISNEY", "TEADS"], 18) == "DISNEY, TEADS"
        assert resumo_curto(["DISNEY", "TEADS", "IG"], 18) == "DISNEY, TEADS +1"

    def test_nomes_longos_degradam_para_contagem(self):
        selecao = ["SISTEMA VERDES MARES — DIÁRIO DO NORDESTE",
                   "MINISTÉRIO DA SAÚDE", "OUTRO"]
        assert resumo_curto(selecao, 54) == "3 sel."

    def test_nunca_ultrapassa_o_teto_inline(self):
        import itertools
        nomes = ["SISTEMA VERDES MARES", "DISNEY", "IG", "CANAL RURAL",
                 "MELODIA", "BRASIL 247"]
        for n in range(1, len(nomes) + 1):
            for combo in itertools.combinations(nomes, n):
                assert len(resumo_curto(list(combo), 21)) <= 28


class TestBusca:
    def test_filtra_case_insensitive(self):
        assert filtrar_opcoes(GRUPOS, "dis") == ["DISNEY"]
        assert filtrar_opcoes(GRUPOS, "Al") == ["CANAL RURAL"]

    def test_busca_vazia_retorna_tudo(self):
        assert filtrar_opcoes(GRUPOS, "") == GRUPOS
        assert filtrar_opcoes(GRUPOS, "   ") == GRUPOS

    def test_sem_resultado(self):
        assert filtrar_opcoes(GRUPOS, "xyz") == []

    def test_realce_do_trecho(self):
        assert realcar_busca("DISNEY", "dis") == "**DIS**NEY"
        assert realcar_busca("CANAL RURAL", "rur") == "CANAL **RUR**AL"

    def test_realce_sem_match_ou_sem_busca(self):
        assert realcar_busca("DISNEY", "") == "DISNEY"
        assert realcar_busca("DISNEY", "xyz") == "DISNEY"

    @pytest.mark.parametrize("texto,busca", [
        ("DISNEY — DISNEY+", "disney"),
        ("SISTEMA VERDES MARES — 93 FM", "93"),
    ])
    def test_realce_preserva_o_texto(self, texto, busca):
        assert realcar_busca(texto, busca).replace("**", "") == texto
