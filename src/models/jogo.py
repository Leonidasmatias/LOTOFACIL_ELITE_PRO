"""Modelo de dominio: Jogo (uma aposta/previsao gerada pelo Motor Elite)."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Jogo:
    perfil: str
    motor: str
    dezenas: tuple[int, ...]
    elite_score: float

    def __post_init__(self) -> None:
        if len(self.dezenas) != 15:
            raise ValueError("Um jogo da Lotofacil precisa ter exatamente 15 dezenas.")
