"""Carga inicial validada offline, com valores exclusivamente sintéticos."""

from __future__ import annotations

import datetime as dt
import json
from dataclasses import replace
from decimal import Decimal
from xml.sax.saxutils import escape
from zipfile import ZipFile

import pandas as pd
import pytest

from scripts import carga_inicial_metas as carga
from src.data.metas import ResultadoMetas
from src.data.metas_schema import COLUNAS_METAS, ErroDeMetas

REFERENCIA = dt.date(2026, 10, 5)
TIMESTAMP = "2026-10-05T12:30:00-03:00"
NOMES = (
    "Teads", "InfoMoney", "Climatempo", "Brasil 247", "Webedia", "Forbes",
    "Disney", "Rádio Melodia", "Carrega +",
)
GRUPOS = (
    "TEADS", "INFOMONEY", "CLIMATEMPO", "BRASIL 247", "WEBEDIA", "FORBES",
    "DISNEY", "MELODIA", "CARREGA+",
)
MESES = (
    "JANEIRO", "FEVEREIRO", "MARÇO", "ABRIL", "MAIO", "JUNHO", "JULHO",
    "AGOSTO", "SETEMBRO", "OUTUBRO", "NOVEMBRO", "DEZEMBRO",
)
NS_PLANILHA = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
NS_RELACIONAMENTOS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def _fonte(*, residuos=False):
    """Valores pequenos calculados para o teste; não reproduzem a planilha real."""
    entidades = []
    for indice, nome in enumerate(NOMES, start=1):
        valores = tuple(
            Decimal(0) if nome == "Brasil 247" and mes >= 4
            else Decimal(indice * 10 + mes) + Decimal("0.25")
            for mes in range(1, 13)
        )
        if residuos and indice == 1:
            valores = (valores[0] + Decimal("0.00000000001"), *valores[1:])
        entidades.append(carga.EntidadeOrigem(nome, sum(valores), valores))
    return _consolidar(tuple(entidades))


def _consolidar(entidades, *, ano=2026):
    totais = tuple(sum(entidade.valores_mensais[mes] for entidade in entidades) for mes in range(12))
    return carga.FonteMetas(ano, entidades, totais, sum(totais))


def _preparar(fonte=None, **opcoes):
    argumentos = {"criado_em": TIMESTAMP, "data_referencia": REFERENCIA, "total_esperado_centavos": None}
    argumentos.update(opcoes)
    return carga.preparar_carga(_fonte() if fonte is None else fonte, **argumentos)


def _alterar_valor(fonte, indice, mes, valor):
    entidades = list(fonte.entidades)
    original = entidades[indice]
    valores = list(original.valores_mensais)
    valores[mes - 1] = valor
    entidades[indice] = replace(original, valores_mensais=tuple(valores))
    return replace(fonte, entidades=tuple(entidades))


def _xlsx(caminho, fonte=None, *, alteracoes=None, strings_compartilhadas=False):
    """XLSX mínimo com resultados cache e layout específico aprovado."""
    fonte = _fonte() if fonte is None else fonte
    celulas = {"B16": "VEÍCULO", "D16": "META 2026"}
    celulas.update({f"{chr(69 + indice)}16": mes for indice, mes in enumerate(MESES)})
    for numero, entidade in enumerate(fonte.entidades, start=17):
        celulas[f"B{numero}"] = entidade.nome
        celulas[f"D{numero}"] = entidade.meta_anual
        celulas.update({f"{chr(69 + indice)}{numero}": valor for indice, valor in enumerate(entidade.valores_mensais)})
    celulas["D26"] = fonte.total_anual
    celulas.update({f"{chr(69 + indice)}26": valor for indice, valor in enumerate(fonte.totais_mensais)})
    celulas.update(alteracoes or {})
    strings = []
    linhas = {}
    for referencia, valor in celulas.items():
        numero = int("".join(caractere for caractere in referencia if caractere.isdigit()))
        if valor is None:
            continue
        if isinstance(valor, tuple):
            formula, cache = valor
            resultado = "" if cache is None else f"<v>{escape(str(cache))}</v>"
            conteudo = f'<c r="{referencia}"><f>{escape(formula)}</f>{resultado}</c>'
        elif isinstance(valor, str):
            if strings_compartilhadas:
                indice = len(strings)
                strings.append(valor)
                conteudo = f'<c r="{referencia}" t="s"><v>{indice}</v></c>'
            else:
                conteudo = f'<c r="{referencia}" t="inlineStr"><is><t>{escape(valor)}</t></is></c>'
        else:
            conteudo = f'<c r="{referencia}"><v>{escape(str(valor))}</v></c>'
        linhas.setdefault(numero, []).append(conteudo)
    xml_linhas = "".join(f'<row r="{numero}">{"".join(linha)}</row>' for numero, linha in sorted(linhas.items()))
    workbook = (
        f'<workbook xmlns="{NS_PLANILHA}" xmlns:r="{NS_RELACIONAMENTOS}">'
        '<sheets><sheet name="META 2026" sheetId="1" r:id="rId1"/></sheets></workbook>'
    )
    relacionamentos = (
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f'<Relationship Id="rId1" Type="{NS_RELACIONAMENTOS}/worksheet" Target="worksheets/sheet1.xml"/>'
        '</Relationships>'
    )
    with ZipFile(caminho, "w") as arquivo:
        arquivo.writestr("xl/workbook.xml", workbook)
        arquivo.writestr("xl/_rels/workbook.xml.rels", relacionamentos)
        arquivo.writestr("xl/worksheets/sheet1.xml", f'<worksheet xmlns="{NS_PLANILHA}"><sheetData>{xml_linhas}</sheetData></worksheet>')
        if strings:
            elementos = "".join(f"<si><t>{escape(texto)}</t></si>" for texto in strings)
            arquivo.writestr("xl/sharedStrings.xml", f'<sst xmlns="{NS_PLANILHA}">{elementos}</sst>')
    return caminho


