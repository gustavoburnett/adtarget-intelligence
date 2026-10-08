"""Design 1D: contratos funcionais comparados ao checkpoint local 1B/1C.

Todos os dados são sintéticos. CSS e dimensões reais são conferidos no
navegador; estes testes verificam conteúdo, séries e interação nativa.
"""

from contextlib import nullcontext
from copy import deepcopy
import datetime as dt
from functools import lru_cache
import json
import subprocess
from types import ModuleType
import xml.etree.ElementTree as ET

import pandas as pd
import pytest
import streamlit as st

from src.components import cards, charts, metas_charts
from src.data import cleaning
from tests.test_performance_meta import _alternar, _figuras, _isolamento, _pagina
from tests.test_performance_meta_chart import _meta, _resultados, _venda
from tests.test_radar import avaliar, frame, linha, recorde


CHECKPOINT_1BC = "b61b362dc5bd3af7acfe341d2ab377257f30066a"


@lru_cache
def _checkpoint(arquivo):
    """Carrega a implementação congelada, sem alterar módulos da aplicação."""
    fonte = subprocess.run(
        ["git", "show", f"{CHECKPOINT_1BC}:{arquivo}"],
        check=True, capture_output=True, text=True,
    ).stdout
    modulo = ModuleType("checkpoint_1bc_" + arquivo.replace("/", "_").replace(".", "_"))
    exec(compile(fonte, f"<{CHECKPOINT_1BC}:{arquivo}>", "exec"), modulo.__dict__)
    return modulo


def _json(figura):
    # Plotly normaliza NaN como null, conservando lacunas em ambos os lados.
    return json.loads(figura.to_json())


def _contrato_figura(figura, *, meta=False):
    """Campos funcionais; cores, fontes e espessuras podem ser redesenhadas."""
    traces = []
    for serie in figura["data"]:
        contrato = {
            campo: serie.get(campo)
            for campo in (
                "type", "name", "x", "y", "mode", "customdata", "hovertemplate",
                "hoverinfo", "connectgaps", "showlegend", "orientation",
            )
        }
        contrato["dash"] = serie.get("line", {}).get("dash")
        if meta:
            contrato["symbol"] = serie.get("marker", {}).get("symbol")
            if serie.get("name") == "Já vendido acumulado":
                tamanhos = serie["marker"]["size"]
                contrato["ancora_oculta"] = [tamanho == 0 for tamanho in tamanhos]
        traces.append(contrato)
    layout = figura["layout"]
    eixos = {
        eixo: {
            campo: layout.get(eixo, {}).get(campo)
            for campo in (
                "type", "range", "autorange", "rangemode", "tickmode", "tickvals",
                "ticktext", "tickformat", "fixedrange",
            )
        }
        for eixo in ("xaxis", "yaxis")
    }
    return {"series": traces, "eixos": eixos, "hovermode": layout.get("hovermode")}


def _capturar_hero(monkeypatch, modulo, aba, dados, limite):
    recebidas = []
    with monkeypatch.context() as contexto:
        contexto.setattr(st, "plotly_chart", lambda fig, **kwargs: recebidas.append(fig))
        funcao = modulo.grafico_hero_vendas if aba == "Vendas" else modulo.grafico_hero_ticket
        funcao(dados, 2026, limite)
    assert len(recebidas) == 1
    return _json(recebidas[0])


def _meta_checkpoint(monkeypatch, resultado, pulso):
    # A implementação congelada importa este helper dentro da função.
    # A troca temporária garante que sua figura use também o estilo antigo.
    with monkeypatch.context() as contexto:
        contexto.setattr(charts, "_aplicar_estilo_hero",
                         _checkpoint("src/components/charts.py")._aplicar_estilo_hero)
        return _json(_checkpoint("src/components/metas_charts.py").evolucao_performance_meta(resultado, pulso))


SERIES = {
    "lacunas": [100, 200, None, 400, 50, None, 280, 230, 180, None, None, None],
    "futuro_vendido": [100, 200, 300, 400, 50, 20, 280, 230, 180, 220, 240, 260],
    "vazia": [None] * 12,
    "negativos": [-100, 200, -300, 400, -50, 20, -280, 230, -180, None, None, None],
    "zero": [0] * 12,
    "um_ponto": [None, None, 123.45] + [None] * 9,
}


