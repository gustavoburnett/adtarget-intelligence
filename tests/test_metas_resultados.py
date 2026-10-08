"""Integração da nova página com Streamlit e engine, usando fontes sintéticas."""

import datetime as dt
import re
from decimal import Decimal
from html import unescape

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from src.data.cleaning import (
    COL_GRUPO,
    COL_MES_GANHO_DATA,
    COL_MES_VEICULACAO_DATA,
    COL_STATUS,
    COL_VALOR_BRUTO,
    COL_VALOR_LIQUIDO,
    COL_VEICULO,
)
from src.data.loader import COL_ANO_ABA
from src.data.metas_schema import COLUNAS_METAS, ErroDeMetas

REF = dt.date(2026, 3, 15)


def _meta(mes=1, valor=100, **extras):
    registro = {
        "NIVEL_META": "GRUPO", "GRUPO": "G", "VEICULO": "",
        "ANO": 2026, "MES": mes, "VALOR_META": valor, "ATIVO": "SIM",
        "REVISAO": 1, "CRIADO_EM": "2026-01-01T00:00:00-03:00", "MOTIVO": "Teste",
    }
    registro.update(extras)
    return registro


def _metas(*registros):
    return pd.DataFrame(registros, columns=COLUNAS_METAS)


def _plano(valor=100):
    return _metas(*[_meta(mes, valor) for mes in range(1, 13)])


def _venda(data="2026-01-01", valor=50, grupo="G", status="FATURADO"):
    return {
        COL_GRUPO: grupo, COL_VEICULO: "V", COL_STATUS: status,
        COL_VALOR_LIQUIDO: valor, COL_VALOR_BRUTO: valor * 10,
        COL_MES_VEICULACAO_DATA: pd.Timestamp(data),
        COL_MES_GANHO_DATA: pd.Timestamp(data), COL_ANO_ABA: int(data[:4]),
    }


def _vendas(*registros):
    df = pd.DataFrame(registros, columns=list(_venda()))
    for coluna in (COL_MES_VEICULACAO_DATA, COL_MES_GANHO_DATA):
        df[coluna] = pd.to_datetime(df[coluna])
    return df


def _base(atual=100, anterior=50):
    return _vendas(*[
        _venda(f"{ano}-{mes:02d}-01", valor)
        for ano, valor in ((2026, atual), (2025, anterior)) for mes in (1, 2)
    ])


def _executar_pagina(vendas, plano, referencia, erro):
    from pages_content.metas_resultados import render
    render(vendas, plano, data_referencia=referencia, erro_metas=erro)


def _pagina(vendas=None, plano=None, *, referencia=REF, ano=2026, erro=None):
    app = AppTest.from_function(
        _executar_pagina,
        args=(_base() if vendas is None else vendas, _plano() if plano is None else plano, referencia, erro),
    )
    app.session_state["metas_ano"] = ano
    app.run(timeout=10)
    assert not app.exception
    return app


def _html(app):
    return "\n".join(elemento.value for elemento in app.markdown)


def _conteudo(app):
    return "\n".join(
        elemento.value
        for tipo in (app.markdown, app.caption, app.error, app.info)
        for elemento in tipo
    )


def test_hero_atingimento_monetarios_periodo_e_like_for_like():
    app = _pagina()
    html = _html(app)
    assert "RITMO FECHADO" in html
    assert "FECHADO ATÉ FEV/2026" in html
    assert "100,0%" in html
    assert "Jan a Fev/2026" in html and "Jan a Fev/2025" in html
    assert "Realizado YTD no perímetro de metas" in html
    assert "YoY no perímetro de metas" in html and "+100,0% YoY" in html
    assert "no mesmo perímetro" in html
    assert 'title="R$ 200,00"' in html and 'title="R$ 100,00"' in html


