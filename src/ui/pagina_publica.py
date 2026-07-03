"""Tela publica: card do concurso, gate de pagamento PIX e resultado com jogos.

Extraido de ``app.py`` (Fase 5 - Phoenix V1), sem alteracao de comportamento.
Fase Phoenix V2: ``render_resultado`` passou a anexar o Elite Score (analise
de qualidade dos jogos ja gerados pelo Motor Elite) antes de exibir a tabela
de resultados -- nao altera a geracao dos jogos em si.

Fase UX Final Simplification: ``render_fluxo_publico`` passou a concentrar
todo o fluxo publico (botao de gerar, gate de pagamento e resultado) numa
unica funcao chamada por ``app.py``, e ``render_resultado`` foi reorganizado
num fluxo linear com secoes claras (Resultado -> Qualidade -> Explicacao ->
Estrategia), com linguagem mais simples e sem informacoes tecnicas internas
redundantes. Nenhuma regra do Motor Elite, do Elite Score ou do Elite
Decision Engine foi alterada -- apenas a apresentacao.
"""
from __future__ import annotations

from datetime import datetime
import json

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

import config
from src.ai import elite_decision_engine
from src.repository.base_repository import COLUNAS_DEZENAS
from src.services import elite_score_service, pagamento_service, previsao_service
from src.ui.componentes import (
    dezenas_html,
    dezenas_grid_lotofacil,
    render_estrategia_recomendada,
    render_explicacao_elite,
    render_qualidade_elite_simplificada,
)


