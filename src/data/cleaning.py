"""Normalização genérica dos dados da Planilha de Vendas AdTarget.

Implementa EXCLUSIVAMENTE as regras genéricas de normalização definidas no
documento 02 (Regras de Negócio e Métricas), seção "Normalização de dados":

- trim (espaços no início/fim) nos campos de texto
- padronização de maiúscula/minúscula para agrupamento e comparação
- unificação de STATUS duplicados por formatação (ex: "FATURADO ")
- conversão de "MÊS/ANO" em texto (ex: "JANEIRO/2024") para data real
  (primeiro dia do mês)
- PI tratado sempre como texto, nunca como número ou data
- VENCIMENTO PI desdobrado em dois campos derivados: data (quando existir)
  e flag booleana de "contra apresentação"

IMPORTANTE (decisão 17 / documento 02): este módulo NÃO contém nenhuma
correção específica de cadastro individual. Inconsistências pontuais são
papel dos alertas genéricos em quality_checks.py, que apenas sinalizam.
"""

from __future__ import annotations

import datetime as _dt
from typing import Any

import pandas as pd

# ---------------------------------------------------------------------------
# Vocabulário controlado e nomes de colunas (documentos 01 e 02)
# ---------------------------------------------------------------------------

#: Vocabulário controlado de STATUS — 8 status oficiais (regra comercial
#: definida pelo responsável do projeto em 2026-07-09, supersedendo a
#: versão 0.2 da documentação). O campo STATUS passou a ser obrigatório na
#: planilha; não existe mais a categoria SEM_STATUS. Um status em branco ou
#: fora deste vocabulário é sinalizado pelo alerta de status desconhecido.
STATUS_VALIDOS = frozenset(
    {
        "A VEICULAR",
        "EM VEICULAÇÃO",
        "CHECKING",
        "AGUARD. DOC. VEÍCULO",
        "FATURADO",
        "DIRETO",
        "CANCELADO",
        "BONIFICADO",
    }
)

#: Nomes canônicos das colunas dimensionais (documento 01). Ponto único de
#: verdade: metrics.py e quality_checks.py importam daqui, nunca repetem
#: literais de nome de coluna.
COL_PRACA = "PRAÇA"
COL_EXECUTIVO = "EXECUTIVO"
COL_GRUPO = "GRUPO"
COL_VEICULO = "VEICULO"
COL_AGENCIA = "AGENCIA"
COL_CLIENTE = "CLIENTE"
COL_CAMPANHA = "CAMPANHA"

#: Campos de texto que recebem trim + padronização de caixa (documento 02)
COLUNAS_TEXTO = [
    COL_PRACA,
    COL_EXECUTIVO,
    COL_GRUPO,
    COL_VEICULO,
    COL_AGENCIA,
    COL_CLIENTE,
    COL_CAMPANHA,
]

COL_STATUS = "STATUS"
COL_PI = "PI"
COL_MES_GANHO = "MÊS (GANHO)"
COL_MES_VEICULACAO = "MÊS (VEICULAÇÃO)"
COL_VALOR_BRUTO = "VALOR PI BRUTO"
COL_VALOR_LIQUIDO = "VALOR PI LIQUIDO"
COL_VENCIMENTO = "VENCIMENTO PI"
COL_NOTA_FISCAL = "NOTA FISCAL"

#: Colunas derivadas criadas pela limpeza
COL_MES_GANHO_DATA = "MES_GANHO_DATA"
COL_MES_VEICULACAO_DATA = "MES_VEICULACAO_DATA"
COL_VENCIMENTO_DATA = "VENCIMENTO_PI_DATA"
COL_CONTRA_APRESENTACAO = "CONTRA_APRESENTACAO"

#: Prefixo de texto que caracteriza vencimento "contra apresentação"
#: (documento 01: valor literal "CONTRA APRESENT." em ~55% das linhas)
_PREFIXO_CONTRA_APRESENTACAO = "CONTRA APRESENT"

#: Meses em português para conversão de "MÊS/ANO" em data
_MESES_PT = {
    "JANEIRO": 1,
    "FEVEREIRO": 2,
    "MARÇO": 3,
    "MARCO": 3,
    "ABRIL": 4,
    "MAIO": 5,
    "JUNHO": 6,
    "JULHO": 7,
    "AGOSTO": 8,
    "SETEMBRO": 9,
    "OUTUBRO": 10,
    "NOVEMBRO": 11,
    "DEZEMBRO": 12,
}

#: Origem do número serial de datas do Google Sheets (UNFORMATTED_VALUE
#: devolve datas como número de dias desde 30/12/1899)
_ORIGEM_SERIAL_SHEETS = pd.Timestamp("1899-12-30")


# ---------------------------------------------------------------------------
# Helpers de conversão (unitários, testáveis isoladamente)
# ---------------------------------------------------------------------------

def normalizar_texto(valor: Any) -> str:
    """Trim + caixa alta para agrupamento/comparação.

    A base real já é integralmente escrita em caixa alta; a padronização de
    caixa aqui apenas garante que variações acidentais de digitação não gerem
    categorias duplicadas (regra genérica do documento 02). Valores vazios ou
    nulos viram string vazia.
    """
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return ""
    texto = str(valor).strip()
    return texto.upper()


def normalizar_status(valor: Any) -> str:
    """Normaliza STATUS: trim + caixa alta.

    Unifica duplicidades por formatação (ex: "FATURADO " -> "FATURADO").
    O campo é obrigatório na planilha: um valor em branco vira string vazia
    e é capturado pelo alerta de status desconhecido (guarda-corpo), sem
    nenhuma categoria interna especial. Status fora do vocabulário NÃO são
    corrigidos aqui — detecção é papel de quality_checks.py.
    """
    return normalizar_texto(valor)


def normalizar_pi(valor: Any) -> str:
    """Trata o campo PI sempre como texto (documento 01).

    Números inteiros lidos como float (ex: 12345.0) viram "12345".
    Datas geradas por engano pelo Google Sheets são mantidas como texto,
    sem qualquer tentativa de "corrigir" o valor.
    """
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return ""
    if isinstance(valor, float) and valor.is_integer():
        return str(int(valor))
    if isinstance(valor, (_dt.date, _dt.datetime, pd.Timestamp)):
        return str(valor)
    return str(valor).strip()


def converter_mes_ano(valor: Any) -> pd.Timestamp:
    """Converte texto "MÊS/ANO" (ex: "JANEIRO/2024") em data real.

    Retorna o primeiro dia do mês (documento 02). Valores vazios ou fora do
    padrão retornam NaT — nunca um erro, para não derrubar a carga por causa
    de uma linha malformada.
    """
    texto = normalizar_texto(valor)
    if not texto or "/" not in texto:
        return pd.NaT
    mes_txt, _, ano_txt = texto.partition("/")
    mes = _MESES_PT.get(mes_txt.strip())
    ano_txt = ano_txt.strip()
    if mes is None or not ano_txt.isdigit() or len(ano_txt) != 4:
        return pd.NaT
    return pd.Timestamp(year=int(ano_txt), month=mes, day=1)


def converter_data(valor: Any) -> pd.Timestamp:
    """Converte um valor genérico em data.

    Aceita: datetime/date nativos, número serial do Google Sheets
    (comportamento do UNFORMATTED_VALUE) e texto no padrão brasileiro
    (dd/mm/aaaa). Qualquer outro conteúdo retorna NaT.
    """
    if valor is None or (isinstance(valor, str) and not valor.strip()):
        return pd.NaT
    if isinstance(valor, pd.Timestamp):
        return valor
    if isinstance(valor, (_dt.datetime, _dt.date)):
        return pd.Timestamp(valor)
    if isinstance(valor, (int, float)):
        if pd.isna(valor):
            return pd.NaT
        return _ORIGEM_SERIAL_SHEETS + pd.Timedelta(days=float(valor))
    try:
        return pd.to_datetime(str(valor).strip(), dayfirst=True, errors="coerce")
    except (ValueError, TypeError):
        return pd.NaT


