"""Orquestra o Trend Hybrid Engine (geração, explicação, backtest e
otimização de divisão) para a camada de apresentação (``src/ui``).

Fase Trend Hybrid V1. Nenhuma fórmula matemática vive aqui: apenas chama
``core.trend_hybrid_engine``, ``core.trend_hybrid_backtest`` e
``ai.trend_hybrid_explainer`` na ordem certa, mesmo padrão de
``previsao_service.py`` e ``elite_score_service.py``.
"""
from __future__ import annotations

import pandas as pd

from ..ai.trend_hybrid_explainer import ExplicacaoBilheteTrendHybrid, explicar_bilhete
from ..core.trend_hybrid_backtest import (
    ResultadoBacktestTrendHybrid,
    executar_backtest_trend_hybrid,
    otimizar_divisao as _otimizar_divisao,
)
from ..core.trend_hybrid_engine import (
    DIVISAO_PADRAO,
    DIVISOES_SUPORTADAS,
    MOTOR_TREND_HYBRID,
    gerar_bilhete_trend_hybrid,
    gerar_trend_scores,
    sortear_bilhete_aleatorio_grupos,
)
from ..models.trend_hybrid import BilheteSorteioGrupos, BilheteTrendHybrid, PesosTendencia
from ..validacao_jogos import ConfiguracaoMotor


def motor_trend_hybrid_nome() -> str:
    return MOTOR_TREND_HYBRID


def divisoes_suportadas() -> tuple[tuple[int, int], ...]:
    return DIVISOES_SUPORTADAS


def gerar_bilhete_do_dia(
    df: pd.DataFrame,
    divisao: tuple[int, int] = DIVISAO_PADRAO,
    pesos: PesosTendencia | None = None,
    configuracao: ConfiguracaoMotor | None = None,
) -> BilheteTrendHybrid:
    """Gera o bilhete Trend Hybrid (divisão Grupo A / Grupo B configurável,
    padrão 9+6) para o próximo concurso ainda não sorteado."""
    return gerar_bilhete_trend_hybrid(df, divisao=divisao, pesos=pesos, configuracao=configuracao)


def sortear_bilhete_aleatorio(
    df: pd.DataFrame,
    divisao: tuple[int, int] = DIVISAO_PADRAO,
    configuracao: ConfiguracaoMotor | None = None,
    semente: int | None = None,
    numero_sorteio: int = 0,
) -> BilheteSorteioGrupos:
    """Sorteia um bilhete novo a cada chamada: N dezenas aleatórias entre as
    do último concurso (Grupo A) + as demais aleatórias entre as que não
    saíram (Grupo B). Sem Trend Score -- para gerar uma carteira diferente
    a cada clique do botão "gerar"."""
    return sortear_bilhete_aleatorio_grupos(
        df, divisao=divisao, configuracao=configuracao, semente=semente, numero_sorteio=numero_sorteio
    )


def gerar_ranking_trend_score(df: pd.DataFrame, pesos: PesosTendencia | None = None) -> pd.DataFrame:
    """Ranking das 25 dezenas pelo Trend Score, para exibição em tabela/heatmap."""
    return gerar_trend_scores(df, pesos=pesos)


def explicar(bilhete: BilheteTrendHybrid) -> ExplicacaoBilheteTrendHybrid:
    """Explica cada dezena (selecionada e descartada) de um bilhete já
    gerado, sem recalcular nenhum valor."""
    return explicar_bilhete(bilhete)


def executar_backtest(
    df: pd.DataFrame,
    divisao: tuple[int, int] = DIVISAO_PADRAO,
    pesos: PesosTendencia | None = None,
    configuracao: ConfiguracaoMotor | None = None,
    historico_minimo: int = 100,
    quantidade_concursos: int | None = None,
) -> ResultadoBacktestTrendHybrid:
    """Backtest temporal (sem vazamento) do Trend Hybrid Engine para uma
    divisão específica."""
    return executar_backtest_trend_hybrid(
        df,
        divisao=divisao,
        pesos=pesos,
        configuracao=configuracao,
        historico_minimo=historico_minimo,
        quantidade_concursos=quantidade_concursos,
    )


def otimizar_divisao(
    df: pd.DataFrame,
    divisoes: tuple[tuple[int, int], ...] = DIVISOES_SUPORTADAS,
    pesos: PesosTendencia | None = None,
    configuracao: ConfiguracaoMotor | None = None,
    historico_minimo: int = 100,
    quantidade_concursos: int | None = None,
):
    """Compara as divisões suportadas (8+7, 9+6, 10+5, 11+4 por padrão) e
    devolve ``(tabela_comparativa, melhor_divisao, resultados_por_divisao)``."""
    return _otimizar_divisao(
        df,
        divisoes=divisoes,
        pesos=pesos,
        configuracao=configuracao,
        historico_minimo=historico_minimo,
        quantidade_concursos=quantidade_concursos,
    )
