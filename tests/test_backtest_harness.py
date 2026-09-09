"""Testes do harness de backtest walk-forward (LF-04).

Cobrem: contratos puros, freeze-before-open estrutural, engine de
referencia, agregacao de metricas, reprodutibilidade e o dataset sintetico
determinístico (Fase 11 do gate). Os testes adversariais dedicados de
vazamento (Fase 10, A-E) estao em ``tests/test_backtest_leakage.py``.

Herméticos: nenhuma rede, nenhuma escrita em CSV/SQLite reais -- tudo em
memoria, com dataset sintetico.
"""
from __future__ import annotations

import dataclasses

import pytest

from src.backtest.contracts import (
    BacktestResult,
    ContestSnapshot,
    FrozenTicket,
    LeakageError,
    PredictionBatch,
    ResultNotYetOpenedError,
    SealedContestResult,
)
from src.backtest.engine_adapter import ReferenceRandomEngine
from src.backtest.fingerprint import data_fingerprint
from src.backtest.harness import (
    load_contests_from_dataframe,
    predict_for_contest,
    reproducibility_record,
    run_walk_forward,
)
from src.backtest.metrics import aggregate, score_batch


def _concurso_sintetico(numero: int) -> ContestSnapshot:
    """Concurso sintetico determinístico (formula simples, sem qualquer
    pretensao estatistica -- so para ter dados variados e reprodutíveis)."""
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


def _base_sintetica(quantidade: int = 30) -> list[ContestSnapshot]:
    return [_concurso_sintetico(n) for n in range(1, quantidade + 1)]


# --- Contratos puros -------------------------------------------------------


def test_contest_snapshot_valida_dezenas_via_contrato_lf02() -> None:
    with pytest.raises(ValueError):
        ContestSnapshot(number=1, date="01/01/2026", numbers=tuple(range(1, 15)))  # 14 dezenas


def test_contest_snapshot_rejeita_numero_nao_positivo() -> None:
    with pytest.raises(ValueError):
        ContestSnapshot(number=0, date="01/01/2026", numbers=tuple(range(1, 16)))


