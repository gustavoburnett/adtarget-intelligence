"""Validações do log METAS com registros exclusivamente sintéticos."""

import datetime as dt
from decimal import Decimal

import pandas as pd
import pytest

from src.data.metas_schema import (
    ALIASES_METAS,
    COL_LINHA_ORIGEM,
    COL_VALOR_META_CENTAVOS,
    COLUNAS_METAS,
    ErroDeMetas,
    data_local,
    normalizar_entidade,
    validar_cabecalho,
    validar_metas,
)

REFERENCIA = dt.date(2026, 10, 5)


def _linha(**campos):
    registro = dict(zip(COLUNAS_METAS, (
        "GRUPO", "GRUPO TESTE", "", 2026, 1, Decimal("123.45"),
        "SIM", 1, "2026-10-05T12:00:00-03:00", "",
    )))
    registro.update(campos)
    return registro


def _validar(*linhas):
    return validar_metas(pd.DataFrame(linhas, columns=COLUNAS_METAS), data_referencia=REFERENCIA)


def test_normalizacao_centavos_fuso_e_invariancia():
    fonte = pd.DataFrame([_linha(GRUPO=" rádio melodia ", ATIVO=" sim ", REVISAO=2.0)])
    original = fonte.copy(deep=True)
    resultado = validar_metas(fonte, data_referencia=REFERENCIA)
    pd.testing.assert_frame_equal(fonte, original)
    assert resultado.loc[0, "GRUPO"] == "MELODIA"
    assert resultado.loc[0, COL_VALOR_META_CENTAVOS] == 12345
    assert resultado.loc[0, "VALOR_META"] == Decimal("123.45")
    assert resultado.loc[0, "REVISAO"] == 2
    assert resultado.loc[0, COL_LINHA_ORIGEM] == 2
    assert str(resultado.loc[0, "CRIADO_EM"].tzinfo) == "America/Sao_Paulo"
    pd.testing.assert_frame_equal(validar_metas(resultado, data_referencia=REFERENCIA), resultado)


@pytest.mark.parametrize("entrada,esperado", [
    (" rádio melodia ", "MELODIA"), ("carrega +", "CARREGA+"),
    ("carrega+", "CARREGA+"), ("carrega", "CARREGA"),
    ("radio melodia", "RADIO MELODIA"), ("CARREGA  +", "CARREGA  +"),
    (" Parceiro Novo ", "PARCEIRO NOVO"),
])
def test_aliases_explicitos_sem_aproximacao(entrada, esperado):
    assert normalizar_entidade(entrada) == esperado


def test_tabela_de_aliases_nao_pode_ser_ampliada_por_mutacao():
    assert len(ALIASES_METAS) == 2
    with pytest.raises(TypeError):
        ALIASES_METAS["OUTRO"] = "ALVO"


