"""Benchmark justo MOTOR_ELITE_V2 vs baseline aleatorio (LF-05).

Reutiliza o harness LF-04 (``predict_for_contest``/``score_batch``) sem
modifica-lo. Constroi, para cada concurso-alvo elegivel, EXATAMENTE uma
avaliacao do motor (seed fixa e determinística por concurso, ver
``motor_seed_policy``) e N avaliacoes do baseline aleatorio (uma por seed,
ver ``random_seeds``), todas com o MESMO numero de tickets
(``tickets_per_contest``) e o MESMO historico (concursos < alvo).

Nenhuma funcao aqui recebe ou usa qualquer metrica de desempenho para
decidir QUAIS concursos avaliar (ver ``eligible_targets``) -- a lista de
concursos-alvo e definida antes e independentemente de qualquer resultado.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .contracts import ContestSnapshot
from .engine_adapter import EngineAdapter, ReferenceRandomEngine
from .harness import predict_for_contest
from .metrics import score_batch


def eligible_targets(all_contests: Sequence[ContestSnapshot], min_history: int) -> list[int]:
    """Todos os numeros de concurso elegiveis como alvo: aqueles que tem
    pelo menos ``min_history`` concursos anteriores disponiveis em
    ``all_contests``. Depende SOMENTE do numero de concursos disponiveis
    -- nunca de resultado, performance, max_hits ou score de nenhum motor
    (Fase 15 -- "no cherry-pick": a assinatura desta funcao nem aceita
    esse tipo de informacao)."""
    numeros_ordenados = sorted(c.number for c in all_contests)
    return numeros_ordenados[min_history:]


def motor_seed_policy(base_seed: int, target_contest: int) -> int:
    """Politica de seed do motor, FIXA e definida antes do benchmark
    (Fase 6): determinística, simples, simetrica entre concursos. Nunca
    testamos varias seeds do motor e escolhemos a melhor -- cada concurso
    tem exatamente UMA seed, dada por esta formula."""
    return base_seed + target_contest


def random_seeds(base_seed: int, count: int) -> list[int]:
    """Lista deterministica de seeds do baseline aleatorio (Fase 5):
    seed_i = base_seed + i, para i em 0..count-1. Definida antes de
    observar qualquer resultado."""
    return [base_seed + i for i in range(count)]


@dataclass(frozen=True, slots=True)
class BenchmarkContestResult:
    """Uma linha de comparacao pareada: um concurso-alvo, o resultado do
    motor (seed fixa por concurso) e o resultado do baseline aleatorio
    para UMA das seeds do baseline. Existem ``len(random_seeds)`` linhas
    por concurso-alvo, todas com o MESMO ``motor_*`` (o motor so roda uma
    vez por concurso) e ``random_*`` diferente por seed.

    Nao armazena nenhum resultado futuro antes do freeze -- os campos
    aqui sao todos DERIVADOS de ``BacktestResult`` (LF-04), que por sua
    vez so existe depois do freeze+score."""

    target_contest: int
    history_max_contest: int

    motor_seed: int | None
    motor_tickets: int
    motor_max_hits: int
    motor_mean_hits: float
    motor_distribution: dict[int, int]

    random_seed: int
    random_tickets: int
    random_max_hits: int
    random_mean_hits: float
    random_distribution: dict[int, int]


def run_fair_benchmark(
    motor_engine: EngineAdapter,
    all_contests: Sequence[ContestSnapshot],
    target_contests: Sequence[int],
    tickets_per_contest: int,
    motor_base_seed: int,
    random_base_seed: int,
    random_seed_count: int,
    baseline_engine_factory=ReferenceRandomEngine,
) -> list[BenchmarkContestResult]:
    """Executa o benchmark pareado para cada concurso em ``target_contests``.

    Para cada concurso-alvo: o motor roda EXATAMENTE uma vez (seed fixa via
    ``motor_seed_policy``); o baseline roda uma vez POR seed em
    ``random_seeds(random_base_seed, random_seed_count)``. Ambos recebem
    ``tickets_per_contest`` (o mesmo K) e o mesmo historico (concursos com
    numero < alvo, via ``predict_for_contest``, que ja levanta
    ``LeakageError`` se o historico contiver o alvo ou algo posterior --
    nenhuma checagem adicional de vazamento e necessaria aqui).
    """
    por_numero = {c.number: c for c in all_contests}
    seeds = random_seeds(random_base_seed, random_seed_count)
    resultados: list[BenchmarkContestResult] = []

    for target in target_contests:
        if target not in por_numero:
            raise ValueError(f"Concurso-alvo {target} nao esta em all_contests.")
        history = [c for c in all_contests if c.number < target]
        alvo_real = por_numero[target]

        motor_seed = motor_seed_policy(motor_base_seed, target)
        motor_batch = predict_for_contest(motor_engine, history, target, tickets_per_contest, motor_seed)
        motor_result = score_batch(motor_batch, alvo_real)

        for seed in seeds:
            random_batch = predict_for_contest(
                baseline_engine_factory(), history, target, tickets_per_contest, seed
            )
            random_result = score_batch(random_batch, alvo_real)
            resultados.append(
                BenchmarkContestResult(
                    target_contest=target,
                    history_max_contest=motor_batch.history_max_contest,
                    motor_seed=motor_seed,
                    motor_tickets=motor_result.batch.number_of_tickets,
                    motor_max_hits=motor_result.max_hits,
                    motor_mean_hits=motor_result.mean_hits,
                    motor_distribution=dict(motor_result.hit_distribution),
                    random_seed=seed,
                    random_tickets=random_result.batch.number_of_tickets,
                    random_max_hits=random_result.max_hits,
                    random_mean_hits=random_result.mean_hits,
                    random_distribution=dict(random_result.hit_distribution),
                )
            )
    return resultados
