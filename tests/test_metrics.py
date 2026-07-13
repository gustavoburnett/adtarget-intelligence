"""Testes dos indicadores comerciais (metrics.py) e dos alertas de qualidade.

Regra vigente (2026-07-09):
- Vendas    = A VEICULAR + EM VEICULAÇÃO + CHECKING + AGUARD. DOC. VEÍCULO
              + FATURADO + DIRETO
- Faturado  = FATURADO + DIRETO
- Em Aberto = Vendas − Faturado
- CANCELADO e BONIFICADO fora de qualquer soma (apenas contagem)

A base sintética reproduz os casos extremos reais da planilha:
- status com espaço no fim ("FATURADO ")
- CANCELADO com valor diferente de zero (caso real de R$ 17.172)
- mesmo nome de campanha em clientes diferentes ("ALWAYS ON")
- mesmo nome de veículo em grupos diferentes ("93 FM")
- MÊS (GANHO) diferente de MÊS (VEICULAÇÃO)
- NF ausente como célula vazia e como texto "SEM NOTA"
- venda DIRETO sem NF (por desenho, não é inconsistência)
- status fora do vocabulário controlado
"""

import datetime

import pandas as pd
import pytest

from src.data import metrics, quality_checks
from src.data.cleaning import limpar_dataframe

#: Data de referência fixa para testes de YTD (determinístico, sem relógio)
HOJE_JUL_2026 = datetime.date(2026, 7, 15)
HOJE_MAR_2026 = datetime.date(2026, 3, 15)


# ---------------------------------------------------------------------------
# Base sintética (valores brutos, passa pelo pipeline real de limpeza)
# ---------------------------------------------------------------------------

def _linha(**kwargs) -> dict:
    base = {
        "PRAÇA": "BRASÍLIA",
        "EXECUTIVO": "EXEC 1",
        "GRUPO": "GRUPO B",
        "VEICULO": "VEIC B",
        "PI": "1000",
        "AGENCIA": "AG1",
        "CLIENTE": "CLIENTE X",
        "CAMPANHA": "CAMPANHA X",
        "MÊS (GANHO)": "JANEIRO/2025",
        "MÊS (VEICULAÇÃO)": "JANEIRO/2025",
        "INÍCIO": "",
        "FIM": "",
        "VALOR PI BRUTO": 0,
        "VALOR PI LIQUIDO": 0,
        "VENCIMENTO PI": "CONTRA APRESENT.",
        "STATUS": "FATURADO",
        "NOTA FISCAL": "999",
        "DATA DE CRIAÇÃO": "",
        "OBSERVAÇÃO": "",
        "ANO_ABA": 2025,
    }
    base.update(kwargs)
    return base