def test_meta_anual_e_projecao_sao_leituras_distintas():
    html = _html(_pagina())
    for titulo in ("META ANUAL · 2026", "GAP COMERCIAL", "NECESSIDADE COMERCIAL", "PLANO FUTURO", "FORECAST"):
        assert titulo in html
    assert 'title="R$ 1.200,00"' in html  # Meta anual e forecast
    assert 'Meta anual já vendida</span><strong>16,7%' in html
    assert 'class="atg-metas-annual-gap atg-metas-neutral"><span class="num" title="R$ 1.000,00"' in html
    assert "ainda precisam ser vendidos" in html
    assert 'title="R$ 100,00">R$ 100,00</span>/mês' in html
    assert "Quanto ainda precisamos conquistar por mês até dezembro" in html
    assert "Mar a Dez/2026" in html
    assert "Run rate simples" in html and "100,0% da meta" in html
    assert "0,0% já cobertos por vendas fechadas" in html
    assert "Para atingir a meta anual, ainda precisamos conquistar" in html
    assert html.index("NECESSIDADE COMERCIAL") < html.index("FORECAST") < html.index("PLANO FUTURO")


@pytest.mark.parametrize("atual,rotulo,classe", [
    (150, "Superávit YTD", "positive"),
    (50, "Déficit YTD", "negative"),
    (100, "Saldo YTD", "neutral"),
])
def test_saldo_ytd_rotulo_magnitude_e_semantica(atual, rotulo, classe):
    html = _html(_pagina(vendas=_base(atual=atual)))
    assert re.search(
        re.escape(rotulo) + r'</div><div class="atg-metas-support-value atg-metas-' + classe + r'">',
        html,
    )
    assert ">-R$" not in html


@pytest.mark.parametrize("atual,texto,classe", [
    (100, '<span class="num" title="R$ 1.000,00"', "neutral"),
    (700, "Meta superada em ", "positive"),
    (600, "Meta anual atingida", "neutral"),
])
def test_gap_positivo_neutro_superado_positivo_e_atingido(atual, texto, classe):
    html = _html(_pagina(vendas=_base(atual=atual)))
    assert f'GAP COMERCIAL</div><div class="atg-metas-annual-gap atg-metas-{classe}">{texto}' in html
    if atual >= 600:
        assert "O plano futuro cobre" not in html
        assert "de cobertura do plano" not in html
        assert "Quanto ainda precisamos conquistar por mês até dezembro" not in html
        assert "Meta anual já superada" in html if atual > 600 else "Meta anual já atingida" in html


def test_perimetro_exclui_entidades_e_mes_aberto_sem_mudar_vendas():
    vendas = pd.concat([
        _base(),
        _vendas(_venda(valor=9999, grupo="FORA"), _venda("2026-03-01", valor=9999)),
    ], ignore_index=True)
    original = vendas.copy(deep=True)
    plano = _plano()
    original_plano = plano.copy(deep=True)
    html = _html(_pagina(vendas=vendas, plano=plano))
    hero = re.search(r'<section class="atg-card atg-metas-hero".*?</section>', html).group()
    assert "100,0%" in hero and "+100,0% YoY" in hero
    assert "9,99 mil" not in hero
    assert 'title="R$ 9.999,00"' in html  # Carteira aparece no módulo anual, sem entrar no Hero.
    pd.testing.assert_frame_equal(vendas, original)
    pd.testing.assert_frame_equal(plano, original_plano)


def test_ano_sem_metas_nao_inventa_zero_ou_projecao():
    app = _pagina(ano=2025)
    html = _html(app)
    assert "Sem meta lançada para o período" in html
    assert "Não há metas cadastradas para 2025" in html
    for titulo in ("RITMO FECHADO", "META ANUAL ·", "GAP COMERCIAL", "NECESSIDADE COMERCIAL", "FORECAST", "Metas por parceiro"):
        assert titulo not in html
    assert not app.expander
    assert 'title="R$ 0,00"' not in html


def test_janeiro_sem_falso_realizado_saldo_yoy_ou_forecast():
    html = _html(_pagina(referencia=dt.date(2026, 1, 31)))
    assert "Aguardando o primeiro mês encerrado" in html
    assert "META ANUAL · 2026" in html and 'title="R$ 1.200,00"' in html
    assert "Dados insuficientes" in html
    assert "Realizado YTD no perímetro de metas</div>" not in html
    assert "Déficit YTD" not in html and "Superávit YTD" not in html
    assert "YoY no perímetro de metas" not in html
    assert "Run rate simples · Realizado YTD" not in html
    assert "O plano futuro cobre" not in html


def test_apenas_um_mes_encerrado_suprime_forecast_e_percentual_projetado():
    html = _html(_pagina(referencia=dt.date(2026, 2, 1)))
    assert "Jan a Jan/2026" in html and "Dados insuficientes" in html
    assert "disponível após dois meses encerrados" in html
    assert "Run rate simples · Realizado YTD" not in html


def test_meta_ytd_zero_preserva_moeda_mas_nao_exibe_percentuais():
    plano = _metas(*[_meta(mes, 0 if mes <= 2 else 100) for mes in range(1, 13)])
    html = _html(_pagina(plano=plano))
    assert "Sem meta lançada para o período" in html
    assert 'title="R$ 200,00"' in html
    assert "Superávit YTD" in html  # Zero ativo mantém o realizado no perímetro.
    assert "da meta anual conquistada" not in html
    assert "projetado de atingimento" not in html
    assert "de cobertura do plano" not in html
    assert "O plano futuro cobre" not in html


def test_meta_anual_zero_sem_divisao_ou_percentuais_inventados():
    html = _html(_pagina(plano=_plano(0)))
    assert "Sem meta lançada para o período" in html
    assert "Meta superada em" in html
    assert "da meta anual conquistada" not in html
    assert "projetado de atingimento" not in html
    assert "O plano futuro cobre" not in html
    assert "nan" not in html.lower() and "infinity" not in html.lower()


@pytest.mark.parametrize("anterior", [0, None])
def test_yoy_zero_ou_ausente_nao_inventa_comparativo(anterior):
    vendas = _base(anterior=0) if anterior == 0 else _vendas(_venda(), _venda("2026-02-01"))
    html = _html(_pagina(vendas=vendas))
    assert "Sem base de comparação" in html
    assert "+100,0% YoY" not in html and "-100,0% YoY" not in html


def test_ano_encerrado_mostra_resultado_final_e_suprime_projecoes():
    html = _html(_pagina(referencia=dt.date(2027, 1, 1)))
    assert "Jan a Dez/2026" in html and "Resultado final do ano" in html
    assert html.count('class="atg-metas-state atg-metas-neutral">Ano encerrado') == 3
    assert "/mês" not in html and "O plano futuro cobre" not in html
    assert "projetado de atingimento" not in html
    assert "Dados insuficientes" not in html


def test_alertas_zero_nao_criam_bloco_nem_texto_de_sucesso():
    app = _pagina()
    assert not app.expander
    assert "Alertas de Qualidade" not in _conteudo(app)
    assert "Nenhum alerta" not in _conteudo(app)


def test_alertas_retroativo_e_coexistencia_ano_selecionado():
    plano = _metas(
        *_plano().to_dict("records"),
        _meta(1, 120, REVISAO=2, CRIADO_EM="2026-02-01T00:00:00-03:00"),
        _meta(1, 10, NIVEL_META="VEICULO", VEICULO="V"),
    )
    app = _pagina(plano=plano)
    assert len(app.expander) == 1
    assert app.expander[0].label == "Alertas de Qualidade (2 ativos)"
    conteudo = _conteudo(app)
    assert "Revisões de metas após o encerramento do mês**: 1" in conteudo
    assert "Metas de Grupo e Veículo no mesmo grupo e mês**: 1" in conteudo
    assert "Linhas da aba METAS: 14" in conteudo
    assert "90,9%" in conteudo  # GRUPO120 + GRUPO100, sem somar VEICULO10.
    anterior = _pagina(plano=plano, ano=2025)
    assert not anterior.expander


def test_schema_invalido_expoe_linhas_sem_kpis_ou_conteudo_sensivel():
    plano = _metas(_meta(1, "VALOR_SENSIVEL"), _meta(2, -1))
    app = _pagina(plano=plano)
    assert len(app.error) == 1
    assert "2 linha(s) inválida(s)" in app.error[0].value
    assert "linha(s) 2, 3 da aba" in app.error[0].value
    assert "VALOR_SENSIVEL" not in _conteudo(app)
    assert "RITMO FECHADO" not in _conteudo(app)
    assert "Nenhum KPI de metas foi consolidado" in app.error[0].value


