"""Design 1F: contratos financeiros e interação contra o Design 1E congelado.

Estas fontes são sintéticas e offline. Não substituem a reconciliação com a
leitura real; teclado, toque e overflow são verificados no navegador.
"""

import ast
import datetime as dt
from decimal import Decimal
from functools import lru_cache
from html.parser import HTMLParser
from pathlib import Path
import subprocess
import re
from types import ModuleType
import xml.etree.ElementTree as ET

import pandas as pd
import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from pages_content import metas_resultados as pagina
from src.components import metas_charts
from src.data import cleaning, loader, metas, metas_loader
from src.data.metas_schema import ErroDeMetas, normalizar_entidade
from tests.test_metas_ux import _meta, _plano, _venda, _vendas
from tests.test_performance_meta import (
    APP, _figuras, _fonte_vendas, _isolamento, _pagina as _performance,
    _plano as _plano_performance,
)


CHECKPOINT_1E = "d2cfd2689dde5fa2c0ff81ec9cabafe741f765b3"
RAIZ = Path(__file__).resolve().parents[1]
REF = dt.date(2026, 10, 6)


@pytest.fixture(autouse=True)
def _relogio_e_cache(monkeypatch):
    yield from _isolamento.__wrapped__(monkeypatch)


@lru_cache
def _fonte_congelada(caminho):
    return subprocess.run(
        ["git", "show", f"{CHECKPOINT_1E}:{caminho}"],
        check=True, capture_output=True, text=True,
    ).stdout


@lru_cache
def _checkpoint(caminho="pages_content/metas_resultados.py"):
    modulo = ModuleType("design_1e_" + caminho.replace("/", "_").replace(".", "_"))
    exec(compile(_fonte_congelada(caminho), f"<{CHECKPOINT_1E}:{caminho}>", "exec"), modulo.__dict__)
    return modulo


class _HTML(HTMLParser):
    """DOM pequeno que aceita imagens HTML sem exigir sintaxe XML."""

    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self, texto):
        super().__init__(convert_charrefs=True)
        self.raiz = ET.Element("root")
        self.pilha = [self.raiz]
        self.feed(texto)

    def handle_starttag(self, tag, attrs):
        elemento = ET.SubElement(self.pilha[-1], tag, dict(attrs))
        if tag not in self.VOID:
            self.pilha.append(elemento)

    def handle_startendtag(self, tag, attrs):
        ET.SubElement(self.pilha[-1], tag, dict(attrs))

    def handle_endtag(self, tag):
        assert self.pilha[-1].tag == tag
        self.pilha.pop()

    def handle_data(self, texto):
        atual = self.pilha[-1]
        if len(atual):
            ultimo = atual[-1]
            ultimo.tail = (ultimo.tail or "") + texto
        else:
            atual.text = (atual.text or "") + texto


def _elementos(raiz, classe):
    return [elemento for elemento in raiz.iter() if classe in elemento.get("class", "").split()]


def _unico(raiz, classe):
    encontrados = _elementos(raiz, classe)
    assert len(encontrados) == 1
    return encontrados[0]


def _texto(raiz):
    def partes(elemento):
        if elemento.get("aria-hidden") == "true":
            return
        if elemento.text:
            yield elemento.text
        for filho in elemento:
            yield from partes(filho)
            if filho.tail:
                yield filho.tail
    return " ".join("".join(partes(raiz)).split())


