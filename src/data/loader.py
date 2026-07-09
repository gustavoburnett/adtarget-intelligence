"""Conexão e leitura bruta do Google Sheets (documento 03).

Responsabilidade ÚNICA deste módulo: autenticar com a Service Account,
descobrir as abas de ano e devolver um DataFrame bruto concatenado com a
coluna ANO_ABA. Nenhuma limpeza ou cálculo acontece aqui — isso é papel de
cleaning.py e metrics.py, executados na sequência.

Regras implementadas (documento 03, "Leitura do Google Sheets"):
- planilha aberta pelo ID do arquivo, nunca pela URL
- descoberta automática de abas cujo nome é um ano de 4 dígitos
- leitura com value_render_option=UNFORMATTED_VALUE (número puro, não "R$")
- validação das colunas esperadas, com erro claro em caso de divergência
- resultado de cada aba vira DataFrame; concatenação final com ANO_ABA

O cache (st.cache_data, ttl=900) é aplicado sobre load_all_sheets na
integração do app.py, mantendo este módulo livre de dependência do
Streamlit e 100% testável.
"""

from __future__ import annotations

import re
from typing import Any, Mapping

import pandas as pd

#: Escopo mínimo necessário: somente leitura
_SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

#: Padrão de nome de aba de ano (ex: "2024", "2025", "2026", futuras "2027"...)
_PADRAO_ABA_ANO = re.compile(r"^\d{4}$")

#: Colunas obrigatórias em TODAS as abas (documento 01)
COLUNAS_OBRIGATORIAS = [
    "PRAÇA",
    "EXECUTIVO",
    "GRUPO",
    "VEICULO",
    "PI",
    "AGENCIA",
    "CLIENTE",
    "CAMPANHA",
    "MÊS (GANHO)",
    "MÊS (VEICULAÇÃO)",
    "INÍCIO",
    "FIM",
    "VALOR PI BRUTO",
    "VALOR PI LIQUIDO",
    "VENCIMENTO PI",
    "STATUS",
    "NOTA FISCAL",
    "DATA DE CRIAÇÃO",
    "OBSERVAÇÃO",
]

#: Colunas que existem apenas na aba 2026 em diante (documento 01)
COLUNAS_OPCIONAIS = ["DATA FATURAMENTO", "DIAS EM ABERTO"]

#: Coluna adicionada na concatenação, indicando a aba de origem
COL_ANO_ABA = "ANO_ABA"


class ErroDeCarga(Exception):
    """Erro de leitura/validação da planilha, com mensagem amigável.

    A camada de interface captura esta exceção e exibe a mensagem ao
    usuário (nunca um stack trace bruto — risco registrado no documento 03).
    """


def criar_cliente(credenciais: Mapping[str, Any]):
    """Cria o cliente gspread autenticado via Service Account.

    ``credenciais`` é o dicionário lido de st.secrets["gcp_service_account"]
    (formato TOML — nunca um arquivo JSON solto no repositório).
    """
    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except ImportError as exc:  # pragma: no cover - depende do ambiente
        raise ErroDeCarga(
            "Bibliotecas de acesso ao Google Sheets não instaladas. "
            "Execute: pip install -r requirements.txt"
        ) from exc

    try:
        creds = Credentials.from_service_account_info(
            dict(credenciais), scopes=_SCOPES
        )
        return gspread.authorize(creds)
    except Exception as exc:
        raise ErroDeCarga(
            "Credenciais do Google não configuradas corretamente. "
            "Verifique o bloco [gcp_service_account] do secrets.toml."
        ) from exc


def descobrir_abas_de_ano(planilha) -> list:
    """Retorna as worksheets cujo título é um ano de 4 dígitos.

    Descoberta automática (documento 03): quando a aba "2027" for criada na
    planilha, ela passa a ser lida sem alteração de código.
    """
    return [
        aba for aba in planilha.worksheets() if _PADRAO_ABA_ANO.match(aba.title)
    ]


def validar_colunas(colunas: list[str], nome_aba: str) -> None:
    """Valida a presença das colunas obrigatórias numa aba.

    Levanta ErroDeCarga com mensagem clara em caso de coluna ausente
    (mitigação do risco de coluna renomeada/reordenada sem aviso —
    documento 03). Colunas extras não são erro.
    """
    faltantes = [c for c in COLUNAS_OBRIGATORIAS if c not in colunas]
    if faltantes:
        raise ErroDeCarga(
            f"A aba '{nome_aba}' não contém as colunas esperadas: "
            f"{', '.join(faltantes)}. "
            "Verifique se a planilha de origem foi alterada."
        )


