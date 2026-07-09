"""Testes das métricas oficiais (metrics.py) e dos alertas de qualidade.

A base sintética reproduz os casos reais da planilha (documentos 01 e 02):
- status com espaço no fim ("FATURADO ")
- linha sem status com valor material
- CANCELADO com valor diferente de zero (caso real de R$ 17.172)
- mesmo nome de campanha em clientes diferentes ("ALWAYS ON")
- mesmo nome de veículo em grupos diferentes ("93 FM")
- MÊS (GANHO) diferente de MÊS (VEICULAÇÃO)
- NF ausente como célula vazia e como texto "SEM NOTA"
- venda DIRETO sem NF (por desenho, não é inconsistência)
"""

import pandas as pd
import pytest

from src.data import metrics, quality_checks
from src.data.cleaning import limpar_dataframe


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
    """Base limpa com casos extremos reais. Faturamento Realizado esperado:
    líquido 49.000 / bruto 59.000 em 6 PIs realizados."""
    linhas = [
        # --- 2025 ---
        _linha(PI="1001", GRUPO="MELODIA", VEICULO="93 FM",
               CLIENTE="CLIENTE A", CAMPANHA="ALWAYS ON",
               **{"MÊS (GANHO)": "JANEIRO/2025", "MÊS (VEICULAÇÃO)": "JANEIRO/2025",
                  "VALOR PI BRUTO": 10000, "VALOR PI LIQUIDO": 8000,
                  "NOTA FISCAL": "111"}),
        # status com espaço no fim + NF em branco (alerta 1)
        _linha(PI="1002", CLIENTE="CLIENTE B", CAMPANHA="ALWAYS ON",
               STATUS="FATURADO ",
               **{"MÊS (GANHO)": "FEVEREIRO/2025", "MÊS (VEICULAÇÃO)": "MAIO/2025",
                  "VALOR PI BRUTO": 20000, "VALOR PI LIQUIDO": 16000,
                  "NOTA FISCAL": ""}),
        # DIRETO sem NF: por desenho, NÃO entra no alerta 1; líquido = bruto
        _linha(PI="1003", GRUPO="GRUPO C", VEICULO="VEIC C",
               CLIENTE="CLIENTE C", CAMPANHA="CAMPANHA C", STATUS="DIRETO",
               **{"MÊS (GANHO)": "MARÇO/2025", "MÊS (VEICULAÇÃO)": "MARÇO/2025",
                  "VALOR PI BRUTO": 5000, "VALOR PI LIQUIDO": 5000,
                  "NOTA FISCAL": "SEM NF"}),
        # Pipeline (campanha exclusiva de pipeline não conta no KPI de campanhas)
        _linha(PI="1004", CLIENTE="CLIENTE Z", CAMPANHA="SO PIPELINE",
               STATUS="CHECKING",
               **{"MÊS (GANHO)": "ABRIL/2025", "MÊS (VEICULAÇÃO)": "ABRIL/2025",
                  "VALOR PI BRUTO": 3000, "VALOR PI LIQUIDO": 2400,
                  "NOTA FISCAL": ""}),
        # Cancelado com valor zerado (comportamento esperado)
        _linha(PI="1005", GRUPO="GRUPO C", VEICULO="VEIC C",
               CLIENTE="CLIENTE C", CAMPANHA="CAMP CANC", STATUS="CANCELADO",
               **{"MÊS (GANHO)": "MAIO/2025", "MÊS (VEICULAÇÃO)": "MAIO/2025",
                  "NOTA FISCAL": ""}),
        # CASO REAL: cancelado com valor NÃO zerado (alerta 5; fora da receita)
        _linha(PI="1011", CLIENTE="CLIENTE B", CAMPANHA="CAMP CANC 2",
               STATUS="CANCELADO",
               **{"MÊS (GANHO)": "JUNHO/2025", "MÊS (VEICULAÇÃO)": "JUNHO/2025",
                  "VALOR PI BRUTO": 17172, "VALOR PI LIQUIDO": 13737.6,
                  "NOTA FISCAL": ""}),
        # --- 2026 ---
        # mesmo veículo "93 FM" (com espaço no fim) sob OUTRO grupo (alerta 3);
        # ganho em janeiro, veiculação em fevereiro (toggle de mês)
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
        # CASO REAL: linha sem status com valor material (alerta 2)
        _linha(PI="1010", GRUPO="GRUPO C", VEICULO="VEIC C",
               CLIENTE="CLIENTE G", CAMPANHA="CAMP G", STATUS="", ANO_ABA=2026,
               **{"MÊS (GANHO)": "ABRIL/2026", "MÊS (VEICULAÇÃO)": "ABRIL/2026",
                  "VALOR PI BRUTO": 1000, "VALOR PI LIQUIDO": 800,
                  "NOTA FISCAL": ""}),
        _linha(PI="1012", GRUPO="GRUPO C", VEICULO="VEIC C",
               CLIENTE="CLIENTE H", CAMPANHA="CAMP H", STATUS="BONIFICADO",
               ANO_ABA=2026,
               **{"MÊS (GANHO)": "ABRIL/2026", "MÊS (VEICULAÇÃO)": "ABRIL/2026",
                  "NOTA FISCAL": ""}),
        # Status novo, fora do vocabulário (alerta 4; fora de qualquer cálculo)
        _linha(PI="1013", GRUPO="GRUPO C", VEICULO="VEIC C",
               CLIENTE="CLIENTE I", CAMPANHA="CAMP I", STATUS="EM NEGOCIAÇÃO",
               ANO_ABA=2026,
               **{"MÊS (GANHO)": "ABRIL/2026", "MÊS (VEICULAÇÃO)": "ABRIL/2026",
                  "VALOR PI BRUTO": 500, "VALOR PI LIQUIDO": 400,
                  "NOTA FISCAL": ""}),
    ]
    return limpar_dataframe(pd.DataFrame(linhas))