def _fontes(estado="regular"):
    if estado == "regular":
        plano = _plano(*[
            _meta(mes=mes, grupo=grupo)
            for grupo in ("TEADS", "DISNEY", "FORBES", "GRUPO NOVO") for mes in (1, 10)
        ], _meta(mes=3, grupo="BRASIL 247"),
            _meta(mes=10, valor=0, grupo="BRASIL 247", ATIVO="NAO"),
            *[_meta(mes=mes, grupo="HYPR") for mes in (10, 11, 12)])
        vendas = _vendas(
            _venda(valor=122.3, grupo="TEADS"),
            _venda(valor=95, grupo="DISNEY"),
            _venda(valor=-5.25, grupo="GRUPO NOVO"),
            _venda(mes=3, valor=10, grupo="BRASIL 247"),
            _venda(mes=10, valor=80, grupo="HYPR"),
            _venda(mes=11, valor=125, grupo="TEADS"),
            _venda(ano=2025, grupo="TEADS", valor=50),
        )
        return vendas, plano, 2026, REF
    if estado == "sem_meta_ytd":
        return _vendas(_venda(mes=10, valor=25)), _plano(_meta(mes=10)), 2026, REF
    if estado == "zero_ativo":
        return _vendas(_venda(valor=12)), _plano(_meta(valor=0), _meta(mes=10, valor=0)), 2026, REF
    if estado == "sem_ano":
        return _vendas(_venda(), _venda(ano=2025)), _plano(_meta()), 2025, REF
    if estado == "encerrado":
        return _vendas(_venda(valor=25)), _plano(_meta(), _meta(mes=10, valor=0, ATIVO="NAO")), 2026, dt.date(2027, 1, 1)
    if estado == "janeiro":
        return _vendas(_venda(valor=25)), _plano(_meta(), _meta(mes=10)), 2026, dt.date(2026, 1, 31)
    valor = {"acima_125": 400, "negativo": -25}[estado]
    return _vendas(_venda(valor=valor)), _plano(_meta(), _meta(mes=10)), 2026, REF


ESTADOS = ("regular", "sem_meta_ytd", "zero_ativo", "sem_ano", "encerrado", "janeiro", "acima_125", "negativo")


def _avaliar(estado="regular"):
    vendas, plano, ano, referencia = _fontes(estado)
    fechado = metas.avaliar_metas(vendas, plano, ano, data_referencia=referencia)
    pulso = metas.avaliar_pulso(vendas, plano, ano, data_referencia=referencia)
    parceiros = metas.avaliar_parceiros(vendas, plano, ano, data_referencia=referencia)
    vigentes = metas.vigencia(plano, data_referencia=referencia)
    return vendas, plano, fechado, pulso, parceiros, vigentes


@pytest.mark.parametrize("estado", ESTADOS)
def test_hero_meta_anual_e_projecao_preservam_html_financeiro_do_design_1e(estado):
    _, _, fechado, pulso, _, _ = _avaliar(estado)
    congelada = _checkpoint()
    assert pagina._hero(fechado) == congelada._hero(fechado)
    assert pagina._meta_anual(pulso) == congelada._meta_anual(pulso)
    assert pagina._projecao(fechado, pulso) == congelada._projecao(fechado, pulso)


@pytest.mark.parametrize("estado", ESTADOS)
def test_reconciliacao_parceiros_preserva_ordem_atividade_numeros_e_detalhes(estado):
    vendas, plano, fechado, pulso, parceiros, vigentes = _avaliar(estado)
    fontes_antes = [fonte.copy(deep=True) for fonte in (vendas, plano, vigentes)]
    atual = _HTML(pagina._parceiros(parceiros, pulso, fechado, vigentes)).raiz
    anterior = _HTML(_checkpoint()._parceiros(parceiros, pulso, fechado, vigentes)).raiz
    linhas_atuais, linhas_anteriores = atual.findall(".//article"), anterior.findall(".//article")
    assert [linha.get("aria-label") for linha in linhas_atuais] == [linha.get("aria-label") for linha in linhas_anteriores]
    for nova, antiga in zip(linhas_atuais, linhas_anteriores, strict=True):
        for atributo in ("data-pct-ytd", "data-scale-max"):
            assert nova.get(atributo) == antiga.get(atributo)
        inativa = "atg-metas-partner-inactive"
        assert (inativa in nova.get("class", "").split()) == (inativa in antiga.get("class", "").split())
        assert _texto(_unico(nova, "atg-metas-partner-pct")) == _texto(_unico(antiga, "atg-metas-partner-pct"))
        status_antigo = _texto(_unico(antiga, "atg-metas-partner-status"))
        status_novo = _unico(nova, "atg-metas-partner-status")
        if inativa in antiga.get("class", "").split():
            assert status_antigo in _texto(nova)
            assert "atg-metas-negative" not in status_novo.get("class", "").split()
        else:
            assert _texto(status_novo) == status_antigo
        for classe in ("atg-metas-partner-comparison", "atg-metas-partner-details"):
            assert _texto(_unico(nova, classe)) == _texto(_unico(antiga, classe))
        moedas = lambda linha: [el.get("title") for el in _elementos(linha, "num") if el.get("title")]
        assert moedas(nova) == moedas(antiga)
        assert _texto(nova.find("details/summary")) == "Compromisso anual e saldo"
        assert "open" not in nova.find("details").attrib
    for fonte, antes in zip((vendas, plano, vigentes), fontes_antes, strict=True):
        pd.testing.assert_frame_equal(fonte, antes)
    assert metas.avaliar_parceiros(vendas, plano, fechado.ano, data_referencia=fechado.data_referencia) == parceiros


