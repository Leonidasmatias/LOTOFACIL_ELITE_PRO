"""Metricas do harness de backtest walk-forward (LF-04, Fase 8).

Nenhuma metrica aqui calcula "probabilidade de ganhar" a partir de score
heuristico -- apenas contagens factuais de acertos (hits) do jogo
congelado contra o resultado real, abertas somente na fase SCORE (depois
do freeze, ver ``harness.score_batch``).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .contracts import BacktestResult, ContestSnapshot, FrozenTicket, PredictionBatch, TicketScore

FAIXAS_PREMIACAO = (11, 12, 13, 14, 15)


def score_ticket(ticket: FrozenTicket, target_result: ContestSnapshot) -> TicketScore:
    hits = len(set(ticket.numbers) & set(target_result.numbers))
    return TicketScore(label=ticket.label, numbers=ticket.numbers, hits=hits)


def score_batch(batch: PredictionBatch, target_result: ContestSnapshot) -> BacktestResult:
    """Fase SCORE: compara um ``PredictionBatch`` JA CONGELADO contra o
    resultado real (que so deveria ter sido aberto agora, ver
    ``contracts.SealedContestResult``). Nao modifica ``batch`` -- ele e
    imutavel (``frozen=True`` com apenas tuplas)."""
    ticket_scores = tuple(score_ticket(ticket, target_result) for ticket in batch.tickets)
    hits_list = [ticket_score.hits for ticket_score in ticket_scores]
    distribuicao = {k: hits_list.count(k) for k in range(16)}
    return BacktestResult(
        batch=batch,
        target_result=target_result,
        ticket_scores=ticket_scores,
        max_hits=max(hits_list),
        mean_hits=sum(hits_list) / len(hits_list),
        hit_distribution=distribuicao,
    )


@dataclass(frozen=True, slots=True)
class AggregateMetrics:
    """Metricas agregadas sobre varios concursos avaliados."""

    contests_evaluated: int
    total_tickets: int
    max_hits: int
    mean_hits: float
    hit_distribution: dict[int, int]
    frequency_ge: dict[int, int]
    frequency_eq15: int


def aggregate(results: Sequence[BacktestResult]) -> AggregateMetrics:
    if not results:
        raise ValueError("Nenhum BacktestResult para agregar.")
    distribuicao_total: dict[int, int] = {k: 0 for k in range(16)}
    todos_hits: list[int] = []
    for resultado in results:
        for chave, quantidade in resultado.hit_distribution.items():
            distribuicao_total[chave] += quantidade
        todos_hits.extend(ticket_score.hits for ticket_score in resultado.ticket_scores)
    frequency_ge = {faixa: sum(1 for hit in todos_hits if hit >= faixa) for faixa in FAIXAS_PREMIACAO}
    return AggregateMetrics(
        contests_evaluated=len(results),
        total_tickets=len(todos_hits),
        max_hits=max(todos_hits),
        mean_hits=round(sum(todos_hits) / len(todos_hits), 6),
        hit_distribution=distribuicao_total,
        frequency_ge=frequency_ge,
        frequency_eq15=distribuicao_total[15],
    )
