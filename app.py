from __future__ import annotations

import re
import time

import pandas as pd
import streamlit as st

from src.carregar_dados import (
    CAMINHO_BASE_PADRAO,
    COLUNAS_DEZENAS,
    buscar_info_concurso_atual,
    carregar_base,
    resumo_base,
)
from src.jogos_salvos import (
    CAMINHO_JOGOS_SALVOS,
    conferir_jogos_salvos,
    ler_jogos_salvos,
    normalizar_colunas_jogos_salvos,
    salvar_carteira,
)
from src.motor_elite_lotofacil import (
    MOTOR_OFICIAL_PRODUCAO,
    NOMES_JOGOS_PRODUCAO,
    assinatura_portfolio,
    gerar_jogos_producao_v1,
    validar_jogos_producao,
)


st.set_page_config(page_title="Lotofácil Elite Pro", page_icon="LF", layout="wide")

DESCRICOES_JOGOS = {
    "Diamante": "Busca dos 15 pelo maior score estatístico geral e ranking temporal.",
    "Ouro": "Busca dos 15 equilibrando score alto, regularidade e frequência recente.",
    "Prata": "Busca dos 15 com alternativa forte e menor dependência das dezenas óbvias.",
    "Agressivo": "Busca dos 15 com maior variação, atrasadas e padrões menos explorados.",
    "Conservador": "Busca dos 15 com estabilidade e padrões históricos consistentes.",
}

TITULOS_JOGOS = {
    "Diamante": "Diamante — maior score",
    "Ouro": "Ouro — equilíbrio premium",
    "Prata": "Prata — alternativa forte",
    "Agressivo": "Agressivo — maior variação",
    "Conservador": "Conservador — maior estabilidade",
}


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


def _lista_dezenas(valor: object) -> list[int]:
    if isinstance(valor, (list, tuple, set, pd.Series)):
        itens = list(valor)
    else:
        itens = re.findall(r"\d+", str(valor or ""))
    dezenas = []
    for item in itens:
        try:
            dezena = int(float(item))
        except (TypeError, ValueError):
            continue
        if dezena not in dezenas:
            dezenas.append(dezena)
    return sorted(dezenas)


def _numero(valor: object, padrao: float = 0.0) -> float:
    numero = pd.to_numeric(valor, errors="coerce")
    return padrao if pd.isna(numero) else float(numero)


