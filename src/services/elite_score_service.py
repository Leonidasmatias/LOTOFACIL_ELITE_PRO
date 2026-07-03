"""Orquestra o calculo do Elite Score sobre um lote de jogos ja gerados.

Fase Phoenix V2. Nao gera jogos (isso e responsabilidade do Motor Elite via
``previsao_service``); apenas chama ``core.elite_score`` sobre jogos que ja
existem e devolve tanto a coluna "Elite Score" pronta para exibir quanto o
detalhamento por jogo, usado na explicacao resumida da UI.
"""
from __future__ import annotations

import pandas as pd

from ..core import elite_score
from ..models.elite_score import EliteScoreResultado
from ..repository.base_repository import COLUNAS_DEZENAS

# As colunas de dezenas de um JOGO (Bola1..Bola15) tem os mesmos nomes das
# colunas de um CONCURSO na base historica -- reaproveita a mesma constante
# ja existente em vez de duplicar a lista.
COLUNAS_BOLAS_JOGO = COLUNAS_DEZENAS


def _extrair_jogos(jogos_df: pd.DataFrame) -> list[list[int]]:
    return [[int(row[coluna]) for coluna in COLUNAS_BOLAS_JOGO] for _, row in jogos_df.iterrows()]


def calcular_scores(jogos_df: pd.DataFrame, df_historico: pd.DataFrame) -> list[EliteScoreResultado]:
    """Calcula o Elite Score de cada jogo em ``jogos_df`` (deve ter as
    colunas Bola1..Bola15), usando ``df_historico`` como base de referencia e
    o proprio ``jogos_df`` como lote para o componente de diversidade."""
    if jogos_df.empty:
        return []
    jogos = _extrair_jogos(jogos_df)
    return elite_score.calcular_elite_score_lote(jogos, df_historico)


def anexar_elite_score(jogos_df: pd.DataFrame, df_historico: pd.DataFrame) -> tuple[pd.DataFrame, list[EliteScoreResultado]]:
    """Devolve uma COPIA de ``jogos_df`` com a coluna 'Elite Score' adicionada
    (arredondada, 0-100), mais a lista de resultados detalhados (na mesma
    ordem das linhas), para a tela poder mostrar a explicacao ao selecionar
    um jogo especifico."""
    resultados = calcular_scores(jogos_df, df_historico)
    jogos_com_score = jogos_df.copy()
    jogos_com_score["Elite Score"] = [round(r.total, 1) for r in resultados]
    return jogos_com_score, resultados