@pytest.fixture
def df() -> pd.DataFrame:
    """Base limpa. Totais esperados (todos os anos):
    Faturado: 49.000 líq / 59.000 bruto (6 PIs)
    Em Aberto: 7.200 líq / 9.000 bruto (4 PIs)
    Vendas: 56.200 líq / 68.000 bruto (10 PIs)"""
    linhas = [
        # --- 2025 ---
        _linha(PI="1001", GRUPO="MELODIA", VEICULO="93 FM",
               CLIENTE="CLIENTE A", CAMPANHA="ALWAYS ON",
               **{"MÊS (GANHO)": "JANEIRO/2025", "MÊS (VEICULAÇÃO)": "JANEIRO/2025",
                  "VALOR PI BRUTO": 10000, "VALOR PI LIQUIDO": 8000,
                  "NOTA FISCAL": "111"}),
        # status com espaço no fim + NF em branco (alerta 1);
        # veiculação em junho (fora do intervalo YTD jan-mai)
        _linha(PI="1002", CLIENTE="CLIENTE B", CAMPANHA="ALWAYS ON",
               STATUS="FATURADO ",
               **{"MÊS (GANHO)": "FEVEREIRO/2025", "MÊS (VEICULAÇÃO)": "JUNHO/2025",
                  "VALOR PI BRUTO": 20000, "VALOR PI LIQUIDO": 16000,
                  "NOTA FISCAL": ""}),
        # DIRETO sem NF: por desenho, NÃO entra no alerta 1; líquido = bruto
        _linha(PI="1003", GRUPO="GRUPO C", VEICULO="VEIC C",
               CLIENTE="CLIENTE C", CAMPANHA="CAMPANHA C", STATUS="DIRETO",
               **{"MÊS (GANHO)": "MARÇO/2025", "MÊS (VEICULAÇÃO)": "MARÇO/2025",
                  "VALOR PI BRUTO": 5000, "VALOR PI LIQUIDO": 5000,
                  "NOTA FISCAL": "SEM NF"}),
        # Em Aberto (CHECKING): conta em Vendas e em Campanhas
        _linha(PI="1004", CLIENTE="CLIENTE Z", CAMPANHA="SO EM ABERTO",
               STATUS="CHECKING",
               **{"MÊS (GANHO)": "ABRIL/2025", "MÊS (VEICULAÇÃO)": "ABRIL/2025",
                  "VALOR PI BRUTO": 3000, "VALOR PI LIQUIDO": 2400,
                  "NOTA FISCAL": ""}),
        # Cancelado com valor zerado (comportamento esperado)
        _linha(PI="1005", GRUPO="GRUPO C", VEICULO="VEIC C",
               CLIENTE="CLIENTE C", CAMPANHA="CAMP CANC", STATUS="CANCELADO",
               **{"MÊS (GANHO)": "MAIO/2025", "MÊS (VEICULAÇÃO)": "MAIO/2025",
                  "NOTA FISCAL": ""}),
        # CASO REAL: cancelado com valor NÃO zerado (alerta 5; fora de Vendas)
        _linha(PI="1011", CLIENTE="CLIENTE B", CAMPANHA="CAMP CANC 2",
               STATUS="CANCELADO",
               **{"MÊS (GANHO)": "JUNHO/2025", "MÊS (VEICULAÇÃO)": "JUNHO/2025",
                  "VALOR PI BRUTO": 17172, "VALOR PI LIQUIDO": 13737.6,
                  "NOTA FISCAL": ""}),
        # --- 2026 ---
        # mesmo veículo "93 FM" (com espaço no fim) sob OUTRO grupo (alerta 3)
        _linha(PI="1006", GRUPO="SISTEMA VERDES MARES", VEICULO="93 FM ",
               CLIENTE="CLIENTE A", CAMPANHA="VERÃO 2026", ANO_ABA=2026,
               **{"MÊS (GANHO)": "JANEIRO/2026", "MÊS (VEICULAÇÃO)": "FEVEREIRO/2026",
                  "VALOR PI BRUTO": 12000, "VALOR PI LIQUIDO": 9600,
                  "NOTA FISCAL": "222"}),
        # FATURADO com "SEM NOTA" (alerta 1, segunda forma de ausência)
        _linha(PI="1007", CLIENTE="CLIENTE D", CAMPANHA="CAMP D", ANO_ABA=2026,
               **{"MÊS (GANHO)": "FEVEREIRO/2026", "MÊS (VEICULAÇÃO)": "FEVEREIRO/2026",
                  "VALOR PI BRUTO": 8000, "VALOR PI LIQUIDO": 6400,
                  "NOTA FISCAL": "SEM NOTA"}),
        _linha(PI="1008", GRUPO="GRUPO C", VEICULO="VEIC C",
               CLIENTE="CLIENTE E", CAMPANHA="CAMP E", STATUS="DIRETO",
               ANO_ABA=2026,
               **{"MÊS (GANHO)": "MARÇO/2026", "MÊS (VEICULAÇÃO)": "MARÇO/2026",
                  "VALOR PI BRUTO": 4000, "VALOR PI LIQUIDO": 4000,
                  "NOTA FISCAL": ""}),
        _linha(PI="1009", CLIENTE="CLIENTE F", CAMPANHA="CAMP F",
               STATUS="AGUARD. DOC. VEÍCULO", ANO_ABA=2026,
               **{"MÊS (GANHO)": "MARÇO/2026", "MÊS (VEICULAÇÃO)": "MARÇO/2026",
                  "VALOR PI BRUTO": 2000, "VALOR PI LIQUIDO": 1600,
                  "NOTA FISCAL": ""}),
        # Novo status oficial: A VEICULAR (Em Aberto)
        _linha(PI="1010", GRUPO="GRUPO C", VEICULO="VEIC C",
               CLIENTE="CLIENTE G", CAMPANHA="CAMP G", STATUS="A VEICULAR",
               ANO_ABA=2026,
               **{"MÊS (GANHO)": "ABRIL/2026", "MÊS (VEICULAÇÃO)": "ABRIL/2026",
                  "VALOR PI BRUTO": 1000, "VALOR PI LIQUIDO": 800,
                  "NOTA FISCAL": ""}),
        _linha(PI="1012", GRUPO="GRUPO C", VEICULO="VEIC C",
               CLIENTE="CLIENTE H", CAMPANHA="CAMP H", STATUS="BONIFICADO",
               ANO_ABA=2026,
               **{"MÊS (GANHO)": "ABRIL/2026", "MÊS (VEICULAÇÃO)": "ABRIL/2026",
                  "NOTA FISCAL": ""}),
        # Status fora do vocabulário (alerta 4; fora de qualquer cálculo)
        _linha(PI="1013", GRUPO="GRUPO C", VEICULO="VEIC C",
               CLIENTE="CLIENTE I", CAMPANHA="CAMP I", STATUS="EM NEGOCIAÇÃO",
               ANO_ABA=2026,
               **{"MÊS (GANHO)": "ABRIL/2026", "MÊS (VEICULAÇÃO)": "ABRIL/2026",
                  "VALOR PI BRUTO": 500, "VALOR PI LIQUIDO": 400,
                  "NOTA FISCAL": ""}),
        # Novo status oficial: EM VEICULAÇÃO (Em Aberto)
        _linha(PI="1014", CLIENTE="CLIENTE J", CAMPANHA="CAMP J",
               STATUS="EM VEICULAÇÃO", ANO_ABA=2026,
               **{"MÊS (GANHO)": "MAIO/2026", "MÊS (VEICULAÇÃO)": "MAIO/2026",
                  "VALOR PI BRUTO": 3000, "VALOR PI LIQUIDO": 2400,
                  "NOTA FISCAL": ""}),
    ]
    return limpar_dataframe(pd.DataFrame(linhas))


