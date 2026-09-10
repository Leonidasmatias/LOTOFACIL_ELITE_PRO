"""Testes do diagnostico de cauda alta 13/14/15 (LF-06, Fase 9).

Cobrem extracao exata de eventos a partir de ``TargetAggregate``
construidos e a reconstrucao de detalhe por-ticket via harness LF-04, sem
vazamento (herdado, nao reimplementado).
"""
from __future__ import annotations

import pytest

from src.backtest.contracts import ContestSnapshot, LeakageError
from src.backtest.diagnostics import TargetAggregate
from src.backtest.engine_adapter import ReferenceRandomEngine
from src.backtest.tail_diagnostics import extract_tail_events, recompute_single_target


def _dist_vazia() -> dict[int, int]:
    return {k: 0 for k in range(16)}


def _linha(target: int, motor_hits: list[int], random_hits_por_seed: dict[int, list[int]]) -> TargetAggregate:
    motor_dist = _dist_vazia()
    for h in motor_hits:
        motor_dist[h] += 1
    random_dist = {}
    random_mean = {}
    for seed, hits in random_hits_por_seed.items():
        dist = _dist_vazia()
        for h in hits:
            dist[h] += 1
        random_dist[seed] = dist
        random_mean[seed] = sum(hits) / len(hits)
    return TargetAggregate(
        target_contest=target,
        motor_seed=1000 + target,
        motor_mean_hits=sum(motor_hits) / len(motor_hits),
        motor_max_hits=max(motor_hits),
        motor_distribution=motor_dist,
        random_seed_mean_hits=random_mean,
        random_seed_distribution=random_dist,
    )


def test_extract_tail_events_encontra_evento_ge13() -> None:
    linhas = [
        _linha(100, motor_hits=[13, 9, 9, 9, 9], random_hits_por_seed={1: [9] * 5, 2: [9] * 5}),
        _linha(101, motor_hits=[9, 9, 9, 9, 9], random_hits_por_seed={1: [9] * 5, 2: [9] * 5}),
    ]
    eventos = extract_tail_events(linhas, threshold=13)
    assert len(eventos) == 1
    assert eventos[0].target_contest == 100
    assert eventos[0].hits == 13
    assert eventos[0].count_at_hits == 1
    assert eventos[0].random_seeds_ge_threshold_count == 0
    assert eventos[0].random_seeds_ge_threshold_fraction == pytest.approx(0.0)


def test_extract_tail_events_zero_eventos_e_valido() -> None:
    linhas = [_linha(100, motor_hits=[9, 9, 9, 9, 9], random_hits_por_seed={1: [9] * 5})]
    assert extract_tail_events(linhas, threshold=14) == []


def test_extract_tail_events_calcula_fracao_random_corretamente() -> None:
    linhas = [
        _linha(
            100,
            motor_hits=[13, 9, 9, 9, 9],
            random_hits_por_seed={1: [13, 9, 9, 9, 9], 2: [9] * 5, 3: [9] * 5, 4: [9] * 5},
        )
    ]
    eventos = extract_tail_events(linhas, threshold=13)
    assert len(eventos) == 1
    assert eventos[0].random_seeds_ge_threshold_count == 1
    assert eventos[0].random_seeds_total == 4
    assert eventos[0].random_seeds_ge_threshold_fraction == pytest.approx(0.25)


def test_extract_tail_events_multiplos_niveis_no_mesmo_concurso() -> None:
    linhas = [_linha(100, motor_hits=[13, 14, 9, 9, 9], random_hits_por_seed={1: [9] * 5})]
    eventos = extract_tail_events(linhas, threshold=13)
    assert {e.hits for e in eventos} == {13, 14}
    assert eventos[0].hits == 14  # ordenado por hits desc dentro do mesmo concurso


def test_extract_tail_events_ordenado_por_concurso() -> None:
    linhas = [
        _linha(200, motor_hits=[13, 9, 9, 9, 9], random_hits_por_seed={1: [9] * 5}),
        _linha(100, motor_hits=[13, 9, 9, 9, 9], random_hits_por_seed={1: [9] * 5}),
    ]
    eventos = extract_tail_events(linhas, threshold=13)
    assert [e.target_contest for e in eventos] == [100, 200]


# --- recompute_single_target: reusa harness LF-04 sem vazamento -------------


def _concurso_sintetico(numero: int) -> ContestSnapshot:
    brutas = sorted(((numero * 7 + i * 3) % 25) + 1 for i in range(15))
    usadas: list[int] = []
    cursor = 1
    for dezena in brutas:
        while dezena in usadas:
            dezena = cursor
            cursor += 1
            if cursor > 25:
                cursor = 1
        usadas.append(dezena)
    return ContestSnapshot(number=numero, date=f"{(numero % 28) + 1:02d}/01/2026", numbers=tuple(sorted(usadas)))


def _base_sintetica(quantidade: int) -> list[ContestSnapshot]:
    return [_concurso_sintetico(n) for n in range(1, quantidade + 1)]


def test_recompute_single_target_e_deterministico() -> None:
    base = _base_sintetica(40)
    r1 = recompute_single_target(ReferenceRandomEngine(), base, target_contest=35, tickets_per_contest=5, seed=42)
    r2 = recompute_single_target(ReferenceRandomEngine(), base, target_contest=35, tickets_per_contest=5, seed=42)
    assert r1 == r2


def test_recompute_single_target_rejeita_alvo_ausente() -> None:
    base = _base_sintetica(40)
    with pytest.raises(ValueError, match="nao esta em all_contests"):
        recompute_single_target(ReferenceRandomEngine(), base, target_contest=9999, tickets_per_contest=5, seed=1)


def test_recompute_single_target_historico_nao_inclui_o_proprio_alvo() -> None:
    base = _base_sintetica(40)
    resultado = recompute_single_target(ReferenceRandomEngine(), base, target_contest=35, tickets_per_contest=5, seed=1)
    assert resultado.batch.history_max_contest == 34


def test_recompute_single_target_herda_leakageerror_do_harness_lf04() -> None:
    """``recompute_single_target`` usa ``all_contests`` para filtrar o
    historico internamente (nao aceita historico pre-filtrado do chamador),
    entao nao ha como um concurso >= alvo entrar no historico -- mas a
    protecao de ``predict_for_contest`` (LF-04) continua ativa por baixo."""
    from src.backtest.harness import predict_for_contest

    base = _base_sintetica(40)
    historico_com_vazamento = base  # inclui concursos >= 35
    with pytest.raises(LeakageError):
        predict_for_contest(ReferenceRandomEngine(), historico_com_vazamento, 35, 5, 1)
