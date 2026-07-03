from __future__ import annotations

from datetime import date, datetime
import re
import time

import pandas as pd
import plotly.express as px
import streamlit as st

from src.carregar_dados import (
    CAMINHO_BASE_PADRAO,
    COLUNAS_DEZENAS,
    buscar_info_concurso,
    buscar_info_concurso_atual,
    carregar_base,
    atualizar_base_local,
    resumo_base,
)
from src.backtest_lotofacil import executar_backtest_comparativo
from src.analises_v5 import JANELAS_V5, paineis_tendencias_v5, ranking_janelas_v5
from src.historico_sqlite import (
    CAMINHO_BANCO_V5,
    conferir_historico_sqlite,
    inicializar_banco,
    listar_historico_sqlite,
    migrar_historico_csv,
    registrar_concurso_visto,
    salvar_carteira_sqlite,
)
from src.jogos_salvos import (
    CAMINHO_JOGOS_SALVOS,
    conferir_jogos_salvos,
    historico_desempenho_carteiras,
    ler_jogos_salvos,
    normalizar_colunas_jogos_salvos,
    salvar_carteira,
)
from src.motor_elite_lotofacil import (
    NOMES_JOGOS_PRODUCAO,
    assinatura_portfolio,
)
from src.motor_elite_v2 import MOTOR_ELITE_V2, gerar_jogos_v2, ranking_dezenas_v2
from src.estrategia_inteligente import gerar_estrategia_do_dia
from src.laboratorio_estatistico import (
    calcular_roi_simulado,
    dados_heatmap,
    executar_laboratorio,
    ler_historico_laboratorio,
    salvar_historico_laboratorio,
)
from src.validacao_jogos import ConfiguracaoMotor, validar_carteira


st.set_page_config(page_title="Lotofácil Elite Pro V5", page_icon="LF", layout="wide")

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


@st.cache_data(ttl=300)
def info_caixa_cached() -> dict:
    info = buscar_info_concurso_atual()
    return info if isinstance(info, dict) else {}


@st.cache_data(ttl=300, show_spinner=False)
def sincronizar_base_automatica_cached(ultimo_local: int, concurso_oficial: int) -> bool:
    print(f"[UPDATE] CSV={ultimo_local}", flush=True)
    print(f"[UPDATE] API={concurso_oficial or 'indisponível'}", flush=True)
    if concurso_oficial <= ultimo_local:
        resultado = "Base já atualizada" if concurso_oficial else "API indisponível; CSV local preservado"
        print(f"[UPDATE] {resultado}", flush=True)
        return False
    atualizou = atualizar_base_local()
    if not atualizou:
        print("[UPDATE] Atualização não concluída; consulte o erro acima", flush=True)
    return atualizou


@st.cache_data(ttl=300, show_spinner=False)
def info_resultado_cached(concurso: int) -> dict:
    info = buscar_info_concurso(concurso)
    return info if isinstance(info, dict) else {}


def forcar_refresh_info_caixa() -> dict:
    info_caixa_cached.clear()
    info = buscar_info_concurso_atual()
    return info if isinstance(info, dict) else {}