# ---------------------------------------------------------------------------
# Faturamento Realizado + toggle Líquido x Bruto
# ---------------------------------------------------------------------------

class TestFaturamentoRealizado:
    def test_liquido_padrao(self, df):
        assert metrics.faturamento_realizado(df) == pytest.approx(49000.0)

    def test_toggle_bruto(self, df):
        assert metrics.faturamento_realizado(df, valor="bruto") == pytest.approx(
            59000.0
        )

    def test_soma_apenas_faturado_e_direto(self, df):
        """CHECKING, AGUARD., CANCELADO (mesmo com valor), BONIFICADO,
        SEM_STATUS e status desconhecido ficam fora da receita."""
        fora = 2400 + 1600 + 13737.6 + 800 + 400  # pipeline + cancel + sem status + novo
        assert metrics.faturamento_realizado(df) == pytest.approx(49000.0)
        assert 49000.0 + fora != metrics.faturamento_realizado(df)

    def test_status_com_espaco_no_fim_entra_no_calculo(self, df):
        """Caso real: "FATURADO " (16.000 líq) precisa contar após normalização."""
        assert metrics.faturamento_realizado(df) >= 16000.0

    def test_etiqueta_direto(self, df):
        detalhado = metrics.faturamento_realizado_detalhado(df)
        assert detalhado["total"] == pytest.approx(49000.0)
        assert detalhado["direto"] == pytest.approx(9000.0)
        assert detalhado["faturado"] == pytest.approx(40000.0)

    def test_toggle_invalido_gera_erro_claro(self, df):
        with pytest.raises(ValueError):
            metrics.faturamento_realizado(df, valor="liquidez")


# ---------------------------------------------------------------------------
# Pipeline em Aberto
# ---------------------------------------------------------------------------

class TestPipeline:
    def test_liquido(self, df):
        assert metrics.pipeline_em_aberto(df) == pytest.approx(4000.0)

    def test_bruto(self, df):
        assert metrics.pipeline_em_aberto(df, valor="bruto") == pytest.approx(5000.0)

    def test_pipeline_separado_do_faturamento(self, df):
        """Pipeline nunca é somado ao Faturamento Realizado."""
        assert metrics.faturamento_realizado(df) + metrics.pipeline_em_aberto(
            df
        ) == pytest.approx(53000.0)


# ---------------------------------------------------------------------------
# Ticket Médio
# ---------------------------------------------------------------------------

class TestTicketMedio:
    def test_liquido(self, df):
        # 49.000 / 6 PIs realizados
        assert metrics.ticket_medio(df) == pytest.approx(49000.0 / 6)

    def test_bruto(self, df):
        assert metrics.ticket_medio(df, valor="bruto") == pytest.approx(59000.0 / 6)

    def test_sem_dados_retorna_none(self, df):
        vazio = df[df["STATUS"] == "INEXISTENTE"]
        assert metrics.ticket_medio(vazio) is None


# ---------------------------------------------------------------------------
# Quantidade de Campanhas (Cliente + Campanha, apenas Realizado)
# ---------------------------------------------------------------------------

class TestQuantidadeCampanhas:
    def test_contagem_por_cliente_campanha(self, df):
        # "ALWAYS ON" existe em 2 clientes -> conta 2, não 1
        # Pares realizados: (A, ALWAYS ON), (B, ALWAYS ON), (C, CAMPANHA C),
        # (A, VERÃO 2026), (D, CAMP D), (E, CAMP E) = 6
        assert metrics.quantidade_campanhas(df) == 6

    def test_campanha_so_em_pipeline_nao_conta(self, df):
        realizadas = df[metrics.mascara_realizado(df)]["CAMPANHA"]
        assert "SO PIPELINE" not in set(realizadas)
        assert metrics.quantidade_campanhas(df) == 6


