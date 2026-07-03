"""Regras de negocio puras sobre pagamentos (validacao de e-mail, calculo de valor).

Extraido de ``src/pagamentos.py`` (Fase 2 - Phoenix V1). A escrita do log de
pagamentos (I/O) ficou em ``src/repository/pagamento_repository.py``.
"""
from __future__ import annotations

import re


VALOR_POR_ANALISE = 1.0
EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def email_cliente_valido(email: str) -> bool:
    return bool(EMAIL_REGEX.match(str(email).strip()))


def calcular_valor_pagamento(quantidade: int = 1) -> float:
    return round(max(1, int(quantidade)) * VALOR_POR_ANALISE, 2)
