"""Contrato e validação pura do log de metas; não lê nem altera a fonte."""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from numbers import Real
from types import MappingProxyType
from zoneinfo import ZoneInfo

import pandas as pd

COLUNAS_METAS = (
    "NIVEL_META", "GRUPO", "VEICULO", "ANO", "MES", "VALOR_META", "ATIVO",
    "REVISAO", "CRIADO_EM", "MOTIVO",
)
COL_VALOR_META_CENTAVOS = "VALOR_META_CENTAVOS"
COL_LINHA_ORIGEM = "LINHA_ORIGEM"
ALIASES_METAS = MappingProxyType({"RÁDIO MELODIA": "MELODIA", "CARREGA +": "CARREGA+"})
FUSO_METAS = ZoneInfo("America/Sao_Paulo")
_ISO_DATA_HORA = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d{1,6})?)?(?:Z|[+-]\d{2}:\d{2})?$")


@dataclass(frozen=True)
class ErroValidacaoMeta:
    linha: int
    campo: str
    codigo: str
    mensagem: str


class ErroDeMetas(Exception):
    """Falha local explícita, sem valores da fonte em mensagens de erro."""

    def __init__(self, mensagem: str, categoria: str = "validacao", erros=()):
        super().__init__(mensagem)
        self.categoria = categoria
        self.erros = tuple(erros)

    @property
    def linhas_invalidas(self) -> tuple[int, ...]:
        return tuple(sorted({erro.linha for erro in self.erros}))

    @property
    def quantidade_linhas_invalidas(self) -> int:
        return len(self.linhas_invalidas)


def normalizar_entidade(valor: str) -> str:
    """Trim e maiúsculas, com apenas as duas equivalências aprovadas."""
    if not isinstance(valor, str):
        return ""
    texto = valor.strip().upper()
    return ALIASES_METAS.get(texto, texto)


def data_local(referencia: dt.date | dt.datetime | None = None) -> dt.date:
    if referencia is None:
        return dt.datetime.now(FUSO_METAS).date()
    if isinstance(referencia, dt.datetime):
        if referencia.tzinfo is None:
            referencia = referencia.replace(tzinfo=FUSO_METAS)
        return referencia.astimezone(FUSO_METAS).date()
    if isinstance(referencia, dt.date):
        return referencia
    raise ValueError("A data de referência deve ser date ou datetime.")


def validar_cabecalho(colunas) -> tuple[str, ...]:
    nomes = tuple(coluna.strip() if isinstance(coluna, str) else "" for coluna in colunas)
    erros = []
    if any(not nome for nome in nomes):
        erros.append(ErroValidacaoMeta(1, "CABECALHO", "cabecalho_vazio", "Toda coluna deve ter cabeçalho."))
    if len(set(nomes)) != len(nomes):
        erros.append(ErroValidacaoMeta(1, "CABECALHO", "cabecalho_duplicado", "Cabeçalhos não podem se repetir."))
    if set(nomes) != set(COLUNAS_METAS):
        erros.append(ErroValidacaoMeta(1, "CABECALHO", "schema_divergente", "O cabeçalho deve conter somente os dez campos do contrato METAS."))
    if erros:
        raise ErroDeMetas("Cabeçalho de METAS inválido na linha 1.", "estrutura", erros)
    return nomes


def _vazio(valor) -> bool:
    if valor is None or (isinstance(valor, str) and not valor.strip()):
        return True
    try:
        return bool(pd.isna(valor))
    except (TypeError, ValueError):
        return False


def _numero(valor) -> Decimal | None:
    # bool, texto numérico e valores não finitos não são números do contrato.
    if isinstance(valor, bool) or type(valor).__name__ == "bool_":
        return None
    if not isinstance(valor, (Real, Decimal)):
        return None
    try:
        numero = Decimal(str(valor))
        return numero if numero.is_finite() else None
    except (InvalidOperation, ValueError):
        return None


def _inteiro(valor) -> int | None:
    numero = _numero(valor)
    if numero is None or numero != numero.to_integral_value():
        return None
    return int(numero)


def _centavos_exatos(valor: Decimal | None) -> int | None:
    if valor is None or valor < 0:
        return None
    numerador, denominador = valor.as_integer_ratio()
    centavos, fracao = divmod(numerador * 100, denominador)
    return centavos if fracao == 0 else None


