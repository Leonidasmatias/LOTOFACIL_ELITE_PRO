"""Explicacoes textuais sobre rankings e jogos ja gerados pelo Motor Elite.

Fase 6 - Phoenix V1 (stub inicial, sem Machine Learning). Todas as funcoes sao
somente-leitura: recebem DataFrames/valores ja calculados pelo Core e devolvem
texto explicativo. Nao recalculam nem alteram score, ranking ou jogo algum.
"""
from __future__ import annotations

import pandas as pd


def justificar_dezena(ranking: pd.DataFrame, dezena: int) -> str:
    """Explica, em texto, por que uma dezena tem o Elite Score que tem."""
    linha = ranking.loc[ranking["Dezena"] == dezena]
    if linha.empty:
        return f"Dezena {dezena:02d} nao encontrada no ranking informado."
    dados = linha.iloc[0].to_dict()
    partes = [f"Dezena {dezena:02d}: Elite Score {dados.get('Elite Score', dados.get('Elite Score V2', 'N/D'))}."]
    if "Frequencia geral" in dados:
        partes.append(f"Frequencia geral: {dados['Frequencia geral']}.")
    if "Atraso" in dados:
        partes.append(f"Atraso atual: {dados['Atraso']} concursos.")
    return " ".join(partes)


def ranquear_estrategias(jogos: pd.DataFrame, coluna_score: str = "Elite Score Temporal") -> pd.DataFrame:
    """Ordena um conjunto de jogos ja gerados pela coluna de score, do maior para o menor.

    Nao recalcula o score: apenas reordena o que o Motor Elite ja produziu.
    """
    if coluna_score not in jogos.columns:
        return jogos
    return jogos.sort_values(coluna_score, ascending=False).reset_index(drop=True)


def resumo_portfolio(jogos: pd.DataFrame, coluna_score: str = "Elite Score Temporal") -> dict:
    """Resumo estatistico simples (min/media/max) do score de um conjunto de jogos."""
    if jogos.empty or coluna_score not in jogos.columns:
        return {"quantidade": 0, "score_minimo": None, "score_medio": None, "score_maximo": None}
    serie = jogos[coluna_score].astype(float)
    return {
        "quantidade": int(len(jogos)),
        "score_minimo": round(float(serie.min()), 3),
        "score_medio": round(float(serie.mean()), 3),
        "score_maximo": round(float(serie.max()), 3),
    }
