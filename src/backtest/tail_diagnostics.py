"""Diagnostico de cauda alta (13/14/15) do resultado LF-05 (LF-06, Fase 9).

Puramente descritivo: identifica em QUAIS concursos o motor atingiu
determinado limiar de acertos e, opcionalmente, reconstroi o detalhe por
ticket para esses concursos especificos reutilizando o harness LF-04
(``predict_for_contest``/``score_batch``) sem modifica-lo. Nao cria regras
nem "padroes" a partir destes eventos -- apenas os lista.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .contracts import ContestSnapshot
from .diagnostics import TargetAggregate, freq_ge
from .engine_adapter import EngineAdapter
from .harness import predict_for_contest
from .metrics import BacktestResult, score_batch


@dataclass(frozen=True, slots=True)
class TailEventSummary:
    """Um evento de cauda alta: no concurso ``target_contest``, o motor
    produziu ``count_at_hits`` ticket(s) com exatamente ``hits`` acertos
    (``hits >= threshold``). ``random_seeds_ge_threshold`` e a fracao das
    seeds do baseline aleatorio que TAMBEM produziram >= ``threshold`` para
    o MESMO concurso -- descritivo, nao usado para nenhuma conclusao de
    "padrao"."""

    target_contest: int
    motor_seed: int | None
    hits: int
    count_at_hits: int
    random_seeds_ge_threshold_fraction: float
    random_seeds_ge_threshold_count: int
    random_seeds_total: int


def extract_tail_events(aggregates: Sequence[TargetAggregate], threshold: int) -> list[TailEventSummary]:
    """Lista, para cada concurso, cada valor de hits >= ``threshold`` que o
    motor efetivamente produziu (com contagem > 0). Concursos onde o motor
    nao atingiu o limiar nao geram evento -- zero eventos e evidencia
    valida, nao omissao."""
    eventos: list[TailEventSummary] = []
    for linha in aggregates:
        for hits_str, quantidade in linha.motor_distribution.items():
            hits = int(hits_str)
            if hits < threshold or quantidade <= 0:
                continue
            seeds_totais = len(linha.random_seed_distribution)
            seeds_ge = sum(
                1
                for distribuicao in linha.random_seed_distribution.values()
                if freq_ge(distribuicao, threshold) > 0
            )
            eventos.append(
                TailEventSummary(
                    target_contest=linha.target_contest,
                    motor_seed=linha.motor_seed,
                    hits=hits,
                    count_at_hits=quantidade,
                    random_seeds_ge_threshold_fraction=(seeds_ge / seeds_totais) if seeds_totais else 0.0,
                    random_seeds_ge_threshold_count=seeds_ge,
                    random_seeds_total=seeds_totais,
                )
            )
    return sorted(eventos, key=lambda evento: (evento.target_contest, -evento.hits))


def recompute_single_target(
    engine: EngineAdapter,
    all_contests: Sequence[ContestSnapshot],
    target_contest: int,
    tickets_per_contest: int,
    seed: int | None,
) -> BacktestResult:
    """Reconstroi o detalhe por-ticket (numeros, rotulo/perfil, hits) de UM
    concurso especifico, reutilizando EXATAMENTE o harness LF-04 (mesmo
    ``predict_for_contest``/``score_batch`` ja usado no benchmark LF-05).
    Determinístico: mesma ``seed`` + mesmo ``history`` -> mesmo resultado.
    Usado apenas para enriquecer eventos de cauda ja identificados -- nunca
    para escolher quais concursos investigar."""
    por_numero = {c.number: c for c in all_contests}
    if target_contest not in por_numero:
        raise ValueError(f"Concurso-alvo {target_contest} nao esta em all_contests.")
    history = [c for c in all_contests if c.number < target_contest]
    batch = predict_for_contest(engine, history, target_contest, tickets_per_contest, seed)
    return score_batch(batch, por_numero[target_contest])