@pytest.mark.parametrize("categoria", ["fonte", "estrutura", "validacao"])
def test_erro_do_loader_isolado_sem_mensagem_raw_stop_ou_kpis(categoria):
    erro = ErroDeMetas("TOKEN_SENSIVEL E DADOS COMERCIAIS", categoria=categoria)
    app = _pagina(erro=erro)
    assert len(app.error) == 1
    assert "As demais páginas continuam disponíveis" in app.error[0].value
    assert "TOKEN_SENSIVEL" not in _conteudo(app)
    assert "RITMO FECHADO" not in _conteudo(app)
    assert "Para vendas totais, consultar Performance Comercial" in _conteudo(app)


def test_metas_none_e_erro_amigavel_nao_sem_metas_lancadas():
    app = AppTest.from_function(_executar_pagina, args=(_base(), None, REF, None)).run(timeout=10)
    assert not app.exception and len(app.error) == 1
    assert "Não foi possível carregar ou validar a aba METAS" in app.error[0].value
    assert "Não há metas cadastradas" not in _conteudo(app)


def test_sem_vendas_disponiveis_nao_quebra_filtro_de_ano():
    app = _pagina(vendas=_vendas())
    assert len(app.info) == 1
    assert "Sem dados de vendas disponíveis" in app.info[0].value


def test_rodape_e_valores_completos_preservam_metodologia_e_precisao():
    html = _html(_pagina(vendas=_base(atual=123.455)))
    assert 'title="R$ 246,91"' in html  # Arredondamento somente na apresentação.
    for texto in ("Vendas Líquidas", "mês de veiculação", "somente meses encerrados", "entidades com meta ativa no mês", "sem sazonalidade", "Para vendas totais, consultar Performance Comercial"):
        assert texto in html
    assert "plotly" not in html.lower()


def test_css_especifico_reutiliza_tokens_e_responsividade_sem_efeito_global():
    from pages_content.metas_resultados import _CSS
    from src.components.metas_styles import CSS_METAS
    from src.components.partner_logos import CSS_PARTNER_LOGOS

    # Uma única fonte de estilos; marca e semântica usam os tokens aprovados.
    assert _CSS == CSS_METAS.replace("</style>", CSS_PARTNER_LOGOS + "</style>")
    assert "var(--atg-brand)" in _CSS
    assert re.search(r'\.st-key-design_metas_content \.atg-metas-positive\s*\{color:var\(--atg-positive\)', _CSS)
    assert re.search(r'\.st-key-design_metas_content \.atg-metas-negative\s*\{color:var\(--atg-negative\)', _CSS)
    assert "background:var(--atg-surface-card)" in _CSS
    assert "border:1px solid var(--atg-line-card)" in _CSS
    for responsivo in (
        "@container atg-metas-partners (width < 1040px)",
        "@container atg-metas-content (width < 700px)",
        "@container atg-metas-partners (width < 480px)",
        "@media(max-width:640px)",
    ):
        assert responsivo in _CSS
    assert "grid-template-columns:minmax(0,1fr)" in _CSS
    assert "overflow-wrap:anywhere" in _CSS
    assert "min-width:0" in _CSS and "font-variant-numeric:tabular-nums" in _CSS
    assert "stSidebar" not in _CSS and "design_performance_" not in _CSS
    texto = re.sub(r'/\*.*?\*/', '', _CSS, flags=re.DOTALL).replace('<style>', '').replace('</style>', '')
    for seletor, _ in re.findall(r'([^{}]+)\{([^{}]*)\}', texto):
        assert '.st-key-design_metas_' in seletor or '.atg-metas.atg-metas-partner-section' in seletor
        if 'stMain' in seletor:
            assert '[data-testid="stMainBlockContainer"]:has(.st-key-design_metas_header)' in seletor


