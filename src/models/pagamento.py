"""Modelo de dominio: Pagamento (transacao PIX associada a uma previsao)."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Pagamento:
    payment_id: str | int | None
    status: str
    valor_total: float
    email_pagador: str
    concurso_alvo: int | str

    @property
    def aprovado(self) -> bool:
        return self.status == "approved"
