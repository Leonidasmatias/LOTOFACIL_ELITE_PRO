"""Testes da analise estatistica do benchmark (LF-05).

Usam ``BenchmarkContestResult`` construidos DIRETAMENTE com valores
conhecidos (nao dependem de rodar motor/random real) para provar que cada
funcao estatistica produz o resultado matematicamente correto e
determinístico -- incluindo os tres ramos de classificacao
(EVIDENCE_POSITIVE / INCONCLUSIVE / EVIDENCE_NEGATIVE), que exigem dados
deliberadamente construidos para cair em cada ramo, nao sorte.
"""
from __future__ import annotations

from src.backtest.benchmark import BenchmarkContestResult
from src.backtest.benchmark_stats import (
    EVIDENCE_NEGATIVE,
    EVIDENCE_POSITIVE,
    INCONCLUSIVE,
    bootstrap_ci_mean_delta,
    classify_evidence,
    compute_paired_deltas,
    high_hit_report,
    paired_deltas_por_concurso_medio_nas_seeds,
    random_aggregates_por_seed,
    summarize_random_distribution,
    win_tie_loss,
)


def _linha(target: int, seed: int, motor_mean: float, random_mean: float, motor_dist=None, random_dist=None) -> BenchmarkContestResult:
    motor_dist = motor_dist or {k: 0 for k in range(16)}
    random_dist = random_dist or {k: 0 for k in range(16)}
    return BenchmarkContestResult(
        target_contest=target,
        history_max_contest=target - 1,
        motor_seed=1000 + target,
        motor_tickets=5,
        motor_max_hits=max(motor_dist, default=0) if any(motor_dist.values()) else 9,
        motor_mean_hits=motor_mean,
        motor_distribution=motor_dist,
        random_seed=seed,
        random_tickets=5,
        random_max_hits=max(random_dist, default=0) if any(random_dist.values()) else 9,
        random_mean_hits=random_mean,
        random_distribution=random_dist,
    )


# --- Distribuicao do random por seed (Fase 10) ------------------------------


def test_random_aggregates_por_seed_agrega_corretamente() -> None:
    linhas = [
        _linha(1, seed=10, motor_mean=9.0, random_mean=8.0, random_dist={8: 5, **{k: 0 for k in range(16) if k != 8}}),
        _linha(2, seed=10, motor_mean=9.0, random_mean=10.0, random_dist={10: 5, **{k: 0 for k in range(16) if k != 10}}),
        _linha(1, seed=20, motor_mean=9.0, random_mean=9.0, random_dist={9: 5, **{k: 0 for k in range(16) if k != 9}}),
    ]
    agregados = random_aggregates_por_seed(linhas)
    assert {a.seed for a in agregados} == {10, 20}
    seed10 = next(a for a in agregados if a.seed == 10)
    # (8*5 + 10*5) / 10 = 9.0
    assert seed10.mean_hits == 9.0


def test_summarize_random_distribution_percentis_conhecidos() -> None:
    valores = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
    resumo = summarize_random_distribution(valores)
    assert resumo.minimum == 1.0
    assert resumo.maximum == 10.0
    assert resumo.median == 5.5
    assert resumo.mean == 5.5


# --- Paired deltas / win-tie-loss (Fase 9) ---------------------------------


def test_win_tie_loss_classifica_corretamente() -> None:
    linhas = [
        _linha(1, 10, motor_mean=10.0, random_mean=9.0),  # win
        _linha(2, 10, motor_mean=9.0, random_mean=9.0),  # tie
        _linha(3, 10, motor_mean=8.0, random_mean=9.0),  # loss
    ]
    deltas = compute_paired_deltas(linhas)
    wtl = win_tie_loss([d.delta_mean_hits for d in deltas])
    assert wtl.wins == 1
    assert wtl.ties == 1
    assert wtl.losses == 1


def test_paired_deltas_por_concurso_medio_nas_seeds_correto() -> None:
    linhas = [
        _linha(1, seed=10, motor_mean=10.0, random_mean=8.0),
        _linha(1, seed=20, motor_mean=10.0, random_mean=10.0),
    ]
    deltas = paired_deltas_por_concurso_medio_nas_seeds(linhas)
    # random medio = (8+10)/2 = 9.0; delta = 10 - 9 = 1.0
    assert deltas[1] == 1.0


