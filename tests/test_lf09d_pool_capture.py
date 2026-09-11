"""Testes de vazamento/determinismo/isolamento da captura LF-09D
(Fase 24/25/26)."""
from __future__ import annotations

from typing import Any

import pytest

from src.backtest.contracts import ContestSnapshot, LeakageError
from src.backtest.lf09d_pool_capture import run_lf09d_target
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


DEFAULTS: dict[str, Any] = dict(motor_base_seed=7_000_000, g0_base_seed=1_000_000, g1_base_seed=2_000_000, g_pool_size=50)


def test_run_lf09d_target_rejeita_alvo_ausente() -> None:
    base = _base_sintetica(40)
    with pytest.raises(ValueError, match="nao esta em all_contests"):
        run_lf09d_target(base, target_contest=9999, **DEFAULTS)


def test_run_lf09d_target_leakageerror_herdado_do_harness() -> None:
    base = _base_sintetica(40)
    from src.backtest.engine_adapter import ReferenceRandomEngine
    from src.backtest.harness import predict_for_contest

    with pytest.raises(LeakageError):
        predict_for_contest(ReferenceRandomEngine(), base, 35, 5, 1)


def test_run_lf09d_target_rejeita_historico_vazio() -> None:
    concurso_unico = [_concurso_sintetico(1)]
    with pytest.raises(ValueError, match="Historico vazio"):
        run_lf09d_target(concurso_unico, target_contest=1, **DEFAULTS)


def test_run_lf09d_target_e_reprodutivel() -> None:
    base = _base_sintetica(60)
    r1 = run_lf09d_target(base, target_contest=50, **DEFAULTS)
    r2 = run_lf09d_target(base, target_contest=50, **DEFAULTS)
    assert r1 == r2


def test_run_lf09d_target_cobre_todos_os_perfis() -> None:
    base = _base_sintetica(60)
    r = run_lf09d_target(base, target_contest=50, **DEFAULTS)
    perfis_no_pool = {c.profile for c in r.pool}
    assert perfis_no_pool == set(PERFIS_V2)
    assert len(r.original_selection) == 5
    assert [s.profile for s in r.original_selection] == PERFIS_V2


def test_run_lf09d_target_g0_g1_tamanho_correto() -> None:
    base = _base_sintetica(60)
    r = run_lf09d_target(base, target_contest=50, **DEFAULTS)
    assert len(r.g0_pool) == 50
    assert len(r.g0_pool_hits) == 50
    assert len(r.g1_pool) == 50
    assert len(r.g1_pool_hits) == 50


def test_run_lf09d_target_hits_no_intervalo_valido() -> None:
    base = _base_sintetica(60)
    r = run_lf09d_target(base, target_contest=50, **DEFAULTS)
    assert all(0 <= c.hits <= 15 for c in r.pool)
    assert all(0 <= h <= 15 for h in r.g0_pool_hits)
    assert all(0 <= h <= 15 for h in r.g1_pool_hits)


def test_run_lf09d_target_motor_seed_policy() -> None:
    from src.backtest.lf09d_pool_capture import motor_seed_policy

    assert motor_seed_policy(1000, 50) == 1050


def test_run_lf09d_target_history_max_contest_e_alvo_menos_um() -> None:
    base = _base_sintetica(60)
    r = run_lf09d_target(base, target_contest=50, **DEFAULTS)
    assert r.history_max_contest == 49


def test_run_lf09d_target_assinatura_nao_aceita_resultado_real() -> None:
    import inspect

    proibidos = {"target_result", "winning_numbers", "resultado_real", "resultado_alvo"}
    assert proibidos.isdisjoint(inspect.signature(run_lf09d_target).parameters)


# --- Fase 25: leakage hardening explicito -----------------------------------


def test_pool_e_selecao_independem_de_qual_resultado_e_revelado_depois() -> None:
    """Mesmo history/seed/config -- congelamento identico -- mesmo com
    dois resultados futuros diferentes e incompativeis apresentados
    DEPOIS. So metricas retrospectivas (hits, oracle) podem mudar;
    pool/selecao/G0/G1 (tickets) NUNCA."""
    base_a = _base_sintetica(60)
    r_a = run_lf09d_target(base_a, target_contest=50, **DEFAULTS)

    # Historico (concursos < 50) IDENTICO; somente o resultado do
    # proprio concurso-alvo 50 e trocado por outro valor valido e
    # diferente -- prediction nao pode ter usado isso.
    base_b = _base_sintetica(60)
    numeros_alternativos = tuple(sorted(set(range(1, 26)) - set(base_b[49].numbers[:10])))[:15]
    assert numeros_alternativos != base_b[49].numbers
    base_b[49] = ContestSnapshot(number=50, date=base_b[49].date, numbers=numeros_alternativos)

    r_b = run_lf09d_target(base_b, target_contest=50, **DEFAULTS)

    tickets_pool_a = [(c.profile, c.ticket, c.raw_structure_score, c.final_candidate_score) for c in r_a.pool]
    tickets_pool_b = [(c.profile, c.ticket, c.raw_structure_score, c.final_candidate_score) for c in r_b.pool]
    assert tickets_pool_a == tickets_pool_b
    assert r_a.g0_pool == r_b.g0_pool
    assert r_a.g1_pool == r_b.g1_pool
    assert [(s.profile, s.selected_ticket) for s in r_a.original_selection] == [
        (s.profile, s.selected_ticket) for s in r_b.original_selection
    ]


# --- Fase 26: RNG invariance (instrumentacao LF-09D nao muda RNG do motor) --


def test_g0_g1_nao_afetam_tickets_do_motor() -> None:
    """Rodar SEM G0/G1 (pool_size minimo permitido) e comparar os
    tickets do motor com uma chamada que usa pool_size maior -- os
    tickets/selecao do MOTOR devem ser identicos, pois G0/G1 usam RNG
    totalmente separado."""
    base = _base_sintetica(60)
    r_pequeno = run_lf09d_target(base, target_contest=50, motor_base_seed=7_000_000, g0_base_seed=1_000_000, g1_base_seed=2_000_000, g_pool_size=15)
    r_grande = run_lf09d_target(base, target_contest=50, motor_base_seed=7_000_000, g0_base_seed=1_000_000, g1_base_seed=2_000_000, g_pool_size=200)
    tickets_a = [(c.profile, c.ticket, c.final_candidate_score) for c in r_pequeno.pool]
    tickets_b = [(c.profile, c.ticket, c.final_candidate_score) for c in r_grande.pool]
    assert tickets_a == tickets_b
    assert [s.selected_ticket for s in r_pequeno.original_selection] == [s.selected_ticket for s in r_grande.original_selection]
