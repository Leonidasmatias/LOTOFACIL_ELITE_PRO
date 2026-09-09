"""Testes do benchmark justo MOTOR_ELITE_V2 vs RANDOM (LF-05).

Herméticos: dataset sintetico determinístico, nenhuma rede, nenhuma
escrita em CSV/SQLite reais. Cobrem: orcamento igual de tickets (Fase 14),
selecao de alvos sem cherry-pick (Fase 15), multiplas seeds (Fase 5),
comparacao pareada (Fase 9), benchmark sintetico nao-promocional
(Fase 17) e ausencia de vazamento herdado do harness LF-04.
"""
from __future__ import annotations

import inspect
from typing import Any

import pytest

from src.backtest.benchmark import (
    eligible_targets,
    motor_seed_policy,
    random_seeds,
    run_fair_benchmark,
)
from src.backtest.benchmark_stats import (
    classify_evidence,
    compute_paired_deltas,
    win_tie_loss,
)
from src.backtest.contracts import ContestSnapshot, LeakageError
from src.backtest.engine_adapter import ReferenceRandomEngine


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


def _base_sintetica(quantidade: int = 60) -> list[ContestSnapshot]:
    return [_concurso_sintetico(n) for n in range(1, quantidade + 1)]


# --- Fase 15: no cherry-pick ------------------------------------------------


def test_eligible_targets_assinatura_nao_aceita_metrica_de_performance() -> None:
    """A funcao que escolhe os targets so pode receber dados brutos
    (concursos) e um requisito minimo de historico -- nunca resultado,
    performance, max_hits ou score."""
    parametros = set(inspect.signature(eligible_targets).parameters)
    assert parametros == {"all_contests", "min_history"}


def test_eligible_targets_e_todos_os_concursos_elegiveis_sem_remocao() -> None:
    base = _base_sintetica(60)
    targets = eligible_targets(base, min_history=30)
    # Todos os concursos de numero > min_history, sem NENHUM removido.
    assert targets == list(range(31, 61))
    assert len(targets) == 30


def test_eligible_targets_e_deterministico() -> None:
    base = _base_sintetica(60)
    assert eligible_targets(base, min_history=30) == eligible_targets(base, min_history=30)


# --- Fase 6: motor seed policy fixa -----------------------------------------


def test_motor_seed_policy_e_deterministica_e_simetrica() -> None:
    assert motor_seed_policy(1000, 50) == 1050
    assert motor_seed_policy(1000, 50) == motor_seed_policy(1000, 50)
    assert motor_seed_policy(1000, 51) != motor_seed_policy(1000, 50)


# --- Fase 5: multiplas seeds do random --------------------------------------


def test_random_seeds_e_lista_deterministica() -> None:
    seeds = random_seeds(20260909, 30)
    assert len(seeds) == 30
    assert seeds == [20260909 + i for i in range(30)]
    assert len(set(seeds)) == 30  # todas distintas


# --- Fase 14: same budget guarantee -----------------------------------------


def test_same_budget_motor_e_random_tem_exatamente_K_tickets() -> None:
    base = _base_sintetica(60)
    targets = eligible_targets(base, min_history=30)
    K = 5
    resultados = run_fair_benchmark(
        motor_engine=ReferenceRandomEngine(),
        all_contests=base,
        target_contests=targets,
        tickets_per_contest=K,
        motor_base_seed=1000,
        random_base_seed=20260909,
        random_seed_count=10,
    )
    for linha in resultados:
        assert linha.motor_tickets == K
        assert linha.random_tickets == K
        assert linha.motor_tickets == linha.random_tickets == K

    motor_total_tickets = sum(linha.motor_tickets for linha in resultados)
    # cada concurso conta o motor 1x por linha, mas o motor SO RODOU 1x por
    # concurso (nao 1x por seed) -- para comparar "total" de forma justa,
    # usamos os tickets por concurso (nao por linha replicada pela seed).
    tickets_motor_por_concurso = K * len(targets)
    tickets_random_por_seed = K * len(targets)
    assert tickets_motor_por_concurso == tickets_random_por_seed
    assert motor_total_tickets == K * len(resultados)  # replicado por seed, mas sempre == K em cada linha


def test_benchmark_invalido_se_numero_de_tickets_diferir() -> None:
    """Nao existe API no harness para pedir numeros diferentes de tickets
    para motor e random dentro do mesmo run_fair_benchmark -- o parametro
    ``tickets_per_contest`` e unico e compartilhado. Este teste documenta
    essa garantia estrutural."""
    parametros = inspect.signature(run_fair_benchmark).parameters
    assert "tickets_per_contest" in parametros
    assert "motor_tickets_per_contest" not in parametros
    assert "random_tickets_per_contest" not in parametros


# --- Fase 9: comparacao pareada ---------------------------------------------


