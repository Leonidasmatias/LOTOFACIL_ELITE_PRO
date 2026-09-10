"""Testes do diagnostico temporal e de distribuicao de acertos (LF-06).

``TargetAggregate`` construidos DIRETAMENTE com valores conhecidos --
provam que particao cronologica, relatorio por bloco e distribuicao de
acertos sao matematicamente exatos, sem depender de rodar motor/random
real.
"""
from __future__ import annotations

import pytest

from src.backtest.diagnostics import (
    TargetAggregate,
    block_report,
    chronological_blocks,
    hit_distribution_report,
)


def _dist_vazia() -> dict[int, int]:
    return {k: 0 for k in range(16)}


def _linha(
    target: int,
    motor_hits_por_ticket: list[int],
    random_hits_por_ticket_por_seed: dict[int, list[int]],
) -> TargetAggregate:
    motor_dist = _dist_vazia()
    for hits in motor_hits_por_ticket:
        motor_dist[hits] += 1
    random_mean = {}
    random_dist = {}
    for seed, hits_lista in random_hits_por_ticket_por_seed.items():
        dist = _dist_vazia()
        for hits in hits_lista:
            dist[hits] += 1
        random_dist[seed] = dist
        random_mean[seed] = sum(hits_lista) / len(hits_lista)
    return TargetAggregate(
        target_contest=target,
        motor_seed=1000 + target,
        motor_mean_hits=sum(motor_hits_por_ticket) / len(motor_hits_por_ticket),
        motor_max_hits=max(motor_hits_por_ticket),
        motor_distribution=motor_dist,
        random_seed_mean_hits=random_mean,
        random_seed_distribution=random_dist,
    )


# --- Particao cronologica (Fase 7: fronteiras algoritmicas) -----------------


def test_chronological_blocks_cobre_todos_os_concursos_exatamente_uma_vez() -> None:
    targets = list(range(101, 3726))  # 3625 concursos, mesmo range do LF-05
    blocos = chronological_blocks(targets, 5)
    assert len(blocos) == 5
    cobertos: list[int] = []
    for primeiro, ultimo in blocos:
        cobertos.extend(range(primeiro, ultimo + 1))
    assert cobertos == targets
    assert len(set(cobertos)) == len(targets)


def test_chronological_blocks_tamanhos_aproximadamente_iguais() -> None:
    blocos = chronological_blocks(list(range(1, 11)), 3)
    tamanhos = [ultimo - primeiro + 1 for primeiro, ultimo in blocos]
    assert tamanhos == [4, 3, 3]
    assert sum(tamanhos) == 10


def test_chronological_blocks_rejeita_mais_blocos_que_concursos() -> None:
    with pytest.raises(ValueError):
        chronological_blocks([1, 2], 5)


def test_chronological_blocks_e_deterministico() -> None:
    targets = list(range(50, 150))
    assert chronological_blocks(targets, 4) == chronological_blocks(targets, 4)


# --- block_report -----------------------------------------------------------


def test_block_report_motor_supera_random_com_margem_clara() -> None:
    linhas = [
        _linha(100 + i, motor_hits_por_ticket=[10, 10, 10, 10, 10], random_hits_por_ticket_por_seed={1: [8, 8, 8, 8, 8], 2: [8, 9, 8, 9, 8]})
        for i in range(5)
    ]
    relatorio = block_report(linhas, (100, 104))
    assert relatorio.n_contests == 5
    assert relatorio.motor_mean_hits == pytest.approx(10.0)
    assert relatorio.wins == 5
    assert relatorio.losses == 0
    assert relatorio.ties == 0


def test_block_report_conta_high_hit_events_do_motor() -> None:
    linhas = [
        _linha(200, motor_hits_por_ticket=[13, 9, 9, 9, 9], random_hits_por_ticket_por_seed={1: [9, 9, 9, 9, 9]}),
    ]
    relatorio = block_report(linhas, (200, 200))
    assert relatorio.motor_ge13 == 1
    assert relatorio.motor_ge14 == 0
    assert relatorio.motor_eq15 == 0


def test_block_report_ignora_linhas_fora_do_intervalo() -> None:
    linhas = [
        _linha(100, [10] * 5, {1: [8] * 5}),
        _linha(999, [15] * 5, {1: [1] * 5}),  # fora do bloco -- nao deve influenciar
    ]
    relatorio = block_report(linhas, (100, 100))
    assert relatorio.n_contests == 1
    assert relatorio.motor_mean_hits == pytest.approx(10.0)


def test_block_report_rejeita_intervalo_vazio() -> None:
    linhas = [_linha(100, [10] * 5, {1: [8] * 5})]
    with pytest.raises(ValueError):
        block_report(linhas, (500, 600))


# --- Distribuicao de acertos (Fase 8) ----------------------------------------


def test_hit_distribution_report_e_exata_em_fixture_pequena() -> None:
    linhas = [
        _linha(100, motor_hits_por_ticket=[9, 9, 9, 9, 9], random_hits_por_ticket_por_seed={1: [8, 8, 8, 8, 8]}),
        _linha(101, motor_hits_por_ticket=[10, 10, 10, 10, 10], random_hits_por_ticket_por_seed={1: [9, 9, 9, 9, 9]}),
    ]
    relatorio = hit_distribution_report(linhas)
    # motor: 5 tickets com 9, 5 com 10 -- total 10 tickets.
    assert relatorio.p_motor[9] == pytest.approx(0.5)
    assert relatorio.p_motor[10] == pytest.approx(0.5)
    assert sum(relatorio.p_motor.values()) == pytest.approx(1.0)
    # random: 5 com 8, 5 com 9 -- total 10 tickets.
    assert relatorio.p_random[8] == pytest.approx(0.5)
    assert relatorio.p_random[9] == pytest.approx(0.5)
    assert sum(relatorio.p_random.values()) == pytest.approx(1.0)
    assert relatorio.delta[9] == pytest.approx(0.5 - 0.5)
    # cumulativo: P(motor >= 10) = 0.5; P(random >= 10) = 0.0
    assert relatorio.cumulative_motor[10] == pytest.approx(0.5)
    assert relatorio.cumulative_random[10] == pytest.approx(0.0)
    assert relatorio.cumulative_delta[10] == pytest.approx(0.5)


def test_hit_distribution_report_rejeita_lista_vazia() -> None:
    with pytest.raises(ValueError):
        hit_distribution_report([])
