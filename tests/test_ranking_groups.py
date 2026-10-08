"""Top 5 Grupos: consolidação e comparações sobre a base oficial de Vendas."""

import datetime as dt

import pandas as pd
import pytest

from src.components.ranking_data import linhas_ranking_grupos
from src.data import metrics
from src.data.cleaning import COL_GRUPO, limpar_dataframe

HOJE = dt.date(2026, 7, 15)
MESES = (
    "JANEIRO", "FEVEREIRO", "MARÇO", "ABRIL", "MAIO", "JUNHO",
    "JULHO", "AGOSTO", "SETEMBRO", "OUTUBRO", "NOVEMBRO", "DEZEMBRO",
)


def _linha(
    grupo, veiculo="VEÍCULO", liquido=100, *, bruto=None, ano=2026,
    mes=1, ganho=None, status="FATURADO", pi="PI SINTÉTICA",
):
    ganho_ano, ganho_mes = ganho if ganho is not None else (ano, mes)
    return {
        "GRUPO": grupo,
        "VEICULO": veiculo,
        "PI": pi,
        "STATUS": status,
        "VALOR PI LIQUIDO": liquido,
        "VALOR PI BRUTO": bruto if bruto is not None else liquido * 2,
        "MÊS (VEICULAÇÃO)": f"{MESES[mes - 1]}/{ano}",
        "MÊS (GANHO)": f"{MESES[ganho_mes - 1]}/{ganho_ano}",
    }


def _dados(*linhas):
    return limpar_dataframe(pd.DataFrame(linhas))


def _ranking(df, *, ano=2026, valor="liquido", criterio_mes="veiculacao", hoje=HOJE):
    df_ano = df[df[metrics.coluna_mes(criterio_mes)].dt.year == ano]
    return linhas_ranking_grupos(df_ano, df, ano, valor, criterio_mes, hoje)


def test_disney_consolida_disney_plus_espn_e_todos_os_outros_veiculos():
    df = _dados(
        _linha("DISNEY", "DISNEY+", 120),
        _linha("DISNEY", "ESPN", 80),
        _linha("DISNEY", "NATIONAL GEOGRAPHIC", 50),
        _linha("TEADS", "TEADS", 200),
        _linha("DISNEY", "DISNEY+", 50, ano=2025),
        _linha("DISNEY", "ESPN", 40, ano=2025),
        _linha("DISNEY", "NATIONAL GEOGRAPHIC", 10, ano=2025),
    )
    linhas = _ranking(df)
    assert [linha["nome"] for linha in linhas] == ["DISNEY", "TEADS"]
    assert linhas[0]["valor"] == 250
    assert linhas[0]["pct"] == pytest.approx(250 / 450 * 100)
    assert linhas[0]["tendencia"] == 150
    assert linhas[1]["valor"] == 200
    assert linhas[1]["pct"] == pytest.approx(200 / 450 * 100)
    assert linhas[1]["tendencia"] is None


def test_variacao_consolidada_nao_soma_variacoes_individuais():
    df = _dados(
        _linha("DISNEY", "DISNEY+", 200),
        _linha("DISNEY", "ESPN", 300),
        _linha("DISNEY", "DISNEY+", 100, ano=2025),
        _linha("DISNEY", "ESPN", 300, ano=2025),
    )
    linha = _ranking(df)[0]
    assert linha["valor"] == 500
    assert linha["tendencia"] == 25  # 500/400 − 1; não 100% + 0%.


def test_veiculo_homonimo_em_outro_grupo_nao_se_mistura():
    df = _dados(
        _linha("DISNEY", "93 FM", 200),
        _linha("MELODIA", "93 FM", 100),
    )
    assert [(linha["nome"], linha["valor"]) for linha in _ranking(df)] == [
        ("DISNEY", 200), ("MELODIA", 100),
    ]


def test_nome_oficial_limpo_define_grupo_sem_mapeamento_manual():
    df = _dados(
        _linha(" Disney ", "DISNEY+", 100),
        _linha("disney", "ESPN", 50),
        _linha("CARREGA +", "A", 30),
        _linha("CARREGA+", "B", 20),
    )
    assert [(linha["nome"], linha["valor"]) for linha in _ranking(df)] == [
        ("DISNEY", 150), ("CARREGA +", 30), ("CARREGA+", 20),
    ]


