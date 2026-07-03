"""Tela administrativa/desenvolvimento (estatisticas, Motor Elite, base).

Extraido de ``app.py`` (Fase 5 - Phoenix V1), sem alteracao de comportamento.
Fase Phoenix V2: a aba "Motor Elite" passou a exibir tambem o Elite Score
(analise de qualidade) dos jogos gerados, renomeando a coluna "Elite Score" ja
produzida pelo Motor Elite (V1) para "Elite Score (Motor V1)" antes de anexar
a nova coluna "Elite Score" (Phoenix V2), evitando colisao de nomes -- nenhuma
das duas e alterada em valor.
"""
from __future__ import annotations

from typing import Callable

import pandas as pd
import streamlit as st

from src.repository.base_repository import CAMINHO_BASE_PADRAO, COLUNAS_DEZENAS, FONTE_CAIXA_URL
from src.services import base_service, elite_score_service, previsao_service
from src.ui.componentes import render_elite_score_painel


def render_admin(df: pd.DataFrame, meta: dict, limpar_cache_info_caixa: Callable[[], None]) -> None:
    st.subheader("Admin / Desenvolvimento")
    col1, col2, col3 = st.columns(3)
    resumo = base_service.resumo(df)
    col1.metric("Concursos", resumo["total_concursos"])
    col2.metric("Ultimo concurso", resumo["ultimo_concurso"])
    col3.metric("Proximo concurso", meta["concurso_alvo"])

    if st.button("Atualizar base oficial CAIXA", type="primary"):
        if base_service.atualizar_base_oficial():
            limpar_cache_info_caixa()
            st.success("Base oficial Lotofacil atualizada.")
            st.rerun()
        else:
            st.warning("Nao foi possivel atualizar pela CAIXA agora. Mantendo base local.")

    abas = st.tabs(["Estatisticas", "Motor Elite", "Base"])
    with abas[0]:
        c1, c2, c3 = st.columns(3)
        c1.dataframe(base_service.dezenas_quentes(df), width="stretch", hide_index=True)
        c2.dataframe(base_service.dezenas_frias(df), width="stretch", hide_index=True)
        c3.dataframe(base_service.dezenas_atrasadas(df).head(10), width="stretch", hide_index=True)
        ultimo = df.iloc[-1][COLUNAS_DEZENAS].astype(int).tolist()
        st.write("Pares x impares", base_service.pares_impares(ultimo))
        st.write("Centro x moldura", base_service.centro_moldura(ultimo))
        st.write("Linhas e colunas", base_service.linhas_colunas(ultimo))
    with abas[1]:
        ranking = previsao_service.obter_ranking_elite(df)
        st.dataframe(ranking, width="stretch", hide_index=True)
        if st.button("Gerar jogos inteligentes", type="primary"):
            st.session_state.jogos_admin = previsao_service.gerar_jogos_admin(df, 10)
        if isinstance(st.session_state.get("jogos_admin"), pd.DataFrame):
            jogos_admin_base = st.session_state.jogos_admin.rename(columns={"Elite Score": "Elite Score (Motor V1)"})
            jogos_admin_com_score, resultados_admin = elite_score_service.anexar_elite_score(jogos_admin_base, df)
            render_elite_score_painel(jogos_admin_com_score, resultados_admin, key_prefix="admin")
    with abas[2]:
        st.link_button("Fonte oficial CAIXA", FONTE_CAIXA_URL)
        st.caption(f"Base local: {CAMINHO_BASE_PADRAO}")
        st.dataframe(df.tail(30), width="stretch", hide_index=True)
