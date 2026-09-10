"""Testes das funcoes puras de calibracao de score (LF-09C, Fase 19)."""
from __future__ import annotations

import pytest

from src.backtest.score_calibration import (
    assign_decile,
    decile_calibration,
    min_max_normalize,
    percentile,
    quantile_boundaries,
    rank_percentile,
    spearman_correlation,
    top_bottom_lift,
    z_score,
)


# --- percentile / quantile_boundaries ---------------------------------------


def test_percentile_extremos() -> None:
    valores = [10.0, 20.0, 30.0, 40.0, 50.0]
    assert percentile(valores, 0.0) == 10.0
    assert percentile(valores, 1.0) == 50.0
    assert percentile(valores, 0.5) == 30.0


def test_percentile_lista_vazia_levanta() -> None:
    with pytest.raises(ValueError):
        percentile([], 0.5)


def test_quantile_boundaries_quatro_grupos() -> None:
    valores = list(range(1, 101))  # 1..100
    fronteiras = quantile_boundaries(valores, 4)
    assert len(fronteiras) == 5
    assert fronteiras[0] == 1
    assert fronteiras[-1] == 100


def test_quantile_boundaries_rejeita_lista_vazia() -> None:
    with pytest.raises(ValueError):
        quantile_boundaries([], 4)


def test_quantile_boundaries_rejeita_n_nao_positivo() -> None:
    with pytest.raises(ValueError):
        quantile_boundaries([1.0, 2.0], 0)


# --- assign_decile -----------------------------------------------------------


def test_assign_decile_dentro_dos_limites() -> None:
    fronteiras = [0.0, 25.0, 50.0, 75.0, 100.0]
    assert assign_decile(0.0, fronteiras) == 0
    assert assign_decile(10.0, fronteiras) == 0
    assert assign_decile(25.0, fronteiras) == 1
    assert assign_decile(100.0, fronteiras) == 3
    assert assign_decile(99.9, fronteiras) == 3


def test_assign_decile_rejeita_poucas_fronteiras() -> None:
    with pytest.raises(ValueError):
        assign_decile(5.0, [1.0])


# --- rank_percentile -----------------------------------------------------------


def test_rank_percentile_ordem_simples() -> None:
    valores = [10.0, 30.0, 20.0]
    ranks = rank_percentile(valores)
    assert ranks[0] == pytest.approx(0.0)  # menor
    assert ranks[2] == pytest.approx(0.5)  # meio
    assert ranks[1] == pytest.approx(1.0)  # maior


def test_rank_percentile_empates_recebem_rank_medio() -> None:
    valores = [10.0, 10.0, 20.0]
    ranks = rank_percentile(valores)
    assert ranks[0] == ranks[1]
    assert ranks[0] == pytest.approx(0.25)  # media dos ranks 0 e 1, / (n-1)=2
    assert ranks[2] == pytest.approx(1.0)


def test_rank_percentile_todos_empatados() -> None:
    valores = [5.0, 5.0, 5.0, 5.0]
    ranks = rank_percentile(valores)
    assert all(r == pytest.approx(0.5) for r in ranks)


def test_rank_percentile_lista_unica() -> None:
    assert rank_percentile([42.0]) == [0.5]


def test_rank_percentile_rejeita_lista_vazia() -> None:
    with pytest.raises(ValueError):
        rank_percentile([])


def test_rank_percentile_determinismo() -> None:
    valores = [3.0, 1.0, 4.0, 1.0, 5.0, 9.0, 2.0, 6.0]
    assert rank_percentile(valores) == rank_percentile(list(valores))


def test_rank_percentile_nao_muta_entrada() -> None:
    valores = [3.0, 1.0, 2.0]
    copia = list(valores)
    rank_percentile(valores)
    assert valores == copia


# --- z_score -------------------------------------------------------------------


def test_z_score_media_zero_desvio_um() -> None:
    valores = [10.0, 20.0, 30.0, 40.0, 50.0]
    zs = z_score(valores)
    assert sum(zs) / len(zs) == pytest.approx(0.0, abs=1e-9)


def test_z_score_constante_devolve_zeros() -> None:
    assert z_score([7.0, 7.0, 7.0]) == [0.0, 0.0, 0.0]


def test_z_score_rejeita_lista_vazia() -> None:
    with pytest.raises(ValueError):
        z_score([])


