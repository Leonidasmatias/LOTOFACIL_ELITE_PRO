"""Metricas puras e deterministicas sobre tickets/portfolios (LF-09A,
Fase 3).

Nenhuma funcao aqui gera, modifica ou recombina dezenas -- apenas mede
relacoes de conjunto entre tickets JA existentes (tuplas de 15 dezenas
validas 1..25). Completamente independente do MOTOR_ELITE_V2.
"""
from __future__ import annotations

from itertools import combinations
from typing import Sequence

Ticket = tuple[int, ...]


def intersection_size(a: Ticket, b: Ticket) -> int:
    """|A ∩ B| -- numero de dezenas em comum."""
    return len(set(a) & set(b))


def symmetric_difference_size(a: Ticket, b: Ticket) -> int:
    """|A △ B| -- quantidade de dezenas que diferem entre os dois tickets."""
    return len(set(a) ^ set(b))


def jaccard_similarity(a: Ticket, b: Ticket) -> float:
    """|A ∩ B| / |A ∪ B|. Para dois tickets de 15 dezenas, |A ∪ B| = 30 -
    |A ∩ B|, portanto o denominador nunca e zero (minimo 15, quando
    A == B)."""
    intersecao = intersection_size(a, b)
    uniao = len(set(a) | set(b))
    return intersecao / uniao


def overlap_ratio(a: Ticket, b: Ticket) -> float:
    """|A ∩ B| / 15 -- fracao das 15 dezenas de um ticket que tambem
    aparece no outro."""
    return intersection_size(a, b) / 15


def portfolio_mean_pairwise_overlap(tickets: Sequence[Ticket]) -> float:
    """Media de ``intersection_size`` sobre todos os C(n,2) pares do
    portfolio. Para n=5, sao C(5,2)=10 pares."""
    pares = list(combinations(tickets, 2))
    if not pares:
        raise ValueError("Sao necessarios pelo menos 2 tickets para overlap par-a-par.")
    return sum(intersection_size(a, b) for a, b in pares) / len(pares)


def portfolio_max_pairwise_overlap(tickets: Sequence[Ticket]) -> int:
    """Maior ``intersection_size`` observado entre qualquer par do
    portfolio."""
    pares = list(combinations(tickets, 2))
    if not pares:
        raise ValueError("Sao necessarios pelo menos 2 tickets para overlap par-a-par.")
    return max(intersection_size(a, b) for a, b in pares)


def unique_number_coverage(tickets: Sequence[Ticket]) -> int:
    """Quantidade de dezenas distintas cobertas pela uniao de todos os
    tickets do portfolio."""
    if not tickets:
        raise ValueError("Sao necessarios tickets para calcular cobertura.")
    uniao: set[int] = set()
    for ticket in tickets:
        uniao |= set(ticket)
    return len(uniao)
