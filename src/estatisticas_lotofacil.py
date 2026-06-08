from __future__ import annotations

import pandas as pd

from .carregar_dados import COLUNAS_DEZENAS


TODAS_DEZENAS = list(range(1, 26))
MOLDURA = {1, 2, 3, 4, 5, 6, 10, 11, 15, 16, 20, 21, 22, 23, 24, 25}
CENTRO = set(TODAS_DEZENAS) - MOLDURA


def _serie_dezenas(df: pd.DataFrame) -> pd.Series:
    if df.empty:
        return pd.Series(dtype=int)
    return df[COLUNAS_DEZENAS].stack().astype(int)


def frequencia_dezenas(df: pd.DataFrame, ultimos: int | None = None) -> pd.DataFrame:
    dados = df.tail(ultimos) if ultimos else df
    contagem = _serie_dezenas(dados).value_counts().reindex(TODAS_DEZENAS, fill_value=0)
    return pd.DataFrame({"Dezena": TODAS_DEZENAS, "Frequencia": [int(contagem[d]) for d in TODAS_DEZENAS]})


def dezenas_quentes(df: pd.DataFrame, limite: int = 10) -> pd.DataFrame:
    return frequencia_dezenas(df).sort_values(["Frequencia", "Dezena"], ascending=[False, True]).head(limite)


def dezenas_frias(df: pd.DataFrame, limite: int = 10) -> pd.DataFrame:
    return frequencia_dezenas(df).sort_values(["Frequencia", "Dezena"], ascending=[True, True]).head(limite)


def dezenas_atrasadas(df: pd.DataFrame) -> pd.DataFrame:
    ultimo = int(df["Concurso"].max()) if not df.empty else 0
    registros = []
    for dezena in TODAS_DEZENAS:
        mask = df[COLUNAS_DEZENAS].eq(dezena).any(axis=1)
        ultimo_sorteio = int(df.loc[mask, "Concurso"].max()) if mask.any() else 0
        registros.append({"Dezena": dezena, "Atraso": ultimo - ultimo_sorteio})
    return pd.DataFrame(registros).sort_values(["Atraso", "Dezena"], ascending=[False, True])


def pares_impares(dezenas: list[int]) -> dict:
    pares = sum(1 for d in dezenas if d % 2 == 0)
    return {"Pares": pares, "Impares": len(dezenas) - pares}


def linhas_colunas(dezenas: list[int]) -> dict:
    linhas = {i: 0 for i in range(1, 6)}
    colunas = {i: 0 for i in range(1, 6)}
    for dezena in dezenas:
        linha = ((dezena - 1) // 5) + 1
        coluna = ((dezena - 1) % 5) + 1
        linhas[linha] += 1
        colunas[coluna] += 1
    return {"Linhas": linhas, "Colunas": colunas}


def centro_moldura(dezenas: list[int]) -> dict:
    centro = sum(1 for d in dezenas if d in CENTRO)
    moldura = sum(1 for d in dezenas if d in MOLDURA)
    return {"Centro": centro, "Moldura": moldura}
