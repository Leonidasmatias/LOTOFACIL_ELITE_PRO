"""Componentes visuais reutilizaveis (bolas, grid de dezenas, cabecalho).

Extraido de ``app.py`` (Fase 5 - Phoenix V1), sem alteracao de comportamento.
``render_elite_score_painel`` foi adicionado na Fase Phoenix V2 (modulo Elite
Score) e continua sendo usado no painel admin (``pagina_admin.py``), sem
nenhuma alteracao nesta fase.
``render_explicacao_elite`` foi adicionado na Fase V1.4 (Elite Score
Explainable AI) e usa apenas o modulo ``src.ai.elite_explainer`` -- nao
recalcula nem altera nenhum valor do Elite Score.
``render_estrategia_recomendada`` foi adicionado na Fase V1.5 (Elite Decision
Engine) e usa apenas o modulo ``src.ai.elite_decision_engine`` -- nao gera
jogos novos nem altera nenhum valor de score.
``render_qualidade_elite_simplificada`` foi adicionado na Fase UX Final
Simplification: uma versao com linguagem simples (sem jargao estatistico) do
mesmo Elite Score ja calculado, usada apenas na tela publica
(``pagina_publica.py``). Nao recalcula nada -- le os mesmos
``EliteScoreResultado`` que ``render_elite_score_painel`` usa.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

import config
from src.ai import elite_explainer
from src.ai.elite_decision_engine import RelatorioEstrategico
from src.models.elite_score import EliteScoreResultado
from src.repository.base_repository import COLUNAS_DEZENAS


def dezenas_html(dezenas: list[int]) -> str:
    return '<div class="balls">' + "".join(f'<span class="ball">{d:02d}</span>' for d in dezenas) + "</div>"


def dezenas_grid_lotofacil(dezenas: list[int]) -> str:
    return '<div class="lotofacil-grid">' + "".join(
        f'<div class="lotofacil-dezena">{dezena:02d}</div>' for dezena in dezenas
    ) + "</div>"


def render_header() -> None:
    st.markdown(
        f"""
        <div class="hero">
            <h1>Lotofacil Elite Pro</h1>
            <div class="hero-sub">Gere seus numeros da sorte com analise estatistica inteligente.</div>
            <div style="margin-top:8px;font-size:13px;font-weight:800;">{config.VERSAO_APP} | {config.STATUS_APP}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_elite_score_painel(
    jogos_com_score: pd.DataFrame,
    resultados: list[EliteScoreResultado],
    key_prefix: str,
    coluna_rotulo: str = "Perfil",
) -> tuple[list[int], EliteScoreResultado] | None:
    """Mostra a tabela de jogos com a coluna 'Elite Score' e, ao selecionar um
    jogo, o detalhamento das metricas que formaram a pontuacao.

    'Elite Score' e uma analise de qualidade do jogo JA GERADO (aderencia
    estatistica ao padrao historico + diversidade em relacao aos outros jogos
    do lote) -- diferente do 'Elite Score Temporal'/'Elite Score V2', que o
    Motor Elite usa internamente para GERAR os jogos.

    Devolve ``(dezenas_do_jogo_selecionado, resultado_selecionado)`` (ou
    ``None`` se nao houver resultados), para quem quiser reaproveitar a
    selecao do usuario -- por exemplo, ``render_explicacao_elite`` (Fase
    V1.4). O valor de retorno e aditivo: chamadas existentes que ignoram o
    retorno (como em ``pagina_admin.py``) continuam funcionando exatamente
    como antes.
    """
    st.caption(
        "\U0001f4a1 'Elite Score' analisa a qualidade do jogo ja gerado (aderencia ao padrao "
        "historico + diversidade em relacao aos outros jogos desta leva). E diferente do "
        "'Elite Score Temporal', que o Motor Elite usa para gerar os jogos."
    )
    st.dataframe(jogos_com_score, width="stretch", hide_index=True)

    if not resultados:
        return None

    if coluna_rotulo in jogos_com_score.columns:
        rotulos = jogos_com_score[coluna_rotulo].astype(str).tolist()
    else:
        rotulos = [f"Jogo {i + 1}" for i in range(len(resultados))]

    indice_escolhido = st.selectbox(
        "Ver detalhamento do Elite Score de:",
        options=list(range(len(rotulos))),
        format_func=lambda i: rotulos[i],
        key=f"{key_prefix}_elite_score_selecao",
    )

    resultado = resultados[indice_escolhido]
    st.markdown(f"**{resultado.explicacao_resumida()}**")

    detalhamento = pd.DataFrame(
        [
            {
                "Componente": c.nome,
                "Valor do jogo": round(c.valor_jogo, 2) if c.valor_jogo == c.valor_jogo else "-",  # nan-safe
                "Faixa tipica (p10-p90)": f"{c.faixa_tipica[0]:.1f} - {c.faixa_tipica[1]:.1f}",
                "Sub-score (0-100)": round(c.sub_score, 1),
                "Peso": f"{c.peso * 100:.0f}%",
                "Contribuicao (pts)": round(c.contribuicao, 2),
            }
            for c in resultado.componentes
        ]
    )
    st.dataframe(detalhamento, width="stretch", hide_index=True)

    linha_escolhida = jogos_com_score.iloc[indice_escolhido]
    dezenas_escolhidas = [int(linha_escolhida[coluna]) for coluna in COLUNAS_DEZENAS]
    return dezenas_escolhidas, resultado


