"""Orquestra o carregamento da base historica e os metadados publicos exibidos na tela.

Extraido de ``app.py`` (Fase 3 - Phoenix V1). O cache do Streamlit
(``st.cache_data``) permanece na camada de UI (``app.py``), pois e uma
preocupacao especifica do framework de apresentacao, nao uma regra de negocio.
"""
from __future__ import annotations

import pandas as pd

from ..core import estatisticas
from ..repository import base_repository
from ..utils.formatacao import formatar_moeda


def carregar_base_atual() -> pd.DataFrame:
    return base_repository.carregar_base()


def atualizar_base_oficial() -> bool:
    return base_repository.atualizar_base_local()


def buscar_info_concurso() -> dict:
    info = base_repository.buscar_info_concurso_atual()
    return info if isinstance(info, dict) else {}


def resumo(df: pd.DataFrame) -> dict:
    return base_repository.resumo_base(df)


def metadados_publicos(df: pd.DataFrame, info: dict) -> dict:
    resumo_atual = resumo(df)
    concurso = info.get("proximo_concurso") or (resumo_atual["ultimo_concurso"] + 1)
    data = info.get("data_proximo_concurso") or "Aguardando CAIXA"
    premio = formatar_moeda(info.get("premio_estimado"))
    return {
        "concurso_alvo": concurso,
        "data_sorteio": data,
        "premio_estimado": premio,
        "acumulou": info.get("acumulou"),
        "fonte": info.get("fonte", "fallback_local"),
    }


# --- Estatisticas (Fase Hardening RC: wrappers finos para a UI nunca chamar
# ``core.estatisticas`` diretamente, reforcando a separacao de camadas ja
# documentada na arquitetura. Nao alteram nenhum calculo, apenas repassam.) ---


def dezenas_quentes(df: pd.DataFrame, limite: int = 10) -> pd.DataFrame:
    return estatisticas.dezenas_quentes(df, limite)


def dezenas_frias(df: pd.DataFrame, limite: int = 10) -> pd.DataFrame:
    return estatisticas.dezenas_frias(df, limite)


def dezenas_atrasadas(df: pd.DataFrame) -> pd.DataFrame:
    return estatisticas.dezenas_atrasadas(df)


def pares_impares(dezenas: list[int]) -> dict:
    return estatisticas.pares_impares(dezenas)


def centro_moldura(dezenas: list[int]) -> dict:
    return estatisticas.centro_moldura(dezenas)


def linhas_colunas(dezenas: list[int]) -> dict:
    return estatisticas.linhas_colunas(dezenas)