# ---------------------------------------------------------------------------
# Vendas / Faturado / Em Aberto + toggle Líquido x Bruto
# ---------------------------------------------------------------------------

class TestVendasFaturadoEmAberto:
    def test_vendas_liquido_padrao(self, df):
        assert metrics.vendas(df) == pytest.approx(56200.0)

    def test_vendas_toggle_bruto(self, df):
        assert metrics.vendas(df, valor="bruto") == pytest.approx(68000.0)

    def test_faturado(self, df):
        assert metrics.faturado(df) == pytest.approx(49000.0)
        assert metrics.faturado(df, valor="bruto") == pytest.approx(59000.0)

    def test_em_aberto(self, df):
        assert metrics.em_aberto(df) == pytest.approx(7200.0)
        assert metrics.em_aberto(df, valor="bruto") == pytest.approx(9000.0)

    def test_identidade_em_aberto_igual_vendas_menos_faturado(self, df):
        """Regra oficial: Em Aberto = Vendas − Faturado."""
        for valor in ("liquido", "bruto"):
            assert metrics.em_aberto(df, valor) == pytest.approx(
                metrics.vendas(df, valor) - metrics.faturado(df, valor)
            )

    def test_cancelado_bonificado_e_desconhecido_fora_de_vendas(self, df):
        """CANCELADO (mesmo com R$ 17.172), BONIFICADO e status fora do
        vocabulário nunca entram em Vendas."""
        assert metrics.vendas(df, valor="bruto") == pytest.approx(68000.0)

    def test_status_com_espaco_no_fim_entra_no_calculo(self, df):
        """Caso real: "FATURADO " (16.000 líq) precisa contar após normalização."""
        assert metrics.faturado(df) >= 16000.0

    def test_vendas_detalhado(self, df):
        detalhado = metrics.vendas_detalhado(df)
        assert detalhado["total"] == pytest.approx(56200.0)
        assert detalhado["faturado"] == pytest.approx(49000.0)
        assert detalhado["em_aberto"] == pytest.approx(7200.0)

    def test_toggle_invalido_gera_erro_claro(self, df):
        with pytest.raises(ValueError):
            metrics.vendas(df, valor="liquidez")


# ---------------------------------------------------------------------------
# Ticket Médio (base Vendas)
# ---------------------------------------------------------------------------

class TestTicketMedio:
    def test_liquido(self, df):
        # 56.200 / 10 PIs na base Vendas
        assert metrics.ticket_medio(df) == pytest.approx(56200.0 / 10)

    def test_bruto(self, df):
        assert metrics.ticket_medio(df, valor="bruto") == pytest.approx(68000.0 / 10)

    def test_sem_dados_retorna_none(self, df):
        vazio = df[df["STATUS"] == "INEXISTENTE"]
        assert metrics.ticket_medio(vazio) is None


# ---------------------------------------------------------------------------
# Quantidade de Campanhas (Cliente + Campanha, base Vendas)
# ---------------------------------------------------------------------------

class TestQuantidadeCampanhas:
    def test_contagem_por_cliente_campanha(self, df):
        # "ALWAYS ON" existe em 2 clientes -> conta 2, não 1.
        # 10 pares distintos na base Vendas (inclui os Em Aberto).
        assert metrics.quantidade_campanhas(df) == 10

    def test_campanha_cancelada_nao_conta(self, df):
        base = df[metrics.mascara_vendas(df)]["CAMPANHA"]
        assert "CAMP CANC" not in set(base)
        assert "CAMP CANC 2" not in set(base)


# ---------------------------------------------------------------------------
# Comparativo Ano contra Ano (mês a mês) + lacunas
# ---------------------------------------------------------------------------

class TestComparativoMensal:
    def test_evolucao_mensal_2026_ganho(self, df):
        evolucao = metrics.evolucao_mensal(df, 2026, criterio_mes="ganho")
        # Jan 9600 | Fev 6400 | Mar 4000+1600 | Abr 800 | Mai 2400
        assert evolucao == {1: 9600.0, 2: 6400.0, 3: 5600.0, 4: 800.0, 5: 2400.0}

    def test_mes_sem_dado_e_lacuna_nao_zero(self, df):
        evolucao = metrics.evolucao_mensal(df, 2026, criterio_mes="ganho")
        assert 6 not in evolucao  # mês futuro: lacuna, nunca 0.0

    def test_yoy_mesmo_mes(self, df):
        comp = metrics.comparativo_mensal(df, 2026, criterio_mes="ganho")
        assert comp.loc[1, "atual"] == pytest.approx(9600.0)
        assert comp.loc[1, "anterior"] == pytest.approx(8000.0)   # Jan/2025
        assert comp.loc[4, "atual"] == pytest.approx(800.0)
        assert comp.loc[4, "anterior"] == pytest.approx(2400.0)   # Abr/2025

    def test_yoy_lacunas_como_nan(self, df):
        comp = metrics.comparativo_mensal(df, 2026, criterio_mes="ganho")
        assert pd.isna(comp.loc[12, "atual"])
        assert pd.isna(comp.loc[12, "anterior"])


# ---------------------------------------------------------------------------
# Toggle Mês Ganho x Mês Veiculação
# ---------------------------------------------------------------------------

class TestToggleMes:
    def test_criterios_divergem(self, df):
        """PI 1002: ganho em Fev/2025, veiculação em Jun/2025."""
        ganho = metrics.evolucao_mensal(df, 2025, criterio_mes="ganho")
        veic = metrics.evolucao_mensal(df, 2025, criterio_mes="veiculacao")
        assert ganho[2] == pytest.approx(16000.0)
        assert 2 not in veic
        assert veic[6] == pytest.approx(16000.0)

    def test_total_do_ano_igual_nos_dois_criterios(self, df):
        """Na base sintética, ganho e veiculação caem no mesmo ano: o total
        anual é o mesmo, só a distribuição mensal muda."""
        ganho = metrics.evolucao_mensal(df, 2025, criterio_mes="ganho")
        veic = metrics.evolucao_mensal(df, 2025, criterio_mes="veiculacao")
        assert sum(ganho.values()) == pytest.approx(sum(veic.values()))


# ---------------------------------------------------------------------------
# YTD (acumulado no ano, intervalo comparável, base Vendas)
# ---------------------------------------------------------------------------

