"""Testes do Trend Hybrid Engine (Fase Trend Hybrid V1 - src/core/trend_hybrid_engine.py).

Cobrem: forma e validade do ranking de Trend Score, validade e determinismo
do bilhete gerado (15 dezenas unicas, divisao respeitada, regras de
ConfiguracaoMotor satisfeitas), normalizacao dos pesos (soma sempre 1.0) e
os erros esperados para configuracoes invalidas.
"""
from __future__ import annotations

from itertools import combinations

import pandas as pd
import pytest

from src.core.trend_hybrid_engine import (
    DIVISAO_PADRAO,
    DIVISOES_SUPORTADAS,
    calcular_trend_scores,
    gerar_bilhete_trend_hybrid,
    gerar_trend_scores,
    indicadores_para_proximo_concurso,
    selecionar_bilhete,
)
from src.models.trend_hybrid import PesosTendencia
from src.repository.base_repository import CAMINHO_BASE_PADRAO, carregar_base
from src.validacao_jogos import ConfiguracaoMotor, validar_jogo


def _base():
    return carregar_base(CAMINHO_BASE_PADRAO)


def config_teste() -> ConfiguracaoMotor:
    return ConfiguracaoMotor()


def test_pesos_efetivos_somam_um() -> None:
    for peso_atraso in (0.0, 0.03, 0.05, 0.10):
        pesos = PesosTendencia(peso_atraso=peso_atraso)
        efetivos = pesos.pesos_efetivos()
        assert abs(sum(efetivos.values()) - 1.0) < 1e-9
        assert efetivos["atraso"] == peso_atraso


def test_pesos_invalidos_geram_erro() -> None:
    with pytest.raises(ValueError):
        PesosTendencia(peso_atraso=0.20).validar()
    with pytest.raises(ValueError):
        PesosTendencia(peso_ult10=-0.1).validar()


def test_ranking_trend_score_tem_25_dezenas_e_colunas_esperadas() -> None:
    ranking = gerar_trend_scores(_base())
    assert len(ranking) == 25
    assert sorted(ranking["Dezena"].tolist()) == list(range(1, 26))
    assert ranking["Posição"].tolist() == list(range(1, 26))
    for coluna in (
        "Trend Score",
        "Frequência últimos 10",
        "Frequência últimos 20",
        "Frequência últimos 50",
        "Frequência últimos 100",
        "Frequência histórica",
        "Atraso",
        "Regularidade",
        "Momentum",
        "Sequência consecutiva",
        "Persistência",
        "Saiu no último",
    ):
        assert coluna in ranking.columns
    # Ordenado do maior para o menor Trend Score.
    assert ranking["Trend Score"].is_monotonic_decreasing


def test_bilhete_padrao_tem_15_dezenas_unicas_e_validas() -> None:
    bilhete = gerar_bilhete_trend_hybrid(_base())
    assert len(bilhete.dezenas) == 15
    assert len(set(bilhete.dezenas)) == 15
    assert all(1 <= d <= 25 for d in bilhete.dezenas)
    assert bilhete.dezenas == tuple(sorted(bilhete.dezenas))


def test_bilhete_respeita_divisao_grupo_a_grupo_b() -> None:
    df = _base()
    indicadores, ultimo_jogo = indicadores_para_proximo_concurso(df)
    pontuacoes = calcular_trend_scores(indicadores)
    for divisao in DIVISOES_SUPORTADAS:
        bilhete = selecionar_bilhete(pontuacoes, ultimo_jogo, divisao=divisao)
        assert len(bilhete.grupo_a_selecionadas) == divisao[0]
        assert len(bilhete.grupo_b_selecionadas) == divisao[1]
        assert set(bilhete.grupo_a_selecionadas).issubset(ultimo_jogo)
        assert set(bilhete.grupo_b_selecionadas).isdisjoint(ultimo_jogo)
        assert set(bilhete.dezenas) == set(bilhete.grupo_a_selecionadas) | set(bilhete.grupo_b_selecionadas)
        # A repeticao do ultimo concurso e sempre exatamente divisao[0] por construcao.
        assert len(set(bilhete.dezenas) & ultimo_jogo) == divisao[0]


def test_bilhete_passa_na_validacao_do_motor_elite() -> None:
    df = _base()
    config = config_teste()
    indicadores, ultimo_jogo = indicadores_para_proximo_concurso(df)
    pontuacoes = calcular_trend_scores(indicadores)
    bilhete = selecionar_bilhete(pontuacoes, ultimo_jogo, DIVISAO_PADRAO, config)
    # Nao deve levantar excecao: o bilhete gerado ja respeita ConfiguracaoMotor.
    validar_jogo(bilhete.dezenas, config, ultimo_jogo)


def test_bilhete_e_reprodutivel_com_os_mesmos_pesos() -> None:
    df = _base()
    primeiro = gerar_bilhete_trend_hybrid(df, pesos=PesosTendencia())
    segundo = gerar_bilhete_trend_hybrid(df, pesos=PesosTendencia())
    assert primeiro.dezenas == segundo.dezenas
    assert primeiro.trend_score_total == segundo.trend_score_total
    assert primeiro.margem_busca == segundo.margem_busca


def test_pontuacoes_do_bilhete_cobrem_as_25_dezenas() -> None:
    bilhete = gerar_bilhete_trend_hybrid(_base())
    dezenas_pontuadas = {p.indicadores.dezena for p in bilhete.pontuacoes}
    assert dezenas_pontuadas == set(range(1, 26))
    # Descartadas + selecionadas = 25, sem sobreposicao.
    todas = (
        set(bilhete.grupo_a_selecionadas)
        | set(bilhete.grupo_b_selecionadas)
        | set(bilhete.grupo_a_descartadas)
        | set(bilhete.grupo_b_descartadas)
    )
    assert todas == set(range(1, 26))


def test_divisao_com_soma_diferente_de_15_levanta_erro() -> None:
    df = _base()
    indicadores, ultimo_jogo = indicadores_para_proximo_concurso(df)
    pontuacoes = calcular_trend_scores(indicadores)
    with pytest.raises(ValueError):
        selecionar_bilhete(pontuacoes, ultimo_jogo, divisao=(9, 5))


def test_todas_as_divisoes_suportadas_geram_bilhetes_diferentes_entre_si_ou_iguais_mas_validos() -> None:
    df = _base()
    config = config_teste()
    indicadores, ultimo_jogo = indicadores_para_proximo_concurso(df)
    pontuacoes = calcular_trend_scores(indicadores)
    bilhetes = {}
    for divisao in DIVISOES_SUPORTADAS:
        bilhete = selecionar_bilhete(pontuacoes, ultimo_jogo, divisao, config)
        validar_jogo(bilhete.dezenas, config, ultimo_jogo)
        bilhetes[divisao] = bilhete
    # Todas as combinacoes de pares de divisoes foram testadas sem excecao.
    for (a, bilhete_a), (b, bilhete_b) in combinations(bilhetes.items(), 2):
        assert isinstance(bilhete_a.trend_score_total, float)
        assert isinstance(bilhete_b.trend_score_total, float)


def test_sem_historico_suficiente_levanta_erro() -> None:
    df_vazio = pd.DataFrame(columns=["Concurso", "Data", *[f"Bola{i}" for i in range(1, 16)]])
    with pytest.raises(ValueError):
        gerar_bilhete_trend_hybrid(df_vazio)
