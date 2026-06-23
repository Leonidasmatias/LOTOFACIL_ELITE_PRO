from __future__ import annotations

from collections import Counter

import pandas as pd

from .carregar_dados import COLUNAS_DEZENAS
from .estatisticas_lotofacil import TODAS_DEZENAS


JANELAS_V5 = (20, 50, 100, 200)


def _contagem(df: pd.DataFrame, janela: int) -> Counter:
    dados = df.tail(min(janela, len(df)))
    return Counter(int(valor) for valor in dados[COLUNAS_DEZENAS].to_numpy().ravel())


def ranking_janelas_v5(df: pd.DataFrame) -> pd.DataFrame:
    dados = df.sort_values("Concurso").reset_index(drop=True)
    if dados.empty:
        return pd.DataFrame(columns=["Dezena"])
    contagens = {janela: _contagem(dados, janela) for janela in JANELAS_V5}
    ultimo = {int(valor) for valor in dados.iloc[-1][COLUNAS_DEZENAS]}
    anterior = {int(valor) for valor in dados.iloc[-2][COLUNAS_DEZENAS]} if len(dados) > 1 else set()
    repetidas_ultimo = ultimo & anterior
    recorte_repeticao = dados.tail(min(200, len(dados)))
    repeticoes = Counter()
    for indice in range(1, len(recorte_repeticao)):
        atual = {int(valor) for valor in recorte_repeticao.iloc[indice][COLUNAS_DEZENAS]}
        previo = {int(valor) for valor in recorte_repeticao.iloc[indice - 1][COLUNAS_DEZENAS]}
        repeticoes.update(atual & previo)

    linhas = []
    for dezena in TODAS_DEZENAS:
        indices = dados.index[dados[COLUNAS_DEZENAS].eq(dezena).any(axis=1)]
        atraso = len(dados) - 1 - int(indices.max()) if len(indices) else len(dados)
        linha: dict[str, object] = {
            "Dezena": dezena,
            "Atraso": atraso,
            "Saiu no último": dezena in ultimo,
            "Repetida no último": dezena in repetidas_ultimo,
            "Repetições consecutivas (200)": int(repeticoes[dezena]),
        }
        indice_recente = 0.0
        for janela in JANELAS_V5:
            amostra = min(janela, len(dados))
            frequencia = int(contagens[janela][dezena])
            percentual = (frequencia / amostra * 100) if amostra else 0.0
            linha[f"Frequência {janela}"] = frequencia
            linha[f"Taxa {janela} (%)"] = round(percentual, 2)
            if janela in (20, 50):
                indice_recente += percentual * (0.6 if janela == 20 else 0.4)
        linha["Índice recente"] = round(indice_recente, 4)
        linhas.append(linha)

    ranking = pd.DataFrame(linhas)
    for janela in JANELAS_V5:
        ranking[f"Posição {janela}"] = ranking[f"Frequência {janela}"].rank(method="min", ascending=False).astype(int)
    return ranking.sort_values(["Índice recente", "Dezena"], ascending=[False, True]).reset_index(drop=True)


def paineis_tendencias_v5(df: pd.DataFrame, limite: int = 8) -> dict[str, pd.DataFrame]:
    ranking = ranking_janelas_v5(df)
    if ranking.empty:
        vazio = pd.DataFrame(columns=["Dezena"])
        return {nome: vazio.copy() for nome in ("Quentes", "Frias", "Atrasadas", "Repetidas")}
    colunas_base = ["Dezena", "Frequência 20", "Frequência 50", "Taxa 20 (%)", "Atraso"]
    quentes = ranking.sort_values(["Índice recente", "Dezena"], ascending=[False, True]).head(limite)
    frias = ranking.sort_values(["Índice recente", "Dezena"], ascending=[True, True]).head(limite)
    atrasadas = ranking.sort_values(["Atraso", "Índice recente"], ascending=[False, True]).head(limite)
    repetidas = ranking[ranking["Repetida no último"]].sort_values(
        ["Repetições consecutivas (200)", "Frequência 20"], ascending=[False, False]
    )
    return {
        "Quentes": quentes[colunas_base + ["Índice recente"]].reset_index(drop=True),
        "Frias": frias[colunas_base + ["Índice recente"]].reset_index(drop=True),
        "Atrasadas": atrasadas[["Dezena", "Atraso", "Frequência 20", "Frequência 50"]].reset_index(drop=True),
        "Repetidas": repetidas[["Dezena", "Frequência 20", "Repetições consecutivas (200)"]].reset_index(drop=True),
    }
