"""Modelo de dominio: Concurso (um sorteio da Lotofacil)."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Concurso:
    numero: int
    data: str
    dezenas: tuple[int, ...]

    def __post_init__(self) -> None:
        if len(self.dezenas) != 15:
            raise ValueError("Um concurso da Lotofacil precisa ter exatamente 15 dezenas.")


@dataclass(frozen=True, slots=True)
class MetaConcurso:
    """Metadados publicos exibidos na tela (concurso alvo, premio, data)."""

    concurso_alvo: int
    data_sorteio: str
    premio_estimado: str
    acumulou: bool | None
    fonte: str
