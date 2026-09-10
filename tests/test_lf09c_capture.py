"""Testes de vazamento/determinismo da captura LF-09C (Fase 14)."""
from __future__ import annotations

import pytest

from src.backtest.contracts import ContestSnapshot, LeakageError
from src.backtest.lf09c_capture import PROFILE_POSITION, run_lf09c_target
from src.motor_elite_v2 import PERFIS_V2


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


def test_profile_position_cobre_todos_os_perfis_na_ordem_correta() -> None:
    assert PROFILE_POSITION == {nome: indice for indice, nome in enumerate(PERFIS_V2)}
    assert PROFILE_POSITION["Diamante"] == 0
    assert PROFILE_POSITION["Conservador"] == 4


def test_run_lf09c_target_rejeita_alvo_ausente() -> None:
    base = _base_sintetica(40)
    with pytest.raises(ValueError, match="nao esta em all_contests"):
        run_lf09c_target(base, target_contest=9999, motor_base_seed=7_000_000)


def test_run_lf09c_target_leakageerror_herdado_do_harness() -> None:
    base = _base_sintetica(40)
    from src.backtest.engine_adapter import ReferenceRandomEngine
    from src.backtest.harness import predict_for_contest

    with pytest.raises(LeakageError):
        predict_for_contest(ReferenceRandomEngine(), base, 35, 5, 1)


def test_run_lf09c_target_rejeita_historico_vazio() -> None:
    concurso_unico = [_concurso_sintetico(1)]
    with pytest.raises(ValueError, match="Historico vazio"):
        run_lf09c_target(concurso_unico, target_contest=1, motor_base_seed=1000)


def test_run_lf09c_target_e_reprodutivel() -> None:
    base = _base_sintetica(60)
    r1 = run_lf09c_target(base, target_contest=50, motor_base_seed=7_000_000)
    r2 = run_lf09c_target(base, target_contest=50, motor_base_seed=7_000_000)
    assert r1 == r2


def test_run_lf09c_target_produz_observacoes_para_todos_os_perfis() -> None:
    base = _base_sintetica(60)
    observacoes = run_lf09c_target(base, target_contest=50, motor_base_seed=7_000_000)
    perfis_observados = {obs.profile for obs in observacoes}
    assert perfis_observados == set(PERFIS_V2)


def test_run_lf09c_target_hits_no_intervalo_valido() -> None:
    base = _base_sintetica(60)
    observacoes = run_lf09c_target(base, target_contest=50, motor_base_seed=7_000_000)
    assert all(0 <= obs.hits <= 15 for obs in observacoes)


def test_run_lf09c_target_contest_correto_em_toda_observacao() -> None:
    base = _base_sintetica(60)
    observacoes = run_lf09c_target(base, target_contest=50, motor_base_seed=7_000_000)
    assert all(obs.contest == 50 for obs in observacoes)


def test_run_lf09c_target_motor_seed_policy_deterministica() -> None:
    from src.backtest.lf09c_capture import motor_seed_policy

    assert motor_seed_policy(1000, 50) == 1050


def test_run_lf09c_target_assinatura_nao_aceita_resultado_real() -> None:
    import inspect

    proibidos = {"target_result", "winning_numbers", "resultado_real", "resultado_alvo"}
    assert proibidos.isdisjoint(inspect.signature(run_lf09c_target).parameters)