@pytest.mark.parametrize("estado", ESTADOS)
def test_graficos_mensal_e_acumulado_preservam_todas_as_series_do_design_1e(estado):
    _, _, fechado, pulso, _, _ = _avaliar(estado)
    congelados = _checkpoint("src/components/metas_charts.py")
    assert metas_charts.evolucao_mensal(fechado, pulso).to_json() == congelados.evolucao_mensal(fechado, pulso).to_json()
    assert metas_charts.evolucao_acumulada(fechado).to_json() == congelados.evolucao_acumulada(fechado).to_json()


@pytest.mark.parametrize("valor", [-25, 0, 74, 95, 100, 122.3, 125, 400])
def test_regua_limita_geometria_a_125_preservando_percentual_e_status_reais(valor):
    plano = _plano(_meta(grupo="PARCEIRO NOVO"), _meta(mes=10, grupo="PARCEIRO NOVO"))
    vendas = _vendas(_venda(valor=valor, grupo="PARCEIRO NOVO"))
    fechado = metas.avaliar_metas(vendas, plano, 2026, data_referencia=REF)
    pulso = metas.avaliar_pulso(vendas, plano, 2026, data_referencia=REF)
    parceiros = metas.avaliar_parceiros(vendas, plano, 2026, data_referencia=REF)
    artigo = _HTML(pagina._parceiros(parceiros, pulso, fechado)).raiz.find(".//article")
    percentual = Decimal(str(valor))
    assert Decimal(artigo.get("data-pct-ytd")) == percentual == parceiros[0].atingimento_ytd_pct
    assert artigo.get("data-scale-max") == "125"
    assert _texto(_unico(artigo, "atg-metas-partner-pct")) == pagina._pct(percentual)
    largura = min(Decimal(125), max(Decimal(0), percentual)) / Decimal(125) * 100
    assert _unico(artigo, "atg-metas-progress-fill").get("style") == f"width:{largura:.2f}%"
    assert len(_elementos(artigo, "atg-metas-progress-reference")) == 1
    assert pagina._pct(percentual) in _texto(artigo)
    trecho_acima = _elementos(artigo, "atg-metas-progress-over")
    assert len(trecho_acima) == int(percentual > 100)
    if percentual > 100:
        excedente = (min(Decimal(125), percentual) - 100) / Decimal(125) * 100
        assert trecho_acima[0].get("style") == f"width:{excedente:.2f}%"
    aviso = _elementos(artigo, "atg-metas-progress-overflow")
    assert len(aviso) == int(percentual > 125)
    if percentual > 125:
        assert _texto(aviso[0]) == "Acima da escala de 125%"


