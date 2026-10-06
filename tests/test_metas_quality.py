"""Alertas de metas com registros fictícios e fronteiras temporais explícitas."""

from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

from src.data.metas_quality import coexistencia_niveis, revisoes_retroativas
from src.data.quality_checks import AlertaQualidade


_REFERENCIA = datetime(2026, 10, 5, tzinfo=ZoneInfo("America/Sao_Paulo"))
_COLUNAS = [
    "NIVEL_META", "GRUPO", "VEICULO", "ANO", "MES", "VALOR_META", "ATIVO",
    "REVISAO", "CRIADO_EM", "MOTIVO", "LINHA_ORIGEM",
]


def _meta(**campos):
    linha = {
        "NIVEL_META": "GRUPO",
        "GRUPO": "GRUPO TESTE",
        "VEICULO": "",
        "ANO": 2026,
        "MES": 1,
        "VALOR_META": 100,
        "ATIVO": "SIM",
        "REVISAO": 1,
        "CRIADO_EM": "2026-01-01T10:00:00-03:00",
        "MOTIVO": "Registro fictício para teste",
        "LINHA_ORIGEM": 2,
    }
    linha.update(campos)
    return linha


def _base(*linhas):
    return pd.DataFrame(linhas, columns=_COLUNAS)


def _revisoes(base):
    return revisoes_retroativas(base, data_referencia=_REFERENCIA)


def _coexistencia(base):
    return coexistencia_niveis(base, data_referencia=_REFERENCIA)


def test_revisao_inicial_nunca_e_retroativa():
    alerta = _revisoes(_base(_meta(CRIADO_EM="2026-10-01T10:00:00-03:00")))
    assert isinstance(alerta, AlertaQualidade)
    assert alerta.codigo == "METAS_REVISAO_RETROATIVA"
    assert alerta.quantidade == 0
    assert not alerta.possui_ocorrencias
    assert alerta.linhas.empty


@pytest.mark.parametrize(
    "criado, esperado",
    [
        ("2026-01-31T00:00:00-03:00", 0),
        ("2026-01-31T23:59:59.999999-03:00", 0),
        ("2026-02-01T00:00:00-03:00", 1),
        ("2026-02-01T02:59:59+00:00", 0),
        ("2026-02-01T03:00:00+00:00", 1),
        ("2026-02-01T00:00:00", 1),
    ],
)
def test_retroatividade_respeita_fim_do_mes_em_sao_paulo(criado, esperado):
    alerta = _revisoes(_base(_meta(REVISAO=2, CRIADO_EM=criado)))
    assert alerta.quantidade == esperado


def test_retroatividade_preserva_todas_as_revisoes_historicas_e_origem():
    base = _base(
        _meta(LINHA_ORIGEM=4),
        _meta(REVISAO=2, CRIADO_EM="2026-02-01T09:00:00-03:00", LINHA_ORIGEM=8),
        _meta(REVISAO=3, CRIADO_EM="2026-03-01T09:00:00-03:00", LINHA_ORIGEM=15),
    )
    antes = base.copy(deep=True)
    alerta = _revisoes(base)
    assert alerta.quantidade == 2
    assert alerta.linhas["REVISAO"].tolist() == [2, 3]
    assert alerta.linhas["LINHA_ORIGEM"].tolist() == [8, 15]
    assert set(_COLUNAS).issubset(alerta.linhas.columns)
    pd.testing.assert_frame_equal(base, antes)


@pytest.mark.parametrize(
    "ano, mes, criado, esperado",
    [
        (2024, 2, "2024-02-29T23:59:59-03:00", 0),
        (2024, 2, "2024-03-01T00:00:00-03:00", 1),
        (2025, 12, "2025-12-31T23:59:59-03:00", 0),
        (2025, 12, "2026-01-01T00:00:00-03:00", 1),
    ],
)
def test_retroatividade_mes_bissexto_e_virada_de_ano(ano, mes, criado, esperado):
    alerta = _revisoes(_base(_meta(ANO=ano, MES=mes, REVISAO=2, CRIADO_EM=criado)))
    assert alerta.quantidade == esperado