def test_wide_long_108_slots_sem_duplicidade_ou_ausencia():
    resultado = _preparar()
    registros = resultado.registros
    assert tuple(registros.columns) == COLUNAS_METAS
    assert len(registros) == 108
    assert set(registros["GRUPO"]) == set(GRUPOS)
    assert registros.groupby("GRUPO")["MES"].apply(set).eq(set(range(1, 13))).all()
    assert not registros.duplicated(["NIVEL_META", "GRUPO", "VEICULO", "ANO", "MES", "REVISAO"]).any()
    assert set(registros["NIVEL_META"]) == {"GRUPO"}
    assert set(registros["VEICULO"]) == {""}
    assert set(registros["ANO"]) == {2026}
    assert set(registros["REVISAO"]) == {1}


def test_aliases_explicitos_aplicados_e_auditaveis():
    resultado = _preparar()
    assert set(resultado.aliases_aplicados) == {("RÁDIO MELODIA", "MELODIA"), ("CARREGA +", "CARREGA+")}
    assert {"RÁDIO MELODIA", "CARREGA +"}.isdisjoint(resultado.registros["GRUPO"])


def test_brasil_247_jan_mar_ativos_abr_dez_inativos_e_zero():
    registros = _preparar().registros
    brasil = registros.loc[registros["GRUPO"] == "BRASIL 247"].sort_values("MES")
    assert brasil.loc[brasil["MES"] <= 3, "ATIVO"].eq("SIM").all()
    assert brasil.loc[brasil["MES"] >= 4, "ATIVO"].eq("NAO").all()
    assert brasil.loc[brasil["MES"] >= 4, "VALOR_META"].eq(Decimal(0)).all()
    assert registros["ATIVO"].eq("NAO").sum() == 9
    assert registros.loc[registros["GRUPO"] != "BRASIL 247", "ATIVO"].eq("SIM").all()


def test_zero_outside_brasil_permanece_ativo_e_no_perimetro():
    fonte = _fonte()
    entidades = list(fonte.entidades)
    teads = entidades[0]
    valores = (Decimal(0), *teads.valores_mensais[1:])
    entidades[0] = replace(teads, valores_mensais=valores, meta_anual=sum(valores))
    preparado = _preparar(_consolidar(tuple(entidades)))
    teads_jan = preparado.registros.query("GRUPO == 'TEADS' and MES == 1").iloc[0]
    assert teads_jan["VALOR_META"] == Decimal(0)
    assert teads_jan["ATIVO"] == "SIM"
    assert any(entidade.grupo == "TEADS" for entidade in preparado.resultado_engine.meses[0].perimetro)


def test_centavos_normalizados_sem_residuos_formula_ou_perda_do_original():
    fonte = _fonte(residuos=True)
    original = fonte.entidades[0].valores_mensais[0]
    preparado = _preparar(fonte)
    assert fonte.entidades[0].valores_mensais[0] == original
    assert preparado.registros.iloc[0]["VALOR_META"] == Decimal("11.25")
    assert ("TEADS", 1, Decimal("-0.00000000001")) in preparado.residuos_normalizados
    for valor in preparado.registros["VALOR_META"]:
        assert isinstance(valor, Decimal)
        assert valor.is_finite() and valor >= 0
        assert valor.as_tuple().exponent == -2
        assert valor * 100 == (valor * 100).to_integral_value()


