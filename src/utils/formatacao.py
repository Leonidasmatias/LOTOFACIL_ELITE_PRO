"""Helpers de formatacao de texto/numero para exibicao.

``formatar_moeda`` foi extraido de ``app.py`` (Fase 3 - Phoenix V1), sem
alteracao de comportamento.
"""
from __future__ import annotations


def formatar_moeda(valor: object) -> str:
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        texto = str(valor or "").strip()
        return texto if texto else "Consultar CAIXA"
    return f"R$ {numero:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