def _timestamp(valor, *, normalizado: bool) -> dt.datetime | None:
    if isinstance(valor, dt.datetime) and normalizado and not pd.isna(valor):
        instante = valor
    elif isinstance(valor, str) and _ISO_DATA_HORA.fullmatch(valor.strip()):
        try:
            instante = dt.datetime.fromisoformat(valor.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    if instante.tzinfo is None:
        instante = instante.replace(tzinfo=FUSO_METAS)
    try:
        return instante.astimezone(FUSO_METAS)
    except (ValueError, OverflowError):
        return None


def validar_metas(df: pd.DataFrame, *, data_referencia=None) -> pd.DataFrame:
    """Valida o log completo ou falha com campos e linhas físicas inválidos.

    Metas viram centavos inteiros; vendas nunca passam por esta conversão.
    A saída pode ser revalidada sem alterar revisão, precisão ou origem.
    """
    if not isinstance(df, pd.DataFrame):
        raise ErroDeMetas("METAS deve ser uma tabela.", "estrutura")
    extras = {COL_LINHA_ORIGEM, COL_VALOR_META_CENTAVOS}
    colunas_fonte = [coluna for coluna in df.columns if coluna not in extras]
    validar_cabecalho(colunas_fonte)
    if df.columns.duplicated().any():
        raise ErroDeMetas("METAS contém colunas duplicadas.", "estrutura")
    # Normalizar nomes permite usar o mesmo contrato fora do loader.
    tabela = df.copy(deep=True)
    tabela.columns = [coluna.strip() for coluna in tabela.columns]
    ano_limite = data_local(data_referencia).year + 1
    normalizado = COL_VALOR_META_CENTAVOS in tabela.columns
    erros: list[ErroValidacaoMeta] = []
    registros = []
    chaves: dict[tuple, list[int]] = {}

    for numero, (_, linha) in enumerate(tabela.iterrows(), start=2):
        origem = _inteiro(linha.get(COL_LINHA_ORIGEM, numero))
        if origem is None or origem < 2:
            erros.append(ErroValidacaoMeta(numero, COL_LINHA_ORIGEM, "origem_invalida", "A linha física deve ser um inteiro a partir de 2."))
            origem = numero
        inicio_erros = len(erros)

        def falha(campo, codigo, mensagem):
            erros.append(ErroValidacaoMeta(origem, campo, codigo, mensagem))

        nivel = linha["NIVEL_META"].strip().upper() if isinstance(linha["NIVEL_META"], str) else ""
        grupo = normalizar_entidade(linha["GRUPO"])
        veiculo = "" if _vazio(linha["VEICULO"]) else normalizar_entidade(linha["VEICULO"])
        if nivel not in {"GRUPO", "VEICULO"}:
            falha("NIVEL_META", "nivel_invalido", "O nível deve ser GRUPO ou VEICULO.")
        if not grupo:
            falha("GRUPO", "grupo_obrigatorio", "GRUPO deve ser um texto preenchido.")
        if nivel == "GRUPO" and not _vazio(linha["VEICULO"]):
            falha("VEICULO", "veiculo_de_grupo", "VEICULO deve ficar vazio no nível GRUPO.")
        if nivel == "VEICULO" and not veiculo:
            falha("VEICULO", "veiculo_obrigatorio", "VEICULO deve ser um texto preenchido no nível VEICULO.")
        ano = _inteiro(linha["ANO"])
        if ano is None or not 2024 <= ano <= min(9999, ano_limite):
            falha("ANO", "ano_invalido", "ANO deve ser inteiro entre 2024 e o ano corrente mais um.")
        mes = _inteiro(linha["MES"])
        if mes is None or not 1 <= mes <= 12:
            falha("MES", "mes_invalido", "MES deve ser inteiro entre 1 e 12.")
        revisao = _inteiro(linha["REVISAO"])
        if revisao is None or revisao < 1:
            falha("REVISAO", "revisao_invalida", "REVISAO deve ser um inteiro positivo.")
        ativo = linha["ATIVO"].strip().upper() if isinstance(linha["ATIVO"], str) else ""
        if ativo not in {"SIM", "NAO"}:
            falha("ATIVO", "atividade_invalida", "ATIVO deve ser SIM ou NAO.")
        valor = _numero(linha["VALOR_META"])
        centavos = _centavos_exatos(valor)
        if centavos is None:
            falha("VALOR_META", "valor_invalido", "VALOR_META deve ser numérico, finito, não negativo e representável em centavos.")
        else:
            if ativo == "NAO" and centavos != 0:
                falha("VALOR_META", "inativo_com_valor", "Uma meta inativa deve ter VALOR_META zero.")
            if normalizado and _inteiro(linha[COL_VALOR_META_CENTAVOS]) != centavos:
                falha(COL_VALOR_META_CENTAVOS, "centavos_inconsistentes", "Os centavos devem corresponder a VALOR_META.")
        criado_em = _timestamp(linha["CRIADO_EM"], normalizado=normalizado)
        if criado_em is None:
            falha("CRIADO_EM", "timestamp_invalido", "CRIADO_EM deve conter data e hora ISO 8601 válidas, com T.")
        motivo = "" if _vazio(linha["MOTIVO"]) else linha["MOTIVO"]
        if not isinstance(motivo, str):
            falha("MOTIVO", "motivo_invalido", "MOTIVO deve ser texto ou ficar vazio.")
        registro = dict(zip(COLUNAS_METAS, (nivel, grupo, veiculo, ano, mes, valor, ativo, revisao, criado_em, motivo)))
        registro[COL_VALOR_META_CENTAVOS] = centavos
        registro[COL_LINHA_ORIGEM] = origem
        registros.append(registro)
        campos_chave = {"NIVEL_META", "GRUPO", "VEICULO", "ANO", "MES", "REVISAO"}
        if not any(erro.campo in campos_chave for erro in erros[inicio_erros:]):
            chave = (nivel, grupo, veiculo, ano, mes, revisao)
            chaves.setdefault(chave, []).append(origem)

    for origens in chaves.values():
        if len(origens) > 1:
            for origem in origens:
                erros.append(ErroValidacaoMeta(origem, "REVISAO", "slot_revisao_duplicado", "Slot e revisão se repetem após normalização dos nomes."))
    if erros:
        linhas = sorted({erro.linha for erro in erros})
        referencias = ", ".join(map(str, linhas))
        raise ErroDeMetas(f"METAS possui {len(linhas)} linha(s) inválida(s): {referencias}. Nenhuma meta foi consolidada.", erros=erros)
    return pd.DataFrame(registros, columns=[*COLUNAS_METAS, COL_VALOR_META_CENTAVOS, COL_LINHA_ORIGEM])