def test_reconciliacao_entidade_mes_anual_e_validacao_real_engine():
    fonte = _fonte()
    resultado = _preparar(fonte)
    assert len(resultado.por_entidade) == 9
    assert set(resultado.por_entidade["GRUPO"]) == set(GRUPOS)
    assert len(resultado.por_mes) == 12
    assert set(resultado.por_mes["MES"]) == set(range(1, 13))
    for tabela in (resultado.por_entidade, resultado.por_mes):
        assert tabela["DIFERENCA"].eq(Decimal(0)).all()
        assert tabela["STATUS"].eq("OK").all()
    assert resultado.por_entidade.set_index("GRUPO").loc["BRASIL 247", "MESES_ATIVOS"] == 3
    assert resultado.por_entidade.set_index("GRUPO").drop("BRASIL 247")["MESES_ATIVOS"].eq(12).all()
    assert resultado.meta_anual_centavos == int(fonte.total_anual * 100)
    assert len(resultado.validada) == 108
    assert resultado.validada["VALOR_META_CENTAVOS"].sum() == resultado.meta_anual_centavos
    assert isinstance(resultado.resultado_engine, ResultadoMetas)
    assert resultado.resultado_engine.meta_anual_centavos == resultado.meta_anual_centavos
    assert tuple(mes.meta_centavos for mes in resultado.resultado_engine.meses) == tuple(int(valor * 100) for valor in fonte.totais_mensais)


def test_reconciliacao_independente_bloqueia_divergencia_por_entidade():
    fonte = _fonte()
    entidades = list(fonte.entidades)
    entidades[0] = replace(entidades[0], meta_anual=entidades[0].meta_anual + Decimal("0.01"))
    with pytest.raises(carga.ErroCargaInicial):
        _preparar(replace(fonte, entidades=tuple(entidades)))


@pytest.mark.parametrize("mes", [1, 12])
def test_reconciliacao_independente_bloqueia_divergencia_por_mes(mes):
    fonte = _fonte()
    totais = list(fonte.totais_mensais)
    totais[mes - 1] += Decimal("0.01")
    with pytest.raises(carga.ErroCargaInicial):
        _preparar(replace(fonte, totais_mensais=tuple(totais)))


def test_reconciliacao_independente_bloqueia_divergencia_anual():
    fonte = _fonte()
    with pytest.raises(carga.ErroCargaInicial):
        _preparar(replace(fonte, total_anual=fonte.total_anual + Decimal("0.01")))


def test_total_oficial_guardado_sem_forcar_fixture_ao_total_real():
    with pytest.raises(carga.ErroCargaInicial):
        carga.preparar_carga(_fonte(), criado_em=TIMESTAMP, data_referencia=REFERENCIA)
    with pytest.raises(carga.ErroCargaInicial):
        _preparar(total_esperado_centavos=123)


@pytest.mark.parametrize("entrada", [
    TIMESTAMP,
    "2026-10-05T15:30:00Z",
    dt.datetime(2026, 10, 5, 15, 30, tzinfo=dt.timezone.utc),
])
def test_timestamp_unico_offset_sao_paulo_em_todos_registros(entrada):
    preparado = _preparar(criado_em=entrada)
    assert preparado.registros["CRIADO_EM"].unique().tolist() == [TIMESTAMP]
    assert preparado.validada["CRIADO_EM"].nunique() == 1
    assert str(preparado.validada["CRIADO_EM"].iloc[0].tzinfo) == "America/Sao_Paulo"


@pytest.mark.parametrize("entrada", [
    "2026-10-05T12:30:00", "2026-10-05", "05/10/2026 12:30", "",
    dt.datetime(2026, 10, 5, 12, 30), 46000, None,
])
def test_timestamp_ambiguo_nao_aceito(entrada):
    with pytest.raises(carga.ErroCargaInicial):
        _preparar(criado_em=entrada)


@pytest.mark.parametrize("nome", ["Parceiro estranho", "Radio Melodia", "Carrega", "Brasil247", "CARREGA  +"])
def test_entidade_desconhecida_sem_fuzzy_bloqueada(nome):
    fonte = _fonte()
    entidades = (replace(fonte.entidades[0], nome=nome), *fonte.entidades[1:])
    with pytest.raises(carga.ErroCargaInicial):
        _preparar(replace(fonte, entidades=entidades))


