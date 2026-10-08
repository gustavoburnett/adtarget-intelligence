"""Design 1G: integração offline contra o Hardening congelado.

As provas comparam contratos financeiros e interações reais de Streamlit.
Não substituem a conferência visual de fontes, responsividade e teclado.
"""

from functools import lru_cache
import json
from pathlib import Path
import subprocess
from types import ModuleType
import xml.etree.ElementTree as ET

import pandas as pd
import pyarrow as pa
import pytest
from streamlit.testing.v1 import AppTest

from pages_content import analitico_comercial as pagina
from src.components import cards
from src.data import cleaning, quality_checks
from tests.test_performance_meta import _fonte_vendas


CHECKPOINT_HARDENING = "48017f4ba115f0c80447c3a7dc9de34df0e15bbf"
RAIZ = Path(__file__).resolve().parents[1]
COLUNAS = [
    "GRUPO", "VEICULO", "PI", "AGENCIA", "CLIENTE", "CAMPANHA",
    "MÊS (GANHO)", "MÊS (VEICULAÇÃO)", "INÍCIO", "FIM",
    "VALOR PI BRUTO", "VALOR PI LIQUIDO", "VENCIMENTO PI",
    "STATUS", "NOTA FISCAL", "EXECUTIVO",
]


@lru_cache
def _congelada():
    caminho = "pages_content/analitico_comercial.py"
    fonte = subprocess.run(
        ["git", "show", f"{CHECKPOINT_HARDENING}:{caminho}"],
        check=True, capture_output=True, text=True, cwd=RAIZ,
    ).stdout
    modulo = ModuleType("analitico_comercial_hardening_congelado")
    exec(compile(fonte, f"<{CHECKPOINT_HARDENING}:{caminho}>", "exec"), modulo.__dict__)
    return modulo


def _fonte():
    fonte = _fonte_vendas()
    fonte["VENCIMENTO PI"] = fonte["VENCIMENTO PI"].astype(object)
    fonte["INÍCIO"] = [f"02/01/{ano}" for ano in fonte["ANO_ABA"]]
    fonte["FIM"] = [f"31/12/{ano}" for ano in fonte["ANO_ABA"]]
    fonte.loc[0, "NOTA FISCAL"] = ""
    fonte.loc[1, "STATUS"] = "STATUS NOVO"
    fonte.loc[2, "VENCIMENTO PI"] = 46052
    fonte.loc[3, "VENCIMENTO PI"] = 46068.5
    fonte.loc[4, "INÍCIO"] = ""
    homonimos = []
    for grupo in ("G", "H"):
        linha = fonte[(fonte["GRUPO"] == grupo) & (fonte["ANO_ABA"] == 2026)].iloc[0].copy()
        linha["VEICULO"] = "HOMÔNIMO"
        linha["PI"] = f"PI HOMONIMO {grupo}"
        linha["VALOR PI LIQUIDO"] = 12.3456789
        linha["VALOR PI BRUTO"] = 123.456789
        homonimos.append(linha)
    fonte = pd.concat([fonte, pd.DataFrame(homonimos)], ignore_index=True)
    return cleaning.limpar_dataframe(fonte)


def _render_atual(df):
    from pages_content.analitico_comercial import render
    render(df)


def _render_congelada(df):
    from tests.test_design_analitico_comercial import _congelada
    _congelada().render(df)


def _pagina(executar=_render_atual, *, fonte=None, ano=2026, valor="Valor Líquido",
            criterio="Mês (Veiculação)", grupos=None, pares=None, pesquisa="",
            permitir_falha=False):
    df = _fonte() if fonte is None else fonte
    app = AppTest.from_function(executar, args=(df,))
    app.session_state["anfat_ano"] = ano
    app.session_state["anfat_valor"] = valor
    app.session_state["anfat_mes"] = criterio
    app.session_state["anfat_pesquisa"] = pesquisa
    if grupos is not None:
        app.session_state["anfat_fc_GRUPO_aplicado"] = grupos
    if pares is not None:
        app.session_state["anfat_fc_VEICULO_PAR_aplicado"] = pares
    app.run(timeout=20)
    if not permitir_falha:
        assert not app.exception
    return app


def _comparar(**opcoes):
    atual = _pagina(_render_atual, **opcoes)
    vazia = _raw(atual.dataframe[-1]).empty
    anterior = _pagina(_render_congelada, permitir_falha=vazia, **opcoes)
    if vazia:
        # Pandas atual mantém dtype datetime ao mapear uma série vazia; o
        # exportador congelado falha em .any(). A página nova tipa somente
        # a cópia vazia para exportar o mesmo cabeçalho, sem tocar o helper.
        assert len(anterior.exception) == 1
        assert anterior.exception[0].message == "datetime64 type does not support operation 'any'"
    return atual, anterior