def test_prediction_batch_e_imutavel() -> None:
    batch = predict_for_contest(
        ReferenceRandomEngine(), history=_base_sintetica(10), target_contest=11, number_of_tickets=3, seed=1
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        batch.target_contest = 999  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        batch.tickets = ()  # type: ignore[misc]


def test_prediction_batch_rejeita_history_max_maior_ou_igual_ao_alvo() -> None:
    with pytest.raises(LeakageError):
        PredictionBatch(
            target_contest=10,
            history_max_contest=10,
            engine_name="x",
            engine_version="1",
            seed=None,
            number_of_tickets=1,
            tickets=(FrozenTicket(label="t", numbers=tuple(range(1, 16))),),
            generated_at="2026-01-01T00:00:00+00:00",
            data_fingerprint="abc",
        )


def test_sealed_contest_result_bloqueia_acesso_antes_de_open() -> None:
    sealed = SealedContestResult(_concurso_sintetico(5))
    with pytest.raises(ResultNotYetOpenedError):
        sealed.peek()
    assert sealed.is_opened is False
    resultado = sealed.open()
    assert resultado.number == 5
    assert sealed.is_opened is True
    assert sealed.peek() == resultado


# --- Freeze-before-open (Fase 5) ------------------------------------------


def test_predict_for_contest_congela_batch_sem_acessar_resultado_futuro() -> None:
    base = _base_sintetica(30)
    history = [c for c in base if c.number < 25]
    batch = predict_for_contest(ReferenceRandomEngine(), history, target_contest=25, number_of_tickets=4, seed=7)
    assert batch.target_contest == 25
    assert batch.history_max_contest == 24
    assert len(batch.tickets) == 4


def test_score_batch_so_e_possivel_depois_do_freeze() -> None:
    base = _base_sintetica(30)
    history = [c for c in base if c.number < 25]
    alvo = next(c for c in base if c.number == 25)
    batch = predict_for_contest(ReferenceRandomEngine(), history, target_contest=25, number_of_tickets=4, seed=7)
    # so agora, com o batch ja congelado, o resultado e "aberto" e comparado.
    resultado = score_batch(batch, alvo)
    assert isinstance(resultado, BacktestResult)
    assert 0 <= resultado.max_hits <= 15


def test_score_batch_rejeita_target_result_de_concurso_errado() -> None:
    base = _base_sintetica(30)
    history = [c for c in base if c.number < 25]
    batch = predict_for_contest(ReferenceRandomEngine(), history, target_contest=25, number_of_tickets=4, seed=7)
    resultado_errado = next(c for c in base if c.number == 26)
    with pytest.raises(ValueError, match="target_contest"):
        score_batch(batch, resultado_errado)


# --- Engine de referencia + harness completo (Fase 11: sintetico 1..30) --


def test_run_walk_forward_sobre_dataset_sintetico_1_a_30() -> None:
    base = _base_sintetica(30)
    engine = ReferenceRandomEngine()
    alvos = list(range(21, 31))
    resultados = run_walk_forward(engine, base, alvos, number_of_tickets=5, seed=42)
    assert len(resultados) == 10
    for resultado, alvo in zip(resultados, alvos):
        assert resultado.batch.target_contest == alvo
        assert resultado.batch.history_max_contest == alvo - 1
        assert resultado.target_result.number == alvo
        assert len(resultado.batch.tickets) == 5


def test_run_walk_forward_falha_se_concurso_alvo_ausente_de_all_contests() -> None:
    base = _base_sintetica(10)
    with pytest.raises(ValueError, match="nao esta em all_contests"):
        run_walk_forward(ReferenceRandomEngine(), base, [999], number_of_tickets=3, seed=1)


def test_load_contests_from_dataframe_ordena_e_valida() -> None:
    import pandas as pd

    linhas = []
    for numero in (3, 1, 2):
        concurso = _concurso_sintetico(numero)
        linha = {"Concurso": concurso.number, "Data": concurso.date}
        for i, d in enumerate(concurso.numbers, start=1):
            linha[f"Bola{i}"] = d
        linhas.append(linha)
    df = pd.DataFrame(linhas)
    contests = load_contests_from_dataframe(df)
    assert [c.number for c in contests] == [1, 2, 3]


# --- Metricas agregadas (Fase 8) ------------------------------------------


def test_aggregate_metrics_sobre_resultados_sinteticos() -> None:
    base = _base_sintetica(30)
    resultados = run_walk_forward(ReferenceRandomEngine(), base, list(range(21, 31)), number_of_tickets=5, seed=42)
    agregado = aggregate(resultados)
    assert agregado.contests_evaluated == 10
    assert agregado.total_tickets == 50
    assert sum(agregado.hit_distribution.values()) == 50
    assert agregado.frequency_ge[11] >= agregado.frequency_ge[12] >= agregado.frequency_ge[13]
    assert agregado.frequency_eq15 == agregado.hit_distribution[15]


def test_aggregate_rejeita_lista_vazia() -> None:
    with pytest.raises(ValueError):
        aggregate([])


# --- Baseline aleatorio justo (Fase 7) ------------------------------------


def test_baseline_gera_exatamente_o_mesmo_numero_de_tickets_do_motor() -> None:
    from src.backtest.random_baseline import compute_fair_baseline

    base = _base_sintetica(30)
    history = [c for c in base if c.number < 25]
    batch_motor = predict_for_contest(ReferenceRandomEngine(), history, target_contest=25, number_of_tickets=7, seed=1)
    batch_baseline = compute_fair_baseline(batch_motor, history, seed=999)
    assert batch_baseline.number_of_tickets == batch_motor.number_of_tickets == 7
    assert batch_baseline.target_contest == batch_motor.target_contest
    assert batch_baseline.history_max_contest == batch_motor.history_max_contest
    for ticket in batch_baseline.tickets:
        assert len(ticket.numbers) == 15
        assert len(set(ticket.numbers)) == 15
        assert all(1 <= d <= 25 for d in ticket.numbers)


# --- Reprodutibilidade (Fase 9) -------------------------------------------


def test_data_fingerprint_e_deterministico() -> None:
    base = _base_sintetica(15)
    assert data_fingerprint(base) == data_fingerprint(base)
    assert data_fingerprint(base) == data_fingerprint(list(base))


def test_data_fingerprint_muda_se_historico_mudar() -> None:
    base = _base_sintetica(15)
    outra = _base_sintetica(16)
    assert data_fingerprint(base) != data_fingerprint(outra)


def test_duas_execucoes_identicas_produzem_resultados_idênticos() -> None:
    base = _base_sintetica(30)
    alvos = list(range(21, 31))
    r1 = run_walk_forward(ReferenceRandomEngine(), base, alvos, number_of_tickets=5, seed=42)
    r2 = run_walk_forward(ReferenceRandomEngine(), base, alvos, number_of_tickets=5, seed=42)
    assert len(r1) == len(r2)
    for a, b in zip(r1, r2):
        assert a.batch.tickets == b.batch.tickets
        assert a.max_hits == b.max_hits
        assert a.mean_hits == b.mean_hits
        assert a.hit_distribution == b.hit_distribution
        assert a.batch.data_fingerprint == b.batch.data_fingerprint


def test_execucoes_com_seed_diferente_produzem_tickets_diferentes() -> None:
    base = _base_sintetica(30)
    alvos = list(range(21, 31))
    r1 = run_walk_forward(ReferenceRandomEngine(), base, alvos, number_of_tickets=5, seed=42)
    r2 = run_walk_forward(ReferenceRandomEngine(), base, alvos, number_of_tickets=5, seed=43)
    assert any(a.batch.tickets != b.batch.tickets for a, b in zip(r1, r2))


def test_reproducibility_record_contem_campos_obrigatorios() -> None:
    base = _base_sintetica(30)
    alvos = list(range(21, 31))
    engine = ReferenceRandomEngine()
    resultados = run_walk_forward(engine, base, alvos, number_of_tickets=5, seed=42)
    registro = reproducibility_record(
        engine, seed=42, number_of_tickets=5, contest_numbers=alvos, history_fingerprint=resultados[0].batch.data_fingerprint
    )
    for campo in ("git_commit_sha", "engine_name", "engine_version", "seed", "number_of_tickets", "contest_range", "timestamp", "data_fingerprint"):
        assert campo in registro
    assert registro["engine_name"] == "REFERENCE_RANDOM_ENGINE"
    assert registro["seed"] == 42
    assert registro["contest_range"] == [21, 30]