# --- min_max_normalize -----------------------------------------------------------


def test_min_max_normalize_extremos() -> None:
    valores = [10.0, 20.0, 30.0]
    normalizados = min_max_normalize(valores)
    assert normalizados[0] == pytest.approx(0.0)
    assert normalizados[-1] == pytest.approx(1.0)
    assert normalizados[1] == pytest.approx(0.5)


def test_min_max_normalize_constante_devolve_meio() -> None:
    assert min_max_normalize([5.0, 5.0, 5.0]) == [0.5, 0.5, 0.5]


def test_min_max_normalize_rejeita_lista_vazia() -> None:
    with pytest.raises(ValueError):
        min_max_normalize([])


# --- spearman_correlation -----------------------------------------------------------


def test_spearman_correlacao_perfeita_positiva() -> None:
    x = [1.0, 2.0, 3.0, 4.0, 5.0]
    y = [10.0, 20.0, 30.0, 40.0, 50.0]
    assert spearman_correlation(x, y) == pytest.approx(1.0)


def test_spearman_correlacao_perfeita_negativa() -> None:
    x = [1.0, 2.0, 3.0, 4.0, 5.0]
    y = [50.0, 40.0, 30.0, 20.0, 10.0]
    assert spearman_correlation(x, y) == pytest.approx(-1.0)


def test_spearman_robusta_a_transformacao_nao_linear_monotonica() -> None:
    """Spearman deve continuar proximo de 1.0 mesmo com relacao
    NAO-linear (mas monotonica) entre x e y -- diferente de Pearson."""
    x = [1.0, 2.0, 3.0, 4.0, 5.0]
    y = [v**3 for v in x]
    assert spearman_correlation(x, y) == pytest.approx(1.0)


def test_spearman_rejeita_tamanhos_diferentes() -> None:
    with pytest.raises(ValueError):
        spearman_correlation([1.0, 2.0], [1.0])


# --- decile_calibration -----------------------------------------------------------


def test_decile_calibration_sinal_saudavel_e_monotonico() -> None:
    # score e hits perfeitamente correlacionados -- decis devem ser
    # estritamente crescentes em mean_hits.
    scores = list(range(1, 101))
    hits = list(range(1, 101))
    relatorios = decile_calibration([float(s) for s in scores], hits, n_deciles=10)
    assert len(relatorios) == 10
    medias = [r.mean_hits for r in relatorios]
    assert medias == sorted(medias)
    assert medias[0] < medias[-1]


def test_decile_calibration_sem_sinal_e_aproximadamente_constante() -> None:
    scores = list(range(1, 101))
    hits = [9] * 100  # sem variacao nenhuma
    relatorios = decile_calibration([float(s) for s in scores], hits, n_deciles=10)
    medias = [r.mean_hits for r in relatorios]
    assert all(m == pytest.approx(9.0) for m in medias)


def test_decile_calibration_rejeita_tamanhos_diferentes() -> None:
    with pytest.raises(ValueError):
        decile_calibration([1.0, 2.0], [1])


def test_decile_calibration_n_cobre_todos_os_candidatos() -> None:
    scores = [float(v) for v in range(1, 51)]
    hits = [v % 16 for v in range(1, 51)]
    relatorios = decile_calibration(scores, hits, n_deciles=5)
    assert sum(r.n for r in relatorios) == 50


# --- top_bottom_lift -----------------------------------------------------------


def test_top_bottom_lift_positivo_quando_score_preve_hits() -> None:
    scores = [float(v) for v in range(1, 101)]
    hits = list(range(1, 101))
    resultado = top_bottom_lift(scores, hits, top_fraction=0.1)
    assert resultado.lift > 0
    assert resultado.top_n == 10
    assert resultado.bottom_n == 10


def test_top_bottom_lift_zero_quando_sem_sinal() -> None:
    scores = [float(v) for v in range(1, 101)]
    hits = [9] * 100
    resultado = top_bottom_lift(scores, hits, top_fraction=0.1)
    assert resultado.lift == pytest.approx(0.0)


def test_top_bottom_lift_rejeita_fracao_invalida() -> None:
    with pytest.raises(ValueError):
        top_bottom_lift([1.0, 2.0], [1, 2], top_fraction=0.6)
    with pytest.raises(ValueError):
        top_bottom_lift([1.0, 2.0], [1, 2], top_fraction=0.0)