def _metricas(app):
    return [(el.label, el.value, el.proto.help) for el in app.metric]


def _seletores(app):
    return [(el.key, el.label, el.options, el.value, el.proto.disabled) for el in app.button_group]


def _filtros(app):
    return [(el.proto.popover.label, el.proto.popover.disabled) for el in app.get("popover")]


def _figuras(app):
    return [json.loads(el.proto.spec) for el in app.get("plotly_chart")]


def _contrato_figura(figura):
    return [
        {campo: serie.get(campo) for campo in ("x", "y", "text", "customdata", "hovertemplate", "orientation")}
        for serie in figura["data"]
    ]


def _raw(tabela):
    return pa.ipc.open_stream(tabela.proto.arrow_data.data).read_all().to_pandas()


def _display(tabela):
    return pa.ipc.open_stream(tabela.proto.arrow_data.styler.display_values).read_all().to_pandas()


@pytest.mark.parametrize("ano", [2024, 2025, 2026])
@pytest.mark.parametrize("valor,criterio", [
    ("Valor Líquido", "Mês (Veiculação)"),
    ("Valor Bruto", "Mês (Veiculação)"),
    ("Valor Líquido", "Mês (Ganho)"),
    ("Valor Bruto", "Mês (Ganho)"),
])
def test_ano_toggles_indicadores_e_series_preservam_baseline(ano, valor, criterio):
    atual, anterior = _comparar(ano=ano, valor=valor, criterio=criterio)
    assert _metricas(atual) == _metricas(anterior)
    assert _seletores(atual) == _seletores(anterior)
    assert _filtros(atual) == _filtros(anterior)
    assert len(_figuras(atual)) == len(_figuras(anterior)) == 1
    nova, antiga = _figuras(atual)[0], _figuras(anterior)[0]
    assert _contrato_figura(nova) == _contrato_figura(antiga)
    assert nova["layout"]["yaxis"]["autorange"] == antiga["layout"]["yaxis"]["autorange"]
    assert "range" not in nova["layout"].get("xaxis", {})
    assert "range" not in antiga["layout"].get("xaxis", {})
    assert list(_raw(atual.dataframe[-1]).columns) == COLUNAS
    for campo in ("VALOR PI BRUTO", "VALOR PI LIQUIDO", "INÍCIO", "FIM"):
        pd.testing.assert_series_equal(
            _raw(atual.dataframe[-1])[campo].reset_index(drop=True),
            _raw(anterior.dataframe[-1])[campo].reset_index(drop=True),
        )


def test_quatro_verificadores_base_completa_e_quantidade_de_categorias_ativas():
    fonte = _fonte()
    esperados = quality_checks.executar_todas(fonte)
    assert len(esperados) == 4
    assert all(alerta.possui_ocorrencias for alerta in esperados)
    atual, anterior = _comparar(fonte=fonte, grupos=["FORA"])
    assert _metricas(atual) == _metricas(anterior)
    assert next(el.value for el in atual.metric if el.label == "Alertas de Qualidade") == "4"
    elementos = [ET.fromstring(el.value) for el in atual.markdown if 'class="atg-analytic-alert ' in el.value]
    assert len(elementos) == 4
    for elemento, esperado in zip(elementos, esperados, strict=True):
        campos = {el.get("class"): "".join(el.itertext()) for el in elemento if el.tag == "span"}
        assert campos["atg-analytic-alert-title"] == esperado.titulo
        assert campos["atg-analytic-alert-count"] == str(esperado.quantidade)
    assert [len(el.value) for el in atual.dataframe[:-1]] == [len(el.value) for el in anterior.dataframe[:-1]]
    assert [exp.label for exp in atual.expander] == ["Filtros", "Alertas de Qualidade (4 ativos)"]
    assert atual.expander[0].proto.expanded
    assert not atual.expander[1].proto.expanded