# ---------------------------------------------------------------------------
# Comparativo Ano contra Ano (mês a mês) + lacunas
# ---------------------------------------------------------------------------

class TestComparativoMensal:
    def test_evolucao_mensal_2026_ganho(self, df):
        evolucao = metrics.evolucao_mensal(df, 2026)
        assert evolucao == {1: 9600.0, 2: 6400.0, 3: 4000.0}

    def test_mes_sem_dado_e_lacuna_nao_zero(self, df):
        """Abril/2026 não tem Faturamento Realizado: deve ser lacuna
        (ausente do dicionário), nunca 0.0."""
        evolucao = metrics.evolucao_mensal(df, 2026)
        assert 4 not in evolucao

    def test_yoy_mesmo_mes(self, df):
        comp = metrics.comparativo_mensal(df, 2026)
        assert comp.loc[1, "atual"] == pytest.approx(9600.0)
        assert comp.loc[1, "anterior"] == pytest.approx(8000.0)  # Jan/2025
        assert comp.loc[2, "atual"] == pytest.approx(6400.0)
        assert comp.loc[2, "anterior"] == pytest.approx(16000.0)  # Fev/2025

    def test_yoy_lacunas_como_nan(self, df):
        comp = metrics.comparativo_mensal(df, 2026)
        assert pd.isna(comp.loc[4, "atual"])      # sem realizado em Abr/2026
        assert pd.isna(comp.loc[12, "atual"])     # mês futuro
        assert pd.isna(comp.loc[12, "anterior"])


# ---------------------------------------------------------------------------
# Toggle Mês Ganho x Mês Veiculação
# ---------------------------------------------------------------------------

class TestToggleMes:
    def test_criterios_divergem(self, df):
        """PI 1002: ganho em Fev/2025, veiculação em Mai/2025."""
        ganho = metrics.evolucao_mensal(df, 2025, criterio_mes="ganho")
        veic = metrics.evolucao_mensal(df, 2025, criterio_mes="veiculacao")
        assert ganho[2] == pytest.approx(16000.0)
        assert 2 not in veic
        assert veic[5] == pytest.approx(16000.0)

    def test_total_do_ano_igual_nos_dois_criterios(self, df):
        """Na base sintética, ganho e veiculação caem no mesmo ano: o total
        anual é o mesmo, só a distribuição mensal muda."""
        ganho = metrics.evolucao_mensal(df, 2025, criterio_mes="ganho")
        veic = metrics.evolucao_mensal(df, 2025, criterio_mes="veiculacao")
        assert sum(ganho.values()) == pytest.approx(sum(veic.values()))


# ---------------------------------------------------------------------------
# YTD (acumulado no ano, intervalo comparável)
# ---------------------------------------------------------------------------

class TestYTD:
    def test_ytd_2026_intervalo_comparavel(self, df):
        """2026 tem dado até março: compara Jan-Mar 2026 x Jan-Mar 2025,
        nunca ano parcial contra ano completo."""
        resultado = metrics.ytd(df, 2026)
        assert resultado["mes_limite"] == 3
        assert resultado["atual"] == pytest.approx(20000.0)   # 9600+6400+4000
        assert resultado["anterior"] == pytest.approx(29000.0)  # 8000+16000+5000
        assert resultado["variacao_pct"] == pytest.approx(
            (20000.0 - 29000.0) / 29000.0 * 100.0
        )

    def test_ytd_nao_compara_com_ano_completo(self, df):
        """O total de 2025 é 29.000 líquido (Jan-Mar); se houvesse meses
        posteriores, ficariam fora. Junho/2025 (cancelado com valor) e
        Abril/2025 (pipeline) não podem vazar para o comparativo."""
        resultado = metrics.ytd(df, 2026)
        total_2025_completo = metrics.faturamento_realizado(
            df[df["ANO_ABA"] == 2025]
        )
        assert resultado["anterior"] <= total_2025_completo

    def test_ytd_recalcula_sobre_toggle_bruto(self, df):
        resultado = metrics.ytd(df, 2026, valor="bruto")
        assert resultado["atual"] == pytest.approx(24000.0)   # 12000+8000+4000
        assert resultado["anterior"] == pytest.approx(35000.0)  # 10000+20000+5000

    def test_ytd_recalcula_sobre_toggle_veiculacao(self, df):
        """Com MÊS (VEICULAÇÃO): PI 1002 sai de Fev p/ Mai/2025, fora do
        intervalo Jan-Mar -> ano anterior cai para 13.000."""
        resultado = metrics.ytd(df, 2026, criterio_mes="veiculacao")
        assert resultado["mes_limite"] == 3
        assert resultado["atual"] == pytest.approx(20000.0)
        assert resultado["anterior"] == pytest.approx(13000.0)  # 8000+5000

    def test_ytd_sem_ano_anterior(self, df):
        """2025 é o primeiro ano da base: 'sem comparativo disponível',
        nunca erro ou divisão por zero."""
        resultado = metrics.ytd(df, 2025)
        assert resultado["atual"] == pytest.approx(29000.0)
        assert resultado["anterior"] is None
        assert resultado["variacao_pct"] is None

    def test_ytd_ano_sem_dado(self, df):
        resultado = metrics.ytd(df, 2030)
        assert resultado["atual"] == 0.0
        assert resultado["variacao_pct"] is None


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

    def test_cancelado_com_valor_fora_da_receita(self, df):
        """Caso real de R$ 17.172: nunca entra no Faturamento Realizado."""
        assert metrics.faturamento_realizado(df, valor="bruto") == pytest.approx(
            59000.0
        )