def test_cada_registro_entra_uma_vez_sem_join_ou_deduplicacao_nova_por_pi():
    # PIs repetidas em linhas distintas mantêm a mesma elegibilidade da baseline.
    df = _dados(
        _linha("DISNEY", "DISNEY+", 100, pi="MESMA PI"),
        _linha("DISNEY", "ESPN", 40, pi="MESMA PI"),
        _linha("DISNEY", "DISNEY+", 20, pi="OUTRA PI"),
        _linha("TEADS", "TEADS", 50, pi="PI TEADS"),
    )
    antes = df.copy(deep=True)
    linhas = _ranking(df)
    assert linhas[0]["valor"] == 160
    assert sum(linha["valor"] for linha in linhas) == metrics.vendas(df) == 210
    pd.testing.assert_frame_equal(df, antes)


@pytest.mark.parametrize("status,elegivel", [
    ("FATURADO", True), ("DIRETO", True), ("A VEICULAR", True),
    ("EM VEICULAÇÃO", True), ("CHECKING", True),
    ("AGUARD. DOC. VEÍCULO", True),
    ("CANCELADO", False), ("BONIFICADO", False),
    ("EM NEGOCIAÇÃO", False), ("", False),
])
def test_elegibilidade_permanece_a_mesma_da_base_oficial(status, elegivel):
    df = _dados(_linha("GRUPO", liquido=250, status=status))
    linhas = _ranking(df)
    if elegivel:
        assert linhas == [{"nome": "GRUPO", "valor": 250, "pct": 100, "tendencia": None}]
    else:
        assert linhas == []


def test_cancelamentos_e_bonificacoes_nao_afetam_totais_participacao_ou_yoy():
    df = _dados(
        _linha("DISNEY", "DISNEY+", 100),
        _linha("DISNEY", "ESPN", 900, status="CANCELADO"),
        _linha("DISNEY", "OUTRO", 500, status="BONIFICADO"),
        _linha("TEADS", liquido=100),
        _linha("DISNEY", liquido=50, ano=2025),
        _linha("DISNEY", liquido=400, ano=2025, status="CANCELADO"),
    )
    assert _ranking(df)[0] == {
        "nome": "DISNEY", "valor": 100, "pct": 50, "tendencia": 100,
    }


@pytest.mark.parametrize("quantidade", range(7))
def test_ate_cinco_grupos_reais_sem_posicoes_ficticias(quantidade):
    df = _dados(*[_linha(f"GRUPO {indice}", liquido=indice + 1)
                  for indice in range(7)])
    recorte = df.iloc[:quantidade]
    linhas = _ranking(recorte)
    assert len(linhas) == min(quantidade, 5)
    assert len({linha["nome"] for linha in linhas}) == len(linhas)
    assert {linha["nome"] for linha in linhas} <= set(recorte[COL_GRUPO])


def test_participacao_usa_todos_os_grupos_e_nao_apenas_os_cinco_primeiros():
    df = _dados(*[_linha(f"GRUPO {indice}", liquido=100)
                  for indice in range(6)])
    linhas = _ranking(df)
    assert [linha["nome"] for linha in linhas] == [f"GRUPO {indice}" for indice in range(5)]
    assert all(linha["pct"] == pytest.approx(100 / 600 * 100) for linha in linhas)
    assert sum(linha["pct"] for linha in linhas) == pytest.approx(500 / 600 * 100)


@pytest.mark.parametrize("semente", [1, 13, 37])
def test_empates_usam_nome_oficial_ascendente_independente_da_ordem_dos_registros(semente):
    df = _dados(
        _linha("TEADS", liquido=100), _linha("MELODIA", liquido=100),
        _linha("DISNEY", "DISNEY+", 40), _linha("DISNEY", "ESPN", 60),
    ).sample(frac=1, random_state=semente)
    assert [linha["nome"] for linha in _ranking(df)] == ["DISNEY", "MELODIA", "TEADS"]


@pytest.mark.parametrize("atual,anterior,esperado", [
    (150, 100, 50), (50, 100, -50), (100, 100, 0),
    (0, 100, -100), (100, 0, None), (0, 0, None),
])
def test_tendencia_preserva_sinal_zero_e_base_anterior_zero(atual, anterior, esperado):
    df = _dados(_linha("GRUPO", liquido=atual), _linha("GRUPO", liquido=anterior, ano=2025))
    assert _ranking(df)[0]["tendencia"] == esperado


def test_grupo_novo_sem_historico_nao_inventa_variacao():
    linha = _ranking(_dados(_linha("NOVO", liquido=120)))[0]
    assert linha["tendencia"] is None


def test_grupo_somente_anterior_nao_cria_posicao_com_venda_atual_ficticia():
    df = _dados(_linha("ATUAL", liquido=20), _linha("SOMENTE ANTERIOR", liquido=500, ano=2025))
    assert [linha["nome"] for linha in _ranking(df)] == ["ATUAL"]


