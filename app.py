from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from src.carregar_dados import (
    CAMINHO_BASE_PADRAO,
    COLUNAS_DEZENAS,
    FONTE_CAIXA_URL,
    atualizar_base_local,
    buscar_info_concurso_atual,
    carregar_base,
    resumo_base,
)
from src.estatisticas_lotofacil import (
    centro_moldura,
    dezenas_atrasadas,
    dezenas_frias,
    dezenas_quentes,
    linhas_colunas,
    pares_impares,
)
from src.mercado_pago_pix import consultar_pagamento_pix, criar_pagamento_pix, extrair_dados_pix
from src.motor_elite_lotofacil import (
    MOTOR_OFICIAL_PRODUCAO,
    gerar_jogos_producao_v1,
    gerar_varios_jogos,
    ranking_elite_lotofacil,
)
from src.pagamentos import calcular_valor_pagamento, email_cliente_valido, registrar_pagamento


st.set_page_config(page_title="Lotofacil Elite Pro", page_icon="LF", layout="wide")

VERSAO_APP = "LOTOFACIL_PRODUCAO_V1"
STATUS_APP = "PRODUCAO"
MODO_ADMIN = False


def modo_admin_ativo() -> bool:
    try:
        return bool(st.secrets.get("MODO_ADMIN", MODO_ADMIN))
    except Exception:
        return MODO_ADMIN


@st.cache_data(ttl=1800)
def info_caixa_cached() -> dict:
    info = buscar_info_concurso_atual()
    return info if isinstance(info, dict) else {}


def formatar_moeda(valor: object) -> str:
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        texto = str(valor or "").strip()
        return texto if texto else "Consultar CAIXA"
    return f"R$ {numero:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def metadados_publicos(df: pd.DataFrame) -> dict:
    info = info_caixa_cached()
    resumo = resumo_base(df)
    concurso = info.get("proximo_concurso") or (resumo["ultimo_concurso"] + 1)
    data = info.get("data_proximo_concurso") or "Aguardando CAIXA"
    premio = formatar_moeda(info.get("premio_estimado"))
    return {
        "concurso_alvo": concurso,
        "data_sorteio": data,
        "premio_estimado": premio,
        "acumulou": info.get("acumulou"),
        "fonte": info.get("fonte", "fallback_local"),
    }