class TestYTD:
    def test_ytd_2026_intervalo_comparavel(self, df):
        """Ano corrente (hoje = jul/2026): compara Jan-Jul 2026 x Jan-Jul
        2025, nunca ano parcial contra ano completo."""
        resultado = metrics.ytd(df, 2026, criterio_mes="ganho", hoje=HOJE_JUL_2026)
        assert resultado["mes_limite"] == 7
        assert resultado["atual"] == pytest.approx(24800.0)
        assert resultado["anterior"] == pytest.approx(31400.0)  # 8000+16000+5000+2400
        assert resultado["variacao_pct"] == pytest.approx(
            (24800.0 - 31400.0) / 31400.0 * 100.0
        )

    def test_ytd_recalcula_sobre_toggle_bruto(self, df):
        resultado = metrics.ytd(
            df, 2026, valor="bruto", criterio_mes="ganho", hoje=HOJE_JUL_2026
        )
        assert resultado["atual"] == pytest.approx(30000.0)
        assert resultado["anterior"] == pytest.approx(38000.0)

    def test_ytd_recalcula_sobre_toggle_veiculacao(self, df):
        """Com MÊS (VEICULAÇÃO) e hoje = mai/2026: PI 1002 (veic Jun/2025)
        fica fora do intervalo Jan-Mai -> ano anterior cai para 15.400."""
        resultado = metrics.ytd(
            df, 2026, criterio_mes="veiculacao",
            hoje=datetime.date(2026, 5, 20),
        )
        assert resultado["mes_limite"] == 5
        assert resultado["atual"] == pytest.approx(24800.0)
        assert resultado["anterior"] == pytest.approx(15400.0)  # 8000+5000+2400

    def test_ytd_sem_ano_anterior(self, df):
        """2025 é o primeiro ano da base: 'sem comparativo disponível',
        nunca erro ou divisão por zero."""
        resultado = metrics.ytd(df, 2025, criterio_mes="ganho", hoje=HOJE_JUL_2026)
        assert resultado["atual"] == pytest.approx(31400.0)
        assert resultado["anterior"] is None
        assert resultado["variacao_pct"] is None

    def test_ytd_ano_sem_dado(self, df):
        resultado = metrics.ytd(df, 2030)
        assert resultado["atual"] == 0.0
        assert resultado["variacao_pct"] is None


class TestYTDAnoCorrenteVsEncerrado:
    """Regra do YTD verdadeiro: ano corrente corta no mês atual;
    ano encerrado compara ano completo contra ano completo."""

    def test_ano_corrente_corta_no_mes_atual_ganho(self, df):
        """Hoje = mar/2026: Jan-Mar/2026 x Jan-Mar/2025 (critério Ganho)."""
        resultado = metrics.ytd(df, 2026, criterio_mes="ganho", hoje=HOJE_MAR_2026)
        assert resultado["mes_limite"] == 3
        assert resultado["atual"] == pytest.approx(21600.0)   # 9600+6400+5600
        assert resultado["anterior"] == pytest.approx(29000.0)  # 8000+16000+5000

    def test_ano_corrente_corta_no_mes_atual_veiculacao(self, df):
        """Hoje = mar/2026: Jan-Mar/2026 x Jan-Mar/2025 (critério oficial,
        Veiculação)."""
        resultado = metrics.ytd(
            df, 2026, criterio_mes="veiculacao", hoje=HOJE_MAR_2026
        )
        assert resultado["mes_limite"] == 3
        assert resultado["atual"] == pytest.approx(21600.0)   # 16000 (Fev) + 5600 (Mar)
        assert resultado["anterior"] == pytest.approx(13000.0)  # 8000 (Jan) + 5000 (Mar)

    def test_ano_corrente_exclui_meses_futuros(self, df):
        """Vendas com mês além do mês atual (ex: veiculações agendadas para
        Abr/Mai) NÃO entram no acumulado do ano corrente."""
        resultado = metrics.ytd(
            df, 2026, criterio_mes="veiculacao", hoje=HOJE_MAR_2026
        )
        assert resultado["atual"] == pytest.approx(21600.0)  # sem 800 (Abr) e 2400 (Mai)

    def test_ano_encerrado_compara_ano_completo_ganho(self, df):
        """2025 encerrado (hoje em 2026): Jan-Dez/2025 x Jan-Dez/2024."""
        resultado = metrics.ytd(df, 2025, criterio_mes="ganho", hoje=HOJE_JUL_2026)
        assert resultado["mes_limite"] == 12
        assert resultado["atual"] == pytest.approx(31400.0)  # ano completo

    def test_ano_encerrado_compara_ano_completo_veiculacao(self, df):
        """Ano encerrado no critério oficial: Jun/2025 (16.000) INCLUÍDO —
        nada do ano encerrado fica de fora."""
        resultado = metrics.ytd(
            df, 2025, criterio_mes="veiculacao", hoje=HOJE_JUL_2026
        )
        assert resultado["mes_limite"] == 12
        assert resultado["atual"] == pytest.approx(31400.0)  # 8000+5000+2400+16000