@pytest.mark.parametrize("grupos,pares", [
    (["G"], None),
    (["H"], None),
    (["G"], ["G — HOMÔNIMO"]),
    (["H"], ["H — HOMÔNIMO"]),
    (["G"], ["H — HOMÔNIMO"]),
    ([], None),
])
def test_cascata_preserva_grupo_e_par_de_veiculo_sem_unificar_homonimos(grupos, pares):
    atual, anterior = _comparar(grupos=grupos, pares=pares)
    assert _metricas(atual) == _metricas(anterior)
    assert _filtros(atual) == _filtros(anterior)
    a, b = _raw(atual.dataframe[-1]), _raw(anterior.dataframe[-1])
    for coluna in ("GRUPO", "VEICULO", "PI", "VALOR PI BRUTO", "VALOR PI LIQUIDO"):
        assert a[coluna].tolist() == b[coluna].tolist()
    if pares == ["G — HOMÔNIMO"]:
        assert a["GRUPO"].tolist() == ["G"]
        assert a["VEICULO"].tolist() == ["HOMÔNIMO"]
    if pares == ["H — HOMÔNIMO"] and grupos == ["G"]:
        assert a.empty
    assert [_contrato_figura(figura) for figura in _figuras(atual)] == [
        _contrato_figura(figura) for figura in _figuras(anterior)
    ]


@pytest.mark.parametrize("pesquisa", ["cliente g", "HOMÔNIMO", "nf teste", "não existe", ".*"])
def test_pesquisa_afeta_somente_tabela_e_csv_original_protegido(monkeypatch, pesquisa):
    capturas = {"atual": [], "anterior": []}
    from src.data.csv_export import gerar_csv_seguro

    def exportar(nome):
        def capturar(tabela):
            captura = [tabela.copy(deep=True), None]
            capturas[nome].append(captura)
            conteudo = gerar_csv_seguro(tabela)
            captura[1] = conteudo
            return conteudo
        return capturar

    monkeypatch.setattr(pagina, "gerar_csv_seguro", exportar("atual"))
    monkeypatch.setattr(_congelada(), "gerar_csv_seguro", exportar("anterior"))
    fonte = _fonte()
    fonte.loc[fonte["ANO_ABA"] == 2026, "CAMPANHA"] = "=FÓRMULA TESTE"
    antes = fonte.copy(deep=True)
    atual, anterior = _comparar(fonte=fonte, pesquisa=pesquisa)
    referencia = _pagina(fonte=fonte)
    assert _metricas(atual) == _metricas(anterior) == _metricas(referencia)
    assert _contrato_figura(_figuras(atual)[0]) == _contrato_figura(_figuras(referencia)[0])
    tabela_atual, csv_atual = capturas["atual"][0]
    tabela_anterior, csv_anterior = capturas["anterior"][0]
    pd.testing.assert_frame_equal(tabela_atual, tabela_anterior, check_dtype=not tabela_atual.empty)
    if tabela_atual.empty:
        assert csv_anterior is None
        assert csv_atual == gerar_csv_seguro(tabela_anterior.astype(object))
    else:
        assert csv_atual == csv_anterior == gerar_csv_seguro(tabela_atual)
    assert list(tabela_atual.columns) == COLUNAS
    assert f"{len(tabela_atual)} linha(s) no recorte" in [el.value for el in atual.caption]
    assert len(atual.get("download_button")) == 1
    if not tabela_atual.empty:
        assert len(anterior.get("download_button")) == 1
    pd.testing.assert_frame_equal(fonte, antes)


def test_limpar_dimensoes_preserva_ano_toggles_e_pesquisa():
    opcoes = dict(ano=2025, valor="Valor Bruto", criterio="Mês (Ganho)", grupos=["G"], pesquisa="cliente g")
    atual, anterior = _comparar(**opcoes)
    for app in (atual, anterior):
        app.button(key="anfat_limpar_filtros").click().run(timeout=20)
        assert not app.exception
        assert app.button_group(key="anfat_ano").value == 2025
        assert app.button_group(key="anfat_valor").value == "Valor Bruto"
        assert app.button_group(key="anfat_mes").value == "Mês (Ganho)"
        assert app.text_input(key="anfat_pesquisa").value == "cliente g"
        assert _raw(app.dataframe[-1])["GRUPO"].unique().tolist() == ["G"]
        assert "anfat_fc_GRUPO_aplicado" not in app.session_state
    assert _metricas(atual) == _metricas(anterior)
    assert _filtros(atual) == _filtros(anterior)


