"""Logging centralizado da aplicacao (Fase 7 - Phoenix V1).

Substitui os ``except Exception: pass`` silenciosos por um registro minimo,
sem alterar nenhum valor de retorno nem o fluxo de controle existente: o
fallback continua exatamente o mesmo, apenas passa a ficar auditavel.
"""
from __future__ import annotations

import logging


def get_logger(nome: str) -> logging.Logger:
    logger = logging.getLogger(nome)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger
