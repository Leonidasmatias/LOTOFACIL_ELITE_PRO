"""Captura walk-forward do pool COMPLETO autentico (tickets + raw score +
score final) e dos controles G0/G1, por concurso (LF-09D, Fase 5/6).

Reusa a mesma infraestrutura leakage-safe do LF-09A/LF-09C
(``engine_adapter._history_para_dataframe``, ``contracts.LeakageError``,
``CandidateTracer`` do LF-08). Controles G0/G1 usam RNG PROPRIO,
independente do motor (``random_pool_controls.py``) -- nunca consomem
nem alteram o ``random.Random`` interno de ``gerar_jogos_v2``.

UMA unica execucao real de ``gerar_jogos_v2`` por concurso. O resultado
real e aberto SOMENTE depois que o trace autentico E os pools G0/G1 ja
estao completamente congelados.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .candidate_trace import CandidateTracer
from .contracts import ContestSnapshot, LeakageError
from .engine_adapter import _history_para_dataframe
from .random_pool_controls import generate_g0_pool, generate_g1_pool
from ..motor_elite_v2 import PERFIS_V2, gerar_jogos_v2
from ..validacao_jogos import ConfiguracaoMotor

Ticket = tuple[int, ...]
PROFILE_POSITION: dict[str, int] = {nome: indice for indice, nome in enumerate(PERFIS_V2)}


def motor_seed_policy(base_seed: int, target_contest: int) -> int:
    return base_seed + target_contest


@dataclass(frozen=True, slots=True)
class PoolCandidate:
    """Um candidato autentico, com AMBOS os scores (raw e final) e seus
    hits reais -- calculado somente apos o freeze completo."""

    profile: str
    ticket: Ticket
    raw_structure_score: float
    final_candidate_score: float
    hits: int


@dataclass(frozen=True, slots=True)
class ProfileSelectionInfo:
    profile: str
    selected_ticket: Ticket
    selected_final_score: float
    attempts: int
    unique_candidates_stored: int


@dataclass(frozen=True, slots=True)
class LF09DTargetCapture:
    contest: int
    history_max_contest: int
    motor_seed: int
    pool: tuple[PoolCandidate, ...]
    original_selection: tuple[ProfileSelectionInfo, ...]
    g0_pool: tuple[Ticket, ...]
    g0_pool_hits: tuple[int, ...]
    g1_pool: tuple[Ticket, ...]
    g1_pool_hits: tuple[int, ...]


def run_lf09d_target(
    all_contests: Sequence[ContestSnapshot],
    target_contest: int,
    motor_base_seed: int,
    g0_base_seed: int,
    g1_base_seed: int,
    g_pool_size: int,
    configuracao: ConfiguracaoMotor | None = None,
) -> LF09DTargetCapture:
    """Executa UMA geracao real (trace habilitado) para
    ``target_contest``, gera os controles G0/G1 (RNG proprio,
    independente), e SO ENTAO abre o resultado real para pontuar tudo."""
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
    ultimo_concurso_historico = max(history, key=lambda c: c.number)
    ultimo = frozenset(ultimo_concurso_historico.numbers)
    config = configuracao or ConfiguracaoMotor()

    tracer = CandidateTracer()
    gerar_jogos_v2(df_historico, quantidade=5, configuracao=config, semente=motor_seed, trace=tracer)

    g0_pool = generate_g0_pool(g_pool_size, seed=g0_base_seed + target_contest)
    g1_pool = generate_g1_pool(g_pool_size, seed=g1_base_seed + target_contest, ultimo=ultimo, configuracao=config)

    # Trace + G0 + G1 completamente congelados -- SOMENTE AGORA o
    # resultado real e aberto.
    resultado_real = set(por_numero[target_contest].numbers)

    pool = tuple(
        PoolCandidate(
            profile=evento.profile,
            ticket=evento.ticket,
            raw_structure_score=evento.raw_structure_score,
            final_candidate_score=evento.final_candidate_score,
            hits=len(set(evento.ticket) & resultado_real),
        )
        for evento in tracer.evaluations
    )
    original_selection = tuple(
        ProfileSelectionInfo(
            profile=resumo.profile,
            selected_ticket=resumo.selected_ticket,
            selected_final_score=resumo.selected_final_score,
            attempts=resumo.attempts,
            unique_candidates_stored=resumo.unique_candidates_stored,
        )
        for resumo in tracer.profile_summaries
    )
    g0_hits = tuple(len(set(t) & resultado_real) for t in g0_pool)
    g1_hits = tuple(len(set(t) & resultado_real) for t in g1_pool)

    return LF09DTargetCapture(
        contest=target_contest,
        history_max_contest=max(c.number for c in history),
        motor_seed=motor_seed,
        pool=pool,
        original_selection=original_selection,
        g0_pool=g0_pool,
        g0_pool_hits=g0_hits,
        g1_pool=g1_pool,
        g1_pool_hits=g1_hits,
    )