@pytest.mark.parametrize("grupo", ["FORBES", "OUTRO PARCEIRO"])
@pytest.mark.parametrize("valor,status", [(0, "↓ Abaixo do ritmo"), (95, "≈ No ritmo"), (150, "✓ Acima do ritmo")])
def test_forbes_e_qualquer_parceiro_compartilham_as_mesmas_regras(grupo, valor, status):
    plano = _plano(_meta(grupo=grupo), _meta(mes=10, grupo=grupo))
    vendas = _vendas(_venda(grupo=grupo, valor=valor))
    fechado = metas.avaliar_metas(vendas, plano, 2026, data_referencia=REF)
    pulso = metas.avaliar_pulso(vendas, plano, 2026, data_referencia=REF)
    parceiros = metas.avaliar_parceiros(vendas, plano, 2026, data_referencia=REF)
    artigo = _HTML(pagina._parceiros(parceiros, pulso, fechado)).raiz.find(".//article")
    assert _texto(_unico(artigo, "atg-metas-partner-status")) == status
    assert parceiros[0].realizado_ytd == Decimal(str(valor))
    assert parceiros[0].meta_ytd == 100
    assert [moeda.get("title") for moeda in _elementos(_unico(artigo, "atg-metas-partner-comparison"), "num")] == [
        f"R$ {valor:.2f}".replace(".", ","), "R$ 100,00",
    ]
    assert "atg-metas-partner-inactive" not in artigo.get("class").split()


@pytest.mark.parametrize("grupo", ["BRASIL 247", "ENCERRADO NOVO"])
def test_encerramento_e_historico_sao_derivados_da_vigencia_para_qualquer_parceiro(grupo):
    plano = _plano(_meta(mes=3, grupo=grupo), _meta(mes=10, valor=0, grupo=grupo, ATIVO="NAO"))
    vendas = _vendas(_venda(mes=3, valor=23.45, grupo=grupo))
    fechado = metas.avaliar_metas(vendas, plano, 2026, data_referencia=REF)
    pulso = metas.avaliar_pulso(vendas, plano, 2026, data_referencia=REF)
    parceiros = metas.avaliar_parceiros(vendas, plano, 2026, data_referencia=REF)
    raiz = _HTML(pagina._parceiros(parceiros, pulso, fechado, metas.vigencia(plano, data_referencia=REF))).raiz
    artigo = raiz.find(".//article")
    assert "atg-metas-partner-inactive" in artigo.get("class").split()
    assert "Operação encerrada em Mar/2026" in _texto(artigo)
    assert "R$ 23,45" in [moeda.get("title") for moeda in _elementos(artigo, "num")]
    assert "23,5%" in _texto(_unico(artigo, "atg-metas-partner-pct"))
    assert len(raiz.findall(".//details")) == 1
    assert "0 parceiros ativos" in _texto(raiz)


@pytest.mark.parametrize("grupo", ["HYPR", "ENTRADA NOVA", "  parceiro & <novo>  "])
def test_entrada_parcial_aparece_dinamicamente_sem_percentual_ytd_inventado(grupo):
    plano = _plano(*[_meta(mes=mes, grupo=grupo) for mes in (10, 11, 12)])
    vendas = _vendas(_venda(mes=9, grupo=grupo, valor=999), _venda(mes=10, grupo=grupo, valor=25))
    fechado = metas.avaliar_metas(vendas, plano, 2026, data_referencia=REF)
    pulso = metas.avaliar_pulso(vendas, plano, 2026, data_referencia=REF)
    parceiros = metas.avaliar_parceiros(vendas, plano, 2026, data_referencia=REF)
    artigo = _HTML(pagina._parceiros(parceiros, pulso, fechado)).raiz.find(".//article")
    assert artigo.get("aria-label") == normalizar_entidade(grupo)
    assert "atg-metas-partner-inactive" not in artigo.get("class").split()
    assert artigo.get("data-pct-ytd") == ""
    assert _texto(_unico(artigo, "atg-metas-partner-pct")) == "—"
    assert not _elementos(artigo, "atg-metas-progress-over")
    assert not _elementos(artigo, "atg-metas-progress-overflow")
    assert parceiros[0].meta_ytd == 0 and parceiros[0].realizado_ytd == 0
    assert parceiros[0].pulso.meta_anual == 300 and parceiros[0].pulso.total_vendido_ano == 25
    assert "R$ 999,00" not in [moeda.get("title") for moeda in _elementos(artigo, "num")]


