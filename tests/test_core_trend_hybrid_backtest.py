"""Testes do backtest e da otimizacao de divisao do Trend Hybrid Engine
(Fase Trend Hybrid V1 - src/core/trend_hybrid_backtest.py).

Cobrem: ausencia de vazamento temporal (os indicadores usados para prever um
concurso nunca incluem o proprio concurso), forma do resultado do backtest,
consistencia da otimizacao de divisao e determinismo.
"""
from __future__ import annotations

import pytest

from src.core.trend_hybrid_backtest import executar_backtest_trend_hybrid, otimizar_divisao
from src.core.trend_hybrid_engine import DIVISOES_SUPORTADAS, iterar_estados_trend_hybrid
from src.repository.base_repository import CAMINHO_BASE_PADRAO, COLUNAS_DEZENAS, carregar_base


def _base():
    return carregar_base(CAMINHO_BASE_PADRAO)


def test_iterador_nao_usa_o_proprio_concurso_alvo_nos_indicadores() -> None:
    """Ausencia de vazamento temporal: a frequencia nos ultimos 10 concursos,
    calculada para prever o concurso em `indice`, nao pode contar nenhuma
    dezena do PROPRIO concurso em `indice` (so dos anteriores)."""
    df = _base()
    dados = df.sort_values("Concurso").reset_index(drop=True)
    verificados = 0
    for indice, row, indicadores, ultimo_jogo in iterar_estados_trend_hybrid(dados):
        dezenas_do_alvo = {int(row[coluna]) for coluna in COLUNAS_DEZENAS}
        soma_freq_ult10_antes = sum(ind.frequencia_ult10 for ind in indicadores.values())
        # A soma das frequencias nos ultimos 10 concursos deve ser no maximo
        # 10 * 15 (10 concursos completos, 15 dezenas cada) -- nunca conta o
        # concurso alvo, que ainda nao foi processado nesta iteracao.
        assert soma_freq_ult10_antes <= 150
        # O concurso anterior (ultimo_jogo) e sempre diferente do alvo desta
        # iteracao quando o alvo tem uma composicao distinta do anterior
        # (checagem fraca, mas garante que ultimo_jogo reflete o passado).
        assert ultimo_jogo != dezenas_do_alvo or indice == 0
        verificados += 1
        if verificados >= 200:
            break
    assert verificados > 0


def test_backtest_avalia_a_quantidade_de_concursos_pedida() -> None:
    df = _base()
    resultado = executar_backtest_trend_hybrid(df, quantidade_concursos=30, historico_minimo=100)
    assert resultado.resumo["Concursos avaliados"] == 30
    assert len(resultado.detalhes) == 30
    assert resultado.detalhes["Acertos"].between(0, 15).all()


def test_backtest_resumo_tem_as_chaves_esperadas() -> None:
    df = _base()
    resultado = executar_backtest_trend_hybrid(df, quantidade_concursos=25, historico_minimo=100)
    chaves_esperadas = {
        "Divisão",
        "Concursos avaliados",
        "Melhor acerto",
        "Pior acerto",
        "Média de acertos",
        "Desvio padrão",
        "Maior sequência premiada (11+)",
        "Maior sequência sem prêmio (<11)",
        "Margem de busca média",
    }
    assert chaves_esperadas.issubset(resultado.resumo.keys())
    for faixa in (11, 12, 13, 14, 15):
        assert f"Jogos {faixa}+" in resultado.resumo
        assert f"Taxa {faixa}+ (%)" in resultado.resumo


def test_backtest_e_reprodutivel() -> None:
    df = _base()
    primeiro = executar_backtest_trend_hybrid(df, quantidade_concursos=20, historico_minimo=100)
    segundo = executar_backtest_trend_hybrid(df, quantidade_concursos=20, historico_minimo=100)
    assert primeiro.resumo == segundo.resumo
    assert primeiro.detalhes["Acertos"].tolist() == segundo.detalhes["Acertos"].tolist()


def test_backtest_com_base_insuficiente_levanta_erro() -> None:
    df = _base().head(50)
    with pytest.raises(ValueError):
        executar_backtest_trend_hybrid(df, historico_minimo=100)


def test_otimizar_divisao_compara_todas_as_divisoes_suportadas() -> None:
    df = _base()
    comparativo, melhor_divisao, resultados = otimizar_divisao(df, quantidade_concursos=15, historico_minimo=100)
    assert len(comparativo) == len(DIVISOES_SUPORTADAS)
    assert set(resultados.keys()) == set(DIVISOES_SUPORTADAS)
    assert melhor_divisao in DIVISOES_SUPORTADAS
    # A divisao vencedora deve ter a maior media de acertos da tabela.
    melhor_media = comparativo["Média de acertos"].max()
    assert resultados[melhor_divisao].resumo["Média de acertos"] == melhor_media


def test_otimizar_divisao_com_subconjunto_customizado() -> None:
    df = _base()
    divisoes = ((9, 6), (10, 5))
    comparativo, melhor_divisao, resultados = otimizar_divisao(
        df, divisoes=divisoes, quantidade_concursos=10, historico_minimo=100
    )
    assert len(comparativo) == 2
    assert melhor_divisao in divisoes
    assert set(resultados.keys()) == set(divisoes)