def test_zero_real_permanece_zero_e_nao_vira_ausencia_de_registro():
    df = _dados(_linha("ZERO", liquido=0), _linha("ZERO", liquido=100, ano=2025))
    assert _ranking(df) == [{"nome": "ZERO", "valor": 0, "pct": 0, "tendencia": -100}]


def test_registro_so_futuro_preserva_ausencia_comparavel_da_tendencia_existente():
    df = _dados(
        _linha("FUTURO", liquido=100, mes=12),
        _linha("FUTURO", liquido=50, ano=2025),
    )
    linha = _ranking(df)[0]
    assert linha["valor"] == 100  # Valor anual existente, mesmo fora do YTD.
    assert linha["tendencia"] is None  # Sem registro atual na janela comparável.


@pytest.mark.parametrize("valor,ordem,totais,percentual", [
    ("liquido", ["DISNEY", "TEADS"], [150, 100], 100),
    ("bruto", ["TEADS", "DISNEY"], [500, 300], 200),
])
def test_metrica_selecionada_recalcula_valor_ordenacao_participacao_e_yoy(
    valor, ordem, totais, percentual,
):
    df = _dados(
        _linha("DISNEY", "DISNEY+", 100, bruto=200),
        _linha("DISNEY", "ESPN", 50, bruto=100),
        _linha("TEADS", liquido=100, bruto=500),
        _linha("DISNEY", liquido=75, bruto=100, ano=2025),
    )
    linhas = _ranking(df, valor=valor)
    assert [linha["nome"] for linha in linhas] == ordem
    assert [linha["valor"] for linha in linhas] == totais
    assert [linha["pct"] for linha in linhas] == pytest.approx([
        total / sum(totais) * 100 for total in totais
    ])
    disney = next(linha for linha in linhas if linha["nome"] == "DISNEY")
    assert disney["tendencia"] == percentual


@pytest.mark.parametrize("criterio_mes,valor,variacao", [
    ("veiculacao", 150, 200), ("ganho", 50, -100 * 2 / 3),
])
def test_criterio_temporal_selecionado_respeita_recorte_anual_e_comparacao(
    criterio_mes, valor, variacao,
):
    df = _dados(
        _linha("DISNEY", "DISNEY+", 100, ganho=(2025, 1)),
        _linha("DISNEY", "ESPN", 50),
        _linha("DISNEY", liquido=50, ano=2025),
    )
    linha = _ranking(df, criterio_mes=criterio_mes)[0]
    assert linha["valor"] == valor
    assert linha["tendencia"] == pytest.approx(variacao)


def test_ano_corrente_preserva_mes_atual_inclusivo_e_mesma_janela_anterior():
    df = _dados(
        _linha("GRUPO", liquido=100, mes=1),
        _linha("GRUPO", liquido=50, mes=7),
        _linha("GRUPO", liquido=850, mes=12),
        _linha("GRUPO", liquido=50, ano=2025, mes=1),
        _linha("GRUPO", liquido=50, ano=2025, mes=7),
        _linha("GRUPO", liquido=900, ano=2025, mes=12),
    )
    linha = _ranking(df)[0]
    assert linha["valor"] == 1_000
    assert linha["tendencia"] == 50  # Jan–Jul: 150 versus 100.


def test_ano_encerrado_compara_ano_completo_apesar_do_mes_atual():
    df = _dados(
        _linha("GRUPO", liquido=100, ano=2025, mes=1),
        _linha("GRUPO", liquido=500, ano=2025, mes=12),
        _linha("GRUPO", liquido=100, ano=2024, mes=1),
        _linha("GRUPO", liquido=200, ano=2024, mes=12),
    )
    linha = _ranking(df, ano=2025)[0]
    assert linha["valor"] == 600
    assert linha["tendencia"] == 100


def test_filtros_aplicados_preservam_total_e_comparacao_do_mesmo_recorte():
    df = _dados(
        _linha("DISNEY", "DISNEY+", 100), _linha("DISNEY", "ESPN", 50),
        _linha("TEADS", liquido=600),
        _linha("DISNEY", liquido=75, ano=2025),
        _linha("TEADS", liquido=300, ano=2025),
    )
    filtrado = df[df[COL_GRUPO] == "DISNEY"]
    assert _ranking(filtrado) == [{"nome": "DISNEY", "valor": 150, "pct": 100, "tendencia": 100}]


def test_chamada_padrao_usa_criterio_temporal_oficial():
    df = _dados(_linha("DISNEY", liquido=100), _linha("DISNEY", liquido=50, ano=2025))
    atual = df[df[metrics.coluna_mes(metrics.CRITERIO_MES_OFICIAL)].dt.year == 2026]
    assert linhas_ranking_grupos(atual, df, 2026, hoje=HOJE) == _ranking(df)