def render_card_publico(df: pd.DataFrame, meta: dict) -> None:
    premio = meta["premio_estimado"] if meta["premio_estimado"] != "Consultar CAIXA" else "Premio estimado aguardando atualizacao oficial."
    ultimo = df.iloc[-1][COLUNAS_DEZENAS].astype(int).tolist() if not df.empty else []
    ultimo_concurso = int(df.iloc[-1]["Concurso"]) if not df.empty else "-"
    data_ultimo = str(df.iloc[-1]["Data"]) if not df.empty else "-"
    grid = dezenas_grid_lotofacil(ultimo)
    st.markdown(
        f"""
        <div class="oficial-shell">
            <div class="public-card">
                <div class="public-title">Resultado / Proximo Concurso</div>
                <div class="public-concurso">Concurso: {meta['concurso_alvo']}</div>
                <div class="public-meta">Data: {meta['data_sorteio']}</div>
                <div class="public-prize-label">Premio estimado</div>
                <div class="public-prize">{premio}</div>
                <div class="public-meta" style="margin-top:12px;color:#0066B3;">Ultimo resultado carregado: concurso {ultimo_concurso} | {data_ultimo}</div>
                {grid}
            </div>
            <div class="premiacao-card">
                <h3>Premiacao</h3>
                <div class="premio-row"><span>15 acertos</span><span>Aguardando</span></div>
                <div class="premio-row"><span>14 acertos</span><span>Aguardando</span></div>
                <div class="premio-row"><span>13 acertos</span><span>Aguardando</span></div>
                <div class="premio-row"><span>12 acertos</span><span>Aguardando</span></div>
                <div class="premio-row"><span>11 acertos</span><span>Aguardando</span></div>
                <div style="margin-top:16px;color:#64748B;font-size:14px;font-weight:750;line-height:1.45;">
                    Dados de premiacao aguardando atualizacao oficial.
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def estado_pagamento() -> dict:
    estado = st.session_state.get("pagamento_pix_lotofacil")
    if not isinstance(estado, dict):
        estado = {}
        st.session_state.pagamento_pix_lotofacil = estado
    return estado


def render_gate_pix(meta: dict) -> bool:
    estado = estado_pagamento()
    valor = pagamento_service.valor_padrao_analise(1)

    if estado.get("aprovado"):
        horario = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        st.success("✅ Pagamento confirmado\n\n🔓 Seus numeros da sorte foram liberados")
        c1, c2 = st.columns(2)
        c1.metric("Horario da geracao", horario)
        c2.metric("Concurso alvo", meta["concurso_alvo"])
        c3, c4 = st.columns(2)
        c3.metric("Premio estimado", meta["premio_estimado"])
        c4.metric("ID da previsao", f"LF-{estado.get('payment_id', 'APROVADO')}-{meta['concurso_alvo']}")
        return True

    st.info("A Lotofacil e aleatoria. Estes numeros sao uma analise estatistica e nao garantem premio.")
    st.markdown('<div class="email-box"><div class="step-label">PASSO 1</div><div class="step-title">Informe seu e-mail para liberar seus numeros da sorte</div>', unsafe_allow_html=True)
    email = st.text_input(
        "📧 Coloque seu e-mail aqui",
        value=str(estado.get("email_cliente", "")),
        placeholder="Digite seu melhor e-mail",
        key="email_pix_lotofacil",
    ).strip()
    st.caption("Seu e-mail e utilizado apenas para identificar sua solicitacao e liberar seus numeros da sorte.")
    st.markdown("</div>", unsafe_allow_html=True)
    email_valido = pagamento_service.email_valido(email)
    if email and not email_valido:
        st.error("Informe um e-mail valido para gerar o PIX.")

    st.markdown('<div class="step-label">PASSO 2</div><div class="step-title">Clique abaixo para gerar seu PIX</div>', unsafe_allow_html=True)
    if st.button("💳 GERAR QR CODE PIX DE R$ 1,00", key="criar_pix_lotofacil", disabled=not email_valido, use_container_width=True):
        token = config.obter_token_mercado_pago()
        try:
            if not token:
                raise ValueError("MERCADO_PAGO_ACCESS_TOKEN nao configurado em st.secrets.")
            dados_pix = pagamento_service.criar_pix(token, valor, f"Lotofacil Elite Pro - concurso {meta['concurso_alvo']}", email)
            estado.update({**dados_pix, "email_cliente": email, "valor_total": valor, "aprovado": dados_pix["status"] == "approved"})
            pagamento_service.registrar_pagamento("Previsao Lotofacil", meta["concurso_alvo"], valor, dados_pix["status"], dados_pix["payment_id"], email)
            st.rerun()
        except Exception as erro:
            pagamento_service.registrar_pagamento("Previsao Lotofacil", meta["concurso_alvo"], valor, "erro_criacao", "", email)
            st.error(f"Falha ao criar PIX: {erro}")
    st.caption("Apos o pagamento seus numeros serao liberados automaticamente.")

    if estado.get("qr_code_base64"):
        st.markdown(
            f"""
            <div style="background:#fff;padding:20px;border-radius:16px;text-align:center;box-shadow:0 4px 12px rgba(0,0,0,.08);max-width:360px;margin:18px auto;">
                <div style="font-size:18px;font-weight:900;color:#111827;margin-bottom:8px;">Pagamento PIX</div>
                <div style="font-size:15px;font-weight:800;color:#065F46;margin-bottom:14px;">Valor: R$ 1,00</div>
                <img src="data:image/png;base64,{estado['qr_code_base64']}" width="300" style="max-width:100%;border-radius:12px;" alt="QR Code PIX">
            </div>
            """,
            unsafe_allow_html=True,
        )
    if estado.get("qr_code"):
        codigo_pix_json = json.dumps(str(estado["qr_code"]))
        components.html(
            f"""
            <div style="text-align:center;">
                <button onclick='navigator.clipboard.writeText({codigo_pix_json})'
                style="background:#005CA9;color:white;border:0;border-radius:10px;padding:11px 18px;font-weight:900;cursor:pointer;">COPIAR PIX</button>
            </div>
            """,
            height=48,
        )
        st.text_area("Codigo PIX copia e cola", estado["qr_code"], height=110)

    if estado.get("payment_id"):
        st.markdown('<div class="step-label">PASSO 3</div><div class="step-title">🔓 Liberar meus numeros da sorte</div>', unsafe_allow_html=True)
        if st.button("🔓 LIBERAR MEUS NUMEROS DA SORTE", type="primary", use_container_width=True):
            token = config.obter_token_mercado_pago()
            try:
                dados_pix = pagamento_service.consultar_pix(token, estado["payment_id"])
                estado.update(dados_pix)
                estado["aprovado"] = dados_pix["status"] == "approved"
                pagamento_service.registrar_pagamento(
                    "Previsao Lotofacil",
                    meta["concurso_alvo"],
                    valor,
                    dados_pix["status"],
                    dados_pix["payment_id"],
                    str(estado.get("email_cliente", "")),
                    "previsao_liberada" if estado["aprovado"] else "",
                )
                st.rerun()
            except Exception as erro:
                st.error(f"Falha ao verificar pagamento: {erro}")
    return False


def render_resultado(df: pd.DataFrame, meta: dict) -> None:
    """Fluxo unico de resultado, em 4 secoes lineares (sem abas, sem cliques
    extras): 📊 Resultado -> 🧠 Qualidade -> 💬 Explicacao -> 🎯 Estrategia.

    Nenhuma das secoes recalcula nada: todas leem os mesmos jogos e os mesmos
    resultados ja calculados pelo Motor Elite, pelo Elite Score e pelo Elite
    Decision Engine (nenhum desses modulos foi alterado nesta fase)."""
    jogos = previsao_service.gerar_previsoes_producao(df)
    jogos_com_score, resultados_elite_score = elite_score_service.anexar_elite_score(jogos, df)

    # 📊 Resultado -----------------------------------------------------
    st.markdown("## 📊 Seus jogos de hoje")
    st.caption(f"Concurso {meta['concurso_alvo']} | Premio estimado: {meta['premio_estimado']}")
    for (_, row), _ in zip(jogos_com_score.iterrows(), resultados_elite_score):
        dezenas = [int(row[coluna]) for coluna in COLUNAS_DEZENAS]
        st.markdown(f"##### {row['Perfil']}")
        st.markdown(dezenas_html(dezenas), unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        c1.metric("Soma dos numeros", int(row["Soma"]))
        c2.metric("Pares e impares", f"{int(row['Pares'])} pares / {int(row['Impares'])} impares")

    # 🧠 Qualidade (Elite Score) ------------------------------------------
    st.markdown("## 🧠 Qualidade de cada jogo")
    selecao = render_qualidade_elite_simplificada(jogos_com_score, resultados_elite_score, key_prefix="publico")

    # 💬 Explicacao (Fase V1.4) --------------------------------------------
    if selecao is not None:
        jogo_selecionado, resultado_selecionado = selecao
        render_explicacao_elite(jogo_selecionado, resultado_selecionado)

    # 🎯 Estrategia (Fase V1.5) -----------------------------------------------
    relatorio_estrategico = elite_decision_engine.gerar_relatorio_estrategico(resultados_elite_score)
    render_estrategia_recomendada(relatorio_estrategico)

    caminho = previsao_service.exportar_previsoes(jogos, meta["concurso_alvo"])
    st.download_button("📥 Baixar meus jogos", jogos.to_csv(index=False).encode("utf-8-sig"), caminho.name, "text/csv")


def render_fluxo_publico(df: pd.DataFrame, meta: dict) -> None:
    """🎯 Gerar jogos: ponto de entrada unico da tela publica.

    Um unico clique inicia o fluxo (gate de pagamento seguido do resultado
    completo em 4 secoes) sem nenhuma navegacao extra ou aba adicional. Movido
    de ``app.py`` para ca (Fase UX Final Simplification) para concentrar toda
    a logica de apresentacao da tela publica num unico lugar; o comportamento
    e as chaves de ``session_state`` (``previsao_iniciada``,
    ``prever_lotofacil_cta``) permanecem exatamente as mesmas de antes."""
    st.markdown('<div style="text-align:center;"><span class="badge">🔥 MAIS ACESSADO</span></div>', unsafe_allow_html=True)
    if st.button("🎯 GERAR MEUS JOGOS", key="prever_lotofacil_cta", use_container_width=True):
        st.session_state.previsao_iniciada = True
    st.session_state.setdefault("previsao_iniciada", True)
    if st.session_state.previsao_iniciada:
        if render_gate_pix(meta):
            render_resultado(df, meta)