def test_tabela_exibe_moeda_e_datas_ptbr_sem_alterar_registros_originais():
    fonte = _fonte()
    antes = fonte.copy(deep=True)
    app = _pagina(fonte=fonte, ano=2024)
    assert [el.value for el in app.subheader] == [
        "Carteira por status (valor e quantidade de PIs)", "Tabela analítica",
    ]
    raw, exibida = _raw(app.dataframe[-1]), _display(app.dataframe[-1])
    assert list(raw.columns) == list(exibida.columns) == COLUNAS
    assert exibida.iloc[2]["VENCIMENTO PI"] == "30/01/2026"
    assert exibida.iloc[3]["VENCIMENTO PI"] == "15/02/2026 12:00"
    assert exibida.iloc[0]["VENCIMENTO PI"] == "CONTRA APRESENT."
    assert exibida.iloc[0]["INÍCIO"] == "02/01/2024"
    assert exibida.iloc[4]["INÍCIO"] == "—"
    for coluna in ("VALOR PI BRUTO", "VALOR PI LIQUIDO"):
        assert pd.api.types.is_numeric_dtype(raw[coluna])
        assert exibida[coluna].tolist() == [cards.formatar_moeda(valor) for valor in raw[coluna]]
    pd.testing.assert_frame_equal(fonte, antes)


def test_alertas_inativos_continuam_visiveis_sem_ocorrencias_inventadas():
    fonte = cleaning.limpar_dataframe(_fonte_vendas())
    fonte = fonte[(fonte["STATUS"] == "FATURADO") & (fonte["GRUPO"] != "FORA")]
    app = _pagina(fonte=fonte)
    assert next(el.value for el in app.metric if el.label == "Alertas de Qualidade") == "0"
    cabecalhos = [ET.fromstring(el.value) for el in app.markdown if 'class="atg-analytic-alert ' in el.value]
    assert len(cabecalhos) == 4
    assert all("atg-analytic-alert-inactive" in el.get("class") for el in cabecalhos)
    assert len(app.dataframe) == 1


def test_recorte_vazio_com_datas_preserva_tipos_e_exporta_apenas_16_cabecalhos(monkeypatch):
    from src.data.csv_export import gerar_csv_seguro
    capturas = []

    def capturar(tabela):
        conteudo = gerar_csv_seguro(tabela)
        capturas.append((tabela.copy(deep=True), conteudo))
        return conteudo

    monkeypatch.setattr(pagina, "gerar_csv_seguro", capturar)
    fonte = _fonte()
    antes = fonte.copy(deep=True)
    app = _pagina(fonte=fonte, grupos=[])
    raw = _raw(app.dataframe[-1])
    assert raw.empty and list(raw.columns) == COLUNAS
    assert pd.api.types.is_datetime64_any_dtype(raw["INÍCIO"])
    assert pd.api.types.is_datetime64_any_dtype(raw["FIM"])
    assert pd.api.types.is_numeric_dtype(raw["VALOR PI LIQUIDO"])
    assert len(capturas) == 1 and capturas[0][0].empty
    cabecalho = ",".join(COLUNAS) + "\n"
    assert capturas[0][1].decode("utf-8-sig") == cabecalho
    assert "0 linha(s) no recorte" in [el.value for el in app.caption]
    assert len(app.get("download_button")) == 1
    pd.testing.assert_frame_equal(fonte, antes)


@pytest.mark.parametrize("coluna", [
    "GRUPO", "VEICULO", "PI", "AGENCIA", "CLIENTE", "CAMPANHA",
    "STATUS", "NOTA FISCAL", "EXECUTIVO",
])
def test_nove_campos_de_pesquisa_continuam_pesquisaveis_sem_mudar_kpis(coluna):
    fonte = _fonte()
    indice = fonte.index[fonte["ANO_ABA"] == 2026][0]
    termo = "ALVO ÚNICO PARA BUSCA"
    fonte.loc[indice, coluna] = termo
    atual, anterior = _comparar(fonte=fonte, pesquisa="alvo único para busca")
    sem_pesquisa = _pagina(fonte=fonte)
    assert _metricas(atual) == _metricas(anterior) == _metricas(sem_pesquisa)
    a, b = _raw(atual.dataframe[-1]), _raw(anterior.dataframe[-1])
    assert len(a) == len(b) == 1
    assert a.iloc[0][coluna] == b.iloc[0][coluna] == termo


def test_defaults_mais_recente_liquido_veiculacao_e_dimensoes_completas_preservados():
    fonte = _fonte()
    apps = [AppTest.from_function(executar, args=(fonte,)).run(timeout=20)
            for executar in (_render_atual, _render_congelada)]
    atual, anterior = apps
    assert not atual.exception and not anterior.exception
    for chave, valor in (("anfat_ano", 2026), ("anfat_valor", "Valor Líquido"),
                        ("anfat_mes", "Mês (Veiculação)")):
        assert atual.button_group(key=chave).value == anterior.button_group(key=chave).value == valor
    assert _filtros(atual) == _filtros(anterior)
    assert len(_filtros(atual)) == 6
    assert _raw(atual.dataframe[-1])["GRUPO"].unique().tolist() == ["G", "H", "FORA"]