# ---------------------------------------------------------------------------
# Cancelado/Bonificado: contagem de PIs, não soma monetária
# ---------------------------------------------------------------------------

class TestCanceladoBonificado:
    def test_contagens_separadas(self, df):
        resultado = metrics.cancelado_bonificado(df)
        assert resultado["cancelados"] == 2
        assert resultado["bonificados"] == 1

    def test_valor_apenas_como_informacao_secundaria(self, df):
        resultado = metrics.cancelado_bonificado(df)
        assert resultado["valor_bruto_secundario"] == pytest.approx(17172.0)


# ---------------------------------------------------------------------------
# Agregação Grupo + Veículo e Veículos Ativos
# ---------------------------------------------------------------------------

class TestAgrupamentoGrupoVeiculo:
    def test_mesmo_nome_de_veiculo_em_grupos_diferentes_nao_mistura(self, df):
        agg = metrics.agregado_por_grupo_veiculo(df)
        linhas_93fm = agg[agg["VEICULO"] == "93 FM"]
        assert len(linhas_93fm) == 2  # MELODIA e SISTEMA VERDES MARES, separados

    def test_veiculos_ativos(self, df):
        # Pares na base Vendas: (MELODIA, 93 FM), (GRUPO B, VEIC B),
        # (GRUPO C, VEIC C), (SISTEMA VERDES MARES, 93 FM)
        assert metrics.veiculos_ativos(df) == 4


# ---------------------------------------------------------------------------
# Agregações de apresentação (usadas pela interface)
# ---------------------------------------------------------------------------

class TestAgregacoesDeApresentacao:
    def test_resumo_por_status_valores_e_contagem(self, df):
        resumo = metrics.resumo_por_status(df)
        por_status = resumo.set_index("STATUS")
        assert por_status.loc["FATURADO", "valor"] == pytest.approx(40000.0)
        assert por_status.loc["FATURADO", "qtd_pis"] == 4
        assert por_status.loc["DIRETO", "valor"] == pytest.approx(9000.0)
        assert por_status.loc["A VEICULAR", "valor"] == pytest.approx(800.0)
        assert por_status.loc["EM VEICULAÇÃO", "valor"] == pytest.approx(2400.0)
        assert por_status.loc["CHECKING", "qtd_pis"] == 1

    def test_resumo_por_status_ordem_do_ciclo_comercial(self, df):
        resumo = metrics.resumo_por_status(df)
        # A VEICULAR primeiro; status fora do vocabulário vai para o fim
        assert resumo.iloc[0]["STATUS"] == "A VEICULAR"
        assert resumo.iloc[-1]["STATUS"] == "EM NEGOCIAÇÃO"

    def test_evolucao_ticket_medio_mensal(self, df):
        # 2026 ganho: Mar tem 2 PIs (4000+1600)/2 = 2800
        ticket = metrics.evolucao_mensal_ticket_medio(df, 2026, criterio_mes="ganho")
        assert ticket[1] == pytest.approx(9600.0)
        assert ticket[3] == pytest.approx(2800.0)
        assert 6 not in ticket  # lacuna, nunca zero

    def test_agregado_por_dimensao_cliente(self, df):
        agg = metrics.agregado_por_dimensao(df, "CLIENTE")
        # CLIENTE A: 8000 + 9600 = 17600, líder do ranking
        assert agg.iloc[0]["CLIENTE"] == "CLIENTE A"
        assert agg.iloc[0]["valor"] == pytest.approx(17600.0)
        # Em Aberto entra na base Vendas: CLIENTE Z aparece
        assert "CLIENTE Z" in set(agg["CLIENTE"])
        # Cancelados/bonificados/desconhecidos fora
        assert "CLIENTE H" not in set(agg["CLIENTE"])
        assert "CLIENTE I" not in set(agg["CLIENTE"])

    def test_agregado_por_dimensao_veta_veiculo_isolado(self, df):
        """Decisão 15: veículo nunca é agregado isoladamente."""
        with pytest.raises(ValueError):
            metrics.agregado_por_dimensao(df, "VEICULO")


