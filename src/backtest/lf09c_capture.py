"""Captura walk-forward de (perfil, score, hits) por evento de avaliacao
autentico (LF-09C, Fase 3).

Reusa a mesma infraestrutura leakage-safe ja aprovada no LF-09A
(``engine_adapter._history_para_dataframe``, ``contracts.LeakageError``)
e o trace autentico do LF-08 (``CandidateTracer``). UMA unica execucao
real de ``gerar_jogos_v2`` por concurso alimenta a captura inteira --
nenhum candidato adicional e gerado, nenhum motor e re-executado por
perfil separadamente.

Disciplina de vazamento identica ao LF-09A/LF-04: o resultado real do
concurso-alvo so e consultado DEPOIS que o trace (todos os eventos de
avaliacao de todos os perfis) ja esta completo e congelado.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .candidate_trace import CandidateTracer
from .contracts import ContestSnapshot, LeakageError
from .engine_adapter import _history_para_dataframe
from ..motor_elite_v2 import PERFIS_V2, gerar_jogos_v2
from ..validacao_jogos import ConfiguracaoMotor

PROFILE_POSITION: dict[str, int] = {nome: indice for indice, nome in enumerate(PERFIS_V2)}


def motor_seed_policy(base_seed: int, target_contest: int) -> int:
    """Mesma forma funcional da politica ja usada no LF-05/LF-09A."""
    return base_seed + target_contest


@dataclass(frozen=True, slots=True)
class CandidateObservation:
    """Uma observacao FACTUAL: um candidato realmente avaliado por
    producao neste concurso, seu perfil, sua posicao na sequencia de
    perfis (0=Diamante..4=Conservador -- Diamante NUNCA sofre
    penalidade de similaridade, por ser sempre o primeiro), seu score
    final autentico, e seus hits contra o resultado REAL (calculado
    somente depois do freeze)."""

    contest: int
    profile: str
    profile_position: int
    score: float
    hits: int


def run_lf09c_target(
    all_contests: Sequence[ContestSnapshot],
    target_contest: int,
    motor_base_seed: int,
    configuracao: ConfiguracaoMotor | None = None,
) -> tuple[CandidateObservation, ...]:
    """Executa UMA geracao real (trace habilitado) para
    ``target_contest`` e devolve uma ``CandidateObservation`` POR
    EVENTO DE AVALIACAO do trace (inclui duplicatas dentro do mesmo
    perfil, exatamente como producao realmente as avaliou)."""
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

    # Trace completo e congelado -- SOMENTE AGORA o resultado real e aberto.
    resultado_real = set(por_numero[target_contest].numbers)

    return tuple(
        CandidateObservation(
            contest=target_contest,
            profile=evento.profile,
            profile_position=PROFILE_POSITION[evento.profile],
            score=evento.final_candidate_score,
            hits=len(set(evento.ticket) & resultado_real),
        )
        for evento in tracer.evaluations
    )
