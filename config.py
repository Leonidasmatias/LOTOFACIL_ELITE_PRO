"""Configuracao centralizada da aplicacao Lotofacil Elite Pro.

Fase 7 - Phoenix V1. Concentra constantes de versao/status e o acesso a
segredos (``st.secrets``), que antes estavam espalhados dentro de ``app.py``.
Comportamento identico ao original: mesmos valores padrao, mesmo fallback
silencioso em caso de ausencia de ``st.secrets`` (agora com log auditavel).
"""
from __future__ import annotations

import streamlit as st

from src.utils.logging_config import get_logger


VERSAO_APP = "LOTOFACIL_PRODUCAO_V1"
STATUS_APP = "PRODUCAO"
MODO_ADMIN_PADRAO = False

_logger = get_logger("lotofacil_elite.config")


def modo_admin_ativo() -> bool:
    try:
        return bool(st.secrets.get("MODO_ADMIN", MODO_ADMIN_PADRAO))
    except Exception as erro:
        _logger.info("st.secrets indisponivel para MODO_ADMIN, usando padrao (%s).", erro)
        return MODO_ADMIN_PADRAO


def obter_token_mercado_pago() -> str:
    try:
        return str(st.secrets.get("MERCADO_PAGO_ACCESS_TOKEN", "")).strip()
    except Exception as erro:
        _logger.info("st.secrets indisponivel para MERCADO_PAGO_ACCESS_TOKEN (%s).", erro)
        return ""