# ---------------------------------------------------------------------------
# Critério temporal oficial (regra v0.4: MÊS VEICULAÇÃO — fonte única)
# ---------------------------------------------------------------------------

class TestCriterioOficial:
    def test_regra_oficial_e_veiculacao(self):
        """REGRA OFICIAL v0.4: 'quanto vendemos' responde por Veiculação."""
        assert metrics.CRITERIO_MES_OFICIAL == "veiculacao"

    def test_coluna_mes_padrao_segue_a_constante(self):
        assert metrics.coluna_mes() == metrics.COLUNAS_MES[
            metrics.CRITERIO_MES_OFICIAL
        ]

    def test_funcoes_temporais_padrao_seguem_a_constante(self, df):
        """Sem argumento explícito, toda função temporal usa a fonte única
        de verdade — nenhum 'ganho' hardcoded como default."""
        oficial = metrics.CRITERIO_MES_OFICIAL
        assert metrics.evolucao_mensal(df, 2026) == metrics.evolucao_mensal(
            df, 2026, criterio_mes=oficial
        )
        assert metrics.ytd(df, 2026) == metrics.ytd(
            df, 2026, criterio_mes=oficial
        )
        assert metrics.evolucao_mensal_ticket_medio(
            df, 2026
        ) == metrics.evolucao_mensal_ticket_medio(df, 2026, criterio_mes=oficial)
        pd.testing.assert_frame_equal(
            metrics.comparativo_mensal(df, 2026),
            metrics.comparativo_mensal(df, 2026, criterio_mes=oficial),
        )

    def test_default_e_veiculacao_na_pratica(self, df):
        """PI 1006 tem ganho em Jan e veiculação em Fev: no default oficial,
        o valor precisa cair em fevereiro."""
        evolucao = metrics.evolucao_mensal(df, 2026)
        assert evolucao[2] == pytest.approx(16000.0)  # 9600 (1006) + 6400 (1007)
        assert 1 not in evolucao  # nada em janeiro no critério oficial

    def test_ganho_permanece_disponivel_como_alternativa(self, df):
        """O toggle analítico não pode ter sido removido."""
        alternativa = metrics.evolucao_mensal(df, 2026, criterio_mes="ganho")
        assert alternativa[1] == pytest.approx(9600.0)


# ---------------------------------------------------------------------------
# Agregações de apresentação da Sprint 2B (tendência e destaques) — apenas
# derivam dados já calculados; nenhum número existente pode mudar
# ---------------------------------------------------------------------------

