"""Orquestra a geracao de jogos (Motor Elite) e a exportacao dos resultados.

Extraido de ``app.py`` (Fase 3 - Phoenix V1). Nenhuma regra matematica vive
aqui: apenas chama ``core.motor_elite`` e ``repository.exportacoes_repository``.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from ..core import motor_elite
from ..repository.exportacoes_repository import exportar_jogos_previstos


def gerar_previsoes_producao(df: pd.DataFrame) -> pd.DataFrame:
    return motor_elite.gerar_jogos_producao_v1(df)


def gerar_jogos_admin(df: pd.DataFrame, quantidade: int = 10) -> pd.DataFrame:
    return motor_elite.gerar_varios_jogos(df, quantidade)


def obter_ranking_elite(df: pd.DataFrame) -> pd.DataFrame:
    return motor_elite.ranking_elite_lotofacil(df)


def motor_oficial_nome() -> str:
    """Nome do motor oficial de producao (ex.: exibicao na UI), sem expor o
    modulo ``core.motor_elite`` diretamente para a camada de apresentacao
    (Fase Hardening RC - reducao de acoplamento UI -> Core, sem alterar
    nenhum valor nem regra do Motor Elite)."""
    return motor_elite.MOTOR_OFICIAL_PRODUCAO


def exportar_previsoes(jogos: pd.DataFrame, concurso_alvo: int | str) -> Path:
    return exportar_jogos_previstos(jogos, concurso_alvo)