@pytest.mark.parametrize("campos,campo", [
    ({"NIVEL_META": "CLIENTE"}, "NIVEL_META"),
    ({"NIVEL_META": None}, "NIVEL_META"),
    ({"GRUPO": " "}, "GRUPO"), ({"GRUPO": 123}, "GRUPO"),
    ({"VEICULO": "VEICULO TESTE"}, "VEICULO"),
    ({"NIVEL_META": "VEICULO", "VEICULO": ""}, "VEICULO"),
    ({"NIVEL_META": "VEICULO", "VEICULO": 123}, "VEICULO"),
    ({"ANO": 2023}, "ANO"), ({"ANO": 2028}, "ANO"),
    ({"ANO": "2026"}, "ANO"), ({"ANO": 2026.5}, "ANO"),
    ({"ANO": True}, "ANO"), ({"ANO": float("inf")}, "ANO"),
    ({"MES": 0}, "MES"), ({"MES": 13}, "MES"),
    ({"MES": "1"}, "MES"), ({"MES": 1.1}, "MES"), ({"MES": False}, "MES"),
    ({"VALOR_META": -0.01}, "VALOR_META"),
    ({"VALOR_META": "123,45"}, "VALOR_META"),
    ({"VALOR_META": "123.45"}, "VALOR_META"),
    ({"VALOR_META": float("nan")}, "VALOR_META"),
    ({"VALOR_META": float("inf")}, "VALOR_META"),
    ({"VALOR_META": True}, "VALOR_META"),
    ({"VALOR_META": Decimal("1.001")}, "VALOR_META"),
    ({"VALOR_META": 0.30000000000000004}, "VALOR_META"),
    ({"ATIVO": "NAO", "VALOR_META": 1}, "VALOR_META"),
    ({"ATIVO": "NÃO"}, "ATIVO"), ({"ATIVO": "S"}, "ATIVO"),
    ({"ATIVO": True}, "ATIVO"), ({"ATIVO": ""}, "ATIVO"),
    ({"REVISAO": 0}, "REVISAO"), ({"REVISAO": -1}, "REVISAO"),
    ({"REVISAO": 1.5}, "REVISAO"), ({"REVISAO": "1"}, "REVISAO"),
    ({"REVISAO": True}, "REVISAO"),
    ({"CRIADO_EM": "05/10/2026 12:00"}, "CRIADO_EM"),
    ({"CRIADO_EM": "2026-10-05"}, "CRIADO_EM"),
    ({"CRIADO_EM": "2026-02-30T12:00:00"}, "CRIADO_EM"),
    ({"CRIADO_EM": "2026-10-05T24:00:00"}, "CRIADO_EM"),
    ({"CRIADO_EM": "2026-10-05 12:00:00"}, "CRIADO_EM"),
    ({"CRIADO_EM": 46000.5}, "CRIADO_EM"),
    ({"CRIADO_EM": dt.datetime(2026, 10, 5, 12)}, "CRIADO_EM"),
    ({"CRIADO_EM": None}, "CRIADO_EM"), ({"MOTIVO": 12}, "MOTIVO"),
])
def test_validacoes_rejeitam_ambiguidade_sem_expor_valores(campos, campo):
    with pytest.raises(ErroDeMetas) as capturado:
        _validar(_linha(**campos))
    assert any(erro.campo == campo and erro.linha == 2 for erro in capturado.value.erros)
    assert capturado.value.quantidade_linhas_invalidas == 1
    assert "GRUPO TESTE" not in str(capturado.value)


@pytest.mark.parametrize("valor,centavos", [
    (0, 0), (12, 1200), (12.3, 1230), (1234.56, 123456),
    (Decimal("12.3400"), 1234), (Decimal("0.01"), 1),
])
def test_meta_finita_representavel_em_centavos(valor, centavos):
    assert _validar(_linha(VALOR_META=valor)).loc[0, COL_VALOR_META_CENTAVOS] == centavos


@pytest.mark.parametrize("ativo", ["SIM", "NAO"])
def test_zero_preserva_atividade_explicita(ativo):
    resultado = _validar(_linha(VALOR_META=0, ATIVO=ativo))
    assert resultado.loc[0, "ATIVO"] == ativo
    assert resultado.loc[0, COL_VALOR_META_CENTAVOS] == 0


def test_meta_veiculo_preserva_par_grupo_e_alias():
    resultado = _validar(_linha(NIVEL_META=" veiculo ", GRUPO=" grupo teste ", VEICULO=" Carrega + "))
    assert resultado.loc[0, "NIVEL_META"] == "VEICULO"
    assert resultado.loc[0, "GRUPO"] == "GRUPO TESTE"
    assert resultado.loc[0, "VEICULO"] == "CARREGA+"


@pytest.mark.parametrize("instante,hora", [
    ("2026-10-05T12:00:00", 12), ("2026-10-05T12:00", 12),
    ("2026-10-05T15:00:00Z", 12), ("2026-10-05T15:00:00+00:00", 12),
    ("2026-10-05T10:00:00-05:00", 12),
])
def test_iso_8601_com_ou_sem_offset(instante, hora):
    resultado = _validar(_linha(CRIADO_EM=instante))
    assert resultado.loc[0, "CRIADO_EM"].hour == hora
    assert str(resultado.loc[0, "CRIADO_EM"].tzinfo) == "America/Sao_Paulo"


def test_slot_revisao_duplicado_apos_alias_reporta_todas_as_linhas():
    fonte = pd.DataFrame([
        _linha(GRUPO="CARREGA +", LINHA_ORIGEM=4),
        _linha(GRUPO="CARREGA+", LINHA_ORIGEM=8),
    ])
    with pytest.raises(ErroDeMetas) as capturado:
        validar_metas(fonte, data_referencia=REFERENCIA)
    assert capturado.value.linhas_invalidas == (4, 8)
    assert all(erro.codigo == "slot_revisao_duplicado" for erro in capturado.value.erros)


def test_mesmo_veiculo_em_grupos_distintos_nao_e_mesmo_slot():
    assert len(_validar(
        _linha(NIVEL_META="VEICULO", VEICULO="V TESTE", GRUPO="A TESTE"),
        _linha(NIVEL_META="VEICULO", VEICULO="V TESTE", GRUPO="B TESTE"),
    )) == 2