def test_percentual_da_engine_ja_esta_em_pontos_percentuais():
    from pages_content.metas_resultados import _pct
    assert _pct(Decimal("67.843878")) == "67,8%"
    assert _pct(Decimal("-3.25"), sinal=True) == "-3,3%"


def test_pulso_e_gap_comercial_incluem_carteira_sem_alterar_hero():
    vendas = pd.concat([_base(), _vendas(_venda("2026-04-01", 300))], ignore_index=True)
    app = _pagina(vendas=vendas)
    html = _html(app)
    hero = re.search(r'<section class="atg-card atg-metas-hero".*?</section>', html).group()
    assert "100,0%" in hero and 'title="R$ 200,00"' in hero
    assert 'Meta anual já vendida</span><strong>41,7%' in html
    assert 'title="R$ 500,00"' in html
    assert 'class="atg-metas-annual-gap atg-metas-neutral"><span class="num" title="R$ 700,00"' in html
    assert 'title="R$ 70,00">R$ 70,00</span>/mês' in html
    assert "30,0% já cobertos por vendas fechadas" in html
    assert 'class="atg-card atg-metas-band"' in html
    assert "O plano futuro cobre" not in html


def test_graficos_integrados_e_hierarquia_antes_dos_parceiros():
    app = _pagina()
    html = _html(app)
    assert len(app.get("plotly_chart")) == 2
    titulos = ["FECHADO ATÉ", "META ANUAL ·", "GAP COMERCIAL", "Projeção",
               "Evolução Mensal", "Evolução Acumulada", "Metas por parceiro"]
    posicoes = [html.index(titulo) for titulo in titulos]
    assert posicoes == sorted(posicoes)
    assert "Realizado nos meses encerrados · Já vendido" in html


def test_parceiro_status_ytd_visivel_e_detalhes_acessiveis_sem_hover():
    vendas = pd.concat([_base(atual=90), _vendas(_venda("2026-12-01", 1000))], ignore_index=True)
    html = _html(_pagina(vendas=vendas))
    parceiro = re.search(r'<article class="atg-metas-partner".*?</article>', html).group()
    essencial = re.split(r'<details\b', parceiro, maxsplit=1)[0]
    fallback = re.search(r'<span class="atg-partner-logo-fallback">(.*?)</span>', essencial)
    assert fallback is not None and unescape(fallback.group(1)) == "G"
    assert 'aria-label="G"' in essencial and "≈ No ritmo" in essencial
    assert "90,0%" in essencial
    assert 'title="R$ 180,00"' in essencial and 'title="R$ 200,00"' in essencial
    summary = re.search(r'<details\b[^>]*><summary\b[^>]*>(.*?)</summary>', parceiro, re.DOTALL)
    assert summary is not None
    # A seta decorativa indica aberto/fechado; o nome do controle permanece.
    acessivel = re.sub(r'<[^>]+aria-hidden="true"[^>]*>.*?</[^>]+>', '', summary.group(1))
    assert unescape(re.sub(r'<[^>]+>', '', acessivel)).strip() == "Compromisso anual e saldo"
    assert "98,3%" in parceiro  # Annual commitment does not classify the closed rhythm.
    assert "Déficit YTD" in parceiro and 'title="R$ 20,00"' in parceiro
    assert 'title="R$ 1.000,00"' in parceiro


def test_ranking_parceiros_por_atingimento_e_escape_de_entidades():
    metas = _metas(*[_meta(m, 100, GRUPO=g) for g in ("A<script>", "B") for m in range(1, 13)])
    vendas = _vendas(_venda(valor=20, grupo="A<script>"), _venda(valor=220, grupo="B"))
    html = _html(_pagina(vendas=vendas, plano=metas))
    assert html.index('aria-label="B"') < html.index('aria-label="A&lt;SCRIPT&gt;"')
    assert "✓ Acima do ritmo" in html and "↓ Abaixo do ritmo" in html
    assert "<SCRIPT>" not in html


def test_ano_sem_meta_suprime_graficos_e_lista_parceiros():
    app = _pagina(ano=2025)
    assert not app.get("plotly_chart")
    assert "Metas por parceiro" not in _html(app)