def normalizar_jogos_gerados(jogos: list[dict] | pd.DataFrame | None) -> pd.DataFrame:
    """Normaliza jogos atuais ou legados para o contrato usado pela interface."""
    if isinstance(jogos, pd.DataFrame):
        normalizados = jogos.copy()
    elif isinstance(jogos, list):
        normalizados = pd.DataFrame(jogos)
    else:
        normalizados = pd.DataFrame()

    linhas = []
    for indice, row in normalizados.reset_index(drop=True).iterrows():
        dados = row.to_dict()
        dezenas = _lista_dezenas(dados.get("Dezenas"))
        if not dezenas:
            dezenas = _lista_dezenas([dados.get(f"Bola{i}") for i in range(1, 16)])

        score = _numero(
            dados.get("Score", dados.get("Elite Score Temporal", dados.get("Elite Score", 0)))
        )
        potencial = _numero(dados.get("Potencial 15", score), score)
        pares = int(_numero(dados.get("Pares"), sum(1 for dezena in dezenas if dezena % 2 == 0)))
        impares = int(
            _numero(
                dados.get("Ímpares", dados.get("Impares")),
                sum(1 for dezena in dezenas if dezena % 2 != 0),
            )
        )

        dados["Perfil"] = str(
            dados.get("Perfil")
            or (NOMES_JOGOS_PRODUCAO[indice] if indice < len(NOMES_JOGOS_PRODUCAO) else f"Jogo {indice + 1}")
        )
        dados["Dezenas"] = dezenas
        dados["Score"] = score
        dados["Elite Score Temporal"] = _numero(dados.get("Elite Score Temporal", score), score)
        dados["Potencial 15"] = potencial
        dados["Soma"] = int(_numero(dados.get("Soma"), sum(dezenas)))
        dados["Pares"] = pares
        dados["Ímpares"] = impares
        dados["Impares"] = impares
        dados["Motor"] = str(dados.get("Motor") or MOTOR_OFICIAL_PRODUCAO)
        dados["Estrategia"] = str(dados.get("Estrategia") or DESCRICOES_JOGOS.get(dados["Perfil"], ""))
        for posicao, dezena in enumerate(dezenas[:15], start=1):
            dados[f"Bola{posicao}"] = dezena
        linhas.append(dados)

    return pd.DataFrame(linhas)


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
        .stApp { background:linear-gradient(180deg,#061526 0%,#0A2340 45%,#07192F 100%); color:#F8FAFC; }
        .block-container { max-width:1180px; padding-top:1rem; padding-bottom:2rem; }
        [data-testid="stHeader"], [data-testid="stToolbar"], #MainMenu, footer { display:none !important; }
        [data-testid="stMarkdownContainer"] p, [data-testid="stCaptionContainer"] { color:rgba(255,255,255,.72); }
        .stApp h1, .stApp h2, .stApp h3 { color:#fff; }
        .hero {
            position:relative; overflow:hidden;
            background: linear-gradient(135deg,#0066B3 0%,#20C7B5 100%);
            color:white; border-radius:20px; padding:34px 36px; margin-bottom:18px;
            box-shadow:0 18px 42px rgba(0,102,179,.24);
        }
        .hero:before, .hero:after {
            content:"25  15  01"; position:absolute; color:rgba(255,255,255,.16);
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
        .public-card, .premiacao-card {
            background:linear-gradient(145deg,rgba(255,255,255,.085),rgba(255,255,255,.035)); border:1px solid rgba(255,255,255,.13);
            border-radius:18px; box-shadow:0 16px 34px rgba(0,0,0,.18); color:#fff;
        }
        .public-card { padding:24px; border-top:4px solid var(--lf-turquoise); }
        .public-title { color:#67E8F9; font-size:18px; font-weight:950; text-transform:uppercase; letter-spacing:.04em; }
        .public-concurso { color:#E879F9; font-size:30px; font-weight:950; margin:6px 0; }
        .public-prize-label { color:rgba(255,255,255,.55); font-size:15px; font-weight:850; margin-top:14px; }
        .public-prize { color:#FFD700; font-size:38px; font-weight:950; margin:2px 0 8px; }
        .public-meta { color:rgba(255,255,255,.72); font-size:16px; font-weight:850; line-height:1.55; }
        .lotofacil-grid {
            display:grid; grid-template-columns:repeat(5, minmax(42px, 1fr)); gap:0;
            border:1px solid rgba(232,121,249,.35); border-radius:14px; overflow:hidden; margin-top:18px;
            background:rgba(176,0,185,.08);
        }
        .lotofacil-dezena {
            min-height:54px; display:flex; align-items:center; justify-content:center;
            color:var(--lf-purple); font-size:25px; font-weight:950;
            border-right:1px solid rgba(232,121,249,.18); border-bottom:1px solid rgba(232,121,249,.18);
        }
        .lotofacil-dezena:nth-child(5n) { border-right:0; }
        .lotofacil-dezena:nth-last-child(-n+5) { border-bottom:0; }
        .premiacao-card { padding:24px; border-top:4px solid #E879F9; }
        .premiacao-card h3 { color:#E879F9; margin:0 0 14px; font-size:24px; font-weight:950; }
        .premio-row {
            display:flex; justify-content:space-between; gap:12px; padding:10px 0;
            border-bottom:1px solid rgba(255,255,255,.1); color:rgba(255,255,255,.75); font-weight:850;
        }
        .premio-row:last-child { border-bottom:0; }
        [data-testid="stAlert"] { border:1px solid rgba(255,215,0,.25); border-radius:16px; background:rgba(255,215,0,.08); color:#fff; }
        .balls { display:flex; gap:8px; flex-wrap:wrap; justify-content:center; margin:12px 0; }
        .ball {
            width:42px; height:42px; border-radius:50%; background:radial-gradient(circle at 32% 28%,#F0ABFC,#B000B9 62%,#701A75);
            color:#fff; display:inline-flex; align-items:center; justify-content:center; font-weight:950;
            box-shadow:inset 0 2px 5px rgba(255,255,255,.28),0 8px 18px rgba(22,163,74,.20);
        }
        .elite-results {
            margin:24px 0; padding:26px; border-radius:22px;
            background:linear-gradient(145deg,#07192F,#063B65); color:#fff;
            box-shadow:0 20px 48px rgba(0,102,179,.22);
        }
        .elite-results-head { text-align:center; margin-bottom:22px; }
        .elite-results-title { font-size:29px; font-weight:950; margin:0; }
        .elite-results-sub { margin-top:8px; color:rgba(255,255,255,.68); font-size:14px; font-weight:700; }
        .elite-games-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:15px; }
        .elite-game-card {
            border:1px solid rgba(255,255,255,.14); border-radius:18px; padding:20px;
            background:rgba(255,255,255,.07); backdrop-filter:blur(8px);
        }
        .elite-game-card:first-child { grid-column:1/-1; border-color:rgba(255,215,0,.55); background:linear-gradient(135deg,rgba(255,215,0,.13),rgba(255,255,255,.06)); }
        .elite-game-top { display:flex; justify-content:space-between; align-items:center; gap:12px; }
        .elite-game-name { font-size:22px; font-weight:950; color:#fff; }
        .elite-game-position { border-radius:999px; padding:5px 9px; background:rgba(33,199,181,.16); color:#67E8F9; font-size:10px; font-weight:950; }
        .elite-game-description { min-height:42px; margin:9px 0 15px; color:rgba(255,255,255,.62); font-size:12px; line-height:1.6; }
        .elite-balls { display:flex; flex-wrap:wrap; gap:7px; }
        .elite-ball {
            width:39px; height:39px; border-radius:50%; display:flex; align-items:center; justify-content:center;
            background:radial-gradient(circle at 30% 25%,#F0ABFC,#B000B9 62%,#701A75);
            color:#fff; font-size:13px; font-weight:950; border:1px solid rgba(255,255,255,.32);
            box-shadow:inset 0 2px 4px rgba(255,255,255,.24),0 6px 14px rgba(0,0,0,.2);
        }
        .elite-game-meta { display:flex; flex-wrap:wrap; gap:8px; margin-top:15px; }
        .elite-game-meta span { border-radius:8px; background:rgba(255,255,255,.08); padding:6px 8px; color:rgba(255,255,255,.72); font-size:10px; font-weight:800; }
        .action-grid { display:grid; grid-template-columns:1.35fr .9fr; gap:12px; }
        .st-key-atualizar_jogos_elite button {
            min-height:58px !important; border-radius:14px !important; background:linear-gradient(135deg,#B000B9,#7E22CE) !important;
            color:#fff !important; border:2px solid #E879F9 !important; font-size:16px !important; font-weight:950 !important;
            box-shadow:0 10px 24px rgba(176,0,185,.22) !important;
        }
        .st-key-atualizar_jogos_elite button * { color:#fff !important; font-weight:950 !important; }
        .st-key-salvar_jogos_elite button, .st-key-conferir_jogos_salvos button {
            min-height:58px !important; border-radius:14px !important; background:rgba(32,199,181,.12) !important;
            color:#CFFAFE !important; border:1px solid rgba(103,232,249,.55) !important; font-weight:900 !important;
        }
        .prediction-note { color:#CFFAFE; text-align:center; font-size:14px; font-weight:800; margin:10px 0 18px; }
        .wallet-badge { display:flex; justify-content:center; margin:4px 0 20px; }
        .wallet-badge span { display:inline-flex; align-items:center; border-radius:999px; padding:10px 20px; border:1px solid rgba(255,215,0,.62); background:linear-gradient(135deg,rgba(255,215,0,.16),rgba(176,0,185,.16)); color:#FFE66D; font-size:14px; font-weight:950; letter-spacing:.08em; box-shadow:0 10px 26px rgba(255,215,0,.1); }
        .engine-panel { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:10px; margin:18px 0; padding:18px; border:1px solid rgba(103,232,249,.18); border-radius:18px; background:rgba(6,59,101,.34); }
        .engine-item { padding:11px 13px; border-radius:12px; background:rgba(255,255,255,.045); }
        .engine-label { color:rgba(255,255,255,.5); font-size:10px; font-weight:900; text-transform:uppercase; letter-spacing:.08em; }
        .engine-value { color:#E0F2FE; font-size:13px; font-weight:850; margin-top:4px; overflow-wrap:anywhere; }
        .summary-title, .saved-title { margin:26px 0 12px; color:#fff; font-size:22px; font-weight:950; }
        .summary-grid { display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:10px; margin-bottom:10px; }
        .summary-card { padding:16px 12px; border-radius:14px; text-align:center; border:1px solid rgba(232,121,249,.2); background:linear-gradient(145deg,rgba(176,0,185,.09),rgba(32,199,181,.07)); }
        .summary-value { color:#F0ABFC; font-size:21px; font-weight:950; }
        .summary-label { margin-top:5px; color:rgba(255,255,255,.58); font-size:10px; font-weight:800; line-height:1.35; }
        .saved-shell { margin-top:28px; padding:22px; border-radius:20px; border:1px solid rgba(103,232,249,.18); background:rgba(7,25,47,.72); }
        .saved-sub { color:rgba(255,255,255,.6); font-size:13px; line-height:1.6; margin-bottom:14px; }
        [data-testid="stDownloadButton"] button { min-height:52px; border-radius:13px; border:1px solid rgba(232,121,249,.45); background:rgba(176,0,185,.14); color:#fff; font-weight:900; }
        [data-testid="stDownloadButton"] button:hover { border-color:#E879F9; background:rgba(176,0,185,.24); color:#fff; }
        .free-analysis-intro { margin:26px 0 18px; padding:20px 22px; border:1px solid rgba(103,232,249,.22); border-radius:18px; background:linear-gradient(135deg,rgba(32,199,181,.11),rgba(176,0,185,.08)); color:rgba(255,255,255,.75); font-size:14px; line-height:1.7; text-align:center; }
        .footer { text-align:center; color:rgba(255,255,255,.48); font-size:12px; line-height:1.7; padding:26px 18px; border:1px solid rgba(255,255,255,.09); background:rgba(255,255,255,.035); border-radius:18px; margin-top:28px; }
        @media (max-width:760px) {
            .hero { padding:24px 22px; }
            .hero h1 { font-size:32px; }
            .oficial-shell { grid-template-columns:1fr; }
            .public-concurso { font-size:25px; }
            .public-prize { font-size:27px; }
            .lotofacil-dezena { min-height:46px; font-size:21px; }
            .elite-results { padding:18px 14px; }
            .elite-results-title { font-size:23px; }
            .elite-games-grid { grid-template-columns:1fr; }
            .elite-game-card:first-child { grid-column:auto; }
            .elite-game-description { min-height:0; }
            .elite-ball { width:36px; height:36px; }
            .engine-panel, .summary-grid { grid-template-columns:1fr; }
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
            <h1>Lotofácil Elite Pro</h1>
            <div class="hero-sub">Versão gratuita • Análise estatística sem garantia de prêmio</div>
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
                <div class="public-title">Resultado / Próximo Concurso</div>
                <div class="public-concurso">Concurso: {meta['concurso_alvo']}</div>
                <div class="public-meta">Data: {meta['data_sorteio']}</div>
                <div class="public-prize-label">Prêmio estimado</div>
                <div class="public-prize">{premio}</div>
                <div class="public-meta" style="margin-top:12px;color:#67E8F9;">Último resultado carregado: concurso {ultimo_concurso} | {data_ultimo}</div>
                {grid}
            </div>
            <div class="premiacao-card">
                <h3>Premiação</h3>
                <div class="premio-row"><span>15 acertos</span><span>Aguardando</span></div>
                <div class="premio-row"><span>14 acertos</span><span>Aguardando</span></div>
                <div class="premio-row"><span>13 acertos</span><span>Aguardando</span></div>
                <div class="premio-row"><span>12 acertos</span><span>Aguardando</span></div>
                <div class="premio-row"><span>11 acertos</span><span>Aguardando</span></div>
                <div style="margin-top:16px;color:#64748B;font-size:14px;font-weight:750;line-height:1.45;">
                    Dados de premiação aguardando atualização oficial.
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def montar_html_jogos(jogos: pd.DataFrame) -> str:
    jogos = normalizar_jogos_gerados(jogos)
    cards = []
    for posicao, nome in enumerate(NOMES_JOGOS_PRODUCAO, start=1):
        row = jogos[jogos["Perfil"] == nome].iloc[0]
        dezenas = [int(row[f"Bola{i}"]) for i in range(1, 16)]
        bolas = "".join(f'<span class="elite-ball">{dezena:02d}</span>' for dezena in dezenas)
        cards.append(
            '<article class="elite-game-card">'
            f'<div class="elite-game-top"><div class="elite-game-name">{TITULOS_JOGOS[nome]}</div><div class="elite-game-position">JOGO {posicao}/5</div></div>'
            f'<div class="elite-game-description">{DESCRICOES_JOGOS[nome]}</div>'
            f'<div class="elite-balls">{bolas}</div>'
            '<div class="elite-game-meta">'
            '<span>15 dezenas</span>'
            f'<span>Score {float(row.get("Score", 0)):.2f}</span>'
            f'<span>Potencial 15 {float(row.get("Potencial 15", row.get("Score", 0))):.2f}%</span>'
            f'<span>Soma {int(row.get("Soma", sum(dezenas)))}</span>'
            f'<span>Pares/Ímpares {int(row.get("Pares", 0))}/{int(row.get("Ímpares", row.get("Impares", 0)))}</span>'
            f'<span>Estratégia: {row.get("Estrategia", "")}</span>'
            '</div></article>'
        )
    return (
        '<section class="elite-results">'
        f'<div class="elite-games-grid">{"".join(cards)}</div>'
        '</section>'
    )


def montar_html_motor(df: pd.DataFrame, meta: dict) -> str:
    ultimo_concurso = int(df["Concurso"].max()) if not df.empty else "-"
    return (
        '<section class="engine-panel">'
        f'<div class="engine-item"><div class="engine-label">Motor</div><div class="engine-value">{MOTOR_OFICIAL_PRODUCAO}</div></div>'
        f'<div class="engine-item"><div class="engine-label">Base histórica</div><div class="engine-value">dados/{CAMINHO_BASE_PADRAO.name}</div></div>'
        f'<div class="engine-item"><div class="engine-label">Último concurso carregado</div><div class="engine-value">{ultimo_concurso}</div></div>'
        f'<div class="engine-item"><div class="engine-label">Próximo concurso estimado</div><div class="engine-value">{meta["concurso_alvo"]}</div></div>'
        '</section>'
    )


def montar_html_resumo(jogos: pd.DataFrame) -> str:
    soma_media = jogos["Soma"].astype(float).mean()
    pares = int(jogos["Pares"].astype(int).sum())
    impares = int(jogos["Impares"].astype(int).sum())
    repetidas = int(jogos["Repeticao anterior"].astype(int).sum())
    score_medio = jogos["Elite Score Temporal"].astype(float).mean()
    itens = [
        (f"{soma_media:.1f}", "Soma média dos jogos"),
        (f"{pares}/{impares}", "Distribuição pares/ímpares"),
        (str(repetidas), "Repetições do último concurso"),
        (f"{score_medio:.2f}", "Score médio da carteira"),
        (str(len(jogos)), "Jogos gerados"),
    ]
    cards = "".join(
        f'<div class="summary-card"><div class="summary-value">{valor}</div><div class="summary-label">{rotulo}</div></div>'
        for valor, rotulo in itens
    )
    return f'<div class="summary-title">Resumo estatístico da carteira</div><section class="summary-grid">{cards}</section>'


def render_conferencia(df: pd.DataFrame) -> None:
    st.markdown(
        '<section class="saved-shell"><div class="saved-title">Conferir Jogos Salvos</div>'
        '<div class="saved-sub">Compare as previsões salvas com os resultados já disponíveis na base histórica.</div></section>',
        unsafe_allow_html=True,
    )
    conferir = st.button("CONFERIR JOGOS SALVOS", key="conferir_jogos_salvos", width="stretch")
    if conferir:
        salvos = conferir_jogos_salvos(df)
    else:
        salvos = ler_jogos_salvos()

    salvos = normalizar_colunas_jogos_salvos(salvos)
    if salvos.empty:
        st.info("Nenhum jogo salvo para conferência.")
        return

    if conferir:
        if salvos["Status"].eq("CONFERIDO").any():
            st.success("Conferência atualizada com base histórica disponível.")
        else:
            st.info("Jogos salvos aguardando resultado oficial.")

    status = salvos["Status"].fillna("").astype(str)
    acertos = pd.to_numeric(salvos["Acertos"], errors="coerce")
    acertos_conferidos = acertos[status.eq("CONFERIDO")].dropna()
    st.markdown("### Resumo das previsões salvas")
    col_total, col_pendentes, col_conferidos, col_melhor, col_media = st.columns(5)
    col_total.metric("Total de jogos salvos", len(salvos))
    col_pendentes.metric("Jogos pendentes", int(status.eq("PENDENTE").sum()))
    col_conferidos.metric("Jogos conferidos", int(status.eq("CONFERIDO").sum()))
    col_melhor.metric("Melhor acerto histórico", int(acertos_conferidos.max()) if not acertos_conferidos.empty else 0)
    col_media.metric("Média de acertos", f"{acertos_conferidos.mean():.2f}" if not acertos_conferidos.empty else "0.00")

    st.markdown("### Dashboard de Busca dos 15 Acertos")
    if acertos_conferidos.empty:
        st.info("Aguardando resultados oficiais para medir a busca estatística pelos 15 acertos.")
    else:
        conferidos = salvos.loc[status.eq("CONFERIDO")].copy()
        conferidos["Acertos Num"] = pd.to_numeric(conferidos["Acertos"], errors="coerce").fillna(0)
        metricas = [
            ("Melhor acerto histórico", str(int(conferidos["Acertos Num"].max()))),
            ("Média geral de acertos", f'{conferidos["Acertos Num"].mean():.2f}'),
            ("Total de jogos conferidos", str(len(conferidos))),
            ("Taxa 11+", f'{conferidos["Acertos Num"].ge(11).mean() * 100:.1f}%'),
            ("Taxa 12+", f'{conferidos["Acertos Num"].ge(12).mean() * 100:.1f}%'),
            ("Taxa 13+", f'{conferidos["Acertos Num"].ge(13).mean() * 100:.1f}%'),
            ("Taxa 14+", f'{conferidos["Acertos Num"].ge(14).mean() * 100:.1f}%'),
            ("Taxa 15", f'{conferidos["Acertos Num"].eq(15).mean() * 100:.1f}%'),
        ]
        colunas_metricas = st.columns(4)
        for indice, (rotulo, valor) in enumerate(metricas):
            colunas_metricas[indice % 4].metric(rotulo, valor)

        ranking = conferidos.groupby("Perfil", as_index=False).agg(
            **{
                "Jogos conferidos": ("Acertos Num", "size"),
                "Média de acertos": ("Acertos Num", "mean"),
                "Melhor acerto": ("Acertos Num", "max"),
            }
        )
        for limite in (11, 12, 13, 14):
            taxas = conferidos.assign(atingiu=conferidos["Acertos Num"].ge(limite)).groupby("Perfil")["atingiu"].mean() * 100
            ranking[f"Taxa {limite}+"] = ranking["Perfil"].map(taxas).fillna(0)
        taxa_15 = conferidos.assign(atingiu=conferidos["Acertos Num"].eq(15)).groupby("Perfil")["atingiu"].mean() * 100
        ranking["Taxa 15"] = ranking["Perfil"].map(taxa_15).fillna(0)
        ranking["Média de acertos"] = ranking["Média de acertos"].round(2)
        ranking = ranking.sort_values(["Média de acertos", "Melhor acerto"], ascending=False)
        melhor_perfil = str(ranking.iloc[0]["Perfil"])
        col_perfil, col_proximo = st.columns(2)
        col_perfil.metric("Perfil com melhor performance", melhor_perfil)
        col_proximo.metric("Perfil mais próximo dos 15", melhor_perfil)
        st.markdown("#### Ranking dos Perfis")
        st.dataframe(ranking, hide_index=True, width="stretch")

    def classificar_desempenho(valor: object) -> str:
        numero = pd.to_numeric(valor, errors="coerce")
        pontos = 0 if pd.isna(numero) else int(numero)
        if pontos == 15:
            return "Acerto máximo"
        if pontos >= 14:
            return "Quase máximo"
        if pontos >= 13:
            return "Desempenho excelente"
        if pontos >= 12:
            return "Desempenho forte"
        if pontos >= 11:
            return "Bom desempenho"
        return "Aguardando" if pontos == 0 else "Em evolução"

    exibicao = salvos.reindex(
        columns=["Concurso Alvo", "Perfil", "Dezenas", "Score", "Status", "Acertos"],
        fill_value="",
    ).tail(25)
    exibicao["Desempenho"] = exibicao["Acertos"].map(classificar_desempenho)
    st.dataframe(exibicao, hide_index=True, width="stretch")
    st.download_button(
        "BAIXAR JOGOS SALVOS CSV",
        CAMINHO_JOGOS_SALVOS.read_bytes(),
        CAMINHO_JOGOS_SALVOS.name,
        "text/csv",
        width="stretch",
    )


def render_resultado(df: pd.DataFrame, meta: dict) -> None:
    st.markdown(
        '<div class="free-analysis-intro"><strong>Previsão estatística para o próximo sorteio.</strong><br>'
        'Números sugeridos pelo Motor Elite a partir da base histórica da Lotofácil.<br>'
        'Busca estatística pelos 15 acertos. Motor preparado para buscar o melhor resultado possível.<br>'
        'Cada carteira é construída para buscar estatisticamente os 15 acertos no próximo concurso.<br>'
        'Os cinco perfis usam estratégias diferentes para ampliar a cobertura inteligente, sempre com foco no melhor resultado possível.</div>',
        unsafe_allow_html=True,
    )
    coluna_gerar, coluna_salvar = st.columns([1.35, 0.9])
    with coluna_gerar:
        atualizar = st.button("GERAR / ATUALIZAR OS 5 JOGOS", key="atualizar_jogos_elite", type="primary", width="stretch")
    with coluna_salvar:
        salvar = st.button("SALVAR JOGOS PARA CONFERÊNCIA", key="salvar_jogos_elite", width="stretch")
    st.markdown(
        '<div class="prediction-note">Previsão estatística para o próximo concurso da Lotofácil.</div>',
        unsafe_allow_html=True,
    )

    try:
        if "elite_generation_counter" not in st.session_state:
            st.session_state.elite_generation_counter = 0
        if atualizar or not isinstance(st.session_state.get("elite_generated_games"), pd.DataFrame):
            st.session_state.elite_generation_counter += 1
            semente = time.time_ns() ^ (st.session_state.elite_generation_counter * 1_000_003)
            jogos_gerados = gerar_jogos_producao_v1(
                df,
                semente=semente,
                assinatura_anterior=st.session_state.get("last_elite_portfolio_signature"),
            )
            jogos_gerados = normalizar_jogos_gerados(jogos_gerados)
            st.session_state.elite_generated_games = jogos_gerados
            st.session_state.last_elite_portfolio_signature = assinatura_portfolio(jogos_gerados)
        st.session_state.jogos_elite_principais = st.session_state.elite_generated_games
        jogos = normalizar_jogos_gerados(st.session_state.jogos_elite_principais)
        validar_jogos_producao(jogos)
    except Exception as erro:
        st.error(f"Nao foi possivel gerar os 5 jogos inteligentes: {erro}")
        return

    for nome in NOMES_JOGOS_PRODUCAO:
        linhas = jogos[jogos["Perfil"] == nome]
        if linhas.empty:
            st.warning(f"O jogo {nome} nao foi gerado pelo motor oficial.")
            return

    if salvar:
        try:
            jogos = normalizar_jogos_gerados(jogos)
            salvar_carteira(
                jogos,
                numero_carteira=st.session_state.elite_generation_counter,
                concurso_alvo=int(meta["concurso_alvo"]),
            )
            st.success(f"Carteira Elite nº {st.session_state.elite_generation_counter} salva para conferência futura.")
        except Exception as erro:
            st.error(f"Não foi possível salvar a carteira: {erro}")

    st.markdown(
        f'<div class="wallet-badge"><span>CARTEIRA ELITE Nº {st.session_state.elite_generation_counter}</span></div>',
        unsafe_allow_html=True,
    )
    st.markdown(montar_html_motor(df, meta), unsafe_allow_html=True)
    st.markdown(montar_html_resumo(jogos), unsafe_allow_html=True)
    jogos = normalizar_jogos_gerados(jogos)
    st.markdown(montar_html_jogos(jogos), unsafe_allow_html=True)

    nome_arquivo = f"lotofacil_previsao_{meta['concurso_alvo']}.csv"
    jogos_csv = normalizar_jogos_gerados(jogos)
    st.download_button(
        "DOWNLOAD CSV",
        jogos_csv.to_csv(index=False).encode("utf-8-sig"),
        nome_arquivo,
        "text/csv",
        width="stretch",
    )
    st.info("Análise estatística sem garantia de prêmio. Não há garantia de prêmio. A Lotofácil é aleatória, e o sistema trabalha com análise estatística da base histórica.")
    render_conferencia(df)


def main() -> None:
    aplicar_css()
    render_header()
    df = carregar_base()
    meta = metadados_publicos(df)
    render_card_publico(df, meta)

    render_resultado(df, meta)

if __name__ == "__main__":
    main()
