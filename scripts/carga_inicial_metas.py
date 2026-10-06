"""Prepara e reconcilia META 2026, sem acesso ou escrita no Google Sheets.

Uso: python scripts/carga_inicial_metas.py arquivo.xlsx --criado-em ISO_COM_OFFSET
Por padrão, somente imprime o relatório. --diretorio-saida exporta um preview
CSV e um relatório JSON locais. Não existe flag nem função de gravação remota.
Resultados numéricos armazenados no XLSX são lidos sem executar fórmulas.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import posixpath
import sys
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext
from numbers import Integral, Real
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import BadZipFile, ZipFile

import pandas as pd

# Permite executar o script diretamente, além de importar nos testes.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data import metas, metrics
from src.data.cleaning import COL_GRUPO, COL_STATUS, COL_VALOR_LIQUIDO, COL_VEICULO
from src.data.metas_schema import (
    ALIASES_METAS,
    COLUNAS_METAS,
    ErroDeMetas,
    FUSO_METAS,
    normalizar_entidade,
    validar_metas,
)

GRUPOS_APROVADOS = (
    "TEADS", "INFOMONEY", "CLIMATEMPO", "BRASIL 247", "WEBEDIA", "FORBES",
    "DISNEY", "MELODIA", "CARREGA+",
)
MESES = (
    "JANEIRO", "FEVEREIRO", "MARÇO", "ABRIL", "MAIO", "JUNHO", "JULHO",
    "AGOSTO", "SETEMBRO", "OUTUBRO", "NOVEMBRO", "DEZEMBRO",
)
_COLUNAS_MESES = tuple("EFGHIJKLMNOP")
_NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
_REL_ID = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
_REL_PACKAGE = "{http://schemas.openxmlformats.org/package/2006/relationships}"
_CENTAVO = Decimal("0.01")
_MOTIVO = "Carga inicial de metas 2026; origem META 2026."


class ErroCargaInicial(ValueError):
    """Fonte incompleta, valor inválido ou reconciliação divergente."""


@dataclass(frozen=True)
class EntidadeOrigem:
    nome: str
    meta_anual: Decimal
    valores_mensais: tuple[Decimal, ...]


@dataclass(frozen=True)
class FonteMetas:
    ano: int
    entidades: tuple[EntidadeOrigem, ...]
    totais_mensais: tuple[Decimal, ...]
    total_anual: Decimal


@dataclass(frozen=True)
class CargaPreparada:
    registros: pd.DataFrame
    validada: pd.DataFrame
    resultado_engine: metas.ResultadoMetas
    por_entidade: pd.DataFrame
    por_mes: pd.DataFrame
    aliases_aplicados: tuple[tuple[str, str], ...]
    residuos_normalizados: tuple[tuple[str, int, Decimal], ...]
    meta_anual_centavos: int


def _decimal(valor, referencia: str) -> Decimal:
    if isinstance(valor, bool) or not isinstance(valor, (Decimal, Real)):
        raise ErroCargaInicial(f"{referencia}: resultado numérico obrigatório.")
    numero = Decimal(str(valor))
    if not numero.is_finite() or numero < 0:
        raise ErroCargaInicial(f"{referencia}: valor deve ser finito e não negativo.")
    return numero


def _normalizar(valor: Decimal) -> Decimal:
    # Somente a migração normaliza resultados Excel; a engine não arredonda vendas.
    with localcontext() as contexto:
        contexto.prec = max(28, len(valor.as_tuple().digits) + max(valor.adjusted(), 0) + 4)
        return valor.quantize(_CENTAVO, rounding=ROUND_HALF_UP)


def _reais(centavos: int) -> Decimal:
    sinal, digitos, expoente = Decimal(centavos).as_tuple()
    return Decimal((sinal, digitos, expoente - 2))


def ler_xlsx(caminho: str | Path) -> FonteMetas:
    """Lê somente o bloco aprovado da V3, incluindo seus controles originais.

    O ano e os meses são confirmados pelos cabeçalhos. O leitor usa o cache
    numérico de cada célula (<v>), inclusive para fórmulas compartilhadas;
    cache ausente ou erro Excel bloqueia a preparação. Nenhuma fórmula é lida
    como valor, recalculada ou transportada.
    """
    try:
        with ZipFile(caminho) as arquivo:
            livro = ET.fromstring(arquivo.read("xl/workbook.xml"))
            abas = [aba for aba in livro.findall("m:sheets/m:sheet", _NS) if aba.get("name") == "META 2026"]
            if len(abas) != 1:
                raise ErroCargaInicial("A fonte deve conter uma única aba META 2026.")
            relacoes = ET.fromstring(arquivo.read("xl/_rels/workbook.xml.rels"))
            relacao = next((r for r in relacoes.findall(f"{_REL_PACKAGE}Relationship") if r.get("Id") == abas[0].get(_REL_ID)), None)
            if relacao is None or relacao.get("TargetMode") == "External":
                raise ErroCargaInicial("A aba META 2026 não possui uma origem interna válida.")
            alvo = relacao.get("Target", "")
            nome_xml = alvo.lstrip("/") if alvo.startswith("/") else posixpath.normpath(posixpath.join("xl", alvo))
            raiz = ET.fromstring(arquivo.read(nome_xml))
            strings = []
            if "xl/sharedStrings.xml" in arquivo.namelist():
                compartilhadas = ET.fromstring(arquivo.read("xl/sharedStrings.xml"))
                strings = ["".join(t.text or "" for t in item.findall(".//m:t", _NS)) for item in compartilhadas.findall("m:si", _NS)]
            celulas = {celula.get("r"): celula for celula in raiz.findall("m:sheetData/m:row/m:c", _NS)}

            def texto(referencia):
                celula = celulas.get(referencia)
                if celula is None:
                    return ""
                if celula.get("t") == "inlineStr":
                    return "".join(t.text or "" for t in celula.findall("m:is//m:t", _NS))
                valor = celula.find("m:v", _NS)
                if valor is None or valor.text is None:
                    return ""
                if celula.get("t") == "s":
                    try:
                        indice = int(valor.text)
                        if indice < 0:
                            raise IndexError
                        return strings[indice]
                    except (ValueError, IndexError):
                        raise ErroCargaInicial(f"{referencia}: texto armazenado inválido.") from None
                if celula.get("t") == "str":
                    return valor.text
                raise ErroCargaInicial(f"{referencia}: cabeçalho ou entidade deve ser texto.")

            def numero(referencia):
                celula = celulas.get(referencia)
                valor = celula.find("m:v", _NS) if celula is not None else None
                if celula is None or celula.get("t", "n") != "n" or valor is None or not valor.text:
                    raise ErroCargaInicial(f"{referencia}: resultado numérico armazenado ausente ou inválido.")
                try:
                    return _decimal(Decimal(valor.text), referencia)
                except InvalidOperation:
                    raise ErroCargaInicial(f"{referencia}: resultado numérico inválido.") from None

            cabecalho_ano = texto("D16").strip().upper()
            if texto("B16").strip().upper() != "VEÍCULO" or cabecalho_ano != "META 2026":
                raise ErroCargaInicial("Cabeçalhos B16/D16 divergem da estrutura aprovada META 2026.")
            for coluna, mes in zip(_COLUNAS_MESES, MESES):
                if texto(f"{coluna}16").strip().upper().split(" - ")[0] != mes:
                    raise ErroCargaInicial(f"{coluna}16: mês ausente, duplicado ou fora de ordem.")
            if texto("B26").strip():
                raise ErroCargaInicial("Há uma entidade adicional no lugar da linha de total 26.")
            entidades = tuple(EntidadeOrigem(
                nome=texto(f"B{linha}"),
                meta_anual=numero(f"D{linha}"),
                valores_mensais=tuple(numero(f"{coluna}{linha}") for coluna in _COLUNAS_MESES),
            ) for linha in range(17, 26))
            return FonteMetas(
                ano=int(cabecalho_ano.split()[1]),
                entidades=entidades,
                totais_mensais=tuple(numero(f"{coluna}26") for coluna in _COLUNAS_MESES),
                total_anual=numero("D26"),
            )
    except (OSError, BadZipFile, ET.ParseError, KeyError):
        raise ErroCargaInicial("Não foi possível ler a estrutura XLSX aprovada.") from None


def _timestamp(criado_em: dt.datetime | str) -> dt.datetime:
    if isinstance(criado_em, str):
        try:
            if "T" not in criado_em:
                raise ValueError
            criado_em = dt.datetime.fromisoformat(criado_em.replace("Z", "+00:00"))
        except ValueError:
            raise ErroCargaInicial("CRIADO_EM deve ser uma data e hora ISO 8601 com offset.") from None
    if not isinstance(criado_em, dt.datetime) or criado_em.tzinfo is None or criado_em.utcoffset() is None:
        raise ErroCargaInicial("CRIADO_EM deve conter data, hora e offset explícito.")
    try:
        return criado_em.astimezone(FUSO_METAS)
    except (ValueError, OverflowError):
        raise ErroCargaInicial("CRIADO_EM não é representável em America/Sao_Paulo.") from None


def preparar_carga(
    fonte: FonteMetas,
    *,
    criado_em: dt.datetime | str,
    data_referencia=None,
    total_esperado_centavos: int | None = 2_790_000_000,
) -> CargaPreparada:
    """Wide → long, validação real do schema/engine e reconciliação independente.

    A referência anual é um controle, nunca um ajuste de valores. Para testar
    outras cifras sintéticas, pode-se injetar outro controle ou None. Vendas
    não são carregadas: a engine recebe uma tabela vazia apenas para conferir
    suas consolidações de METAS; resultados comerciais não são reportados.
    """
    instante = _timestamp(criado_em)
    referencia = data_referencia if data_referencia is not None else instante
    if isinstance(fonte.ano, bool) or not isinstance(fonte.ano, Integral) or fonte.ano != 2026:
        raise ErroCargaInicial("Esta carga inicial exige o ano 2026 confirmado na fonte.")
    if len(fonte.entidades) != 9 or len(fonte.totais_mensais) != 12:
        raise ErroCargaInicial("A fonte deve ter nove entidades e doze meses completos.")
    registros, aliases, residuos, originais = [], [], [], {}
    for entidade in fonte.entidades:
        grupo = normalizar_entidade(entidade.nome)
        if grupo not in GRUPOS_APROVADOS:
            raise ErroCargaInicial("Há uma entidade desconhecida; nenhum mapeamento por aproximação é permitido.")
        if grupo in originais:
            raise ErroCargaInicial("Há entidades duplicadas após a aplicação dos aliases aprovados.")
        if len(entidade.valores_mensais) != 12:
            raise ErroCargaInicial(f"{grupo}: os doze valores mensais são obrigatórios.")
        nome_origem = entidade.nome.strip().upper()
        if nome_origem in ALIASES_METAS:
            aliases.append((nome_origem, grupo))
        originais[grupo] = _decimal(entidade.meta_anual, f"{grupo}: meta anual original")
        mensais = tuple(_decimal(valor, f"{grupo}, mês {mes}") for mes, valor in enumerate(entidade.valores_mensais, start=1))
        if _normalizar(sum(mensais, Decimal(0))) != _normalizar(originais[grupo]):
            raise ErroCargaInicial(f"{grupo}: soma dos meses diverge da meta anual original.")
        for mes, original in enumerate(mensais, start=1):
            inativo = grupo == "BRASIL 247" and mes >= 4
            if inativo and original != 0:
                raise ErroCargaInicial("BRASIL 247: meses inativos devem estar zerados na origem; nenhum valor será descartado.")
            normalizado = _normalizar(original)
            if normalizado != original:
                residuos.append((grupo, mes, normalizado - original))
            registros.append(dict(zip(COLUNAS_METAS, (
                "GRUPO", grupo, "", fonte.ano, mes, normalizado,
                "NAO" if inativo else "SIM", 1, instante.isoformat(), _MOTIVO,
            ))))
    if set(originais) != set(GRUPOS_APROVADOS):
        raise ErroCargaInicial("A fonte não contém exatamente as nove entidades aprovadas.")

    bruto = pd.DataFrame(registros, columns=COLUNAS_METAS)
    validada = validar_metas(bruto, data_referencia=referencia)
    vendas_vazias = pd.DataFrame(columns=[COL_GRUPO, COL_VEICULO, COL_STATUS, COL_VALOR_LIQUIDO])
    vendas_vazias[metrics.coluna_mes("veiculacao")] = pd.Series(dtype="datetime64[ns]")
    resultado = metas.avaliar_metas(vendas_vazias, validada, fonte.ano, data_referencia=referencia)

    por_entidade = []
    for grupo, anual in originais.items():
        selecao = validada[validada["GRUPO"] == grupo]
        preparada = _reais(sum(int(valor) for valor in selecao.loc[selecao["ATIVO"] == "SIM", "VALOR_META_CENTAVOS"]))
        original = _normalizar(anual)
        if preparada != original:
            raise ErroCargaInicial(f"{grupo}: meta anual preparada diverge da fonte.")
        por_entidade.append({
            "GRUPO": grupo, "META_ANUAL_ORIGINAL": original,
            "META_ANUAL_PREPARADA": preparada, "DIFERENCA": preparada - original,
            "MESES_ATIVOS": int((selecao["ATIVO"] == "SIM").sum()), "STATUS": "OK",
        })
    por_mes = []
    for mes, controle in enumerate(fonte.totais_mensais, start=1):
        original = _normalizar(_decimal(controle, f"Controle mensal, mês {mes}"))
        soma_origem = sum((_decimal(e.valores_mensais[mes - 1], f"Origem, mês {mes}") for e in fonte.entidades), Decimal(0))
        preparada = resultado.meses[mes - 1].meta
        if _normalizar(soma_origem) != original or preparada != original:
            raise ErroCargaInicial(f"Mês {mes}: consolidação diverge do controle mensal original.")
        por_mes.append({
            "MES": mes, "META_CONSOLIDADA_ORIGINAL": original,
            "META_CONSOLIDADA_PREPARADA": preparada,
            "DIFERENCA": preparada - original, "STATUS": "OK",
        })
    anual_original = _normalizar(_decimal(fonte.total_anual, "Controle anual"))
    if any(_normalizar(valor) != anual_original for valor in (
        sum(originais.values(), Decimal(0)),
        sum((_decimal(v, "Controle mensal") for v in fonte.totais_mensais), Decimal(0)),
        resultado.meta_anual,
    )):
        raise ErroCargaInicial("Reconciliação anual diverge do controle original da planilha.")
    if total_esperado_centavos is not None and resultado.meta_anual_centavos != total_esperado_centavos:
        raise ErroCargaInicial("A meta anual diverge da referência aprovada para esta carga inicial.")
    return CargaPreparada(
        registros=bruto, validada=validada, resultado_engine=resultado,
        por_entidade=pd.DataFrame(por_entidade), por_mes=pd.DataFrame(por_mes),
        aliases_aplicados=tuple(aliases), residuos_normalizados=tuple(residuos),
        meta_anual_centavos=resultado.meta_anual_centavos,
    )


def _json(valor):
    if isinstance(valor, Decimal):
        return format(valor, "f")
    raise TypeError("Valor não serializável no relatório de metas.")


def relatorio(carga: CargaPreparada) -> dict:
    return {
        "veredito": "PRONTA PARA GRAVAÇÃO", "escrita_google_sheets": False,
        "registros": len(carga.registros), "entidades": len(carga.por_entidade), "meses": 12,
        "ano": carga.resultado_engine.ano,
        "criado_em_preview": carga.registros.iloc[0]["CRIADO_EM"],
        "meta_anual_centavos": carga.meta_anual_centavos,
        "por_entidade": carga.por_entidade.to_dict("records"),
        "por_mes": carga.por_mes.to_dict("records"),
        "aliases_aplicados": carga.aliases_aplicados,
        "residuos_normalizados": carga.residuos_normalizados,
        "preview": carga.registros.to_dict("records"),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("xlsx", type=Path)
    parser.add_argument("--criado-em", help="Timestamp ISO com offset para preview reproduzível.")
    parser.add_argument("--diretorio-saida", type=Path, help="Exporta somente arquivos locais; não grava na fonte.")
    args = parser.parse_args(argv)
    try:
        carga = preparar_carga(ler_xlsx(args.xlsx), criado_em=args.criado_em or dt.datetime.now(FUSO_METAS))
        texto = json.dumps(relatorio(carga), default=_json, ensure_ascii=False, indent=2)
        if args.diretorio_saida:
            if args.diretorio_saida.resolve().is_relative_to(Path(__file__).resolve().parents[1]):
                raise ErroCargaInicial("O preview da carga real deve ficar fora do repositório.")
            # Nunca permitir que um preview substitua o próprio XLSX de origem.
            destinos = [args.diretorio_saida / "preview_metas.csv", args.diretorio_saida / "relatorio_metas.json"]
            if any(destino.resolve() == args.xlsx.resolve() for destino in destinos):
                raise ErroCargaInicial("O destino do preview não pode substituir a fonte.")
            if any(destino.exists() for destino in destinos):
                raise ErroCargaInicial("Já existe um preview no destino. Escolha outro diretório; nenhum arquivo será sobrescrito.")
            args.diretorio_saida.mkdir(parents=True, exist_ok=True)
            with destinos[0].open("x", encoding="utf-8", newline="") as arquivo:
                writer = csv.DictWriter(arquivo, fieldnames=COLUNAS_METAS)
                writer.writeheader()
                writer.writerows(carga.registros.to_dict("records"))
            with destinos[1].open("x", encoding="utf-8") as arquivo:
                arquivo.write(texto + "\n")
        print(texto)
        return 0
    except (ErroCargaInicial, ErroDeMetas) as erro:
        print(f"BLOQUEADA: {erro}", file=sys.stderr)
        return 1
    except OSError:
        print("BLOQUEADA: Não foi possível gerar o preview local. Verifique o destino e as permissões.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