@pytest.mark.parametrize("aba", ["Vendas", "Ticket Médio"])
@pytest.mark.parametrize("limite", [None, 10])
@pytest.mark.parametrize("estado", SERIES)
def test_vendas_ticket_preservam_series_lacunas_hover_e_escalas_do_checkpoint(
    monkeypatch, aba, limite, estado,
):
    valores = SERIES[estado]
    if aba == "Vendas":
        dados = pd.DataFrame(
            {"atual": valores, "anterior": [60, None, 100, 0, 150, None, 160, 50, 80, None, None, None]},
            index=pd.Index(range(1, 13), name="mes"), dtype=float,
        )
        copia = dados.copy(deep=True)
    else:
        dados = {mes: float(valor) for mes, valor in enumerate(valores, 1) if valor is not None}
        copia = deepcopy(dados)
    antes = _capturar_hero(monkeypatch, _checkpoint("src/components/charts.py"), aba, dados, limite)
    depois = _capturar_hero(monkeypatch, charts, aba, dados, limite)
    assert _contrato_figura(depois) == _contrato_figura(antes)
    if isinstance(dados, pd.DataFrame):
        pd.testing.assert_frame_equal(dados, copia)
    else:
        assert dados == copia
    for serie in depois["data"]:
        assert serie.get("line", {}).get("shape", "linear") == "linear"
    if estado == "futuro_vendido":
        principal = next(s for s in depois["data"] if s.get("name", "").startswith("2026"))
        assert principal["y"][-2:] == [240, 260]
        # A faixa do calendário não pode apagar registros de meses futuros.
        futuras = lambda fig: [a["text"] for a in fig["layout"].get("annotations", [])
                               if "sem dado disponível" in a.get("text", "")]
        if aba == "Ticket Médio":
            assert futuras(depois) == futuras(antes)
        else:
            assert not futuras(depois)
            assert any("meses futuros" in a.get("text", "")
                       for a in depois["layout"].get("annotations", [])) == (limite is not None)
    if limite is not None:
        faixas = depois["layout"].get("shapes", [])
        assert any(faixa["x0"] == limite + 0.5 and faixa["x1"] == 12.5 for faixa in faixas)


ESTADOS_META = {
    "atual": {},
    "encerrado": {"referencia": dt.date(2027, 1, 1)},
    "janeiro": {"referencia": dt.date(2026, 1, 15)},
    "futuro": {"ano": 2027},
    "meta_zero": {"plano": [_meta(mes, valor=0) for mes in range(1, 13)]},
    "sem_plano": {"plano": []},
    "sem_vendas": {"vendas": []},
    "sem_base_anterior": {"vendas": [_venda(1, 20)]},
    "negativos": {"vendas": [_venda(1, -10), _venda(10, -30), _venda(11, -40), _venda(12, -50)]},
    "fracionarios": {"vendas": [_venda(1, 0.011), _venda(10, 0.004), _venda(11, 0.004), _venda(12, 0.004)]},
}


@pytest.mark.parametrize("estado", ESTADOS_META)
def test_meta_preserva_exatamente_valores_hovers_e_distincao_temporal_do_checkpoint(monkeypatch, estado):
    resultado, pulso = _resultados(**ESTADOS_META[estado])
    copia = deepcopy((resultado, pulso))
    antes = _meta_checkpoint(monkeypatch, resultado, pulso)
    assert _json(metas_charts.evolucao_performance_meta(resultado, pulso)) == antes
    depois = _json(metas_charts.evolucao_performance_meta(resultado, pulso, design_performance=True))
    assert _contrato_figura(depois, meta=True) == _contrato_figura(antes, meta=True)
    assert (resultado, pulso) == copia
    andamento = [mes for mes in resultado.meses if mes.estado_mes == "em_andamento"]
    for mes in andamento:
        assert any(faixa["x0"] == mes.mes - 0.45 and faixa["x1"] == mes.mes + 0.45
                   and faixa["line"]["dash"] == "dash"
                   for faixa in depois["layout"].get("shapes", []))
    for serie in depois["data"]:
        assert serie.get("line", {}).get("shape", "linear") == "linear"
        if serie["name"] != "Já vendido acumulado":
            continue
        for mes, hover in zip(serie["x"], serie["customdata"], strict=True):
            if resultado.meses[mes - 1].estado_mes == "encerrado":
                continue  # A âncora da carteira conserva o hover oficial fechado.
            assert "Total já vendido acumulado:" in hover
            assert all(texto not in hover for texto in (
                "Realizado acumulado:", "Atingimento:", "Déficit:", "Superávit:", "YoY:",
            ))


