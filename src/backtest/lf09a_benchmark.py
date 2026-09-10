"""Benchmark walk-forward: SELECTOR_ORIGINAL vs selectors LF-09A sobre o
MESMO pool autentico, por concurso (LF-09A, Fase 9).

Reusa o motor de producao (``gerar_jogos_v2``, com o parametro ``trace``
ja aprovado no LF-08/LF-08A) e o tradutor de historico ja existente em
``engine_adapter.py`` (``_history_para_dataframe`` -- mesma funcao
reaproveitada pelo ``MotorEliteV2Adapter`` do LF-04, sem duplicacao).
NAO cria um segundo motor, NAO gera um segundo pool: UMA unica execucao
real por concurso alimenta TODOS os selectors comparados.

Disciplina de vazamento identica ao harness LF-04: o historico entregue
ao motor e verificado ANTES da chamada (nenhum concurso >= alvo), e o
resultado real do concurso-alvo so e consultado DEPOIS que todas as
selecoes (original + LF-09A + random) ja estao congeladas.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .candidate_trace import CandidateTracer
from .contracts import ContestSnapshot, LeakageError
from .engine_adapter import _history_para_dataframe
from .portfolio_selector_lf09a import (
    RESEARCH_CONFIGS,
    LF09AConfig,
    build_candidate_pool_from_trace,
    original_selected_tickets,
    select_portfolio_lf09a,
    select_portfolio_random,
)
from .ticket_metrics import (
    portfolio_max_pairwise_overlap,
    portfolio_mean_pairwise_overlap,
    unique_number_coverage,
)
from ..motor_elite_v2 import gerar_jogos_v2
from ..validacao_jogos import ConfiguracaoMotor

Ticket = tuple[int, ...]


def motor_seed_policy(base_seed: int, target_contest: int) -> int:
    """Mesma forma funcional da politica original do LF-05
    (``base_seed + target_contest``) -- fixa, deterministica, definida
    antes de qualquer execucao."""
    return base_seed + target_contest


@dataclass(frozen=True, slots=True)
class PortfolioOutcome:
    """Resultado factual de UM portfolio de 5 tickets contra o
    resultado real de UM concurso -- calculado SOMENTE depois que a
    selecao (de qualquer selector) ja estava congelada."""

    selector_name: str
    tickets: tuple[Ticket, ...]
    hits: tuple[int, ...]
    mean_hits: float
    max_hits: int
    min_hits: int
    mean_pairwise_overlap: float
    max_pairwise_overlap: int
    unique_number_coverage: int
    prediction_scores: tuple[float, ...]
    mean_prediction_score: float
    min_prediction_score: float
    max_prediction_score: float


def _avaliar_portfolio(
    nome: str,
    tickets: Sequence[Ticket],
    resultado_real: set[int],
    score_por_ticket: dict[Ticket, float],
) -> PortfolioOutcome:
    hits = tuple(len(set(t) & resultado_real) for t in tickets)
    scores = tuple(score_por_ticket[t] for t in tickets)
    return PortfolioOutcome(
        selector_name=nome,
        tickets=tuple(tickets),
        hits=hits,
        mean_hits=sum(hits) / len(hits),
        max_hits=max(hits),
        min_hits=min(hits),
        mean_pairwise_overlap=portfolio_mean_pairwise_overlap(tickets),
        max_pairwise_overlap=portfolio_max_pairwise_overlap(tickets),
        unique_number_coverage=unique_number_coverage(tickets),
        prediction_scores=scores,
        mean_prediction_score=sum(scores) / len(scores),
        min_prediction_score=min(scores),
        max_prediction_score=max(scores),
    )


@dataclass(frozen=True, slots=True)
class LF09ATargetResult:
    target_contest: int
    history_max_contest: int
    motor_seed: int
    pool_size: int
    original: PortfolioOutcome
    por_config: dict[str, PortfolioOutcome]
    random_controls: tuple[PortfolioOutcome, ...]


def run_lf09a_target(
    all_contests: Sequence[ContestSnapshot],
    target_contest: int,
    motor_base_seed: int,
    random_control_seeds: Sequence[int],
    configuracao: ConfiguracaoMotor | None = None,
    configs: Sequence[LF09AConfig] = RESEARCH_CONFIGS,
) -> LF09ATargetResult:
    """Executa UMA unica geracao real (trace habilitado) para
    ``target_contest``, deriva o pool autentico, aplica TODOS os
    selectors ao MESMO pool, e SO ENTAO abre o resultado real desse
    concurso para pontuar."""
    por_numero = {c.number: c for c in all_contests}
    if target_contest not in por_numero:
        raise ValueError(f"Concurso-alvo {target_contest} nao esta em all_contests.")
    history = [c for c in all_contests if c.number < target_contest]
    invasores = [c.number for c in history if c.number >= target_contest]
    if invasores:
        raise LeakageError(f"Historico contem concurso(s) >= alvo {target_contest}: {sorted(invasores)[:5]}")
    if not history:
        raise ValueError("Historico vazio.")

    df_historico = _history_para_dataframe(history)
    motor_seed = motor_seed_policy(motor_base_seed, target_contest)

    tracer = CandidateTracer()
    gerar_jogos_v2(df_historico, quantidade=5, configuracao=configuracao, semente=motor_seed, trace=tracer)

    pool = build_candidate_pool_from_trace(tracer)
    tickets_originais = original_selected_tickets(tracer)
    # Score AUTORITATIVO por ticket, do pool global (usado pelos
    # selectors LF-09A/random, que escolhem DO pool). Para o ORIGINAL,
    # usamos abaixo o ``selected_final_score`` exato de cada resumo de
    # perfil -- a fonte de verdade de producao -- em vez do pool global,
    # que poderia (raramente) colidir se o MESMO ticket fisico aparecer
    # em mais de um perfil com scores diferentes.
    score_por_ticket = {c.ticket: c.final_candidate_score for c in pool}
    scores_originais = {
        resumo.selected_ticket: resumo.selected_final_score for resumo in tracer.profile_summaries
    }

    selecoes_lf09a = {config.name: select_portfolio_lf09a(pool, config) for config in configs}
    selecoes_random = {
        f"RANDOM_SEED_{seed}": select_portfolio_random(pool, seed=seed) for seed in random_control_seeds
    }

    # Freeze completo (original + LF-09A + random) -- SOMENTE AGORA o
    # resultado real e aberto.
    resultado_real = set(por_numero[target_contest].numbers)

    original_outcome = _avaliar_portfolio("ORIGINAL", tickets_originais, resultado_real, scores_originais)
    por_config = {
        nome: _avaliar_portfolio(nome, tickets, resultado_real, score_por_ticket)
        for nome, tickets in selecoes_lf09a.items()
    }
    random_outcomes = tuple(
        _avaliar_portfolio(nome, tickets, resultado_real, score_por_ticket) for nome, tickets in selecoes_random.items()
    )

    return LF09ATargetResult(
        target_contest=target_contest,
        history_max_contest=max(c.number for c in history),
        motor_seed=motor_seed,
        pool_size=len(pool),
        original=original_outcome,
        por_config=por_config,
        random_controls=random_outcomes,
    )
