"""Loader METAS offline: acesso somente leitura e erros isolados."""

from __future__ import annotations

import datetime as dt
import traceback

import pandas as pd
import pytest

from src.data import loader, metas_loader
from src.data.metas_schema import (
    COL_LINHA_ORIGEM,
    COLUNAS_METAS,
    ErroDeMetas,
)


REFERENCIA = dt.date(2026, 10, 5)


class FakeWorksheet:
    def __init__(self, valores, erro=None):
        self.valores = valores
        self.erro = erro
        self.leituras = []

    def get(self, **opcoes):
        self.leituras.append(opcoes)
        if self.erro:
            raise self.erro
        return self.valores


class FakePlanilha:
    def __init__(self, aba, erro=None):
        self.aba = aba
        self.erro = erro
        self.abas_solicitadas = []

    def worksheet(self, nome):
        self.abas_solicitadas.append(nome)
        if self.erro:
            raise self.erro
        return self.aba


class FakeCliente:
    def __init__(self, planilha, erro=None):
        self.planilha = planilha
        self.erro = erro
        self.ids_solicitados = []

    def open_by_key(self, spreadsheet_id):
        self.ids_solicitados.append(spreadsheet_id)
        if self.erro:
            raise self.erro
        return self.planilha


def _registro(**campos):
    linha = {
        "NIVEL_META": "GRUPO",
        "GRUPO": "PARCEIRO TESTE",
        "VEICULO": "",
        "ANO": 2026,
        "MES": 1,
        "VALOR_META": 1234.56,
        "ATIVO": "SIM",
        "REVISAO": 1,
        "CRIADO_EM": "2026-10-05T12:00:00-03:00",
        "MOTIVO": "TESTE OFFLINE",
    }
    linha.update(campos)
    return [linha[coluna] for coluna in COLUNAS_METAS]


def _fonte(monkeypatch, valores, *, etapa_erro=None):
    erro = RuntimeError("DETALHE_PRIVADO_DA_API_TESTE")
    aba = FakeWorksheet(valores, erro if etapa_erro == "leitura" else None)
    planilha = FakePlanilha(aba, erro if etapa_erro == "aba" else None)
    cliente = FakeCliente(planilha, erro if etapa_erro == "planilha" else None)
    chamadas = []

    def criar_cliente(credenciais):
        chamadas.append(credenciais)
        if etapa_erro == "autenticacao":
            raise erro
        return cliente

    monkeypatch.setattr(loader, "criar_cliente", criar_cliente)
    return cliente, planilha, aba, chamadas


def _carregar():
    return metas_loader.load_metas(
        "ID_APENAS_TESTE", {"campo": "VALOR_APENAS_TESTE"},
        data_referencia=REFERENCIA,
    )


def test_le_so_metas_por_id_sem_descobrir_abas_anuais(monkeypatch):
    cliente, planilha, aba, chamadas = _fonte(
        monkeypatch, [list(COLUNAS_METAS), _registro()],
    )
    monkeypatch.setattr(
        loader, "load_all_sheets",
        lambda *_: pytest.fail("O loader anual não deve ser chamado"),
    )
    df = _carregar()
    assert cliente.ids_solicitados == ["ID_APENAS_TESTE"]
    assert planilha.abas_solicitadas == ["METAS"]
    assert aba.leituras == [{"value_render_option": "UNFORMATTED_VALUE"}]
    assert chamadas == [{"campo": "VALOR_APENAS_TESTE"}]
    assert df[COL_LINHA_ORIGEM].tolist() == [2]
    assert df["VALOR_META_CENTAVOS"].tolist() == [123456]
    assert str(df.loc[0, "CRIADO_EM"].tzinfo) == "America/Sao_Paulo"


def test_preserva_numeros_fisicos_apos_linhas_vazias(monkeypatch):
    _fonte(monkeypatch, [
        list(COLUNAS_METAS), [], [None] * 10, _registro(),
        [" "] * 10, _registro(MES=2),
    ])
    df = _carregar()
    assert df[COL_LINHA_ORIGEM].tolist() == [4, 6]
    assert df["MES"].tolist() == [1, 2]


def test_linha_curta_preenche_motivo_opcional_sem_deslocamento(monkeypatch):
    _fonte(monkeypatch, [list(COLUNAS_METAS), _registro()[:-1]])
    df = _carregar()
    assert df.loc[0, "MES"] == 1
    assert df.loc[0, "VALOR_META_CENTAVOS"] == 123456


def test_cabecalho_reordenado_e_com_trim_eh_aceito(monkeypatch):
    _fonte(monkeypatch, [
        [f" {coluna} " for coluna in reversed(COLUNAS_METAS)],
        list(reversed(_registro())),
    ])
    df = _carregar()
    assert df.loc[0, "GRUPO"] == "PARCEIRO TESTE"
    assert df.loc[0, "VALOR_META_CENTAVOS"] == 123456


def test_apenas_cabecalho_representa_log_vazio_valido(monkeypatch):
    _fonte(monkeypatch, [list(COLUNAS_METAS)])
    df = _carregar()
    assert df.empty
    assert set(COLUNAS_METAS).issubset(df.columns)
    assert "VALOR_META_CENTAVOS" in df.columns
    assert COL_LINHA_ORIGEM in df.columns


@pytest.mark.parametrize("valores", [None, [], [[]], [[None] * 10]])
def test_sem_cabecalho_eh_erro(monkeypatch, valores):
    _fonte(monkeypatch, valores)
    with pytest.raises(ErroDeMetas):
        _carregar()