def test_revisoes_distintas_e_meses_distintos_sao_preservados_no_log():
    assert len(_validar(_linha(), _linha(REVISAO=2), _linha(MES=2))) == 3


def test_erros_agrupados_por_linha_fisica_sem_consolidacao_parcial():
    fonte = pd.DataFrame([
        _linha(LINHA_ORIGEM=5),
        _linha(MES=13, ATIVO="TALVEZ", LINHA_ORIGEM=9),
        _linha(ANO=2023, LINHA_ORIGEM=12),
    ])
    with pytest.raises(ErroDeMetas) as capturado:
        validar_metas(fonte, data_referencia=REFERENCIA)
    assert capturado.value.linhas_invalidas == (9, 12)
    assert capturado.value.quantidade_linhas_invalidas == 2


@pytest.mark.parametrize("colunas", [
    COLUNAS_METAS[:-1], (*COLUNAS_METAS, "EXTRA"),
    (*COLUNAS_METAS, " GRUPO "), (*COLUNAS_METAS[:-1], ""),
])
def test_cabecalho_incompleto_extra_ou_duplicado_e_invalido(colunas):
    with pytest.raises(ErroDeMetas) as capturado:
        validar_cabecalho(colunas)
    assert capturado.value.categoria == "estrutura"
    assert capturado.value.linhas_invalidas == (1,)


def test_cabecalho_admite_ordem_diferente_e_espacos_exteriores():
    assert validar_cabecalho([f" {coluna} " for coluna in reversed(COLUNAS_METAS)]) == tuple(reversed(COLUNAS_METAS))


def test_log_vazio_valido_nao_inventa_linhas():
    fonte = pd.DataFrame(columns=COLUNAS_METAS)
    assert validar_metas(fonte, data_referencia=REFERENCIA).empty


def test_coluna_de_centavos_interna_nao_pode_contradizer_valor():
    fonte = _validar(_linha())
    fonte.loc[0, COL_VALOR_META_CENTAVOS] += 1
    with pytest.raises(ErroDeMetas) as capturado:
        validar_metas(fonte, data_referencia=REFERENCIA)
    assert capturado.value.erros[0].campo == COL_VALOR_META_CENTAVOS


def test_limite_do_ano_usa_data_local_e_nao_utc():
    virada_utc = dt.datetime(2027, 1, 1, 1, tzinfo=dt.timezone.utc)
    assert data_local(virada_utc) == dt.date(2026, 12, 31)
    fonte = pd.DataFrame([_linha(ANO=2028)])
    with pytest.raises(ErroDeMetas):
        validar_metas(fonte, data_referencia=virada_utc)


def test_data_naive_e_interpretada_em_sao_paulo():
    assert data_local(dt.datetime(2026, 1, 1, 1)) == dt.date(2026, 1, 1)


def test_conversao_centavos_independe_da_precisao_do_contexto_decimal():
    valor = Decimal("123456789012345678901234567890.01")
    resultado = _validar(_linha(VALOR_META=valor))
    assert resultado.loc[0, COL_VALOR_META_CENTAVOS] == 12345678901234567890123456789001
    assert resultado.loc[0, "VALOR_META"] == valor


def test_valor_grande_com_fracao_de_centavo_nao_e_arredondado_em_silencio():
    with pytest.raises(ErroDeMetas):
        _validar(_linha(VALOR_META=Decimal("123456789012345678901234567.891")))


@pytest.mark.parametrize("instante", [
    "0001-01-01T00:00:00+14:00", "9999-12-31T23:59:59-12:00",
])
def test_timestamp_nao_representavel_no_fuso_tem_erro_amigavel(instante):
    with pytest.raises(ErroDeMetas) as capturado:
        _validar(_linha(CRIADO_EM=instante))
    assert capturado.value.erros[0].campo == "CRIADO_EM"


def test_colisao_de_slot_tambem_e_reportada_quando_ha_outro_campo_invalido():
    with pytest.raises(ErroDeMetas) as capturado:
        _validar(_linha(), _linha(ATIVO="INVALIDO"))
    assert capturado.value.linhas_invalidas == (2, 3)
    assert {erro.linha for erro in capturado.value.erros if erro.codigo == "slot_revisao_duplicado"} == {2, 3}
    assert any(erro.campo == "ATIVO" and erro.linha == 3 for erro in capturado.value.erros)