def render_qualidade_elite_simplificada(
    jogos_com_score: pd.DataFrame,
    resultados: list[EliteScoreResultado],
    key_prefix: str,
    coluna_rotulo: str = "Perfil",
) -> tuple[list[int], EliteScoreResultado] | None:
    """Versao em linguagem simples (sem jargao estatistico) do Elite Score de
    cada jogo, usada apenas na tela publica (Fase UX Final Simplification).

    Nao recalcula nada: usa os mesmos ``EliteScoreResultado`` ja calculados
    (``resultados``) e apenas a funcao de classificacao ja existente
    (``elite_explainer.classificar_score``) -- os detalhes tecnicos completos
    continuam disponiveis (sem serem removidos), apenas escondidos por
    padrao num expansor opcional, para nao poluir a tela do usuario final.

    Devolve ``(dezenas_do_jogo_selecionado, resultado_selecionado)`` (ou
    ``None`` se nao houver resultados), para a secao de explicacao usar em
    seguida.
    """
    st.caption(
        "Cada jogo recebe uma nota de 0 a 100: quanto mais alta, mais ele segue "
        "os padroes mais comuns dos sorteios ja realizados."
    )
    if not resultados:
        return None

    if coluna_rotulo in jogos_com_score.columns:
        rotulos = jogos_com_score[coluna_rotulo].astype(str).tolist()
    else:
        rotulos = [f"Jogo {i + 1}" for i in range(len(resultados))]

    tabela_simples = pd.DataFrame(
        {
            "Jogo": rotulos,
            "Nota": [round(r.total, 1) for r in resultados],
            "Classificacao": [elite_explainer.classificar_score(r.total) for r in resultados],
        }
    )
    st.dataframe(tabela_simples, width="stretch", hide_index=True)

    indice_escolhido = st.selectbox(
        "Ver mais detalhes de qual jogo?",
        options=list(range(len(rotulos))),
        format_func=lambda i: rotulos[i],
        key=f"{key_prefix}_qualidade_selecao",
    )

    resultado_escolhido = resultados[indice_escolhido]
    with st.expander("Ver detalhes tecnicos (opcional)"):
        detalhamento = pd.DataFrame(
            [
                {
                    "Item avaliado": c.nome,
                    "Nota deste item": round(c.sub_score, 1),
                    "Peso no total": f"{c.peso * 100:.0f}%",
                }
                for c in resultado_escolhido.componentes
            ]
        )
        st.dataframe(detalhamento, width="stretch", hide_index=True)

    linha_escolhida = jogos_com_score.iloc[indice_escolhido]
    dezenas_escolhidas = [int(linha_escolhida[coluna]) for coluna in COLUNAS_DEZENAS]
    return dezenas_escolhidas, resultado_escolhido


def render_explicacao_elite(jogo: list[int], resultado: EliteScoreResultado) -> None:
    """Secao 'Por que essa nota?' (Fase V1.4 - Elite Score Explainable AI).
    Usa apenas ``src.ai.elite_explainer`` para traduzir o Elite Score ja
    calculado (``resultado``) numa explicacao interpretavel: classificacao,
    pontos fortes e pontos de atencao. Nao recalcula nem altera nenhum valor
    do Elite Score."""
    explicacao = elite_explainer.explicar_resultado(jogo, resultado)

    st.markdown("## 💬 Por que essa nota?")
    st.markdown(f"**{explicacao.classificacao}** ({explicacao.score:.1f}/100)")
    st.caption(explicacao.resumo)

    col_fortes, col_atencao = st.columns(2)
    with col_fortes:
        st.markdown("**Pontos fortes**")
        if explicacao.pontos_fortes:
            for ponto in explicacao.pontos_fortes:
                st.markdown(f"- {ponto.componente}: {ponto.sub_score:.0f}/100")
        else:
            st.caption("Nenhum ponto forte de destaque nesta rodada.")
    with col_atencao:
        st.markdown("**Pontos de atencao**")
        if explicacao.penalidades:
            for ponto in explicacao.penalidades:
                st.markdown(f"- {ponto.componente}: {ponto.sub_score:.0f}/100")
        else:
            st.caption("Nenhum ponto de atencao nesta rodada.")


def render_estrategia_recomendada(relatorio: RelatorioEstrategico) -> None:
    """Secao '🎯 Nossa recomendacao para hoje' (Fase V1.5 - Elite Decision
    Engine). Usa apenas ``src.ai.elite_decision_engine`` para agregar os
    Elite Scores ja calculados do lote de jogos numa recomendacao de
    estrategia (perfil, risco, justificativa e potencial teorico). Nao gera
    jogos novos nem recalcula nenhum score -- nenhum valor aqui e recalculado,
    apenas reapresentado com linguagem mais simples (Fase UX Final
    Simplification)."""
    st.markdown("## 🎯 Nossa recomendacao para hoje")

    estrategia = relatorio.estrategia
    c1, c2, c3 = st.columns(3)
    c1.metric("Estilo recomendado", estrategia.perfil)
    c2.metric("Nivel de risco", estrategia.nivel_risco)
    c3.metric("Qualidade media dos jogos", f"{estrategia.potencial_teorico:.1f}/100")

    st.caption(estrategia.justificativa)

    total_jogos = sum(relatorio.distribuicao.values())
    if total_jogos:
        resumo_distribuicao = ", ".join(
            f"{quantidade} {classificacao.lower()}"
            for classificacao, quantidade in relatorio.distribuicao.items()
            if quantidade > 0
        )
        st.caption(f"Resumo dos jogos gerados: {resumo_distribuicao}.")