def test_nao_busca_cabecalho_em_linha_posterior(monkeypatch):
    _fonte(monkeypatch, [[], list(COLUNAS_METAS), _registro()])
    with pytest.raises(ErroDeMetas):
        _carregar()


@pytest.mark.parametrize("cabecalho", [
    list(COLUNAS_METAS[:-1]),
    [*COLUNAS_METAS[:-1], "ATIVO"],
    [*COLUNAS_METAS, "EXTRA"],
    [*COLUNAS_METAS, COL_LINHA_ORIGEM],
])
def test_cabecalho_divergente_nao_cria_dataframe_parcial(monkeypatch, cabecalho):
    _fonte(monkeypatch, [cabecalho, _registro()])
    with pytest.raises(ErroDeMetas):
        _carregar()


@pytest.mark.parametrize("valor", ["sem cabecalho", 0, False])
def test_rejeita_celula_extra_nao_vazia(monkeypatch, valor):
    _fonte(monkeypatch, [list(COLUNAS_METAS), _registro() + [valor]])
    with pytest.raises(ErroDeMetas, match="linha 2.*sem cabeçalho"):
        _carregar()


def test_celulas_extras_vazias_nao_perdem_dados(monkeypatch):
    _fonte(monkeypatch, [list(COLUNAS_METAS), _registro() + [None, " ", ""]])
    assert _carregar()["VALOR_META_CENTAVOS"].tolist() == [123456]


@pytest.mark.parametrize("valores", [
    "nao tabular", ["cabecalho nao tabular"], [list(COLUNAS_METAS), "linha"],
])
def test_resposta_nao_tabular_eh_erro_amigavel(monkeypatch, valores):
    _fonte(monkeypatch, valores)
    with pytest.raises(ErroDeMetas):
        _carregar()


@pytest.mark.parametrize("etapa", ["autenticacao", "planilha", "aba", "leitura"])
def test_erros_de_fonte_nao_expoem_detalhes_privados(monkeypatch, etapa):
    _fonte(monkeypatch, [list(COLUNAS_METAS)], etapa_erro=etapa)
    with pytest.raises(ErroDeMetas) as capturado:
        _carregar()
    erro = capturado.value
    assert erro.categoria == "fonte"
    assert "DETALHE_PRIVADO" not in str(erro)
    assert "ID_APENAS_TESTE" not in str(erro)
    assert "VALOR_APENAS_TESTE" not in str(erro)
    assert "DETALHE_PRIVADO" not in "".join(traceback.format_exception(erro))


def test_rejeita_serial_criado_em_preservando_linha_da_fonte(monkeypatch):
    _fonte(monkeypatch, [list(COLUNAS_METAS), [], _registro(CRIADO_EM=46000.5)])
    with pytest.raises(ErroDeMetas) as capturado:
        _carregar()
    assert any(
        erro.linha == 3 and erro.campo == "CRIADO_EM"
        for erro in capturado.value.erros
    )


@pytest.mark.parametrize("data", [
    dt.datetime(2026, 10, 5, 12),
    pd.Timestamp("2026-10-05T12:00:00-03:00"),
])
def test_rejeita_datetime_bruto_mesmo_que_validador_aceite_interno(monkeypatch, data):
    _fonte(monkeypatch, [list(COLUNAS_METAS), _registro(CRIADO_EM=data)])
    with pytest.raises(ErroDeMetas) as capturado:
        _carregar()
    assert any(
        erro.linha == 2 and erro.campo == "CRIADO_EM"
        for erro in capturado.value.erros
    )


def test_combina_erros_de_tipo_da_fonte_com_demais_validacoes(monkeypatch):
    _fonte(monkeypatch, [
        list(COLUNAS_METAS), _registro(CRIADO_EM=46000.5),
        _registro(MES=13),
    ])
    with pytest.raises(ErroDeMetas) as capturado:
        _carregar()
    erros = capturado.value.erros
    assert {erro.linha for erro in erros} == {2, 3}
    assert sum(erro.linha == 2 and erro.campo == "CRIADO_EM" for erro in erros) == 1


def test_falha_de_schema_nao_retira_linhas_invalidas_em_silencio(monkeypatch):
    _fonte(monkeypatch, [
        list(COLUNAS_METAS), _registro(), [], _registro(MES=13),
    ])
    with pytest.raises(ErroDeMetas) as capturado:
        _carregar()
    assert any(erro.linha == 4 for erro in capturado.value.erros)


def test_delega_data_referencia_e_nao_altera_resultado_validado(monkeypatch):
    _fonte(monkeypatch, [list(COLUNAS_METAS), _registro()])
    esperado = pd.DataFrame({"RESULTADO_VALIDADO": [123]})
    recebidos = []

    def validar(df, *, data_referencia):
        recebidos.append((df, data_referencia))
        return esperado

    monkeypatch.setattr(metas_loader, "validar_metas", validar)
    assert _carregar() is esperado
    bruto, referencia = recebidos[0]
    assert referencia == REFERENCIA
    assert bruto[COL_LINHA_ORIGEM].tolist() == [2]
    assert bruto["VALOR_META"].tolist() == [1234.56]


def test_usa_escopo_somente_leitura_existente():
    assert loader._SCOPES == ["https://www.googleapis.com/auth/spreadsheets.readonly"]