class TestTendenciaEDestaques:
    def test_tendencia_cliente_vs_intervalo_comparavel(self, df):
        """CLIENTE A: 9.600 (2026, jan-jul ganho) vs 8.000 (2025) = +20%."""
        tendencia = metrics.tendencia_por_dimensao(
            df, "CLIENTE", 2026, criterio_mes="ganho", hoje=HOJE_JUL_2026
        )
        assert tendencia["CLIENTE A"] == pytest.approx(20.0)

    def test_tendencia_sem_base_anterior_e_none(self, df):
        """Entidade sem valor no ano anterior: badge neutro, nunca % quebrado."""
        tendencia = metrics.tendencia_por_dimensao(
            df, "CLIENTE", 2026, criterio_mes="ganho", hoje=HOJE_JUL_2026
        )
        assert tendencia["CLIENTE D"] is None

    def test_tendencia_grupo_veiculo(self, df):
        tendencia = metrics.tendencia_grupo_veiculo(
            df, 2026, criterio_mes="ganho", hoje=HOJE_JUL_2026
        )
        # GRUPO B/VEIC B: 10.400 (2026) vs 18.400 (2025, jan-jul) = -43,48%
        assert tendencia[("GRUPO B", "VEIC B")] == pytest.approx(
            (10400 - 18400) / 18400 * 100.0
        )
        # 93 FM sob SVM não existia em 2025: None
        assert tendencia[("SISTEMA VERDES MARES", "93 FM")] is None

    def test_destaques_concentracao(self, df):
        destaques = metrics.destaques_do_recorte(df, 2026, criterio_mes="ganho")
        grupo, pct = destaques["concentracao"]
        assert grupo == "GRUPO B"
        assert pct == pytest.approx(10400 / 24800 * 100.0)

    def test_destaques_maior_mes_e_maior_queda(self, df):
        destaques = metrics.destaques_do_recorte(df, 2026, criterio_mes="ganho")
        assert destaques["maior_mes"] == (1, pytest.approx(9600.0))
        mes, mes_anterior, variacao = destaques["maior_queda"]
        assert (mes, mes_anterior) == (4, 3)
        assert variacao == pytest.approx((800 - 5600) / 5600 * 100.0)

    def test_destaques_ano_sem_dado(self, df):
        destaques = metrics.destaques_do_recorte(df, 2030, criterio_mes="ganho")
        assert destaques == {
            "concentracao": None, "maior_mes": None, "maior_queda": None,
        }

    def test_agregacoes_nao_alteram_numeros_existentes(self, df):
        """Prova do critério de aceite: rodar as agregações novas não muda
        nenhum indicador oficial."""
        antes = (
            metrics.vendas(df), metrics.faturado(df), metrics.em_aberto(df)
        )
        metrics.tendencia_por_dimensao(df, "CLIENTE", 2026, hoje=HOJE_JUL_2026)
        metrics.destaques_do_recorte(df, 2026)
        assert (
            metrics.vendas(df), metrics.faturado(df), metrics.em_aberto(df)
        ) == antes


# ---------------------------------------------------------------------------
# Alertas de Qualidade (detectam, nunca corrigem)
# ---------------------------------------------------------------------------

class TestAlertasQualidade:
    def test_alerta_1_faturado_sem_nf(self, df):
        alerta = quality_checks.faturado_sem_nota_fiscal(df)
        # PI 1002 (célula vazia) + PI 1007 ("SEM NOTA") = 2.
        # PI 1003 (DIRETO com "SEM NF") NÃO conta: DIRETO nunca tem NF por desenho.
        assert alerta.quantidade == 2
        assert set(alerta.linhas["PI"]) == {"1002", "1007"}

    def test_alerta_3_veiculo_com_mais_de_um_grupo(self, df):
        alerta = quality_checks.veiculo_com_multiplos_grupos(df)
        assert alerta.quantidade == 1
        assert alerta.detalhes["veiculos"] == {
            "93 FM": ["MELODIA", "SISTEMA VERDES MARES"]
        }

    def test_alerta_4_status_desconhecido(self, df):
        alerta = quality_checks.status_desconhecido(df)
        assert alerta.quantidade == 1
        assert alerta.detalhes["valores"] == ["EM NEGOCIAÇÃO"]

    def test_alerta_4_status_em_branco_e_guarda_corpo(self, df):
        """O campo é obrigatório na planilha; se um branco escapar, o
        alerta 4 sinaliza como "(VAZIO)" em vez de existir uma categoria
        SEM_STATUS."""
        com_branco = df.copy()
        com_branco.loc[com_branco.index[0], "STATUS"] = ""
        alerta = quality_checks.status_desconhecido(com_branco)
        assert alerta.quantidade == 2
        assert "(VAZIO)" in alerta.detalhes["valores"]

    def test_alerta_5_cancelado_com_valor(self, df):
        alerta = quality_checks.cancelado_bonificado_com_valor(df)
        assert alerta.quantidade == 1
        assert alerta.detalhes["valor_bruto"] == pytest.approx(17172.0)
        assert set(alerta.linhas["PI"]) == {"1011"}

    def test_alertas_nao_alteram_os_dados(self, df):
        copia = df.copy(deep=True)
        quality_checks.executar_todas(df)
        pd.testing.assert_frame_equal(df, copia)

    def test_executar_todas_retorna_os_4_alertas_vigentes(self, df):
        alertas = quality_checks.executar_todas(df)
        # Alerta 2 (sem status) removido em 2026-07-09; códigos preservados
        assert [a.codigo for a in alertas] == ["1", "3", "4", "5"]
