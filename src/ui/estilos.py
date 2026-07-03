"""CSS da aplicacao. Extraido de ``app.py::aplicar_css`` (Fase 5 - Phoenix V1),
sem nenhuma alteracao visual.
"""
from __future__ import annotations

import streamlit as st


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
            content:"ðŸ€ ðŸ€ ðŸ€"; position:absolute; color:rgba(255,255,255,.22);
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
