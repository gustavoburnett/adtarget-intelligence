"""Leitura independente, somente leitura, do log da aba METAS.

Não descobre nem modifica abas anuais e não depende do Streamlit. O cache
de 15 minutos será aplicado pela integração da aplicação, separadamente
do cache das vendas. Datas ISO permanecem texto até a validação do schema.
"""

from __future__ import annotations

import datetime as _dt
from collections.abc import Mapping, Sequence
from typing import Any

import pandas as pd

from src.data import loader
from src.data.metas_schema import (
    COL_LINHA_ORIGEM,
    ErroDeMetas,
    ErroValidacaoMeta,
    validar_cabecalho,
    validar_metas,
)


def _celula_vazia(valor: Any) -> bool:
    return valor is None or (isinstance(valor, str) and not valor.strip())


def _linha_tabular(linha: Any) -> bool:
    return isinstance(linha, Sequence) and not isinstance(linha, (str, bytes))


def load_metas(
    spreadsheet_id: str,
    credenciais: Mapping[str, Any],
    *,
    data_referencia: _dt.date | _dt.datetime | None = None,
) -> pd.DataFrame:
    """Lê METAS e devolve o log validado, com números físicos das linhas.

    A leitura usa os resultados não formatados das células; o validador
    exige ISO textual em CRIADO_EM, sem inferir datas de seriais numéricos.
    Erros de fonte têm mensagens próprias, sem reproduzir detalhes da API.
    Um cabeçalho válido sem registros representa um log vazio válido.
    """
    try:
        cliente = loader.criar_cliente(credenciais)
    except Exception:
        raise ErroDeMetas(
            "Não foi possível autenticar a leitura de METAS. "
            "Verifique a configuração de acesso à fonte.",
            categoria="fonte",
        ) from None

    try:
        planilha = cliente.open_by_key(spreadsheet_id)
    except Exception:
        raise ErroDeMetas(
            "Não foi possível acessar a planilha de METAS. "
            "Verifique a configuração e a permissão de leitura.",
            categoria="fonte",
        ) from None

    try:
        aba = planilha.worksheet("METAS")
    except Exception:
        raise ErroDeMetas(
            "A aba METAS não existe ou não está acessível na fonte.",
            categoria="fonte",
        ) from None

    try:
        valores = aba.get(value_render_option="UNFORMATTED_VALUE")
    except Exception:
        raise ErroDeMetas(
            "Não foi possível ler a aba METAS. Tente atualizar novamente.",
            categoria="fonte",
        ) from None

    if not _linha_tabular(valores) or not valores:
        raise ErroDeMetas(
            "A aba METAS está vazia ou não possui cabeçalho na linha 1.",
            categoria="estrutura",
        )
    if not _linha_tabular(valores[0]):
        raise ErroDeMetas(
            "O cabeçalho de METAS na linha 1 não possui formato tabular.",
            categoria="estrutura",
        )

    cabecalho = validar_cabecalho(list(valores[0]))
    if COL_LINHA_ORIGEM in cabecalho:
        raise ErroDeMetas(
            "O cabeçalho de METAS contém uma coluna reservada à leitura.",
            categoria="estrutura",
        )
    largura = len(cabecalho)
    registros = []
    for numero_linha, linha in enumerate(valores[1:], start=2):
        if not _linha_tabular(linha):
            raise ErroDeMetas(
                f"A linha {numero_linha} de METAS não possui formato tabular.",
                categoria="estrutura",
            )
        if all(_celula_vazia(valor) for valor in linha):
            continue
        if any(not _celula_vazia(valor) for valor in linha[largura:]):
            raise ErroDeMetas(
                f"A linha {numero_linha} de METAS contém valores sem cabeçalho.",
                categoria="estrutura",
            )
        normalizada = list(linha[:largura])
        normalizada += [None] * (largura - len(normalizada))
        registro = dict(zip(cabecalho, normalizada))
        registro[COL_LINHA_ORIGEM] = numero_linha
        registros.append(registro)

    bruto = pd.DataFrame(registros, columns=[*cabecalho, COL_LINHA_ORIGEM])
    # O validador aceita datetimes internos na revalidação. Na fronteira
    # da fonte, porém, só ISO textual oferece um contrato sem ambiguidade.
    erros_data = tuple(
        ErroValidacaoMeta(
            linha=int(registro[COL_LINHA_ORIGEM]),
            campo="CRIADO_EM",
            codigo="iso_textual",
            mensagem="CRIADO_EM deve ser texto ISO 8601, nunca serial de data.",
        )
        for registro in registros
        if not isinstance(registro["CRIADO_EM"], str)
    )
    try:
        validado = validar_metas(bruto, data_referencia=data_referencia)
    except ErroDeMetas as erro:
        if not erros_data or not erro.erros:
            raise
        datas_invalidas = {item.linha for item in erros_data}
        erros = erros_data + tuple(
            item for item in erro.erros
            if item.campo != "CRIADO_EM" or item.linha not in datas_invalidas
        )
    else:
        if not erros_data:
            return validado
        erros = erros_data

    linhas_invalidas = sorted({item.linha for item in erros})
    raise ErroDeMetas(
        f"A aba METAS contém {len(linhas_invalidas)} linha(s) inválida(s): "
        + ", ".join(str(linha) for linha in linhas_invalidas)
        + ". Verifique os campos indicados na fonte.",
        categoria="validacao",
        erros=erros,
    ) from None