def _linha_vazia(linha: list) -> bool:
    """True quando todas as células da linha estão vazias/nulas."""
    return all(
        celula is None or str(celula).strip() == "" for celula in linha
    )


def _localizar_cabecalho(valores: list[list], nome_aba: str) -> tuple[int, list[str]]:
    """Localiza a primeira linha válida de cabeçalho da aba.

    A planilha real pode ter linhas vazias (ou de título) ANTES do
    cabeçalho verdadeiro — o cabeçalho não pode ser assumido como a
    primeira linha da aba. Estratégia:

    1. Percorre as linhas e retorna a primeira que contém TODAS as
       colunas obrigatórias (essa é a linha de cabeçalho).
    2. Se nenhuma linha satisfaz o critério, valida a primeira linha não
       vazia como candidata, para que o erro aponte exatamente quais
       colunas obrigatórias estão faltando (mitigação do risco de coluna
       renomeada — documento 03).
    """
    primeiro_nao_vazio: int | None = None
    for indice, linha in enumerate(valores):
        if _linha_vazia(linha):
            continue
        celulas = [str(c).strip() for c in linha]
        if primeiro_nao_vazio is None:
            primeiro_nao_vazio = indice
        if all(coluna in celulas for coluna in COLUNAS_OBRIGATORIAS):
            return indice, celulas

    if primeiro_nao_vazio is None:
        raise ErroDeCarga(
            f"A aba '{nome_aba}' está vazia ou não possui um cabeçalho "
            "reconhecível."
        )
    # Nenhuma linha contém o cabeçalho completo: gera o erro específico
    # nomeando as colunas faltantes da melhor candidata.
    candidata = [str(c).strip() for c in valores[primeiro_nao_vazio]]
    validar_colunas(candidata, nome_aba)
    return primeiro_nao_vazio, candidata  # inalcançável: a linha acima levanta


def _aba_para_dataframe(aba) -> pd.DataFrame:
    """Converte uma worksheet em DataFrame bruto.

    Leitura com UNFORMATTED_VALUE para garantir número puro nas colunas
    monetárias (nunca "R$ 99.879,98" como texto). O cabeçalho é localizado
    automaticamente (pode não estar na primeira linha da aba). Linhas
    totalmente vazias são descartadas; totais pré-calculados NÃO são
    filtrados aqui de forma especial — a planilha mantém os dados
    transacionais nas linhas e a aplicação recalcula tudo a partir delas
    (documento 02).
    """
    valores = aba.get(value_render_option="UNFORMATTED_VALUE")
    if not valores:
        return pd.DataFrame()

    indice_cabecalho, cabecalho = _localizar_cabecalho(valores, aba.title)

    linhas = valores[indice_cabecalho + 1 :]
    if not linhas:
        return pd.DataFrame()
    largura = len(cabecalho)
    # A API pode devolver linhas mais curtas (células finais vazias)
    linhas_normalizadas = [
        linha + [None] * (largura - len(linha)) if len(linha) < largura else linha[:largura]
        for linha in linhas
    ]
    df = pd.DataFrame(linhas_normalizadas, columns=cabecalho)

    # Descarta linhas totalmente vazias (sobras de formatação da planilha)
    df = df.dropna(how="all")
    df = df[~df.apply(lambda r: all(str(v).strip() == "" for v in r if v is not None), axis=1)]
    return df.reset_index(drop=True)


def load_all_sheets(
    spreadsheet_id: str, credenciais: Mapping[str, Any]
) -> pd.DataFrame:
    """Lê todas as abas de ano e devolve um único DataFrame bruto.

    Cada aba vira um DataFrame; a concatenação final recebe a coluna
    ANO_ABA (int) indicando a origem. O resultado é dado BRUTO: a
    normalização é feita na sequência por cleaning.limpar_dataframe.
    """
    cliente = criar_cliente(credenciais)
    try:
        planilha = cliente.open_by_key(spreadsheet_id)
    except Exception as exc:
        raise ErroDeCarga(
            "Não foi possível abrir a planilha. Verifique o spreadsheet_id "
            "no secrets.toml e se a Service Account tem permissão de Leitor."
        ) from exc

    abas = descobrir_abas_de_ano(planilha)
    if not abas:
        raise ErroDeCarga(
            "Nenhuma aba de ano (nome com 4 dígitos) encontrada na planilha."
        )

    quadros = []
    for aba in abas:
        df = _aba_para_dataframe(aba)
        if df.empty:
            continue
        df[COL_ANO_ABA] = int(aba.title)
        quadros.append(df)

    if not quadros:
        raise ErroDeCarga("As abas de ano foram encontradas, mas estão vazias.")

    return pd.concat(quadros, ignore_index=True)