@pytest.mark.parametrize("estado", ESTADOS_META)
def test_graficos_de_metas_resultados_fora_do_escopo_permanecem_integrais(estado):
    resultado, pulso = _resultados(**ESTADOS_META[estado])
    baseline = _checkpoint("src/components/metas_charts.py")
    assert _json(metas_charts.evolucao_acumulada(resultado)) == _json(baseline.evolucao_acumulada(resultado))
    assert _json(metas_charts.evolucao_mensal(resultado, pulso)) == _json(baseline.evolucao_mensal(resultado, pulso))


def test_barra_horizontal_fora_do_escopo_permanece_integral(monkeypatch):
    dados = pd.DataFrame({"nome": ["Um", "Dois"], "valor": [100, 90]})
    copia = dados.copy(deep=True)
    figuras = []
    monkeypatch.setattr(st, "plotly_chart", lambda figura, **kwargs: figuras.append(_json(figura)))
    _checkpoint("src/components/charts.py").grafico_barra_horizontal(dados, "nome", "valor", "Ranking")
    charts.grafico_barra_horizontal(dados, "nome", "valor", "Ranking")
    assert len(figuras) == 2 and figuras[0] == figuras[1]
    pd.testing.assert_frame_equal(dados, copia)


def _dados_radar(quantidade):
    if quantidade == 0:
        return frame(linha("2025-01-01", 100), linha("2026-01-01", 100))
    if quantidade == 1:
        return frame(linha("2025-01-01", 100, "<Grupo & Parceiro> +"),
                     linha("2026-01-01", 120, "<Grupo & Parceiro> +"))
    extras = frame(linha("2025-01-01", 100, "Queda"), linha("2026-01-01", 80, "Queda"),
                   linha("2025-09-01", 100, "Crescimento"), linha("2026-09-01", 200, "Crescimento"))
    return extras if quantidade == 2 else pd.concat([recorde(300), extras], ignore_index=True)


def _radar_html(monkeypatch, modulo, estado):
    html, captions = [], []
    with monkeypatch.context() as contexto:
        contexto.setattr(st, "container", lambda **kwargs: nullcontext())
        contexto.setattr(st, "markdown", lambda valor, **kwargs: html.append(valor))
        contexto.setattr(st, "caption", captions.append)
        modulo.render_radar(estado)
    return [ET.fromstring(valor) for valor in html], captions


def _com_classe(raizes, classe):
    return [elemento for raiz in raizes for elemento in raiz.iter()
            if classe in elemento.get("class", "").split()]


def _copy_radar(raizes, captions):
    classes = ("atg-radar-title", "atg-radar-meta", "atg-radar-category",
               "atg-radar-headline", "atg-radar-context", "atg-radar-cta")
    return {
        classe: [("".join(elemento.itertext()), elemento.get("title"))
                 for elemento in _com_classe(raizes, classe)]
        for classe in classes
    }, captions