@pytest.mark.parametrize("quantidade", [0, 1, 9, 13])
def test_quantidade_de_parceiros_e_ordem_nao_dependem_da_lista_de_marcas(quantidade):
    grupos = [f"NOVO GRUPO {indice:02d}" for indice in range(quantidade)]
    plano = _plano(*[_meta(mes=mes, grupo=grupo) for grupo in grupos for mes in (1, 10)])
    vendas = _vendas(*[_venda(valor=indice * 10, grupo=grupo) for indice, grupo in enumerate(grupos)])
    fechado = metas.avaliar_metas(vendas, plano, 2026, data_referencia=REF)
    pulso = metas.avaliar_pulso(vendas, plano, 2026, data_referencia=REF)
    parceiros = metas.avaliar_parceiros(vendas, plano, 2026, data_referencia=REF)
    artigos = _HTML(pagina._parceiros(parceiros, pulso, fechado)).raiz.findall(".//article")
    assert [artigo.get("aria-label") for artigo in artigos] == grupos[::-1]
    assert len(artigos) == quantidade


def _render_metas_congelada(vendas, plano, referencia, erro):
    from tests.test_design_metas import _checkpoint
    _checkpoint().render(vendas, plano, data_referencia=referencia, erro_metas=erro)


def _render_metas_atual(vendas, plano, referencia, erro):
    from pages_content.metas_resultados import render
    render(vendas, plano, data_referencia=referencia, erro_metas=erro)


@pytest.mark.parametrize("estado", ["regular", "sem_ano", "janeiro"])
def test_controle_nativo_de_ano_e_graficos_preservados_em_render(estado):
    vendas, plano, ano, referencia = _fontes(estado)
    vendas[loader.COL_ANO_ABA] = vendas[cleaning.COL_MES_VEICULACAO_DATA].dt.year
    apps = []
    for executar in (_render_metas_atual, _render_metas_congelada):
        app = AppTest.from_function(executar, args=(vendas, plano, referencia, None))
        app.session_state["metas_ano"] = ano
        apps.append(app.run(timeout=20))
    atual, congelada = apps
    assert not atual.exception and not congelada.exception
    assert [(seletor.key, seletor.options, seletor.value) for seletor in atual.button_group] == [
        (seletor.key, seletor.options, seletor.value) for seletor in congelada.button_group
    ]
    assert atual.button_group(key="metas_ano").value == ano
    assert _figuras(atual) == _figuras(congelada)
    assert [erro.value for erro in atual.error] == [erro.value for erro in congelada.error]
    assert [info.value for info in atual.info] == [info.value for info in congelada.info]
    if estado == "sem_ano":
        assert not atual.get("plotly_chart")
        assert not any("Metas por parceiro" in el.value for el in atual.markdown)


@pytest.mark.parametrize("categoria", ["fonte", "estrutura", "validacao"])
def test_erros_preservam_mensagens_amigaveis_sem_expor_conteudo_da_fonte(categoria):
    vendas, plano, ano, referencia = _fontes()
    vendas[loader.COL_ANO_ABA] = vendas[cleaning.COL_MES_VEICULACAO_DATA].dt.year
    erro = ErroDeMetas("CONTEUDO_SENSIVEL_QUE_NAO_DEVE_APARECER", categoria)
    apps = [AppTest.from_function(executar, args=(vendas, plano, referencia, erro)).run(timeout=20)
            for executar in (_render_metas_atual, _render_metas_congelada)]
    atual, congelada = apps
    assert not atual.exception and not congelada.exception
    assert [item.value for item in atual.error] == [item.value for item in congelada.error]
    assert not atual.get("plotly_chart")
    assert not any("CONTEUDO_SENSIVEL" in el.value for el in (*atual.markdown, *atual.error))


def _render_performance_congelada(vendas, plano):
    from pages_content import performance_comercial
    from tests.test_design_metas import _checkpoint
    modulo = _checkpoint("pages_content/performance_comercial.py")
    modulo._dt = performance_comercial._dt
    modulo.render(vendas, carregar_metas=lambda: plano)


