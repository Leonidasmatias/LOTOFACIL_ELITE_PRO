"""Testes do mecanismo B -- captura pre-filtro (LF-09D, Pendencia 1).

Provam RNG invariance direta (a instrumentacao nao consome/altera RNG
nem muda o output do motor), reconstrucao correta dos tickets brutos, e
leakage/determinismo."""
from __future__ import annotations

import pytest

from src.backtest.contracts import ContestSnapshot, LeakageError
from src.backtest.engine_adapter import _history_para_dataframe
from src.backtest.structural_filter_capture import capturar_draws_brutos, run_structural_filter_target
from src.motor_elite_v2 import gerar_jogos_v2
from src.validacao_jogos import validar_jogo


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


def test_run_structural_filter_target_rejeita_alvo_ausente() -> None:
    base = _base_sintetica(40)
    with pytest.raises(ValueError, match="nao esta em all_contests"):
        run_structural_filter_target(base, target_contest=9999, motor_base_seed=7_000_000)


def test_run_structural_filter_target_leakageerror_herdado() -> None:
    base = _base_sintetica(40)
    from src.backtest.engine_adapter import ReferenceRandomEngine
    from src.backtest.harness import predict_for_contest

    with pytest.raises(LeakageError):
        predict_for_contest(ReferenceRandomEngine(), base, 35, 5, 1)


def test_run_structural_filter_target_e_reprodutivel() -> None:
    base = _base_sintetica(60)
    r1 = run_structural_filter_target(base, target_contest=50, motor_base_seed=7_000_000)
    r2 = run_structural_filter_target(base, target_contest=50, motor_base_seed=7_000_000)
    assert r1 == r2


def test_todos_aceitos_passam_em_validar_jogo() -> None:
    base = _base_sintetica(60)
    r = run_structural_filter_target(base, target_contest=50, motor_base_seed=7_000_000)
    ultimo = frozenset(max([c for c in base if c.number < 50], key=lambda c: c.number).numbers)
    for c in r.raw_candidates:
        if c.accepted:
            validar_jogo(c.ticket, ultimo_concurso=ultimo)  # nao deve levantar


def test_algum_rejeitado_existe_e_falha_em_validar_jogo() -> None:
    base = _base_sintetica(60)
    r = run_structural_filter_target(base, target_contest=50, motor_base_seed=7_000_000)
    rejeitados = [c for c in r.raw_candidates if not c.accepted]
    assert len(rejeitados) > 0
    ultimo = frozenset(max([c for c in base if c.number < 50], key=lambda c: c.number).numbers)
    with pytest.raises(ValueError):
        validar_jogo(rejeitados[0].ticket, ultimo_concurso=ultimo)


def test_contagem_de_aceitos_bate_com_post_filter_hits() -> None:
    base = _base_sintetica(60)
    r = run_structural_filter_target(base, target_contest=50, motor_base_seed=7_000_000)
    aceitos = sum(1 for c in r.raw_candidates if c.accepted)
    assert aceitos == len(r.post_filter_hits)


def test_hits_no_intervalo_valido() -> None:
    base = _base_sintetica(60)
    r = run_structural_filter_target(base, target_contest=50, motor_base_seed=7_000_000)
    assert all(0 <= c.hits <= 15 for c in r.raw_candidates)


# --- RNG invariance direta ----------------------------------------------------


def test_capturar_draws_brutos_nao_altera_output_do_motor() -> None:
    """Comparacao DIRETA: mesmo historico/seed, COM e SEM o context
    manager de captura ativo -- outputs devem ser byte-identicos."""
    base = _base_sintetica(60)
    history = [c for c in base if c.number < 50]
    df_hist = _history_para_dataframe(history)

    r_sem_captura = gerar_jogos_v2(df_hist, quantidade=5, semente=7000050)
    with capturar_draws_brutos():
        r_com_captura = gerar_jogos_v2(df_hist, quantidade=5, semente=7000050)

    assert r_sem_captura.equals(r_com_captura)


def test_capturar_draws_brutos_restaura_random_choices_original() -> None:
    """Apos o context manager sair, ``random.Random.choices`` deve
    voltar a ser exatamente o metodo original da stdlib."""
    import random

    original_antes = random.Random.choices
    with capturar_draws_brutos():
        pass
    assert random.Random.choices is original_antes


def test_numero_de_escolhas_capturadas_e_multiplo_de_15() -> None:
    base = _base_sintetica(60)
    history = [c for c in base if c.number < 50]
    df_hist = _history_para_dataframe(history)
    with capturar_draws_brutos() as escolhas:
        gerar_jogos_v2(df_hist, quantidade=5, semente=7000050)
    assert len(escolhas) % 15 == 0
    assert len(escolhas) > 0


def test_tickets_brutos_reconstruidos_tem_15_dezenas_validas() -> None:
    base = _base_sintetica(60)
    r = run_structural_filter_target(base, target_contest=50, motor_base_seed=7_000_000)
    for c in r.raw_candidates:
        assert len(c.ticket) == 15
        assert len(set(c.ticket)) == 15
        assert all(1 <= d <= 25 for d in c.ticket)


def test_assinatura_nao_aceita_resultado_real() -> None:
    import inspect

    proibidos = {"target_result", "winning_numbers", "resultado_real", "resultado_alvo"}
    assert proibidos.isdisjoint(inspect.signature(run_structural_filter_target).parameters)
