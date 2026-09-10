"""Testes das metricas de diversidade de portfolio (LF-06, Fase 10).

Casos com valores calculados a mao para provar corretude matematica exata
das metricas de pares (intersecao, distancia, cobertura, frequencia por
dezena), alem da classificacao de diversidade e da associacao (Pearson).
"""
from __future__ import annotations

import pytest

from src.backtest.portfolio_diagnostics import (
    INCONCLUSIVE,
    MORE_CONCENTRATED,
    MORE_DIVERSE,
    SIMILAR,
    classify_diversity,
    compute_portfolio_diversity,
    pearson_association,
)


def test_compute_portfolio_diversity_dois_tickets_identicos() -> None:
    ticket = tuple(range(1, 16))
    metrica = compute_portfolio_diversity([ticket, ticket])
    assert metrica.mean_pairwise_intersection == 15
    assert metrica.mean_pairwise_distance == 0
    assert metrica.unique_numbers_covered == 15
    assert metrica.concentration_max_frequency == 2


def test_compute_portfolio_diversity_dois_tickets_minimo_overlap_possivel() -> None:
    """Identidade combinatoria: a intersecao minima possivel entre dois
    subconjuntos de 15 elementos de um universo de 25 e |A|+|B|-25 = 5."""
    a = tuple(range(1, 16))  # 1..15
    b = tuple(range(11, 26))  # 11..25 -- intersecao = {11..15} = 5
    metrica = compute_portfolio_diversity([a, b])
    assert metrica.mean_pairwise_intersection == 5
    assert metrica.mean_pairwise_distance == 2 * (15 - 5)
    assert metrica.unique_numbers_covered == 25


def test_compute_portfolio_diversity_frequencia_por_dezena_exata() -> None:
    a = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15)
    b = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 16, 17, 18, 19, 20)
    metrica = compute_portfolio_diversity([a, b])
    assert metrica.number_frequency[1] == 2
    assert metrica.number_frequency[11] == 1
    assert metrica.number_frequency[16] == 1
    assert metrica.number_frequency[25] == 0
    assert metrica.concentration_max_frequency == 2


def test_compute_portfolio_diversity_tres_tickets_min_max_intersecao() -> None:
    a = tuple(range(1, 16))
    b = tuple(range(1, 16))
    c = tuple(range(11, 26))
    metrica = compute_portfolio_diversity([a, b, c])
    assert metrica.min_pairwise_intersection == 5
    assert metrica.max_pairwise_intersection == 15


def test_compute_portfolio_diversity_rejeita_menos_de_dois_tickets() -> None:
    with pytest.raises(ValueError):
        compute_portfolio_diversity([tuple(range(1, 16))])


# --- Classificacao (mesma logica de classify_evidence do LF-05) -------------


def test_classify_diversity_more_diverse() -> None:
    assert classify_diversity(delta_mean_distance=2.0, ci_low=0.5, ci_high=3.5) == MORE_DIVERSE


def test_classify_diversity_more_concentrated() -> None:
    assert classify_diversity(delta_mean_distance=-2.0, ci_low=-3.5, ci_high=-0.5) == MORE_CONCENTRATED


def test_classify_diversity_inconclusive_quando_ci_cruza_zero() -> None:
    assert classify_diversity(delta_mean_distance=0.5, ci_low=-1.0, ci_high=2.0) == INCONCLUSIVE


def test_classify_diversity_similar_quando_delta_e_zero() -> None:
    assert classify_diversity(delta_mean_distance=0.0, ci_low=-0.1, ci_high=0.1) == SIMILAR


# --- Associacao (Pearson) ----------------------------------------------------


def test_pearson_association_correlacao_perfeita_positiva() -> None:
    x = [1.0, 2.0, 3.0, 4.0, 5.0]
    y = [2.0, 4.0, 6.0, 8.0, 10.0]
    assert pearson_association(x, y) == pytest.approx(1.0)


def test_pearson_association_correlacao_perfeita_negativa() -> None:
    x = [1.0, 2.0, 3.0, 4.0, 5.0]
    y = [10.0, 8.0, 6.0, 4.0, 2.0]
    assert pearson_association(x, y) == pytest.approx(-1.0)


def test_pearson_association_sem_variancia_retorna_zero() -> None:
    x = [5.0, 5.0, 5.0]
    y = [1.0, 2.0, 3.0]
    assert pearson_association(x, y) == 0.0


def test_pearson_association_rejeita_tamanhos_diferentes() -> None:
    with pytest.raises(ValueError):
        pearson_association([1.0, 2.0], [1.0])