@pytest.mark.parametrize("aba", ["Vendas", "Ticket Médio", "Meta"])
@pytest.mark.parametrize("valor,criterio,grupos", [
    ("Valor Líquido", "Mês (Veiculação)", None),
    ("Valor Bruto", "Mês (Ganho)", ["G"]),
])
def test_performance_preserva_kpis_radar_evolucao_e_rankings_do_design_1e(aba, valor, criterio, grupos):
    atual, vendas = _performance(aba=aba, valor=valor, criterio=criterio, grupos=grupos)
    congelada = AppTest.from_function(_render_performance_congelada, args=(vendas, _plano_performance()))
    for chave, selecao in (("performance_evolucao_tab", aba), ("perf_ano", 2026), ("perf_valor", valor), ("perf_mes", criterio)):
        congelada.session_state[chave] = selecao
    if grupos is not None:
        congelada.session_state[f"perf_fc_{cleaning.COL_GRUPO}_aplicado"] = grupos
    congelada.run(timeout=20)
    assert not atual.exception and not congelada.exception
    assert [el.value for el in atual.markdown] == [el.value for el in congelada.markdown]
    assert _figuras(atual) == _figuras(congelada)
    assert [(botao.key, botao.label, botao.disabled) for botao in atual.button] == [
        (botao.key, botao.label, botao.disabled) for botao in congelada.button
    ]


def test_shell_metas_preserva_titulo_unico_navegacao_atualizacao_e_chaves_nativas(monkeypatch):
    leituras = {"vendas": 0, "metas": 0}

    def ler_vendas(*_):
        leituras["vendas"] += 1
        return _fonte_vendas()

    def ler_metas(*_):
        leituras["metas"] += 1
        return _plano_performance()

    monkeypatch.setattr(st, "secrets", {"spreadsheet_id": "TESTE_DESIGN_1F_OFFLINE", "gcp_service_account": {}, "dev_auditoria": False})
    monkeypatch.setattr(loader, "load_all_sheets", ler_vendas)
    monkeypatch.setattr(metas_loader, "load_metas", ler_metas)
    atual = AppTest.from_file(str(APP))
    atual.session_state["autenticado"] = True
    atual.session_state["nav_pagina"] = "Metas e Resultados"
    atual.session_state["metas_ano"] = 2026
    atual.run(timeout=20)
    assert not atual.exception

    def chaves_visuais(app):
        return {elemento.proto.id.rsplit('-', 1)[-1] for elemento in app.get('flex_container') if elemento.proto.id}

    chaves_metas = {'design_metas_header', 'design_metas_title', 'design_metas_actions', 'design_metas_refresh',
                    'design_metas_theme', 'design_metas_content', 'design_metas_filters', 'design_metas_year'}
    assert chaves_metas <= chaves_visuais(atual)
    assert not any(chave.startswith('design_performance_') for chave in chaves_visuais(atual))
    titulos = [_texto(_HTML(el.value).raiz) for el in atual.main.markdown if 'class="atg-h1"' in el.value]
    assert titulos == ["Metas e Resultados"]
    assert atual.button_group(key="metas_ano").value == 2026
    assert atual.button(key="masthead_tema").disabled
    assert leituras == {"vendas": 1, "metas": 1}
    opcoes = atual.radio(key="nav_pagina").options
    atual.button(key="masthead_refresh").click().run(timeout=20)
    assert not atual.exception and leituras == {"vendas": 2, "metas": 2}
    assert atual.toast[0].value == "Dados atualizados"
    assert atual.button_group(key="metas_ano").value == 2026
    atual.radio(key="nav_pagina").set_value("Performance Comercial").run(timeout=20)
    assert not atual.exception and leituras == {"vendas": 2, "metas": 2}
    assert 'design_performance_header' in chaves_visuais(atual)
    assert not any(chave.startswith('design_metas_') for chave in chaves_visuais(atual))
    assert {'perf_ano', 'perf_valor', 'perf_mes'} <= {controle.key for controle in atual.button_group}
    atual.radio(key="nav_pagina").set_value("Metas e Resultados").run(timeout=20)
    assert not atual.exception and atual.button_group(key="metas_ano").value == 2026
    assert atual.radio(key="nav_pagina").options == opcoes
    assert leituras == {"vendas": 2, "metas": 2}
    assert chaves_metas <= chaves_visuais(atual)