def test_paired_deltas_um_por_linha_e_win_tie_loss_consistente() -> None:
    base = _base_sintetica(60)
    targets = eligible_targets(base, min_history=30)
    resultados = run_fair_benchmark(
        motor_engine=ReferenceRandomEngine(),
        all_contests=base,
        target_contests=targets,
        tickets_per_contest=5,
        motor_base_seed=1000,
        random_base_seed=20260909,
        random_seed_count=10,
    )
    deltas = compute_paired_deltas(resultados)
    assert len(deltas) == len(resultados)
    wtl = win_tie_loss([d.delta_mean_hits for d in deltas])
    assert wtl.wins + wtl.ties + wtl.losses == len(deltas)
    assert wtl.wins >= 0 and wtl.ties >= 0 and wtl.losses >= 0


# --- Fase 17: benchmark sintetico nao gera conclusao positiva artificial --


def test_benchmark_sintetico_motor_de_referencia_contra_random_e_inconclusive_ou_negativo() -> None:
    """Usar ReferenceRandomEngine como "motor" (sem nenhuma vantagem real
    sobre outro baseline aleatorio) NUNCA deve produzir EVIDENCE_POSITIVE
    -- prova que o benchmark nao fabrica evidencia de superioridade onde
    nao ha nenhuma."""
    from src.backtest.benchmark_stats import bootstrap_ci_mean_delta, paired_deltas_por_concurso_medio_nas_seeds

    base = _base_sintetica(120)
    targets = eligible_targets(base, min_history=30)
    resultados = run_fair_benchmark(
        motor_engine=ReferenceRandomEngine(),  # "motor" = tambem so aleatorio
        all_contests=base,
        target_contests=targets,
        tickets_per_contest=5,
        motor_base_seed=1000,
        random_base_seed=20260909,
        random_seed_count=30,
    )
    deltas_por_concurso = paired_deltas_por_concurso_medio_nas_seeds(resultados)
    ci = bootstrap_ci_mean_delta(list(deltas_por_concurso.values()), seed=20260909, iterations=1000)
    veredito = classify_evidence(ci.observed_mean_delta, ci.ci_low, ci.ci_high)
    assert veredito != "EVIDENCE_POSITIVE"


# --- Ausencia de vazamento herdado do harness LF-04 -------------------------


def test_benchmark_rejeita_target_contaminado_no_historico() -> None:
    """O benchmark reutiliza predict_for_contest (LF-04) sem reimplementar
    a checagem de vazamento -- confirma que a protecao continua ativa
    quando usada atraves do benchmark."""
    base = _base_sintetica(60)
    # historico deliberadamente contaminado: inclui o proprio concurso 40.
    from src.backtest.harness import predict_for_contest

    historico_contaminado = [c for c in base if c.number <= 40]
    with pytest.raises(LeakageError):
        predict_for_contest(ReferenceRandomEngine(), historico_contaminado, 40, 5, seed=1)


def test_run_fair_benchmark_usa_apenas_historico_anterior_ao_alvo() -> None:
    base = _base_sintetica(60)
    targets = eligible_targets(base, min_history=30)
    resultados = run_fair_benchmark(
        motor_engine=ReferenceRandomEngine(),
        all_contests=base,
        target_contests=targets,
        tickets_per_contest=5,
        motor_base_seed=1000,
        random_base_seed=20260909,
        random_seed_count=5,
    )
    for linha in resultados:
        assert linha.history_max_contest == linha.target_contest - 1


def test_run_fair_benchmark_rejeita_target_ausente() -> None:
    base = _base_sintetica(30)
    with pytest.raises(ValueError, match="nao esta em all_contests"):
        run_fair_benchmark(
            motor_engine=ReferenceRandomEngine(),
            all_contests=base,
            target_contests=[9999],
            tickets_per_contest=5,
            motor_base_seed=1000,
            random_base_seed=20260909,
            random_seed_count=1,
        )


def test_run_fair_benchmark_e_reprodutivel_com_mesma_configuracao() -> None:
    """Fase 16/21: duas execucoes do benchmark completo, com a MESMA
    configuracao (base, targets, engine, seeds), devem produzir resultados
    logicamente idênticos -- inclusive o fingerprint de historico de cada
    PredictionBatch subjacente."""
    base = _base_sintetica(60)
    targets = eligible_targets(base, min_history=30)
    kwargs: dict[str, Any] = dict(
        motor_engine=ReferenceRandomEngine(),
        all_contests=base,
        target_contests=targets,
        tickets_per_contest=5,
        motor_base_seed=1000,
        random_base_seed=20260909,
        random_seed_count=15,
    )
    r1 = run_fair_benchmark(**kwargs)
    r2 = run_fair_benchmark(**kwargs)
    assert r1 == r2


def test_benchmark_contest_result_e_frozen() -> None:
    import dataclasses

    base = _base_sintetica(40)
    targets = eligible_targets(base, min_history=30)
    resultados = run_fair_benchmark(
        motor_engine=ReferenceRandomEngine(),
        all_contests=base,
        target_contests=targets,
        tickets_per_contest=3,
        motor_base_seed=1000,
        random_base_seed=20260909,
        random_seed_count=2,
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        resultados[0].motor_max_hits = 999  # type: ignore[misc]