# --- Bootstrap CI (Fase 11) e classificacao (Fase 12) -----------------------


def test_bootstrap_ci_mean_delta_e_reprodutivel_com_mesma_seed() -> None:
    deltas = [0.5, 1.0, -0.2, 0.8, 0.3, 0.1, -0.1, 0.6]
    ci1 = bootstrap_ci_mean_delta(deltas, seed=42, iterations=500)
    ci2 = bootstrap_ci_mean_delta(deltas, seed=42, iterations=500)
    assert ci1 == ci2


def test_bootstrap_ci_muda_com_seed_diferente() -> None:
    deltas = [0.5, 1.0, -0.2, 0.8, 0.3, 0.1, -0.1, 0.6]
    ci1 = bootstrap_ci_mean_delta(deltas, seed=1, iterations=500)
    ci2 = bootstrap_ci_mean_delta(deltas, seed=2, iterations=500)
    assert (ci1.ci_low, ci1.ci_high) != (ci2.ci_low, ci2.ci_high)


def test_classify_evidence_positive_deliberadamente_construido() -> None:
    # deltas todos POSITIVOS e afastados de zero -> CI95 nao deve cruzar 0.
    deltas = [2.0 + 0.01 * i for i in range(-10, 11)]  # media ~2.0, variancia minima
    ci = bootstrap_ci_mean_delta(deltas, seed=20260909, iterations=2000)
    assert ci.observed_mean_delta > 0
    assert ci.ci_low > 0
    assert classify_evidence(ci.observed_mean_delta, ci.ci_low, ci.ci_high) == EVIDENCE_POSITIVE


def test_classify_evidence_negative_deliberadamente_construido() -> None:
    deltas = [-2.0 + 0.01 * i for i in range(-10, 11)]  # media ~-2.0
    ci = bootstrap_ci_mean_delta(deltas, seed=20260909, iterations=2000)
    assert ci.observed_mean_delta < 0
    assert ci.ci_high < 0
    assert classify_evidence(ci.observed_mean_delta, ci.ci_low, ci.ci_high) == EVIDENCE_NEGATIVE


def test_classify_evidence_inconclusive_quando_ci_cruza_zero() -> None:
    # delta pequeno com alta variancia -> CI95 cruza 0.
    deltas = [5.0, -5.0, 4.0, -4.0, 3.0, -3.0, 0.1, -0.1]
    ci = bootstrap_ci_mean_delta(deltas, seed=20260909, iterations=2000)
    assert ci.ci_low < 0 < ci.ci_high
    assert classify_evidence(ci.observed_mean_delta, ci.ci_low, ci.ci_high) == INCONCLUSIVE


def test_classify_evidence_funcao_pura_sem_bootstrap() -> None:
    assert classify_evidence(1.0, 0.5, 1.5) == EVIDENCE_POSITIVE
    assert classify_evidence(-1.0, -1.5, -0.5) == EVIDENCE_NEGATIVE
    assert classify_evidence(0.2, -0.1, 0.5) == INCONCLUSIVE
    assert classify_evidence(0.0, -0.1, 0.1) == INCONCLUSIVE


# --- High-hit events (Fase 13) ----------------------------------------------


def test_high_hit_report_classifica_low_sample() -> None:
    distribuicao = {k: 0 for k in range(16)}
    distribuicao[13] = 2
    distribuicao[11] = 50
    relatorio = high_hit_report(distribuicao)
    assert relatorio.motor_ge13 == 2
    assert relatorio.sample_classification == "LOW_SAMPLE"


def test_high_hit_report_classifica_adequate() -> None:
    distribuicao = {k: 0 for k in range(16)}
    distribuicao[13] = 25
    relatorio = high_hit_report(distribuicao)
    assert relatorio.motor_ge13 == 25
    assert relatorio.sample_classification == "ADEQUATE"


def test_high_hit_report_nunca_promove_uma_ocorrencia_isolada() -> None:
    distribuicao = {k: 0 for k in range(16)}
    distribuicao[15] = 1
    relatorio = high_hit_report(distribuicao)
    assert relatorio.motor_eq15 == 1
    assert relatorio.sample_classification == "LOW_SAMPLE"
