"""Persistencia de exportacoes geradas pela aplicacao (CSV de jogos previstos).

Extraido de ``app.py::render_resultado`` (Fase 3 - Phoenix V1), sem alterar o
formato ou conteudo do arquivo gerado.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd


PASTA_EXPORTS = Path("exports")


def exportar_jogos_previstos(jogos: pd.DataFrame, concurso_alvo: int | str) -> Path:
    PASTA_EXPORTS.mkdir(exist_ok=True)
    caminho = PASTA_EXPORTS / f"lotofacil_previsao_{concurso_alvo}.csv"
    jogos.to_csv(caminho, index=False, encoding="utf-8-sig")
    return caminho
