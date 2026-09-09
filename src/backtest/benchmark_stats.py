"""Analise estatistica do benchmark justo MOTOR_ELITE_V2 vs RANDOM (LF-05).

Nenhuma funcao aqui produz um "score composto" arbitrario -- todas operam
sobre metricas primarias factuais (mean hits, max hits, frequencia de
faixas de acerto) definidas em ``src/backtest/metrics.py`` e agregadas por
``src/backtest/benchmark.py::BenchmarkContestResult``.
"""
from __future__ import annotations

from dataclasses import dataclass
import random
import statistics
from typing import Sequence

from .benchmark import BenchmarkContestResult

FAIXAS_PREMIACAO = (11, 12, 13, 14, 15)


# --- Distribuicao do baseline random por seed (Fase 10) -------------------


def _somar_distribuicoes(distribuicoes: Sequence[dict[int, int]]) -> dict[int, int]:
    total = {k: 0 for k in range(16)}
    for distribuicao in distribuicoes:
        for hits, quantidade in distribuicao.items():
            total[hits] += quantidade
    return total


def _mean_hits_de_distribuicao(distribuicao: dict[int, int]) -> float:
    total_tickets = sum(distribuicao.values())
    total_hits = sum(hits * quantidade for hits, quantidade in distribuicao.items())
    return total_hits / total_tickets


def _freq_ge_de_distribuicao(distribuicao: dict[int, int], faixa: int) -> int:
    return sum(quantidade for hits, quantidade in distribuicao.items() if hits >= faixa)


@dataclass(frozen=True, slots=True)
class RandomSeedAggregate:
    """Metricas agregadas do baseline random para UMA seed, sobre TODOS os
    concursos-alvo avaliados com essa seed."""

    seed: int
    mean_hits: float
    max_hits: int
    distribution: dict[int, int]
    frequency_ge: dict[int, int]


def random_aggregates_por_seed(results: Sequence[BenchmarkContestResult]) -> list[RandomSeedAggregate]:
    """Uma linha por seed do baseline random, agregando sobre todos os
    concursos-alvo que usaram aquela seed."""
    por_seed: dict[int, list[BenchmarkContestResult]] = {}
    for resultado in results:
        por_seed.setdefault(resultado.random_seed, []).append(resultado)

    agregados = []
    for seed, linhas in por_seed.items():
        distribuicao = _somar_distribuicoes([linha.random_distribution for linha in linhas])
        agregados.append(
            RandomSeedAggregate(
                seed=seed,
                mean_hits=_mean_hits_de_distribuicao(distribuicao),
                max_hits=max(linha.random_max_hits for linha in linhas),
                distribution=distribuicao,
                frequency_ge={faixa: _freq_ge_de_distribuicao(distribuicao, faixa) for faixa in FAIXAS_PREMIACAO},
            )
        )
    return sorted(agregados, key=lambda item: item.seed)


@dataclass(frozen=True, slots=True)
class RandomDistributionSummary:
    """Estatisticas descritivas de uma metrica do baseline random,
    calculadas sobre a distribuicao das multiplas seeds (Fase 10):
    media, mediana, p5, p95, minimo, maximo."""

    mean: float
    median: float
    p5: float
    p95: float
    minimum: float
    maximum: float


def _percentile(valores_ordenados: Sequence[float], p: float) -> float:
    if not valores_ordenados:
        raise ValueError("Lista vazia nao tem percentil.")
    if len(valores_ordenados) == 1:
        return valores_ordenados[0]
    posicao = p * (len(valores_ordenados) - 1)
    indice_baixo = int(posicao)
    indice_alto = min(indice_baixo + 1, len(valores_ordenados) - 1)
    fracao = posicao - indice_baixo
    return valores_ordenados[indice_baixo] + (valores_ordenados[indice_alto] - valores_ordenados[indice_baixo]) * fracao


def summarize_random_distribution(valores: Sequence[float]) -> RandomDistributionSummary:
    if not valores:
        raise ValueError("Nenhum valor para sumarizar -- necessario ao menos 1 seed.")
    ordenados = sorted(valores)
    return RandomDistributionSummary(
        mean=statistics.fmean(ordenados),
        median=statistics.median(ordenados),
        p5=_percentile(ordenados, 0.05),
        p95=_percentile(ordenados, 0.95),
        minimum=ordenados[0],
        maximum=ordenados[-1],
    )


# --- Comparacao pareada por concurso (Fase 9) ------------------------------


@dataclass(frozen=True, slots=True)
class PairedDelta:
    target_contest: int
    random_seed: int
    delta_mean_hits: float
    delta_max_hits: int


def compute_paired_deltas(results: Sequence[BenchmarkContestResult]) -> list[PairedDelta]:
    return [
        PairedDelta(
            target_contest=resultado.target_contest,
            random_seed=resultado.random_seed,
            delta_mean_hits=resultado.motor_mean_hits - resultado.random_mean_hits,
            delta_max_hits=resultado.motor_max_hits - resultado.random_max_hits,
        )
        for resultado in results
    ]


@dataclass(frozen=True, slots=True)
class WinTieLoss:
    wins: int
    ties: int
    losses: int


