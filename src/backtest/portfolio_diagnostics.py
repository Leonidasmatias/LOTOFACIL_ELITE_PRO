"""Diagnostico de diversidade/cobertura de portfolio (LF-06, Fase 10).

Mede SOMENTE o que o motor de producao ja faz -- nenhuma nova otimizacao,
nenhum "Portfolio Optimizer". Opera sobre os tickets JA CONGELADOS de um
``PredictionBatch`` (LF-04), nunca sobre o resultado do concurso-alvo.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
import statistics
from typing import Sequence

TODAS_DEZENAS = tuple(range(1, 26))


@dataclass(frozen=True, slots=True)
class PortfolioDiversityMetrics:
    """Metricas estruturais de UM portfolio (conjunto de tickets de UM
    concurso-alvo). ``pairwise_distance`` e o tamanho da diferenca simetrica
    entre dois tickets (2 * (15 - intersecao)) -- quanto maior, mais
    diverso o par."""

    n_tickets: int
    mean_pairwise_intersection: float
    min_pairwise_intersection: int
    max_pairwise_intersection: int
    mean_pairwise_distance: float
    unique_numbers_covered: int
    number_frequency: dict[int, int]
    concentration_max_frequency: int


def compute_portfolio_diversity(tickets: Sequence[tuple[int, ...]]) -> PortfolioDiversityMetrics:
    if len(tickets) < 2:
        raise ValueError("Sao necessarios pelo menos 2 tickets para metricas de pares.")
    conjuntos = [set(t) for t in tickets]
    intersecoes = [len(a & b) for a, b in combinations(conjuntos, 2)]
    distancias = [2 * (15 - intersecao) for intersecao in intersecoes]
    uniao: set[int] = set()
    for conjunto in conjuntos:
        uniao |= conjunto
    frequencia = {d: sum(1 for conjunto in conjuntos if d in conjunto) for d in TODAS_DEZENAS}
    return PortfolioDiversityMetrics(
        n_tickets=len(tickets),
        mean_pairwise_intersection=statistics.fmean(intersecoes),
        min_pairwise_intersection=min(intersecoes),
        max_pairwise_intersection=max(intersecoes),
        mean_pairwise_distance=statistics.fmean(distancias),
        unique_numbers_covered=len(uniao),
        number_frequency=frequencia,
        concentration_max_frequency=max(frequencia.values()),
    )


MORE_DIVERSE = "MORE_DIVERSE"
SIMILAR = "SIMILAR"
MORE_CONCENTRATED = "MORE_CONCENTRATED"
INCONCLUSIVE = "INCONCLUSIVE"


def classify_diversity(delta_mean_distance: float, ci_low: float, ci_high: float) -> str:
    """Classificacao pre-registrada (mesma logica de ``classify_evidence``
    do LF-05): compara a distancia media par-a-par do motor contra a do
    random, pareada por concurso, via CI95 bootstrap. delta = motor - random.
    """
    if delta_mean_distance > 0 and ci_low > 0:
        return MORE_DIVERSE
    if delta_mean_distance < 0 and ci_high < 0:
        return MORE_CONCENTRATED
    return SIMILAR if abs(delta_mean_distance) < 1e-9 else INCONCLUSIVE


def pearson_association(x: Sequence[float], y: Sequence[float]) -> float:
    """Coeficiente de correlacao de Pearson entre duas series pareadas.
    Retorna 0.0 se qualquer serie tiver variancia nula (sem associacao
    linear definida). Uso: ASSOCIACAO apenas -- nunca causalidade."""
    if len(x) != len(y):
        raise ValueError("As duas series precisam ter o mesmo tamanho.")
    if len(x) < 2:
        raise ValueError("Sao necessarios pelo menos 2 pares para correlacao.")
    media_x, media_y = statistics.fmean(x), statistics.fmean(y)
    cov = sum((a - media_x) * (b - media_y) for a, b in zip(x, y))
    var_x = sum((a - media_x) ** 2 for a in x)
    var_y = sum((b - media_y) ** 2 for b in y)
    if var_x == 0 or var_y == 0:
        return 0.0
    return cov / ((var_x**0.5) * (var_y**0.5))