@pytest.mark.parametrize("quantidade", [0, 1, 2, 3])
def test_radar_dinamico_preserva_quantidade_ordem_copy_e_sincronizacao(monkeypatch, quantidade):
    dados = _dados_radar(quantidade)
    copia_dados = dados.copy(deep=True)
    estado = avaliar(dados, sincronizado_em=dt.datetime(2026, 9, 18, 12, 30))
    copia_estado = deepcopy(estado)
    assert len(estado.insights) == quantidade
    antigas, captions_antigas = _radar_html(monkeypatch, _checkpoint("src/components/cards.py"), estado)
    atuais, captions_atuais = _radar_html(monkeypatch, cards, estado)
    copy_atual, _ = _copy_radar(atuais, captions_atuais)
    copy_antiga, _ = _copy_radar(antigas, captions_antigas)
    # Hardening autoriza nome integral e períodos explícitos; título, metadados,
    # CTA, sincronização e referência técnica continuam protegidos.
    for classe in ("atg-radar-title", "atg-radar-meta", "atg-radar-cta"):
        assert copy_atual[classe] == copy_antiga[classe]
    assert captions_atuais == captions_antigas
    assert [titulo for _, titulo in copy_atual["atg-radar-context"]] == [
        titulo for _, titulo in copy_antiga["atg-radar-context"]
    ]
    itens = _com_classe(atuais, "atg-radar-item")
    assert len(itens) == quantidade
    assert [item.get("data-radar-kind") for item in itens] == [insight.tipo for insight in estado.insights]
    for item, insight in zip(itens, estado.insights, strict=True):
        for classe in ("atg-radar-category", "atg-radar-headline", "atg-radar-context", "atg-radar-cta"):
            assert len(_com_classe([item], classe)) == 1
        if insight.tipo == "destaque":
            antigo = _com_classe(antigas, "atg-radar-item")[[i.tipo for i in estado.insights].index("destaque")]
            assert _copy_radar([item], []) == _copy_radar([antigo], [])
    assert "Última sincronização com a fonte: 18/09/2026 12:30" in captions_atuais
    for item in itens:
        assert not any(elemento.tag in ("a", "button", "input") for elemento in item.iter())
        icones = _com_classe([item], "atg-radar-icon")
        assert len(icones) == 1
        svg = icones[0].find("svg")
        assert svg is not None
        assert svg.get("fill") == "none" and svg.get("stroke") == "currentColor"
        assert svg.get("aria-hidden") == "true" and svg.get("focusable") == "false"
    if quantidade:
        composicao = _com_classe(atuais, "atg-radar")
        assert len(composicao) == 1
        classe = {1: "atg-radar-single", 2: "atg-radar-two", 3: "atg-radar-three"}[quantidade]
        assert classe in composicao[0].get("class").split()
    assert estado == copia_estado
    pd.testing.assert_frame_equal(dados, copia_dados)


def _kpis_rankings(app):
    return [elemento.value for elemento in app.markdown if any(
        classe in elemento.value for classe in ('class="atg-kpi-row"', 'class="atg-card atg-rank"')
    )]


@pytest.fixture
def _relogio_performance(monkeypatch):
    yield from _isolamento.__wrapped__(monkeypatch)


@pytest.mark.parametrize("destino", ["Vendas", "Ticket Médio"])
@pytest.mark.parametrize("valor,criterio,grupos", [
    ("Valor Líquido", "Mês (Veiculação)", None),
    ("Valor Bruto", "Mês (Veiculação)", ["G"]),
    ("Valor Líquido", "Mês (Ganho)", ["H"]),
    ("Valor Bruto", "Mês (Ganho)", []),
])
def test_meta_roundtrip_preserva_kpis_rankings_fontes_e_restauracao_dos_quatro_recortes(
    _relogio_performance, destino, valor, criterio, grupos,
):
    app, vendas = _pagina(aba=destino, valor=valor, criterio=criterio, grupos=grupos)
    assert not app.exception
    copia = vendas.copy(deep=True)
    blocos = _kpis_rankings(app)
    figuras = [_contrato_figura(figura) for figura in _figuras(app)]
    assert len(blocos) == 4
    assert [aba.label for aba in app.tabs] == ["Vendas", "Ticket Médio", "Meta"]
    _alternar(app, "Meta")
    assert not app.exception
    for chave, fixo in (("performance_meta_valor", "Valor Líquido"),
                        ("performance_meta_mes", "Mês (Veiculação)")):
        controle = app.button_group(key=chave)
        assert controle.proto.disabled and controle.value == fixo
    assert _kpis_rankings(app) == blocos
    _alternar(app, destino)
    assert not app.exception
    assert app.button_group(key="perf_valor").value == valor
    assert app.button_group(key="perf_mes").value == criterio
    assert not app.button_group(key="perf_valor").proto.disabled
    assert not app.button_group(key="perf_mes").proto.disabled
    if grupos is not None:
        assert app.session_state[f"perf_fc_{cleaning.COL_GRUPO}_aplicado"] == grupos
    assert [_contrato_figura(figura) for figura in _figuras(app)] == figuras
    assert _kpis_rankings(app) == blocos
    pd.testing.assert_frame_equal(vendas, copia)