def converter_valor(valor: Any) -> float:
    """Converte valor monetário em float.

    Com UNFORMATTED_VALUE o valor já chega numérico; a conversão defensiva
    cobre célula vazia (vira 0.0) e eventuais strings numéricas. Não há
    parsing de formatação "R$" — a leitura correta é garantida no loader.
    """
    if valor is None or (isinstance(valor, str) and not valor.strip()):
        return 0.0
    convertido = pd.to_numeric(valor, errors="coerce")
    if pd.isna(convertido):
        return 0.0
    return float(convertido)


def desdobrar_vencimento(valor: Any) -> tuple[pd.Timestamp, bool]:
    """Desdobra VENCIMENTO PI em (data, flag contra apresentação).

    - Texto iniciando com "CONTRA APRESENT" -> (NaT, True)
    - Data real (nativa, serial ou texto) -> (data, False)
    - Vazio/nulo -> (NaT, False)
    """
    if isinstance(valor, str):
        texto = valor.strip().upper()
        if texto.startswith(_PREFIXO_CONTRA_APRESENTACAO):
            return pd.NaT, True
    data = converter_data(valor)
    return data, False


def normalizar_nota_fiscal(valor: Any) -> str:
    """Normaliza NOTA FISCAL como texto (trim + caixa alta).

    Números inteiros lidos como float viram texto sem o ".0". A semântica de
    "NF ausente" (célula em branco ou "SEM NF"/"SEM NOTA") é avaliada em
    quality_checks.py, não aqui.
    """
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return ""
    if isinstance(valor, float) and valor.is_integer():
        return str(int(valor))
    return str(valor).strip().upper()


# ---------------------------------------------------------------------------
# Pipeline principal de limpeza
# ---------------------------------------------------------------------------

def limpar_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica toda a normalização genérica e retorna um novo DataFrame.

    Executada sempre depois da leitura (loader) e antes de qualquer cálculo
    de métrica ou verificação de qualidade (documento 03). Nunca altera o
    DataFrame recebido (trabalha sobre cópia).

    Colunas derivadas criadas:
    - MES_GANHO_DATA / MES_VEICULACAO_DATA (Timestamp, dia 1 do mês)
    - VENCIMENTO_PI_DATA (Timestamp ou NaT)
    - CONTRA_APRESENTACAO (bool)
    """
    dados = df.copy()

    for coluna in COLUNAS_TEXTO:
        if coluna in dados.columns:
            dados[coluna] = dados[coluna].map(normalizar_texto)

    if COL_STATUS in dados.columns:
        dados[COL_STATUS] = dados[COL_STATUS].map(normalizar_status)

    if COL_PI in dados.columns:
        dados[COL_PI] = dados[COL_PI].map(normalizar_pi)

    if COL_MES_GANHO in dados.columns:
        dados[COL_MES_GANHO_DATA] = dados[COL_MES_GANHO].map(converter_mes_ano)
    if COL_MES_VEICULACAO in dados.columns:
        dados[COL_MES_VEICULACAO_DATA] = dados[COL_MES_VEICULACAO].map(
            converter_mes_ano
        )

    for coluna in (COL_VALOR_BRUTO, COL_VALOR_LIQUIDO):
        if coluna in dados.columns:
            dados[coluna] = dados[coluna].map(converter_valor)

    if COL_VENCIMENTO in dados.columns:
        desdobrado = dados[COL_VENCIMENTO].map(desdobrar_vencimento)
        dados[COL_VENCIMENTO_DATA] = desdobrado.map(lambda par: par[0])
        dados[COL_CONTRA_APRESENTACAO] = desdobrado.map(lambda par: par[1])

    if COL_NOTA_FISCAL in dados.columns:
        dados[COL_NOTA_FISCAL] = dados[COL_NOTA_FISCAL].map(normalizar_nota_fiscal)

    for coluna in ("INÍCIO", "FIM", "DATA DE CRIAÇÃO", "DATA FATURAMENTO"):
        if coluna in dados.columns:
            dados[coluna] = dados[coluna].map(converter_data)

    return dados
