"""Cadastro comercial independente de vendas e metas; leitura somente leitura."""
from __future__ import annotations

import datetime as dt
import hashlib
from dataclasses import dataclass
from typing import Mapping

from src.data import loader
from src.data.metas_schema import normalizar_entidade

COLUNAS = ("GRUPO", "STATUS_REPRESENTACAO", "CONFIRMADO_EM", "FONTE", "FIM_REPRESENTACAO")
NAO_INFORMADO = "NÃO INFORMADO"
STATUS_VALIDOS = {"ATIVA", "ENCERRADA", NAO_INFORMADO}
# Impressão da referência pública homologada; nunca exibir o ID ou credenciais.
_FONTE_HOMOLOGADA_SHA256 = "d5ca5c6c7a0c77050a25cb9dfc74c180214d6fe448bec0e0e442eefa1bed30c1"
_PENDENCIA = "Validação de representações pendente; alertas anteriores preservados."


class ErroRepresentacoes(Exception):
    """Falha de fonte/estrutura, sem expor credenciais ou resposta da API."""


@dataclass(frozen=True)
class CadastroRepresentacoes:
    status_por_grupo: Mapping[str, str]
    avisos: tuple[str, ...] = ()
    fonte_confirmada: bool = False
    cadastro_acessivel: bool = False
    validacao_concluida: bool = False

    def status(self, grupo: str) -> str:
        return self.status_por_grupo.get(normalizar_entidade(grupo), NAO_INFORMADO)


def _texto(valor) -> str:
    return valor.strip() if isinstance(valor, str) else ""


def _data(valor, *, opcional=False) -> bool:
    if opcional and not _texto(valor):
        return valor is None or valor == "" or isinstance(valor, str)
    try:
        texto = _texto(valor)
        return dt.date.fromisoformat(texto).isoformat() == texto
    except ValueError:
        return False


def validar_representacoes(valores) -> CadastroRepresentacoes:
    if not isinstance(valores, list) or not valores or not isinstance(valores[0], list):
        raise ErroRepresentacoes("REPRESENTACOES sem cabeçalho válido.")
    cabecalho = [_texto(c) for c in valores[0]]
    if (len(set(cabecalho)) != len(cabecalho) or "" in cabecalho
            or not set(COLUNAS).issubset(cabecalho)):
        raise ErroRepresentacoes("Cabeçalho de REPRESENTACOES inválido.")
    registros: dict[str, str] = {}
    vistos: set[str] = set()
    avisos = []
    for numero, linha in enumerate(valores[1:], 2):
        if not isinstance(linha, list):
            raise ErroRepresentacoes("Formato de REPRESENTACOES inválido; alertas existentes preservados.")
        if not any(c is not None and str(c).strip() for c in linha):
            continue
        registro = dict(zip(cabecalho, list(linha) + [""] * len(cabecalho)))
        grupo = normalizar_entidade(registro["GRUPO"])
        status = _texto(registro["STATUS_REPRESENTACAO"]).upper() or NAO_INFORMADO
        valido = (
            bool(grupo) and status in STATUS_VALIDOS
            and not any(c is not None and str(c).strip() for c in linha[len(cabecalho):])
            and _data(registro["FIM_REPRESENTACAO"], opcional=True)
            and (status == NAO_INFORMADO or (
                _data(registro["CONFIRMADO_EM"]) and bool(_texto(registro["FONTE"]))
            ))
        )
        if grupo in vistos:
            registros[grupo] = NAO_INFORMADO
            avisos.append(f"REPRESENTACOES: identidade duplicada na linha {numero}; status NÃO INFORMADO.")
        else:
            registros[grupo] = status if valido else NAO_INFORMADO
            if not valido:
                avisos.append(f"REPRESENTACOES: linha {numero} inválida; status NÃO INFORMADO.")
        vistos.add(grupo)
    return CadastroRepresentacoes(registros, tuple(avisos))


def load_representacoes(spreadsheet_id: str, credenciais: Mapping) -> CadastroRepresentacoes:
    """Valida a fonte no próprio ambiente, sem expor configuração ou exceções.

    O chamador guarda tanto sucesso como pendência no cache de 15 minutos.
    Catraca é uma evidência de homologação; a regra de exclusão segue genérica.
    """
    fonte_confirmada = False
    cadastro_acessivel = False
    try:
        planilha = loader.criar_cliente(credenciais).open_by_key(spreadsheet_id)
        metadata = planilha.fetch_sheet_metadata(params={"fields": "spreadsheetId"})
        identidade = metadata.get("spreadsheetId")
        fonte_confirmada = (
            isinstance(identidade, str)
            and hashlib.sha256(identidade.encode()).hexdigest() == _FONTE_HOMOLOGADA_SHA256
        )
        if not fonte_confirmada:
            return CadastroRepresentacoes({}, (_PENDENCIA,))
        valores = planilha.worksheet("REPRESENTACOES").get(value_render_option="UNFORMATTED_VALUE")
        cadastro_acessivel = True
        cadastro = validar_representacoes(valores)
        if cadastro.status("CATRACA LIVRE") != "ENCERRADA":
            return CadastroRepresentacoes(
                {}, (_PENDENCIA, *cadastro.avisos), fonte_confirmada=True, cadastro_acessivel=True,
            )
        return CadastroRepresentacoes(
            cadastro.status_por_grupo, cadastro.avisos,
            fonte_confirmada=True, cadastro_acessivel=True, validacao_concluida=True,
        )
    except Exception:
        # Falhas previstas de acesso/estrutura não escapam ao cache nem aos logs.
        return CadastroRepresentacoes(
            {}, (_PENDENCIA,), fonte_confirmada=fonte_confirmada,
            cadastro_acessivel=cadastro_acessivel,
        )
