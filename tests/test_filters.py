"""Testes do filtro compacto (Sprint 3A) — funções puras do componente.

O rascunho/aplicado e a interação do popover são validados no smoke test
e nas capturas de tela; aqui fica a lógica determinística: resumo do
campo recolhido, busca com realce e recorte do subconjunto buscado.
"""

import pytest

from src.components.filters import (
    filtrar_opcoes,
    realcar_busca,
    resumo_selecao,
)

GRUPOS = ["DISNEY", "TEADS", "IG", "CANAL RURAL", "MELODIA"]


class TestResumoSelecao:
    def test_todos_selecionados(self):
        assert resumo_selecao(GRUPOS, 5, "grupos") == "Todos os grupos (5)"

    def test_todos_com_genero_feminino(self):
        assert resumo_selecao(["A", "B"], 2, "agências", genero="a") == (
            "Todas as agências (2)"
        )

    def test_nenhum_selecionado(self):
        assert resumo_selecao([], 18, "grupos") == "Nenhum selecionado"
        assert resumo_selecao([], 26, "agências", genero="a") == (
            "Nenhuma selecionada"
        )

    def test_parcial_pequeno_mostra_nomes(self):
        assert resumo_selecao(["DISNEY", "TEADS", "IG"], 18, "grupos") == (
            "DISNEY, TEADS, IG"
        )

    def test_parcial_grande_mostra_nomes_e_contador(self):
        selecao = ["DISNEY", "TEADS", "IG", "MELODIA", "CANAL RURAL"]
        assert resumo_selecao(selecao, 18, "grupos") == "DISNEY, TEADS, IG +2"

    def test_nomes_longos_degradam_para_um_nome_mais_contador(self):
        selecao = ["SISTEMA VERDES MARES", "MINISTÉRIO DA SAÚDE",
                   "DEPARTAMENTO DE PUBLICAÇÕES", "OUTRO", "MAIS UM"]
        assert resumo_selecao(selecao, 90, "clientes") == (
            "SISTEMA VERDES MARES +4"
        )

    def test_nome_gigante_degrada_para_contagem_pura(self):
        selecao = ["DEPARTAMENTO DE PUBLICAÇÕES BRASILIA LTDA", "OUTRO"]
        assert resumo_selecao(selecao, 90, "clientes") == (
            "2 clientes selecionados"
        )

    def test_resumo_nunca_ultrapassa_uma_linha(self):
        import itertools
        nomes = ["SISTEMA VERDES MARES", "DISNEY", "IG", "CANAL RURAL",
                 "LIGA OOH", "WEBEDIA", "MELODIA", "BRASIL 247"]
        for n in range(1, len(nomes) + 1):
            for combo in itertools.combinations(nomes, n):
                resumo = resumo_selecao(list(combo), 21, "grupos")
                # teto folgado: nomes até 32 chars ou contagem curta
                assert len(resumo) <= 40, resumo

    def test_universo_vazio(self):
        assert resumo_selecao([], 0, "grupos") == "Sem grupos no recorte"


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