def win_tie_loss(deltas: Sequence[float]) -> WinTieLoss:
    """win = motor > random (delta > 0); tie = delta == 0; loss = delta < 0."""
    return WinTieLoss(
        wins=sum(1 for delta in deltas if delta > 0),
        ties=sum(1 for delta in deltas if delta == 0),
        losses=sum(1 for delta in deltas if delta < 0),
    )


def paired_deltas_por_concurso_medio_nas_seeds(results: Sequence[BenchmarkContestResult]) -> dict[int, float]:
    """Para o bootstrap PAREADO POR CONCURSO (Fase 11): reduz as multiplas
    seeds do random a uma unica media por concurso, ANTES de calcular o
    delta contra o motor (que so tem 1 valor por concurso). Devolve
    {target_contest: delta_medio_mean_hits}."""
    por_concurso: dict[int, list[BenchmarkContestResult]] = {}
    for resultado in results:
        por_concurso.setdefault(resultado.target_contest, []).append(resultado)

    deltas: dict[int, float] = {}
    for target, linhas in por_concurso.items():
        motor_mean_hits = linhas[0].motor_mean_hits  # igual em todas as linhas do mesmo concurso
        random_mean_hits_medio = statistics.fmean(linha.random_mean_hits for linha in linhas)
        deltas[target] = motor_mean_hits - random_mean_hits_medio
    return deltas


# --- Bootstrap pareado por concurso (Fase 11) ------------------------------


@dataclass(frozen=True, slots=True)
class BootstrapCI:
    observed_mean_delta: float
    ci_low: float
    ci_high: float
    iterations: int
    seed: int


def bootstrap_ci_mean_delta(
    deltas_por_concurso: Sequence[float],
    seed: int,
    iterations: int = 2000,
) -> BootstrapCI:
    """Bootstrap pareado por concurso: reamostra COM REPOSICAO a lista de
    deltas (um valor por concurso) ``iterations`` vezes, calcula a media de
    cada reamostra, e devolve o intervalo de confianca 95% (percentil 2.5 e
    97.5 das medias de reamostra) junto com a media observada real (sem
    reamostragem). Seed fixa -- reprodutivel."""
    if not deltas_por_concurso:
        raise ValueError("Nenhum delta para bootstrap.")
    rng = random.Random(seed)
    n = len(deltas_por_concurso)
    observado = statistics.fmean(deltas_por_concurso)
    medias_bootstrap = []
    for _ in range(iterations):
        amostra = [deltas_por_concurso[rng.randrange(n)] for _ in range(n)]
        medias_bootstrap.append(statistics.fmean(amostra))
    medias_bootstrap.sort()
    ci_low = _percentile(medias_bootstrap, 0.025)
    ci_high = _percentile(medias_bootstrap, 0.975)
    return BootstrapCI(observed_mean_delta=observado, ci_low=ci_low, ci_high=ci_high, iterations=iterations, seed=seed)


# --- Classificacao (Fase 12) -----------------------------------------------

EVIDENCE_POSITIVE = "EVIDENCE_POSITIVE"
INCONCLUSIVE = "INCONCLUSIVE"
EVIDENCE_NEGATIVE = "EVIDENCE_NEGATIVE"


def classify_evidence(delta: float, ci_low: float, ci_high: float) -> str:
    """Classificacao puramente descritiva do benchmark (Fase 12) -- nunca
    uma promessa de resultado futuro.

    EVIDENCE_POSITIVE: delta > 0 e o CI95 inteiro > 0 (nao cruza zero).
    EVIDENCE_NEGATIVE: delta < 0 e o CI95 inteiro < 0.
    INCONCLUSIVE: caso contrario (CI95 cruza zero, ou delta == 0).
    """
    if delta > 0 and ci_low > 0:
        return EVIDENCE_POSITIVE
    if delta < 0 and ci_high < 0:
        return EVIDENCE_NEGATIVE
    return INCONCLUSIVE


# --- High-hit events (Fase 13) ---------------------------------------------

LIMIAR_LOW_SAMPLE = 20


@dataclass(frozen=True, slots=True)
class HighHitReport:
    motor_ge11: int
    motor_ge12: int
    motor_ge13: int
    motor_ge14: int
    motor_eq15: int
    sample_classification: str  # "ADEQUATE" ou "LOW_SAMPLE"


def high_hit_report(motor_distribution_total: dict[int, int]) -> HighHitReport:
    """Contagens factuais de eventos de alta faixa do MOTOR (agregado sobre
    todos os concursos avaliados -- motor roda 1x por concurso, entao nao
    ha "seeds" aqui). Classifica LOW_SAMPLE se o total de eventos >=13 for
    pequeno (< ``LIMIAR_LOW_SAMPLE``) -- nunca promove 1 ocorrencia isolada
    a conclusao estatistica."""
    ge13 = _freq_ge_de_distribuicao(motor_distribution_total, 13)
    return HighHitReport(
        motor_ge11=_freq_ge_de_distribuicao(motor_distribution_total, 11),
        motor_ge12=_freq_ge_de_distribuicao(motor_distribution_total, 12),
        motor_ge13=ge13,
        motor_ge14=_freq_ge_de_distribuicao(motor_distribution_total, 14),
        motor_eq15=motor_distribution_total.get(15, 0),
        sample_classification="ADEQUATE" if ge13 >= LIMIAR_LOW_SAMPLE else "LOW_SAMPLE",
    )