def test_coexistencia_conta_grupo_meses_e_preserva_todas_linhas_vigentes():
    base = _base(
        _meta(LINHA_ORIGEM=3),
        _meta(NIVEL_META="VEICULO", VEICULO="VEICULO A", LINHA_ORIGEM=5),
        _meta(NIVEL_META="VEICULO", VEICULO="VEICULO B", LINHA_ORIGEM=7),
        _meta(MES=2, LINHA_ORIGEM=9),
        _meta(MES=2, NIVEL_META="VEICULO", VEICULO="VEICULO A", LINHA_ORIGEM=11),
        _meta(GRUPO="OUTRO GRUPO", LINHA_ORIGEM=13),
    )
    antes = base.copy(deep=True)
    alerta = _coexistencia(base)
    assert isinstance(alerta, AlertaQualidade)
    assert alerta.codigo == "METAS_COEXISTENCIA_NIVEIS"
    assert alerta.quantidade == 2
    assert alerta.possui_ocorrencias
    assert sorted(alerta.linhas["LINHA_ORIGEM"].tolist()) == [3, 5, 7, 9, 11]
    assert alerta.detalhes["grupo_meses"] == [
        {"GRUPO": "GRUPO TESTE", "ANO": 2026, "MES": 1},
        {"GRUPO": "GRUPO TESTE", "ANO": 2026, "MES": 2},
    ]
    assert set(_COLUNAS).issubset(alerta.linhas.columns)
    pd.testing.assert_frame_equal(base, antes)


@pytest.mark.parametrize("ativo", ["SIM", "NAO"])
def test_coexistencia_independe_de_atividade_e_valor_zero(ativo):
    alerta = _coexistencia(_base(
        _meta(VALOR_META=0, ATIVO=ativo),
        _meta(NIVEL_META="VEICULO", VEICULO="VEICULO A", LINHA_ORIGEM=3),
    ))
    assert alerta.quantidade == 1
    assert len(alerta.linhas) == 2


def test_coexistencia_usa_maior_revisao_de_cada_slot():
    alerta = _coexistencia(_base(
        _meta(LINHA_ORIGEM=2),
        _meta(REVISAO=2, ATIVO="NAO", VALOR_META=0, LINHA_ORIGEM=4),
        _meta(NIVEL_META="VEICULO", VEICULO="VEICULO A", LINHA_ORIGEM=6),
        _meta(NIVEL_META="VEICULO", VEICULO="VEICULO A", REVISAO=2,
              LINHA_ORIGEM=8),
    ))
    assert alerta.quantidade == 1
    assert sorted(alerta.linhas["LINHA_ORIGEM"].tolist()) == [4, 8]
    assert alerta.linhas["REVISAO"].tolist() == [2, 2]


def test_niveis_em_meses_ou_grupos_diferentes_nao_coexistem():
    alerta = _coexistencia(_base(
        _meta(),
        _meta(MES=2, NIVEL_META="VEICULO", VEICULO="VEICULO A", LINHA_ORIGEM=3),
        _meta(GRUPO="OUTRO GRUPO", NIVEL_META="VEICULO", VEICULO="VEICULO B",
              LINHA_ORIGEM=4),
    ))
    assert alerta.quantidade == 0
    assert alerta.linhas.empty
    assert alerta.detalhes["grupo_meses"] == []


@pytest.mark.parametrize("verificador", [_revisoes, _coexistencia])
def test_alertas_sem_lancamentos_preservam_schema_e_nao_tem_ocorrencias(verificador):
    alerta = verificador(_base())
    assert alerta.quantidade == 0
    assert not alerta.possui_ocorrencias
    assert alerta.linhas.empty
    assert set(_COLUNAS).issubset(alerta.linhas.columns)


@pytest.mark.parametrize("verificador", [_revisoes, _coexistencia])
def test_dataframe_de_auditoria_nao_compartilha_dados_com_entrada(verificador):
    base = _base(
        _meta(REVISAO=2, CRIADO_EM="2026-02-02T09:00:00-03:00"),
        _meta(NIVEL_META="VEICULO", VEICULO="VEICULO A", LINHA_ORIGEM=3),
    )
    antes = base.copy(deep=True)
    alerta = verificador(base)
    alerta.linhas.loc[:, "MOTIVO"] = "Alterado somente no resultado do teste"
    pd.testing.assert_frame_equal(base, antes)