# ---------------------------------------------------------------------------
# Agregação Grupo + Veículo e Veículos Ativos
# ---------------------------------------------------------------------------

class TestAgrupamentoGrupoVeiculo:
    def test_mesmo_nome_de_veiculo_em_grupos_diferentes_nao_mistura(self, df):
        agg = metrics.agregado_por_grupo_veiculo(df)
        linhas_93fm = agg[agg["VEICULO"] == "93 FM"]
        assert len(linhas_93fm) == 2  # MELODIA e SISTEMA VERDES MARES, separados

    def test_veiculos_ativos(self, df):
        # Pares com realizado: (MELODIA, 93 FM), (GRUPO B, VEIC B),
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
        assert por_status.loc["CHECKING", "qtd_pis"] == 1
        assert por_status.loc["SEM_STATUS", "valor"] == pytest.approx(800.0)

    def test_resumo_por_status_ordem_oficial(self, df):
        resumo = metrics.resumo_por_status(df)
        # FATURADO primeiro; status fora do vocabulário vai para o fim
        assert resumo.iloc[0]["STATUS"] == "FATURADO"
        assert resumo.iloc[-1]["STATUS"] == "EM NEGOCIAÇÃO"

    def test_resumo_por_status_respeita_toggle(self, df):
        bruto = metrics.resumo_por_status(df, valor="bruto").set_index("STATUS")
        assert bruto.loc["FATURADO", "valor"] == pytest.approx(50000.0)

    def test_evolucao_ticket_medio_mensal(self, df):
        # 2026 ganho: 1 PI por mês -> ticket do mês = valor do mês
        ticket = metrics.evolucao_mensal_ticket_medio(df, 2026)
        assert ticket == {1: 9600.0, 2: 6400.0, 3: 4000.0}
        assert 4 not in ticket  # lacuna, nunca zero

    def test_agregado_por_dimensao_cliente(self, df):
        agg = metrics.agregado_por_dimensao(df, "CLIENTE")
        # CLIENTE A: 8000 (PI 1001) + 9600 (PI 1006) = 17600, líder do ranking
        assert agg.iloc[0]["CLIENTE"] == "CLIENTE A"
        assert agg.iloc[0]["valor"] == pytest.approx(17600.0)
        # Pipeline e cancelados fora: CLIENTE Z não aparece
        assert "CLIENTE Z" not in set(agg["CLIENTE"])

    def test_agregado_por_dimensao_veta_veiculo_isolado(self, df):
        """Decisão 15: veículo nunca é agregado isoladamente."""
        with pytest.raises(ValueError):
            metrics.agregado_por_dimensao(df, "VEICULO")


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

    def test_alerta_2_sem_status_com_valor_financeiro(self, df):
        alerta = quality_checks.linhas_sem_status(df)
        assert alerta.quantidade == 1
        assert alerta.detalhes["valor_bruto"] == pytest.approx(1000.0)
        assert alerta.detalhes["valor_liquido"] == pytest.approx(800.0)

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

    def test_alerta_5_cancelado_com_valor(self, df):
        alerta = quality_checks.cancelado_bonificado_com_valor(df)
        assert alerta.quantidade == 1
        assert alerta.detalhes["valor_bruto"] == pytest.approx(17172.0)
        assert set(alerta.linhas["PI"]) == {"1011"}

    def test_alertas_nao_alteram_os_dados(self, df):
        copia = df.copy(deep=True)
        quality_checks.executar_todas(df)
        pd.testing.assert_frame_equal(df, copia)

    def test_executar_todas_retorna_os_5_alertas(self, df):
        alertas = quality_checks.executar_todas(df)
        assert [a.codigo for a in alertas] == ["1", "2", "3", "4", "5"]
