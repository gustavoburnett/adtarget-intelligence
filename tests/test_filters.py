"""Testes das regras de resumo do filtro de Grupo recolhido (Sprint 2A).

Apenas a função pura de resumo; a interação do popover é coberta pelo
smoke test. Nenhuma semântica de filtro mudou — só a apresentação.
"""

from src.components.filters import resumo_grupos


class TestResumoGrupos:
    def test_todos_selecionados(self):
        assert resumo_grupos(["A", "B", "C"], total=3) == "Grupo: Todos"

    def test_selecao_pequena_mostra_nomes(self):
        assert resumo_grupos(["Disney", "Teads", "Brasil 247"], total=21) == (
            "Grupo: Disney, Teads, Brasil 247"
        )

    def test_selecao_grande_resume_com_contador(self):
        selecionados = ["Disney", "Teads", "IG", "Melodia", "Canal Rural",
                        "Webedia", "Liga OOH"]
        assert resumo_grupos(selecionados, total=21) == "Grupo: Disney, Teads +5"

    def test_nenhum_selecionado_e_intencional(self):
        assert resumo_grupos([], total=21) == "Grupo: Nenhum selecionado"

    def test_resumo_nunca_ultrapassa_o_contador(self):
        """Regra de espaço do PO: no máximo 2 nomes + contador."""
        muitos = [f"GRUPO {i}" for i in range(15)]
        resumo = resumo_grupos(muitos, total=21)
        assert resumo.count(",") == 1  # só 2 nomes visíveis
        assert "+13" in resumo

    def test_nomes_longos_degradam_para_menos_nomes(self):
        """Nomes reais longos (ex: SISTEMA VERDES MARES) não podem estourar
        o teto de uma linha: o resumo degrada para 1 nome + contador."""
        resumo = resumo_grupos(
            ["SISTEMA VERDES MARES", "CANAL RURAL", "LIGA OOH", "DISNEY"],
            total=21,
        )
        assert len(resumo) <= 38
        assert resumo == "Grupo: SISTEMA VERDES MARES +3"

    def test_ultimo_recurso_e_contagem_pura(self):
        """Se nem 1 nome couber, o resumo vira contagem pura."""
        resumo = resumo_grupos(
            ["NOME ABSURDAMENTE COMPRIDO DE GRUPO DE MÍDIA LTDA", "OUTRO"],
            total=21,
        )
        assert len(resumo) <= 38
        assert resumo == "Grupo: 2 de 21 selecionados"

    def test_teto_vale_para_qualquer_combinacao(self):
        import itertools
        nomes = ["SISTEMA VERDES MARES", "DISNEY", "IG", "CANAL RURAL",
                 "LIGA OOH", "WEBEDIA", "MELODIA", "CARREGA+", "BRASIL 247"]
        for n in range(1, len(nomes)):
            for combo in itertools.combinations(nomes, n):
                assert len(resumo_grupos(list(combo), total=21)) <= 38