def formatar_moeda(valor: object) -> str:
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        texto = str(valor or "").strip()
        return texto if texto else "Consultar CAIXA"
    return f"R$ {numero:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def metadados_publicos(
    df: pd.DataFrame,
    info: dict | None = None,
    info_resultado: dict | None = None,
    hoje: date | None = None,
) -> dict:
    info = info if isinstance(info, dict) else info_caixa_cached()
    resumo = resumo_base(df)
    ultimo_local = resumo["ultimo_concurso"]
    info_resultado = info_resultado if isinstance(info_resultado, dict) else info
    try:
        concurso_oficial = int(info.get("concurso_atual"))
    except (TypeError, ValueError):
        concurso_oficial = 0
    try:
        concurso_rateio = int(info_resultado.get("concurso_atual"))
    except (TypeError, ValueError):
        concurso_rateio = 0
    base_sincronizada = bool(ultimo_local and concurso_oficial == ultimo_local)
    resultado_sincronizado = bool(ultimo_local and concurso_rateio == ultimo_local)
    referencia_proximo = info_resultado if resultado_sincronizado else (info if base_sincronizada else {})

    hoje = hoje or date.today()

    def data_oficial(referencia: dict) -> date | None:
        valor = str(referencia.get("data_proximo_concurso") or "").strip()
        try:
            return datetime.strptime(valor, "%d/%m/%Y").date()
        except ValueError:
            return None

    data_referencia = data_oficial(referencia_proximo)
    data_vencida = bool(data_referencia and data_referencia < hoje)
    if data_vencida:
        data_api_atual = data_oficial(info)
        if data_api_atual and data_api_atual >= hoje:
            referencia_proximo = info
            data_referencia = data_api_atual
        else:
            data_referencia = None
    concurso = referencia_proximo.get("proximo_concurso") or ultimo_local + 1
    data = referencia_proximo.get("data_proximo_concurso") if data_referencia else None
    premio = formatar_moeda(referencia_proximo.get("premio_estimado"))
    return {
        "concurso_alvo": concurso,
        "data_sorteio": data or "Data aguardando atualização oficial da CAIXA",
        "premio_estimado": premio,
        "premiacao_resultado": info_resultado.get("premiacao_resultado", {}) if resultado_sincronizado else {},
        "base_sincronizada": base_sincronizada,
        "resultado_sincronizado": resultado_sincronizado,
        "acumulou": info_resultado.get("acumulou") if resultado_sincronizado else None,
        "fonte": info_resultado.get("fonte", "fallback_local") if resultado_sincronizado else "base_local_validada",
        "data_proximo_vencida": data_vencida,
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
        dados["Repeticao anterior"] = int(
            _numero(dados.get("Repeticao anterior", dados.get("Repetidas")), 0)
        )
        dados["Motor"] = str(dados.get("Motor") or MOTOR_ELITE_V2)
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
            --lt-navy:#04111F;
            --lt-cyan:#22D3EE;
            --lt-gold:#D6B86A;
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
            background:linear-gradient(135deg,#04111F 0%,#0A2945 62%,#075E75 100%);
            color:white; border-radius:20px; padding:34px 36px; margin-bottom:18px;
            box-shadow:0 18px 42px rgba(0,102,179,.24);
        }
        .hero:before, .hero:after {
            content:"•  ─  •  ╱  •  5G  •  AI"; position:absolute; color:rgba(34,211,238,.22);
            font-size:46px; font-weight:900; letter-spacing:18px; transform:rotate(-12deg);
        }
        .hero:before { right:22px; top:18px; }
        .hero:after { left:28px; bottom:-8px; font-size:34px; opacity:.5; }
        .hero h1 { margin:0; font-size:46px; line-height:1.05; font-weight:950; position:relative; }
        .hero-sub { margin-top:10px; font-size:18px; font-weight:750; opacity:.98; position:relative; }
        .lt-signature { position:relative; display:flex; align-items:center; gap:10px; margin-bottom:16px; color:#A5F3FC; font-size:11px; font-weight:900; letter-spacing:.16em; text-transform:uppercase; }
        .lt-signature:before { content:"LT"; display:grid; place-items:center; width:34px; height:34px; border:1px solid var(--lt-cyan); border-radius:9px; color:var(--lt-cyan); transform:rotate(45deg); }
        .lt-signature span { color:var(--lt-gold); font-size:9px; letter-spacing:.12em; }
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
        .proximo-sorteio { margin-top:20px; padding-top:18px; border-top:1px solid rgba(103,232,249,.22); }
        .proximo-sorteio-titulo { color:#67E8F9; font-size:16px; font-weight:950; text-transform:uppercase; letter-spacing:.04em; }
        .proximo-sorteio-concurso { color:#fff; font-size:24px; font-weight:950; margin:5px 0 2px; }
        .public-prize-label { color:rgba(255,255,255,.55); font-size:15px; font-weight:850; margin-top:14px; }
        .public-prize { color:#FFD700; font-size:38px; font-weight:950; margin:2px 0 8px; }
        .public-meta { color:rgba(255,255,255,.72); font-size:16px; font-weight:850; line-height:1.55; }
        .caixa-link {
            display:inline-flex; align-items:center; justify-content:center; margin-top:16px; padding:11px 16px;
            border:1px solid rgba(103,232,249,.5); border-radius:12px; background:rgba(34,211,238,.1);
            color:#A5F3FC !important; font-size:14px; font-weight:900; text-decoration:none !important;
            transition:background .2s ease,border-color .2s ease,transform .2s ease;
        }
        .caixa-link:hover { background:rgba(34,211,238,.18); border-color:#67E8F9; transform:translateY(-1px); }
        .caixa-aviso { margin-top:12px; color:rgba(255,255,255,.56); font-size:12px; font-weight:700; line-height:1.5; }
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
            display:grid; grid-template-columns:minmax(96px,.8fr) minmax(150px,1.2fr); gap:18px;
            align-items:center; padding:12px 0; border-bottom:1px solid rgba(255,255,255,.1);
        }
        .premio-row:last-child { border-bottom:0; }
        .premio-faixa { color:rgba(255,255,255,.78); font-size:15px; font-weight:900; }
        .premio-detalhes { display:flex; flex-direction:column; align-items:flex-end; gap:3px; text-align:right; }
        .premio-ganhadores { color:#A5F3FC; font-size:13px; font-weight:800; }
        .premio-valor { color:#fff; font-size:17px; font-weight:950; white-space:nowrap; }
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
        .lt-footer { margin-top:34px; padding:24px; text-align:center; border-top:1px solid rgba(34,211,238,.18); background:linear-gradient(180deg,rgba(4,17,31,0),rgba(4,17,31,.75)); color:#A5F3FC; }
        .lt-footer strong { display:block; color:#fff; font-size:15px; letter-spacing:.18em; }
        .lt-footer span { display:block; margin-top:6px; color:#D6B86A; font-size:10px; font-weight:800; letter-spacing:.15em; text-transform:uppercase; }
        .lt-footer small { display:block; margin-top:12px; color:rgba(255,255,255,.48); }
        @media (max-width:760px) {
            .hero { padding:24px 22px; }
            .hero h1 { font-size:32px; }
            .oficial-shell { grid-template-columns:1fr; }
            .public-concurso { font-size:25px; }
            .proximo-sorteio-concurso { font-size:21px; }
            .caixa-link { display:flex; width:100%; box-sizing:border-box; }
            .premiacao-card { padding:20px; }
            .premio-row { grid-template-columns:minmax(84px,.75fr) minmax(138px,1.25fr); gap:10px; }
            .premio-valor { font-size:15px; }
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
            <div class="lt-signature">LEONIDAS TECH <span>Conectando o Futuro</span></div>
            <h1>Lotofácil Elite Pro V5</h1>
            <div class="hero-sub">V5 Inteligência de Dezenas • Versão gratuita • Laboratório Estatístico • Análise sem garantia de prêmio</div>
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
    rateio = meta.get("premiacao_resultado") or {}
    linhas_premiacao = []
    for acertos in (15, 14, 13, 12, 11):
        faixa = rateio.get(acertos, {})
        valor = formatar_moeda(faixa.get("valor")) if faixa else "Aguardando"
        ganhadores = faixa.get("ganhadores") if faixa else None
        if ganhadores is None:
            texto_ganhadores = "Rateio não publicado"
        else:
            quantidade = f"{int(ganhadores):,}".replace(",", ".")
            texto_ganhadores = f"{quantidade} {'ganhador' if int(ganhadores) == 1 else 'ganhadores'}"
        linhas_premiacao.append(
            '<div class="premio-row">'
            f'<span class="premio-faixa">{acertos} acertos</span>'
            '<span class="premio-detalhes">'
            f'<span class="premio-ganhadores">{texto_ganhadores}</span>'
            f'<strong class="premio-valor">{valor}</strong>'
            '</span></div>'
        )
    texto_premiacao = (
        f"Premiação oficial do concurso {ultimo_concurso}."
        if rateio
        else "Dados de premiação aguardando atualização oficial."
    )
    st.markdown(
        f"""
        <div class="oficial-shell">
            <div class="public-card">
                <div class="public-title">Resultado oficial</div>
                <div class="public-concurso">Concurso {ultimo_concurso}</div>
                <div class="public-meta">Data do resultado: {data_ultimo}</div>
                {grid}
                <div class="proximo-sorteio">
                    <div class="proximo-sorteio-titulo">Próximo sorteio</div>
                    <div class="proximo-sorteio-concurso">Concurso {meta['concurso_alvo']}</div>
                    <div class="public-meta">Data prevista: {meta['data_sorteio']}</div>
                    <div class="public-prize-label">Prêmio estimado</div>
                    <div class="public-prize">{premio}</div>
                    <a class="caixa-link" href="https://loterias.caixa.gov.br/Paginas/Lotofacil.aspx" target="_blank" rel="noopener noreferrer">Conferir no site oficial da CAIXA</a>
                    <div class="caixa-aviso">Análise estatística sem garantia de prêmio. Confira sempre os dados no site oficial da CAIXA.</div>
                </div>
            </div>
            <div class="premiacao-card">
                <h3>Premiação</h3>
                {''.join(linhas_premiacao)}
                <div style="margin-top:16px;color:#64748B;font-size:14px;font-weight:750;line-height:1.45;">
                    {texto_premiacao}
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def montar_html_jogos(jogos: pd.DataFrame) -> str:
    jogos = normalizar_jogos_gerados(jogos)
    cards = []
    ocorrencias: dict[str, int] = {}
    total = len(jogos)
    for posicao, (_, row) in enumerate(jogos.iterrows(), start=1):
        nome = str(row["Perfil"])
        ocorrencias[nome] = ocorrencias.get(nome, 0) + 1
        titulo = TITULOS_JOGOS.get(nome, nome)
        if ocorrencias[nome] > 1:
            titulo = f"{titulo} · variação {ocorrencias[nome]}"
        dezenas = [int(row[f"Bola{i}"]) for i in range(1, 16)]
        bolas = "".join(f'<span class="elite-ball">{dezena:02d}</span>' for dezena in dezenas)
        cards.append(
            '<article class="elite-game-card">'
            f'<div class="elite-game-top"><div class="elite-game-name">{titulo}</div><div class="elite-game-position">JOGO {posicao}/{total}</div></div>'
            f'<div class="elite-game-description">{DESCRICOES_JOGOS.get(nome, "Estratégia estatística diversificada.")}</div>'
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
        f'<div class="engine-item"><div class="engine-label">Motor</div><div class="engine-value">V3_INTELIGENTE sobre {MOTOR_ELITE_V2} · evolução do ELITE_SCORE_V35_TEMPORAL</div></div>'
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
        conferir_historico_sqlite(df)
    else:
        salvos = ler_jogos_salvos()

    salvos = normalizar_colunas_jogos_salvos(salvos)
    st.markdown("### Histórico V5 em SQLite")
    historico_sqlite = listar_historico_sqlite()
    st.caption(f"Banco persistente: {CAMINHO_BANCO_V5}")
    if historico_sqlite.empty:
        st.info("O SQLite será preenchido automaticamente na próxima geração de carteira.")
    else:
        exibicao_sqlite = historico_sqlite.rename(columns={"Concurso Alvo": "Concurso SQLite"})
        st.dataframe(exibicao_sqlite.tail(100), hide_index=True, width="stretch")
        st.download_button(
            "EXPORTAR HISTÓRICO SQLITE CSV",
            historico_sqlite.to_csv(index=False).encode("utf-8-sig"),
            "historico_jogos_v5_sqlite.csv",
            "text/csv",
            width="stretch",
        )
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
    st.markdown('<div class="summary-title">Histórico de desempenho das carteiras</div>', unsafe_allow_html=True)
    historico = historico_desempenho_carteiras()
    if historico.empty:
        st.info("O histórico agregado será exibido após salvar a primeira carteira.")
    else:
        st.dataframe(historico, hide_index=True, width="stretch")
        st.download_button(
            "EXPORTAR HISTÓRICO CSV",
            historico.to_csv(index=False).encode("utf-8-sig"),
            "historico_carteiras_lotofacil_v3.csv",
            "text/csv",
            width="stretch",
        )


def render_resultado(df: pd.DataFrame, meta: dict, configuracao: ConfiguracaoMotor | None = None) -> None:
    st.markdown(
        '<div class="free-analysis-intro"><strong>Previsão estatística para o próximo sorteio.</strong><br>'
        'Números sugeridos pelo Motor Elite a partir da base histórica da Lotofácil.<br>'
        'Busca estatística pelos 15 acertos. Motor preparado para buscar o melhor resultado possível.<br>'
        'Cada carteira é construída para buscar estatisticamente os 15 acertos no próximo concurso.<br>'
        'Os cinco perfis usam estratégias diferentes para ampliar a cobertura inteligente, sempre com foco no melhor resultado possível.</div>',
        unsafe_allow_html=True,
    )
    quantidade = st.selectbox("Quantidade de jogos da carteira", [5, 10, 20, 30], key="quantidade_carteira")
    custo_unitario = float(st.session_state.get("cfg_custo_unitario", 3.50))
    st.caption(f"Custo estimado da carteira: R$ {quantidade * custo_unitario:,.2f} · valor unitário configurável")
    coluna_gerar, coluna_salvar = st.columns([1.35, 0.9])
    with coluna_gerar:
        atualizar = st.button("GERAR / ATUALIZAR CARTEIRA", key="atualizar_jogos_elite", type="primary", width="stretch")
    with coluna_salvar:
        salvar = st.button("SALVAR JOGOS PARA CONFERÊNCIA", key="salvar_jogos_elite", width="stretch")
    st.markdown(
        '<div class="prediction-note">Previsão estatística para o próximo concurso da Lotofácil.</div>',
        unsafe_allow_html=True,
    )

    try:
        if "elite_generation_counter" not in st.session_state:
            st.session_state.elite_generation_counter = 0
        nova_geracao = False
        if (
            atualizar
            or not isinstance(st.session_state.get("elite_generated_games"), pd.DataFrame)
            or int(st.session_state.get("elite_generated_quantity", 0)) != quantidade
        ):
            st.session_state.elite_generation_counter += 1
            semente = time.time_ns() ^ (st.session_state.elite_generation_counter * 1_000_003)
            jogos_gerados = gerar_jogos_v2(df, quantidade=quantidade, configuracao=configuracao, semente=semente)
            jogos_gerados = normalizar_jogos_gerados(jogos_gerados)
            st.session_state.elite_generated_games = jogos_gerados
            st.session_state.elite_generated_quantity = quantidade
            st.session_state.last_elite_portfolio_signature = assinatura_portfolio(jogos_gerados)
            nova_geracao = True
        st.session_state.jogos_elite_principais = st.session_state.elite_generated_games
        jogos = normalizar_jogos_gerados(st.session_state.jogos_elite_principais)
        validar_carteira(
            ([int(row[f"Bola{i}"]) for i in range(1, 16)] for _, row in jogos.iterrows()),
            configuracao,
        )
        if nova_geracao:
            salvar_carteira_sqlite(
                jogos,
                numero_carteira=st.session_state.elite_generation_counter,
                concurso_alvo=int(meta["concurso_alvo"]),
            )
    except Exception as erro:
        st.error(f"Não foi possível gerar a carteira inteligente: {erro}")
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


def configuracao_atual() -> ConfiguracaoMotor:
    return ConfiguracaoMotor(
        soma_minima=int(st.session_state.get("cfg_soma_min", 165)),
        soma_maxima=int(st.session_state.get("cfg_soma_max", 225)),
        pares_minimo=int(st.session_state.get("cfg_pares_min", 6)),
        pares_maximo=int(st.session_state.get("cfg_pares_max", 9)),
        repetidas_minimo=int(st.session_state.get("cfg_repetidas_min", 7)),
        repetidas_maximo=int(st.session_state.get("cfg_repetidas_max", 12)),
        sequencia_maxima=int(st.session_state.get("cfg_sequencia", 7)),
        diferenca_minima_entre_jogos=int(st.session_state.get("cfg_diversidade", 3)),
        candidatos_por_perfil=int(st.session_state.get("cfg_candidatos", 700)),
    )


def render_backtest(df: pd.DataFrame) -> None:
    st.subheader("Backtest histórico sem vazamento temporal")
    st.caption("Cada concurso é simulado usando somente os resultados anteriores a ele.")
    quantidade = st.slider("Concursos para simular", 10, min(150, max(10, len(df) - 100)), 20, 10)
    quantidade_jogos = st.selectbox("Jogos por carteira no backtest", [5, 10, 20, 30], key="backtest_quantidade_jogos")
    if st.button("EXECUTAR BACKTEST", type="primary", width="stretch"):
        with st.spinner("Simulando concursos históricos..."):
            st.session_state.backtest_v3 = executar_backtest_comparativo(
                df,
                quantidade_concursos=quantidade,
                quantidade_jogos=quantidade_jogos,
                configuracao=configuracao_atual(),
                candidatos_por_perfil=min(220, configuracao_atual().candidatos_por_perfil),
            )
    resultado = st.session_state.get("backtest_v3")
    if resultado is None:
        st.info("Execute o backtest para medir 11+, 12+, 13+, 14+ e 15 acertos por perfil.")
        return
    melhor_perfil = str(resultado.resumo_perfis.iloc[0]["Perfil"]) if not resultado.resumo_perfis.empty else "Sem resultado"
    st.success(f"Melhor perfil na amostra: {melhor_perfil}")
    st.markdown("#### Motor Elite × carteiras aleatórias")
    st.dataframe(resultado.resumo, hide_index=True, width="stretch")
    st.caption("Vantagem positiva favorece o Motor Elite; valor negativo indica desvantagem. Valores em pontos percentuais sobre a carteira aleatória equivalente.")
    if resultado.melhor_carteira:
        st.info(
            f"Melhor carteira simulada: {resultado.melhor_carteira['Motor']} · "
            f"concurso {resultado.melhor_carteira['Concurso']} · "
            f"{resultado.melhor_carteira['Melhor acerto']} acertos."
        )
    st.markdown("#### Desempenho por perfil")
    st.dataframe(resultado.resumo_perfis, hide_index=True, width="stretch")
    st.dataframe(resultado.detalhes.tail(250), hide_index=True, width="stretch")
    st.download_button(
        "EXPORTAR RELATÓRIO DE BACKTEST CSV",
        resultado.csv_bytes(),
        "backtest_lotofacil_v2_funcional.csv",
        "text/csv",
        width="stretch",
    )


def render_ranking(df: pd.DataFrame) -> None:
    st.subheader("Ranking das Dezenas")
    st.caption("V5 · Frequências comparáveis nos últimos 20, 50, 100 e 200 concursos.")
    ranking_v5 = ranking_janelas_v5(df)
    janela = st.selectbox("Janela do Ranking V5", list(JANELAS_V5), index=1, key="ranking_v5_janela")
    tabela_janela = ranking_v5.sort_values([f"Posição {janela}", "Dezena"])[
        ["Dezena", f"Posição {janela}", f"Frequência {janela}", f"Taxa {janela} (%)", "Atraso", "Saiu no último"]
    ].reset_index(drop=True)
    st.bar_chart(tabela_janela.head(15).set_index("Dezena")[f"Frequência {janela}"])
    st.dataframe(tabela_janela, hide_index=True, width="stretch")

    st.markdown("### Painéis de Tendência V5")
    paineis = paineis_tendencias_v5(df)
    col_quentes, col_frias = st.columns(2)
    with col_quentes:
        st.markdown("#### 🔥 Quentes")
        st.caption("Maior índice combinado nos últimos 20 e 50 concursos.")
        st.dataframe(paineis["Quentes"], hide_index=True, width="stretch")
    with col_frias:
        st.markdown("#### ❄️ Frias")
        st.caption("Menor índice combinado nos últimos 20 e 50 concursos.")
        st.dataframe(paineis["Frias"], hide_index=True, width="stretch")
    col_atrasadas, col_repetidas = st.columns(2)
    with col_atrasadas:
        st.markdown("#### ⏳ Atrasadas")
        st.caption("Mais concursos transcorridos desde a última ocorrência.")
        st.dataframe(paineis["Atrasadas"], hide_index=True, width="stretch")
    with col_repetidas:
        st.markdown("#### 🔁 Repetidas")
        st.caption("Dezenas presentes nos dois concursos mais recentes.")
        st.dataframe(paineis["Repetidas"], hide_index=True, width="stretch")

    st.download_button(
        "EXPORTAR RANKING V5 CSV",
        ranking_v5.to_csv(index=False).encode("utf-8-sig"),
        "ranking_dezenas_lotofacil_v5.csv",
        "text/csv",
        width="stretch",
    )

    st.markdown("### Ranking por Perfil do Motor")
    perfil = st.selectbox("Perfil estatístico", NOMES_JOGOS_PRODUCAO)
    ranking = ranking_dezenas_v2(df, perfil)
    st.bar_chart(ranking.head(15).set_index("Dezena")["Score da dezena"])
    st.dataframe(ranking, hide_index=True, width="stretch")
    st.download_button(
        "EXPORTAR RANKING CSV",
        ranking.to_csv(index=False).encode("utf-8-sig"),
        "ranking_dezenas_lotofacil_v2.csv",
        "text/csv",
        width="stretch",
    )


def render_configuracoes() -> None:
    st.subheader("Configurações do Motor Elite V2")
    coluna_a, coluna_b = st.columns(2)
    with coluna_a:
        st.number_input("Soma mínima", 100, 250, 165, key="cfg_soma_min")
        st.number_input("Pares mínimo", 0, 15, 6, key="cfg_pares_min")
        st.number_input("Repetidas do último — mínimo", 0, 15, 7, key="cfg_repetidas_min")
        st.number_input("Diferença mínima entre jogos", 1, 10, 3, key="cfg_diversidade")
    with coluna_b:
        st.number_input("Soma máxima", 100, 300, 225, key="cfg_soma_max")
        st.number_input("Pares máximo", 0, 15, 9, key="cfg_pares_max")
        st.number_input("Repetidas do último — máximo", 0, 15, 12, key="cfg_repetidas_max")
        st.number_input("Sequência máxima", 2, 15, 7, key="cfg_sequencia")
    st.slider("Candidatos analisados por perfil", 100, 2000, 700, 100, key="cfg_candidatos")
    st.number_input("Custo estimado por jogo (R$)", 0.0, 100.0, 3.50, 0.50, key="cfg_custo_unitario")
    try:
        configuracao_atual().validar()
        st.success("Configuração válida.")
    except ValueError as erro:
        st.error(str(erro))
    if st.button("ATUALIZAR BASE OFICIAL", width="stretch"):
        with st.spinner("Consultando dados oficiais..."):
            if atualizar_base_local():
                st.cache_data.clear()
                st.success("Base histórica atualizada com sucesso.")
            else:
                st.warning("Não foi possível atualizar agora. A base local foi preservada.")
    st.info("Jogue com responsabilidade. A busca estatística pelos 15 acertos não garante prêmio.")


@st.cache_data(show_spinner=False)
def estrategia_do_dia_cached(df: pd.DataFrame, config: ConfiguracaoMotor):
    return gerar_estrategia_do_dia(df, configuracao=config)


def render_estrategia_inteligente(df: pd.DataFrame) -> None:
    st.subheader("Estratégia Inteligente")
    st.caption("Decisão operacional baseada no histórico e em backtest temporal sem resultado futuro.")
    with st.spinner("Calculando a melhor estratégia do dia..."):
        estrategia = estrategia_do_dia_cached(df, configuracao_atual())
    colunas = st.columns(3)
    colunas[0].metric("Melhor perfil do dia", estrategia.perfil_recomendado)
    colunas[1].metric("Nível de risco", estrategia.nivel_risco)
    colunas[2].metric("Jogos recomendados", estrategia.quantidade_jogos)
    st.info(estrategia.justificativa)
    st.dataframe(estrategia.ranking_perfis, hide_index=True, width="stretch")
    forte, alerta = st.columns(2)
    forte.markdown("**Dezenas mais fortes**")
    forte.write(" · ".join(f"{dezena:02d}" for dezena in estrategia.dezenas_fortes))
    alerta.markdown("**Dezenas em alerta**")
    alerta.write(" · ".join(f"{dezena:02d}" for dezena in estrategia.dezenas_alerta))
    st.text_area("Melhor Estratégia do Dia", estrategia.texto(), height=310)
    csv, txt = st.columns(2)
    csv.download_button("EXPORTAR ESTRATÉGIA CSV", estrategia.csv_bytes(), "melhor_estrategia_do_dia.csv", "text/csv", width="stretch")
    txt.download_button("EXPORTAR ESTRATÉGIA TXT", estrategia.texto().encode("utf-8"), "melhor_estrategia_do_dia.txt", "text/plain", width="stretch")


def render_laboratorio_estatistico(df: pd.DataFrame) -> None:
    st.subheader("Laboratório Estatístico")
    st.caption("Todas as estratégias usam o mesmo passado, a mesma quantidade de jogos e o mesmo concurso-alvo.")

    heatmap = dados_heatmap(df)
    metrica_heatmap = st.selectbox(
        "Métrica do heatmap 5×5",
        ["Frequência histórica", "Frequência recente", "Atraso", "Score V3"],
        key="lab_metrica_heatmap",
    )
    grade = heatmap.pivot(index="Linha", columns="Coluna", values=metrica_heatmap)
    figura = px.imshow(
        grade,
        text_auto=".1f",
        color_continuous_scale="Viridis",
        aspect="equal",
        labels={"color": metrica_heatmap},
        title=f"Heatmap das 25 dezenas · {metrica_heatmap}",
    )
    figura.update_xaxes(title="Coluna", dtick=1)
    figura.update_yaxes(title="Linha", dtick=1, autorange="reversed")
    st.plotly_chart(figura, width="stretch")

    controles = st.columns(4)
    concursos = controles[0].selectbox("Concursos no laboratório", [5, 10, 20, 30, 50], index=1, key="lab_concursos")
    quantidade_jogos = controles[1].selectbox("Jogos por estratégia", [5, 10, 20, 30], key="lab_quantidade_jogos")
    valor_unitario = controles[2].number_input("Valor estimado por jogo (R$)", 0.01, 100.0, float(st.session_state.get("cfg_custo_unitario", 3.50)), 0.50, key="lab_valor_unitario")
    amostra_minima = controles[3].number_input("Amostra mínima por padrão", 1, 10_000, 10, 1, key="lab_amostra_minima")

    with st.expander("Premiações estimadas para simulação de ROI"):
        premios = {
            11: st.number_input("Retorno estimado — 11 acertos", 0.0, 10_000_000.0, 7.0, 1.0, key="lab_premio_11"),
            12: st.number_input("Retorno estimado — 12 acertos", 0.0, 10_000_000.0, 14.0, 1.0, key="lab_premio_12"),
            13: st.number_input("Retorno estimado — 13 acertos", 0.0, 10_000_000.0, 35.0, 5.0, key="lab_premio_13"),
            14: st.number_input("Retorno estimado — 14 acertos", 0.0, 10_000_000.0, 1500.0, 100.0, key="lab_premio_14"),
            15: st.number_input("Retorno estimado — 15 acertos", 0.0, 100_000_000.0, 1_500_000.0, 10_000.0, key="lab_premio_15"),
        }
    st.warning("ROI e retornos usam valores estimados e não garantidos. Confirme valores oficiais antes de qualquer decisão.")

    if st.button("EXECUTAR LABORATÓRIO ESTATÍSTICO", type="primary", width="stretch"):
        with st.spinner("Comparando estratégias sem usar resultados futuros..."):
            resultado = executar_laboratorio(
                df,
                quantidade_concursos=concursos,
                quantidade_jogos=quantidade_jogos,
                configuracao=configuracao_atual(),
                amostra_minima_padrao=int(amostra_minima),
            )
            roi = calcular_roi_simulado(resultado.detalhes_jogos, valor_unitario, premios)
            salvar_historico_laboratorio(resultado, roi, quantidade_jogos)
            st.session_state.laboratorio_v4 = resultado
            st.session_state.laboratorio_v4_roi = roi

    resultado = st.session_state.get("laboratorio_v4")
    roi = st.session_state.get("laboratorio_v4_roi")
    if resultado is None or roi is None:
        st.info("Execute o laboratório para comparar as cinco estratégias.")
    else:
        st.markdown("#### Comparação das estratégias")
        st.dataframe(resultado.resumo, hide_index=True, width="stretch")
        melhores = pd.DataFrame([{"Métrica": metrica, "Melhor estratégia": estrategia} for metrica, estrategia in resultado.melhores_metricas.items()])
        st.markdown("#### Melhor estratégia por métrica")
        st.dataframe(melhores, hide_index=True, width="stretch")
        st.markdown("#### ROI simulado")
        st.dataframe(roi, hide_index=True, width="stretch")
        st.markdown("#### Padrões com amostra mínima")
        if resultado.padroes.empty:
            st.info("Nenhum padrão atingiu a amostra mínima nesta execução.")
        else:
            st.dataframe(resultado.padroes.head(100), hide_index=True, width="stretch")
        downloads = st.columns(3)
        downloads[0].download_button("EXPORTAR LABORATÓRIO CSV", resultado.csv_bytes(), "laboratorio_estatistico_v4.csv", "text/csv", width="stretch")
        downloads[1].download_button("EXPORTAR ROI CSV", roi.to_csv(index=False).encode("utf-8-sig"), "roi_simulado_v4.csv", "text/csv", width="stretch")
        downloads[2].download_button("EXPORTAR PADRÕES CSV", resultado.padroes.to_csv(index=False).encode("utf-8-sig"), "padroes_estatisticos_v4.csv", "text/csv", width="stretch")

    historico = ler_historico_laboratorio()
    st.markdown("#### Banco histórico de estratégias")
    if historico.empty:
        st.info("O banco será preenchido após a primeira execução do laboratório.")
    else:
        st.dataframe(historico.tail(100), hide_index=True, width="stretch")
        st.download_button("EXPORTAR HISTÓRICO DO LABORATÓRIO", historico.to_csv(index=False).encode("utf-8-sig"), "historico_laboratorio_v4.csv", "text/csv", width="stretch")


def render_rodape_institucional() -> None:
    st.markdown(
        """
        <footer class="lt-footer">
            <strong>LEONIDAS TECH</strong>
            <span>Conectando o Futuro</span>
            <small>Lotofácil Elite Pro V5 · Laboratório estatístico responsável · leonidastech.com.br</small>
        </footer>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    aplicar_css()
    render_header()
    try:
        inicializar_banco()
        migrar_historico_csv()
    except Exception as erro:
        st.warning(f"Histórico SQLite temporariamente indisponível: {erro}")
    df = carregar_base()
    info = info_caixa_cached()
    ultimo_local = int(df.iloc[-1]["Concurso"]) if not df.empty else 0
    try:
        concurso_oficial = int(info.get("concurso_atual") or 0)
    except (TypeError, ValueError):
        concurso_oficial = 0
    base_desatualizada = concurso_oficial > ultimo_local
    atualizou_automaticamente = sincronizar_base_automatica_cached(ultimo_local, concurso_oficial)
    if atualizou_automaticamente:
        df = carregar_base()
    ultimo_validado = int(df.iloc[-1]["Concurso"]) if not df.empty else 0
    try:
        novo_persistido = registrar_concurso_visto(ultimo_validado)
    except Exception:
        novo_persistido = False
    if atualizou_automaticamente or novo_persistido:
        st.success(f"🆕 Novo concurso detectado: {ultimo_validado}. Base oficial atualizada automaticamente.")
    elif base_desatualizada:
        st.warning(
            f"Novo concurso {concurso_oficial} identificado, mas a atualização não foi concluída. "
            "A base local anterior foi preservada."
        )
    info_resultado = info_resultado_cached(ultimo_validado) if ultimo_validado else {}
    meta = metadados_publicos(df, info, info_resultado)
    if meta["data_proximo_vencida"]:
        info = forcar_refresh_info_caixa()
        meta = metadados_publicos(df, info, info_resultado)
    render_card_publico(df, meta)

    abas = st.tabs(["Gerar Jogos", "Estratégia Inteligente", "Laboratório Estatístico", "Backtest", "Conferir Jogos", "Ranking das Dezenas", "Configurações"])
    with abas[0]:
        render_resultado(df, meta, configuracao_atual())
    with abas[1]:
        render_estrategia_inteligente(df)
    with abas[2]:
        render_laboratorio_estatistico(df)
    with abas[3]:
        render_backtest(df)
    with abas[4]:
        render_conferencia(df)
    with abas[5]:
        render_ranking(df)
    with abas[6]:
        render_configuracoes()
    render_rodape_institucional()

if __name__ == "__main__":
    main()