@pytest.mark.parametrize("nome", [" rádio melodia ", "MELODIA", "CARREGA+"])
def test_normalizacao_aprovada_sem_novas_equivalencias(nome):
    fonte = _fonte()
    indice = 8 if nome == "CARREGA+" else 7
    entidades = list(fonte.entidades)
    entidades[indice] = replace(entidades[indice], nome=nome)
    resultado = _preparar(replace(fonte, entidades=tuple(entidades)))
    assert set(resultado.registros["GRUPO"]) == set(GRUPOS)


@pytest.mark.parametrize("alteracao", ["ausente", "duplicada", "dez_meses", "treze_meses", "ano_incorreto"])
def test_estrutura_incompleta_duplicada_ou_ano_incorreto_bloqueada(alteracao):
    fonte = _fonte()
    if alteracao == "ausente":
        fonte = replace(fonte, entidades=fonte.entidades[:-1])
    elif alteracao == "duplicada":
        fonte = replace(fonte, entidades=(*fonte.entidades[:-1], fonte.entidades[0]))
    elif alteracao == "dez_meses":
        fonte = replace(fonte, entidades=(replace(fonte.entidades[0], valores_mensais=fonte.entidades[0].valores_mensais[:10]), *fonte.entidades[1:]))
    elif alteracao == "treze_meses":
        fonte = replace(fonte, totais_mensais=(*fonte.totais_mensais, Decimal(0)))
    else:
        fonte = replace(fonte, ano=2025)
    with pytest.raises(carga.ErroCargaInicial):
        _preparar(fonte)


@pytest.mark.parametrize("valor", [
    Decimal("-0.01"), Decimal("NaN"), Decimal("Infinity"), Decimal("-Infinity"),
    "=10+2", "12.25", "12,25", None, True,
])
def test_valor_invalido_nao_substituido_por_zero(valor):
    with pytest.raises(carga.ErroCargaInicial):
        _preparar(_alterar_valor(_fonte(), 0, 1, valor))


def test_brasil_inativo_com_valor_na_origem_bloqueado_sem_apagar_valor():
    fonte = _alterar_valor(_fonte(), 3, 4, Decimal("0.01"))
    with pytest.raises(carga.ErroCargaInicial):
        _preparar(fonte)
    assert fonte.entidades[3].valores_mensais[3] == Decimal("0.01")


def test_validacao_schema_real_nao_contornada(monkeypatch):
    def schema_bloqueado(*args, **kwargs):
        raise ErroDeMetas("Falha sintética de validação")
    monkeypatch.setattr(carga, "validar_metas", schema_bloqueado)
    with pytest.raises(ErroDeMetas, match="Falha sintética"):
        _preparar()


@pytest.mark.parametrize("compartilhadas", [False, True])
def test_ler_xlsx_resultados_numericos_sem_formulas(tmp_path, compartilhadas):
    fonte = _fonte()
    caminho = _xlsx(tmp_path / "sintetica.xlsx", fonte, strings_compartilhadas=compartilhadas)
    assert carga.ler_xlsx(caminho) == fonte


def test_formula_excel_usa_cache_numerico_nunca_calculo_ou_texto(tmp_path):
    fonte = _fonte()
    caminho = _xlsx(tmp_path / "sintetica.xlsx", fonte, alteracoes={"E17": ("999999+999999", fonte.entidades[0].valores_mensais[0])})
    lida = carga.ler_xlsx(caminho)
    assert lida == fonte
    assert _preparar(lida).registros.iloc[0]["VALOR_META"] == fonte.entidades[0].valores_mensais[0]


@pytest.mark.parametrize("referencia", ["E17", "P25", "D17", "D26", "E26"])
def test_formula_sem_cache_bloqueia_carga_nao_inventa_resultado(tmp_path, referencia):
    caminho = _xlsx(tmp_path / "sintetica.xlsx", alteracoes={referencia: ("SUM(E17:P17)", None)})
    with pytest.raises(carga.ErroCargaInicial):
        carga.ler_xlsx(caminho)


@pytest.mark.parametrize("alteracoes", [
    {"E16": "FEVEREIRO"}, {"P16": None}, {"B16": "PARCEIRO"},
    {"D16": "META 2025"}, {"B17": None}, {"E17": None},
    {"E17": "=2+3"}, {"E17": "123,45"}, {"B26": "Entidade extra"},
])
def test_layout_ou_celula_invalida_bloqueados(tmp_path, alteracoes):
    caminho = _xlsx(tmp_path / "sintetica.xlsx", alteracoes=alteracoes)
    with pytest.raises(carga.ErroCargaInicial):
        _preparar(carga.ler_xlsx(caminho))


