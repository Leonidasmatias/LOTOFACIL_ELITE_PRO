"""Testes das metricas puras de ticket/portfolio (LF-09A, Fase 3/13)."""
from __future__ import annotations

import pytest

from src.backtest.ticket_metrics import (
    intersection_size,
    jaccard_similarity,
    overlap_ratio,
    portfolio_max_pairwise_overlap,
    portfolio_mean_pairwise_overlap,
    symmetric_difference_size,
    unique_number_coverage,
)


def test_intersection_size_identicos() -> None:
    t = tuple(range(1, 16))
    assert intersection_size(t, t) == 15


def test_intersection_size_minima_possivel() -> None:
    # Identidade combinatoria: |A|+|B|-25 = 15+15-25 = 5.
    a = tuple(range(1, 16))
    b = tuple(range(11, 26))
    assert intersection_size(a, b) == 5


def test_symmetric_difference_size_identicos_e_zero() -> None:
    t = tuple(range(1, 16))
    assert symmetric_difference_size(t, t) == 0


def test_symmetric_difference_size_minima_overlap() -> None:
    a = tuple(range(1, 16))
    b = tuple(range(11, 26))
    # intersecao=5 -> diferenca simetrica = 2*(15-5) = 20
    assert symmetric_difference_size(a, b) == 20


def test_jaccard_similarity_identicos_e_um() -> None:
    t = tuple(range(1, 16))
    assert jaccard_similarity(t, t) == pytest.approx(1.0)


def test_jaccard_similarity_minima_overlap() -> None:
    a = tuple(range(1, 16))
    b = tuple(range(11, 26))
    # intersecao=5, uniao=25 (universo inteiro) -> 5/25=0.2
    assert jaccard_similarity(a, b) == pytest.approx(0.2)


def test_overlap_ratio_identicos_e_um() -> None:
    t = tuple(range(1, 16))
    assert overlap_ratio(t, t) == pytest.approx(1.0)


def test_overlap_ratio_minima() -> None:
    a = tuple(range(1, 16))
    b = tuple(range(11, 26))
    assert overlap_ratio(a, b) == pytest.approx(5 / 15)


def test_portfolio_mean_pairwise_overlap_exato() -> None:
    a = tuple(range(1, 16))
    b = tuple(range(1, 16))
    c = tuple(range(11, 26))
    # pares: (a,b)=15, (a,c)=5, (b,c)=5 -> media = 25/3
    assert portfolio_mean_pairwise_overlap([a, b, c]) == pytest.approx(25 / 3)


def test_portfolio_max_pairwise_overlap_exato() -> None:
    a = tuple(range(1, 16))
    b = tuple(range(1, 16))
    c = tuple(range(11, 26))
    assert portfolio_max_pairwise_overlap([a, b, c]) == 15


def test_portfolio_overlap_rejeita_menos_de_dois() -> None:
    with pytest.raises(ValueError):
        portfolio_mean_pairwise_overlap([tuple(range(1, 16))])
    with pytest.raises(ValueError):
        portfolio_max_pairwise_overlap([tuple(range(1, 16))])


def test_unique_number_coverage_exato() -> None:
    a = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15)
    b = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 16, 17, 18, 19, 20)
    assert unique_number_coverage([a, b]) == 20


def test_unique_number_coverage_rejeita_lista_vazia() -> None:
    with pytest.raises(ValueError):
        unique_number_coverage([])