@pytest.mark.parametrize("caminho", [
    "src/data/metas.py", "src/data/metas_schema.py", "src/data/metas_loader.py",
    "src/data/metas_quality.py", "src/data/loader.py", "src/auth/gate.py",
    "src/components/metas_charts.py", "pages_content/performance_comercial.py",
    "pages_content/analitico_comercial.py", "pages_content/analitico_veiculos.py",
    "requirements.txt",
])
def test_design_1f_preserva_fontes_protegidas_do_design_1e(caminho):
    atual = (RAIZ / caminho).read_text()
    anterior = _fonte_congelada(caminho)
    autorizadas = {
        "src/data/loader.py": {"load_all_sheets"},
        "pages_content/performance_comercial.py": {"render", "_linhas_ranking_dimensao"},
        "pages_content/analitico_comercial.py": {"render"},
    }
    if caminho not in autorizadas:
        assert atual == anterior
    else:
        # As funções corrigidas têm testes de comportamento no hardening;
        # todas as demais definições/constantes continuam iguais à baseline.
        def protegidas(fonte):
            return [ast.dump(no) for no in ast.parse(fonte).body
                    if not isinstance(no, (ast.Import, ast.ImportFrom))
                    and getattr(no, "name", None) not in autorizadas[caminho]]
        assert protegidas(atual) == protegidas(anterior)


def test_novo_css_isola_metas_e_usa_largura_util_sem_ocultar_dados_financeiros():
    from src.components.metas_styles import CSS_METAS
    texto = re.sub(r'/\*.*?\*/', '', CSS_METAS, flags=re.DOTALL).replace('<style>', '').replace('</style>', '')
    regras = re.findall(r'([^{}]+)\{([^{}]*)\}', texto)
    assert regras
    for seletor, _ in regras:
        assert '.st-key-design_metas_' in seletor or '.atg-metas.atg-metas-partner-section' in seletor
    assert 'container-name:atg-metas-partners' in CSS_METAS
    assert '@container atg-metas-partners (width < 1040px)' in CSS_METAS
    assert '@media(max-width:1366px)' not in CSS_METAS
    assert '[data-testid="stSidebar"]' not in CSS_METAS
    assert 'var(--atg-brand)' in CSS_METAS and 'var(--atg-positive)' in CSS_METAS
    assert 'var(--atg-radius-card)' in CSS_METAS
    # Ocultar o conteúdo exige somente o estado fechado do expansor nativo.
    regras_ocultas = [seletor.strip() for seletor, declaracoes in regras if 'display:none;' in declaracoes]
    assert regras_ocultas == [
        '.st-key-design_metas_content .atg-metas-partner summary::-webkit-details-marker',
        '.st-key-design_metas_content .atg-metas-partner details:not([open]) > .atg-metas-partner-details',
    ]


def test_css_da_regua_e_expansor_preserva_referencia_trecho_positivo_e_toque():
    from src.components.metas_styles import CSS_METAS

    def declaracao(seletor):
        resultado = re.search(re.escape(seletor) + r'\s*\{([^}]+)\}', CSS_METAS)
        assert resultado is not None
        return resultado.group(1)

    prefixo = '.st-key-design_metas_content .atg-metas-'
    assert 'height:8px;' in declaracao(prefixo + 'progress')
    assert 'max-width:80%;' in declaracao(prefixo + 'progress-fill')
    acima = declaracao(prefixo + 'progress-over')
    assert 'left:80%;' in acima and 'max-width:20%;' in acima and 'var(--atg-positive)' in acima
    assert 'left:80%;' in declaracao(prefixo + 'progress-reference')
    assert 'min-height:44px;' in declaracao(prefixo + 'partner summary')
    assert 'outline:2px solid var(--atg-focus-ring);' in declaracao(prefixo + 'partner summary:focus-visible')
    assert 'rotate(45deg)' in declaracao(prefixo + 'partner summary::after')
    assert 'rotate(225deg)' in declaracao(prefixo + 'partner details[open] summary::after')