def test_arquivo_nao_xlsx_bloqueado(tmp_path):
    caminho = tmp_path / "arquivo.xlsx"
    caminho.write_text("conteúdo sintético", encoding="utf-8")
    with pytest.raises(carga.ErroCargaInicial):
        carga.ler_xlsx(caminho)


def _cli_sintetica(monkeypatch):
    original = carga.preparar_carga
    def preparar_sem_total_real(fonte, **opcoes):
        opcoes["total_esperado_centavos"] = None
        opcoes["data_referencia"] = REFERENCIA
        return original(fonte, **opcoes)
    monkeypatch.setattr(carga, "preparar_carga", preparar_sem_total_real)
    monkeypatch.setattr(carga, "ler_xlsx", lambda caminho: _fonte())


def test_cli_padrao_apenas_preview_sem_qualquer_escrita(tmp_path, monkeypatch, capsys):
    _cli_sintetica(monkeypatch)
    monkeypatch.chdir(tmp_path)
    arquivos_antes = set(tmp_path.rglob("*"))
    assert carga.main(["sintetica.xlsx", "--criado-em", TIMESTAMP]) == 0
    relatorio = json.loads(capsys.readouterr().out)
    assert isinstance(relatorio, dict)
    assert set(tmp_path.rglob("*")) == arquivos_antes


def test_saida_local_so_quando_diretorio_explicito(tmp_path, monkeypatch, capsys):
    _cli_sintetica(monkeypatch)
    destino = tmp_path / "preview"
    assert carga.main(["sintetica.xlsx", "--criado-em", TIMESTAMP, "--diretorio-saida", str(destino)]) == 0
    assert {arquivo.name for arquivo in destino.iterdir()} == {"preview_metas.csv", "relatorio_metas.json"}
    preview = pd.read_csv(destino / "preview_metas.csv", keep_default_na=False)
    assert tuple(preview.columns) == COLUNAS_METAS
    assert len(preview) == 108
    assert preview["CRIADO_EM"].unique().tolist() == [TIMESTAMP]
    assert isinstance(json.loads((destino / "relatorio_metas.json").read_text(encoding="utf-8")), dict)


@pytest.mark.parametrize("flag", ["--write", "--gravar", "--google-sheets"])
def test_cli_nao_oferece_flag_para_escrita_no_sheets(tmp_path, monkeypatch, flag):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit) as erro:
        carga.main(["sintetica.xlsx", flag])
    assert erro.value.code == 2
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("nome", ["preview_metas.csv", "relatorio_metas.json"])
def test_preview_nao_sobrescreve_arquivo_existente(tmp_path, monkeypatch, capsys, nome):
    _cli_sintetica(monkeypatch)
    destino = tmp_path / "preview"
    destino.mkdir()
    existente = destino / nome
    existente.write_text("conteúdo anterior", encoding="utf-8")
    assert carga.main(["sintetica.xlsx", "--criado-em", TIMESTAMP, "--diretorio-saida", str(destino)]) == 1
    assert existente.read_text(encoding="utf-8") == "conteúdo anterior"
    assert len(list(destino.iterdir())) == 1
    assert "sobrescrito" in capsys.readouterr().err


def test_preview_real_nao_pode_ser_exportado_dentro_do_repositorio(monkeypatch, capsys):
    _cli_sintetica(monkeypatch)
    destino = carga.Path(carga.__file__).resolve().parents[1] / "preview_checkpoint_2_nao_criado"
    assert not destino.exists()
    assert carga.main(["sintetica.xlsx", "--criado-em", TIMESTAMP, "--diretorio-saida", str(destino)]) == 1
    assert not destino.exists()
    assert "fora do repositório" in capsys.readouterr().err


def test_erro_local_de_exportacao_e_amigavel(tmp_path, monkeypatch, capsys):
    _cli_sintetica(monkeypatch)
    destino = tmp_path / "preview"

    def negar_criacao(*args, **kwargs):
        raise PermissionError("Detalhe técnico desnecessário")

    monkeypatch.setattr(carga.Path, "mkdir", negar_criacao)
    assert carga.main(["sintetica.xlsx", "--criado-em", TIMESTAMP, "--diretorio-saida", str(destino)]) == 1
    erro = capsys.readouterr().err
    assert "permissões" in erro
    assert "Detalhe técnico" not in erro
