"""Apresentação nativa das tabelas analíticas, sem alterar a base comercial.

O Styler conserva números no dataframe e envia sua formatação separadamente.
A cópia usada pela toolbar nativa recebe a mesma proteção do CSV explícito;
textos neutralizados são restaurados somente nos valores exibidos, por célula.
Assim, a ordenação textual dessas células pode considerar o apóstrofo protetor.
O CSV explícito continua sendo gerado a partir da tabela original.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Sequence

import pandas as pd
import streamlit as st
from pandas.io.formats.style import Styler

from src.components.cards import formatar_moeda
from src.data.cleaning import COL_VENCIMENTO_DATA
from src.data.csv_export import _neutralizar_formula


_MOEDAS = {"VALOR PI BRUTO", "VALOR PI LIQUIDO"}
_DATAS = {"INÍCIO", "FIM"}
_TEXTOS = {
    "GRUPO", "VEICULO", "PI", "AGENCIA", "CLIENTE", "CAMPANHA",
    "MÊS (GANHO)", "MÊS (VEICULAÇÃO)", "STATUS", "NOTA FISCAL", "EXECUTIVO",
}
_LARGURAS = {
    "GRUPO": 140, "VEICULO": 180, "PI": 120, "AGENCIA": 170,
    "CLIENTE": 220, "CAMPANHA": 300, "MÊS (GANHO)": 160,
    "MÊS (VEICULAÇÃO)": 180, "VENCIMENTO PI": 230, "STATUS": 200,
    "NOTA FISCAL": 160, "EXECUTIVO": 170,
}


def _ausente(valor: object) -> bool:
    return bool(pd.isna(valor))


def _texto(valor: object) -> str | None:
    return None if _ausente(valor) else str(valor)


def _formatar_data(valor: object) -> str:
    if _ausente(valor):
        return "—"
    if not isinstance(valor, (dt.date, dt.datetime, pd.Timestamp)):
        return str(valor)
    data = pd.Timestamp(valor)
    exibida = data.strftime("%d/%m/%Y")
    if any((data.hour, data.minute, data.second, data.microsecond, data.nanosecond)):
        exibida += data.strftime(" %H:%M")
        if any((data.second, data.microsecond, data.nanosecond)):
            exibida += data.strftime(":%S")
        if data.microsecond or data.nanosecond:
            fracao = f"{data.microsecond:06d}{data.nanosecond:03d}".rstrip("0")
            exibida += f".{fracao}"
    if data.tzinfo is not None:
        exibida += data.strftime(" %z")
    return exibida


def _vencimento_textual(valor: object, data_derivada: object) -> str | None:
    """Usa apenas a data derivada existente; não interpreta termos comerciais.

    Os números de VENCIMENTO foram comprovados como datas na fonte. Sua
    apresentação pode usar VENCIMENTO_PI_DATA, criado pela limpeza existente.
    Sem esse campo, um número permanece textual, sem inferir uma data.
    """
    if _ausente(valor):
        return None
    if isinstance(valor, str):
        return valor
    if isinstance(valor, (dt.date, dt.datetime, pd.Timestamp)):
        return _formatar_data(valor)
    if not _ausente(data_derivada):
        return _formatar_data(data_derivada)
    return str(valor)


def preparar_tabela(
    df: pd.DataFrame, *, colunas: Sequence[str] | None = None,
) -> Styler:
    """Cria cópia segura com formatos pt-BR, preservando ordem e campos pedidos.

    Passe o dataframe completo e ``colunas`` quando VENCIMENTO_PI_DATA estiver
    disponível. Índices repetidos são resetados somente na cópia de exibição.
    O dataframe original e seus valores/tipos nunca são modificados.
    """
    origem = df.reset_index(drop=True)
    campos = list(df.columns if colunas is None else colunas)
    apresentacao = origem.loc[:, campos].copy(deep=True)
    if "VENCIMENTO PI" in apresentacao:
        datas = (
            origem[COL_VENCIMENTO_DATA]
            if COL_VENCIMENTO_DATA in origem
            else pd.Series(pd.NaT, index=origem.index)
        )
        apresentacao["VENCIMENTO PI"] = [
            _vencimento_textual(valor, data)
            for valor, data in zip(apresentacao["VENCIMENTO PI"], datas)
        ]
    for coluna in _TEXTOS.intersection(apresentacao.columns):
        apresentacao[coluna] = apresentacao[coluna].map(_texto)

    # Preserva a correspondência posicional: '=1+1' e "'=1+1" podem acabar
    # iguais na cópia protegida, mas precisam continuar distintos na tela.
    restauracoes: list[tuple[int, str, str]] = []
    for coluna in apresentacao:
        serie = apresentacao[coluna]
        if not any(isinstance(valor, str) for valor in serie):
            continue
        protegida = serie.map(_neutralizar_formula, na_action="ignore")
        for indice, (original, seguro) in enumerate(zip(serie, protegida)):
            if isinstance(original, str) and original != seguro:
                restauracoes.append((indice, coluna, original))
        apresentacao[coluna] = protegida

    formatos = {
        coluna: (lambda valor: "—" if _ausente(valor) else formatar_moeda(valor))
        for coluna in _MOEDAS.intersection(campos)
    }
    formatos.update({coluna: _formatar_data for coluna in _DATAS.intersection(campos)})
    styler = apresentacao.style.format(formatos, na_rep="—")
    for indice, coluna, original in restauracoes:
        styler.format(
            lambda _valor, texto=original: texto,
            subset=pd.IndexSlice[[indice], [coluna]],
        )
    return styler


def configuracao_colunas(
    df: pd.DataFrame, *, colunas: Sequence[str] | None = None,
) -> dict:
    """Larguras e alinhamentos nativos sem sobrepor os formatos do Styler."""
    campos = list(df.columns if colunas is None else colunas)
    configuracao = {}
    for coluna in campos:
        if coluna in _MOEDAS:
            valores = [
                formatar_moeda(valor) for valor in df[coluna] if not _ausente(valor)
            ]
            largura = max(190, max((len(v) for v in valores), default=0) * 8 + 40)
            configuracao[coluna] = st.column_config.NumberColumn(
                width=largura, alignment="right",
            )
        elif coluna in _DATAS:
            valores = [_formatar_data(valor) for valor in df[coluna] if not _ausente(valor)]
            largura = max(160, max((len(v) for v in valores), default=0) * 8 + 40)
            configuracao[coluna] = st.column_config.DatetimeColumn(
                width=largura,
            )
        else:
            configuracao[coluna] = st.column_config.TextColumn(
                width=_LARGURAS.get(coluna, 170),
            )
    return configuracao