def aplicar_css() -> None:
    st.markdown(
        """
        <style>
        :root {
            --lf-blue:#0066B3;
            --lf-turquoise:#20C7B5;
            --lf-purple:#B000B9;
            --lf-green:#00A859;
            --lf-neon:#00FF66;
            --lf-gold:#FFD700;
            --lf-bg:#F5FBFF;
            --text:#111827;
        }
        .stApp { background: linear-gradient(180deg,#F5FBFF 0%,#E9FFFB 100%); color:var(--text); }
        .block-container { max-width: 1180px; padding-top: 1rem; }
        .hero {
            position:relative; overflow:hidden;
            background: linear-gradient(135deg,#0066B3 0%,#20C7B5 100%);
            color:white; border-radius:20px; padding:34px 36px; margin-bottom:18px;
            box-shadow:0 18px 42px rgba(0,102,179,.24);
        }
        .hero:before, .hero:after {
            content:"ðŸ€ ðŸ€ ðŸ€"; position:absolute; color:rgba(255,255,255,.22);
            font-size:46px; font-weight:900; letter-spacing:18px; transform:rotate(-12deg);
        }
        .hero:before { right:22px; top:18px; }
        .hero:after { left:28px; bottom:-8px; font-size:34px; opacity:.5; }
        .hero h1 { margin:0; font-size:46px; line-height:1.05; font-weight:950; position:relative; }
        .hero-sub { margin-top:10px; font-size:18px; font-weight:750; opacity:.98; position:relative; }
        .oficial-shell {
            display:grid; grid-template-columns:1.35fr .85fr; gap:18px; align-items:stretch;
            margin:16px 0 20px;
        }
        .public-card, .premiacao-card, .payment-panel {
            background:#fff; border:1.5px solid rgba(32,199,181,.42);
            border-radius:18px; box-shadow:0 16px 34px rgba(0,102,179,.10);
        }
        .public-card { padding:24px; border-top:6px solid var(--lf-turquoise); }
        .public-title { color:var(--lf-blue); font-size:18px; font-weight:950; text-transform:uppercase; letter-spacing:.04em; }
        .public-concurso { color:var(--lf-purple); font-size:30px; font-weight:950; margin:6px 0; }
        .public-prize-label { color:#475569; font-size:15px; font-weight:850; margin-top:14px; }
        .public-prize { color:var(--lf-purple); font-size:38px; font-weight:950; margin:2px 0 8px; }
        .public-meta { color:#334155; font-size:16px; font-weight:850; line-height:1.55; }
        .lotofacil-grid {
            display:grid; grid-template-columns:repeat(5, minmax(42px, 1fr)); gap:0;
            border:1px solid #D8B4FE; border-radius:14px; overflow:hidden; margin-top:18px;
            background:#FBF5FF;
        }
        .lotofacil-dezena {
            min-height:54px; display:flex; align-items:center; justify-content:center;
            color:var(--lf-purple); font-size:25px; font-weight:950;
            border-right:1px solid #E9D5FF; border-bottom:1px solid #E9D5FF;
        }
        .lotofacil-dezena:nth-child(5n) { border-right:0; }
        .lotofacil-dezena:nth-last-child(-n+5) { border-bottom:0; }
        .premiacao-card { padding:24px; border-top:6px solid var(--lf-purple); }
        .premiacao-card h3 { color:var(--lf-purple); margin:0 0 14px; font-size:24px; font-weight:950; }
        .premio-row {
            display:flex; justify-content:space-between; gap:12px; padding:10px 0;
            border-bottom:1px solid #E0F2FE; color:#1F2937; font-weight:850;
        }
        .premio-row:last-child { border-bottom:0; }
        @keyframes megaLed {
            0%,100% { opacity:.78; box-shadow:0 0 8px var(--lf-neon); }
            50% { opacity:1; box-shadow:0 0 20px var(--lf-neon),0 0 40px var(--lf-neon),0 0 80px var(--lf-neon); }
        }
        .st-key-prever_lotofacil_cta button {
            width:70% !important; max-width:760px !important; min-height:60px !important;
            background:#00C853 !important; color:#fff !important; border:3px solid var(--lf-neon) !important;
            border-radius:14px !important; font-size:19px !important; font-weight:900 !important;
            animation:megaLed 1s infinite !important;
            box-shadow:0 0 10px var(--lf-neon),0 0 20px var(--lf-neon),0 0 40px var(--lf-neon) !important;
        }
        .st-key-prever_lotofacil_cta { text-align:center !important; }
        .st-key-prever_lotofacil_cta button * { color:#fff !important; font-weight:900 !important; }
        .badge {
            display:inline-block; margin:8px auto; padding:7px 14px; border-radius:999px;
            background:#FEF3C7; color:#92400E; border:1px solid #F59E0B;
            font-size:13px; font-weight:950;
        }
        .step-label { margin:20px 0 6px; color:var(--lf-blue); font-size:17px; font-weight:950; letter-spacing:.04em; }
        .step-title { color:#111827; font-size:23px; line-height:1.2; font-weight:950; margin-bottom:10px; }
        .email-box {
            background:#fff; border:2px solid rgba(32,199,181,.48); border-radius:18px;
            padding:20px; margin:20px 0 18px; box-shadow:0 12px 28px rgba(0,102,179,.10);
        }
        @keyframes emailGlow {
            0%,100% { box-shadow:0 0 0 rgba(0,255,102,0),0 12px 28px rgba(22,163,74,.10); }
            50% { box-shadow:0 0 18px rgba(0,255,102,.34),0 12px 28px rgba(22,163,74,.14); }
        }
        .st-key-email_pix_lotofacil input {
            min-height:70px !important; border:3px solid var(--lf-turquoise) !important; border-radius:16px !important;
            font-size:22px !important; font-weight:850 !important; padding:14px 18px !important;
            background:#fff !important; color:#111827 !important;
        }
        .st-key-email_pix_lotofacil input:placeholder-shown { animation:emailGlow 1.8s infinite ease-in-out; }
        .st-key-email_pix_lotofacil label, .st-key-email_pix_lotofacil label * {
            color:var(--lf-blue) !important; font-size:18px !important; font-weight:950 !important;
        }
        @keyframes pulseGlowPix {
            0%,100% { box-shadow:0 0 20px #FFD700,0 0 40px #FFD700,0 0 60px rgba(255,215,0,.8); transform:scale(1); }
            50% { box-shadow:0 0 28px #FFD700,0 0 58px #FFD700,0 0 86px rgba(255,215,0,.92); transform:scale(1.018); }
        }
        .st-key-criar_pix_lotofacil button {
            background:#FFD700 !important; color:#111827 !important; border:3px solid #EAB308 !important;
            border-radius:18px !important; min-height:90px !important; width:100% !important;
            font-size:24px !important; font-weight:950 !important;
            animation:pulseGlowPix 1.35s infinite ease-in-out !important;
        }
        .st-key-criar_pix_lotofacil button *, .st-key-criar_pix_lotofacil button p { color:#111827 !important; font-weight:950 !important; }
        .balls { display:flex; gap:8px; flex-wrap:wrap; justify-content:center; margin:12px 0; }
        .ball {
            width:42px; height:42px; border-radius:50%; background:radial-gradient(circle at 32% 28%,#F0ABFC,#B000B9 62%,#701A75);
            color:#fff; display:inline-flex; align-items:center; justify-content:center; font-weight:950;
            box-shadow:inset 0 2px 5px rgba(255,255,255,.28),0 8px 18px rgba(22,163,74,.20);
        }
        .footer { text-align:center; color:#4B5563; font-size:13px; padding:24px 0 10px; border-top:1px solid rgba(0,102,179,.14); margin-top:22px; }
        @media (max-width:760px) {
            .hero { padding:24px 22px; }
            .hero h1 { font-size:32px; }
            .oficial-shell { grid-template-columns:1fr; }
            .public-concurso { font-size:25px; }
            .public-prize { font-size:27px; }
            .lotofacil-dezena { min-height:46px; font-size:21px; }
            .st-key-prever_lotofacil_cta button { width:100% !important; min-height:80px !important; font-size:15px !important; }
            .st-key-criar_pix_lotofacil button { min-height:86px !important; font-size:20px !important; white-space:normal !important; }
            .st-key-email_pix_lotofacil input { font-size:19px !important; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


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
            <div style="margin-top:8px;font-size:13px;font-weight:800;">{VERSAO_APP} | {STATUS_APP}</div>
        </div>
        """,
        unsafe_allow_html=True,
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


def obter_token_mercado_pago() -> str:
    try:
        return str(st.secrets.get("MERCADO_PAGO_ACCESS_TOKEN", "")).strip()
    except Exception:
        return ""


def estado_pagamento() -> dict:
    estado = st.session_state.get("pagamento_pix_lotofacil")
    if not isinstance(estado, dict):
        estado = {}
        st.session_state.pagamento_pix_lotofacil = estado
    return estado


def render_gate_pix(meta: dict) -> bool:
    estado = estado_pagamento()
    valor = calcular_valor_pagamento(1)

    if estado.get("aprovado"):
        horario = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        st.success("âœ… Pagamento confirmado\n\nðŸ”“ Seus numeros da sorte foram liberados")
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
        "ðŸ“§ Coloque seu e-mail aqui",
        value=str(estado.get("email_cliente", "")),
        placeholder="Digite seu melhor e-mail",
        key="email_pix_lotofacil",
    ).strip()
    st.caption("Seu e-mail e utilizado apenas para identificar sua solicitacao e liberar seus numeros da sorte.")
    st.markdown("</div>", unsafe_allow_html=True)
    email_valido = email_cliente_valido(email)
    if email and not email_valido:
        st.error("Informe um e-mail valido para gerar o PIX.")

    st.markdown('<div class="step-label">PASSO 2</div><div class="step-title">Clique abaixo para gerar seu PIX</div>', unsafe_allow_html=True)
    if st.button("ðŸ’³ GERAR QR CODE PIX DE R$ 1,00", key="criar_pix_lotofacil", disabled=not email_valido, use_container_width=True):
        token = obter_token_mercado_pago()
        try:
            if not token:
                raise ValueError("MERCADO_PAGO_ACCESS_TOKEN nao configurado em st.secrets.")
            resposta = criar_pagamento_pix(token, valor, f"Lotofacil Elite Pro - concurso {meta['concurso_alvo']}", email)
            dados_pix = extrair_dados_pix(resposta)
            estado.update({**dados_pix, "email_cliente": email, "valor_total": valor, "aprovado": dados_pix["status"] == "approved"})
            registrar_pagamento("Previsao Lotofacil", meta["concurso_alvo"], valor, dados_pix["status"], dados_pix["payment_id"], email)
            st.rerun()
        except Exception as erro:
            registrar_pagamento("Previsao Lotofacil", meta["concurso_alvo"], valor, "erro_criacao", "", email)
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
        st.markdown('<div class="step-label">PASSO 3</div><div class="step-title">ðŸ”“ Liberar meus numeros da sorte</div>', unsafe_allow_html=True)
        if st.button("ðŸ”“ LIBERAR MEUS NUMEROS DA SORTE", type="primary", use_container_width=True):
            token = obter_token_mercado_pago()
            try:
                dados_pix = extrair_dados_pix(consultar_pagamento_pix(token, estado["payment_id"]))
                estado.update(dados_pix)
                estado["aprovado"] = dados_pix["status"] == "approved"
                registrar_pagamento(
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
    jogos = gerar_jogos_producao_v1(df)
    st.markdown("### Resultado")
    st.markdown("#### 5 jogos inteligentes liberados")
    st.caption(f"Motor oficial: {MOTOR_OFICIAL_PRODUCAO}")
    for _, row in jogos.iterrows():
        dezenas = [int(row[f"Bola{i}"]) for i in range(1, 16)]
        st.markdown(f"##### {row['Perfil']}")
        st.markdown(dezenas_html(dezenas), unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Score temporal", f"{float(row['Elite Score Temporal']):.2f}")
        c2.metric("Soma", int(row["Soma"]))
        c3.metric("Pares/Impares", f"{int(row['Pares'])}/{int(row['Impares'])}")
        c4.metric("Repeticao", int(row["Repeticao anterior"]))
    st.caption(f"Concurso alvo: {meta['concurso_alvo']} | Premio estimado: {meta['premio_estimado']}")

    st.dataframe(jogos, width="stretch", hide_index=True)
    Path("exports").mkdir(exist_ok=True)
    caminho = Path("exports") / f"lotofacil_previsao_{meta['concurso_alvo']}.csv"
    jogos.to_csv(caminho, index=False, encoding="utf-8-sig")
    st.download_button("Baixar jogos CSV", jogos.to_csv(index=False).encode("utf-8-sig"), caminho.name, "text/csv")


def render_admin(df: pd.DataFrame, meta: dict) -> None:
    st.subheader("Admin / Desenvolvimento")
    col1, col2, col3 = st.columns(3)
    resumo = resumo_base(df)
    col1.metric("Concursos", resumo["total_concursos"])
    col2.metric("Ultimo concurso", resumo["ultimo_concurso"])
    col3.metric("Proximo concurso", meta["concurso_alvo"])

    if st.button("Atualizar base oficial CAIXA", type="primary"):
        if atualizar_base_local():
            info_caixa_cached.clear()
            st.success("Base oficial Lotofacil atualizada.")
            st.rerun()
        else:
            st.warning("Nao foi possivel atualizar pela CAIXA agora. Mantendo base local.")

    abas = st.tabs(["Estatisticas", "Motor Elite", "Base"])
    with abas[0]:
        c1, c2, c3 = st.columns(3)
        c1.dataframe(dezenas_quentes(df), width="stretch", hide_index=True)
        c2.dataframe(dezenas_frias(df), width="stretch", hide_index=True)
        c3.dataframe(dezenas_atrasadas(df).head(10), width="stretch", hide_index=True)
        ultimo = df.iloc[-1][COLUNAS_DEZENAS].astype(int).tolist()
        st.write("Pares x impares", pares_impares(ultimo))
        st.write("Centro x moldura", centro_moldura(ultimo))
        st.write("Linhas e colunas", linhas_colunas(ultimo))
    with abas[1]:
        ranking = ranking_elite_lotofacil(df)
        st.dataframe(ranking, width="stretch", hide_index=True)
        if st.button("Gerar jogos inteligentes", type="primary"):
            st.session_state.jogos_admin = gerar_varios_jogos(df, 10)
        if isinstance(st.session_state.get("jogos_admin"), pd.DataFrame):
            st.dataframe(st.session_state.jogos_admin, width="stretch", hide_index=True)
    with abas[2]:
        st.link_button("Fonte oficial CAIXA", FONTE_CAIXA_URL)
        st.caption(f"Base local: {CAMINHO_BASE_PADRAO}")
        st.dataframe(df.tail(30), width="stretch", hide_index=True)


def main() -> None:
    aplicar_css()
    render_header()
    df = carregar_base()
    meta = metadados_publicos(df)
    render_card_publico(df, meta)

    if modo_admin_ativo():
        render_admin(df, meta)
    else:
        st.markdown('<div style="text-align:center;"><span class="badge">ðŸ”¥ MAIS ACESSADO</span></div>', unsafe_allow_html=True)
        if st.button("ðŸŽ¯ PREVER PROXIMO SORTEIO", key="prever_lotofacil_cta", use_container_width=True):
            st.session_state.previsao_iniciada = True
        st.session_state.setdefault("previsao_iniciada", True)
        if st.session_state.previsao_iniciada:
            if render_gate_pix(meta):
                render_resultado(df, meta)

    st.markdown(
        f"""
        <div class="footer">
            Lotofacil Elite Pro | {VERSAO_APP} | {STATUS_APP}<br>
            Analise estatistica sem garantia de acerto, premio ou resultado.
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
