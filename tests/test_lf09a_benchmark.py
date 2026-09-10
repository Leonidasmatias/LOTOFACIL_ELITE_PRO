"""Testes do benchmark walk-forward LF-09A (Fase 9/13).

Herméticos: dataset sintetico determinístico, nenhuma rede. Cobrem
vazamento (historico nao pode conter o alvo), reprodutibilidade, mesmo
orcamento (K=5) para todo selector, e ausencia de escolha de concursos
por desempenho.
"""
from __future__ import annotations

import pytest

from src.backtest.contracts import ContestSnapshot, LeakageError
from src.backtest.lf09a_benchmark import run_lf09a_target


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


def test_run_lf09a_target_rejeita_alvo_ausente() -> None:
    base = _base_sintetica(40)
    with pytest.raises(ValueError, match="nao esta em all_contests"):
        run_lf09a_target(base, target_contest=9999, motor_base_seed=7_000_000, random_control_seeds=[1])


def test_run_lf09a_target_levanta_leakageerror_com_historico_contaminado() -> None:
    base = _base_sintetica(40)
    historico_com_vazamento = base  # inclui concursos >= 35
    from src.backtest.harness import predict_for_contest
    from src.backtest.engine_adapter import ReferenceRandomEngine

    with pytest.raises(LeakageError):
        predict_for_contest(ReferenceRandomEngine(), historico_com_vazamento, 35, 5, 1)


def test_run_lf09a_target_history_max_contest_e_alvo_menos_um() -> None:
    base = _base_sintetica(60)
    resultado = run_lf09a_target(base, target_contest=50, motor_base_seed=7_000_000, random_control_seeds=[1])
    assert resultado.history_max_contest == 49


def test_run_lf09a_target_e_reprodutivel() -> None:
    base = _base_sintetica(60)
    r1 = run_lf09a_target(base, target_contest=50, motor_base_seed=7_000_000, random_control_seeds=[1, 2])
    r2 = run_lf09a_target(base, target_contest=50, motor_base_seed=7_000_000, random_control_seeds=[1, 2])
    assert r1 == r2


def test_run_lf09a_target_todos_os_selectors_usam_k5() -> None:
    base = _base_sintetica(60)
    resultado = run_lf09a_target(base, target_contest=50, motor_base_seed=7_000_000, random_control_seeds=[1, 2, 3])
    assert len(resultado.original.tickets) == 5
    for outcome in resultado.por_config.values():
        assert len(outcome.tickets) == 5
    for outcome in resultado.random_controls:
        assert len(outcome.tickets) == 5


def test_run_lf09a_target_motor_seed_policy_e_deterministica() -> None:
    base = _base_sintetica(60)
    r1 = run_lf09a_target(base, target_contest=50, motor_base_seed=1000, random_control_seeds=[1])
    assert r1.motor_seed == 1050


def test_run_lf09a_target_rejeita_historico_vazio() -> None:
    concurso_unico = [_concurso_sintetico(1)]
    with pytest.raises(ValueError, match="Historico vazio"):
        run_lf09a_target(concurso_unico, target_contest=1, motor_base_seed=1000, random_control_seeds=[1])
