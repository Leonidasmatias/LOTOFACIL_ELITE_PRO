"""Teste de vazamento (LF-09A) -- equivalente ao teste E do LF-04.

Prova que a selecao de portfolio (pool + todos os selectors) e
COMPLETAMENTE independente de qualquer resultado futuro: a mesma
combinacao (historico, seed, config) produz sempre o MESMO pool e as
MESMAS selecoes, ainda que dois resultados-alvo diferentes e
incompativeis sejam "revelados" depois."""
from __future__ import annotations

import pandas as pd

from src.backtest.candidate_trace import CandidateTracer
from src.backtest.portfolio_selector_lf09a import (
    RESEARCH_CONFIGS,
    build_candidate_pool_from_trace,
    original_selected_tickets,
    select_portfolio_lf09a,
    select_portfolio_random,
)
from src.motor_elite_v2 import gerar_jogos_v2


def _concurso_sintetico(numero: int) -> dict:
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
    linha = {"Concurso": numero, "Data": f"{(numero % 28) + 1:02d}/01/2026"}
    for posicao, dezena in enumerate(sorted(usadas), start=1):
        linha[f"Bola{posicao}"] = dezena
    return linha


def _base_sintetica(quantidade: int) -> pd.DataFrame:
    return pd.DataFrame([_concurso_sintetico(n) for n in range(1, quantidade + 1)])


def _score_contra_resultado(ticket: tuple[int, ...], resultado: tuple[int, ...]) -> int:
    return len(set(ticket) & set(resultado))


def test_selecao_completa_independe_de_qual_resultado_e_revelado_depois() -> None:
    df = _base_sintetica(60)

    # Fase de PREDICAO: historico/seed/config fixos -- NENHUM resultado
    # e consultado aqui.
    tracer = CandidateTracer()
    gerar_jogos_v2(df, quantidade=5, semente=42, trace=tracer)
    pool = build_candidate_pool_from_trace(tracer)
    original = original_selected_tickets(tracer)
    selecoes_lf09a = {cfg.name: select_portfolio_lf09a(pool, cfg) for cfg in RESEARCH_CONFIGS}
    selecao_random = select_portfolio_random(pool, seed=20260909)

    # SOMENTE AGORA "revelamos" dois resultados diferentes e
    # incompativeis -- a selecao acima ja estava congelada antes disso.
    resultado_a = tuple(sorted(range(1, 16)))
    resultado_b = tuple(sorted(range(11, 26)))
    assert resultado_a != resultado_b

    score_original_a = sum(_score_contra_resultado(t, resultado_a) for t in original)
    score_original_b = sum(_score_contra_resultado(t, resultado_b) for t in original)
    assert score_original_a != score_original_b  # os SCORES mudam (esperado)

    # ...mas repetir a predicao do zero (mesmo historico/seed/config)
    # produz o MESMO pool e as MESMAS selecoes -- provando que nenhuma
    # das duas rodadas de scoring acima poderia ter influenciado a
    # selecao (ela ja tinha acontecido, de forma identica, antes).
    tracer_repeticao = CandidateTracer()
    gerar_jogos_v2(df, quantidade=5, semente=42, trace=tracer_repeticao)
    pool_repeticao = build_candidate_pool_from_trace(tracer_repeticao)
    original_repeticao = original_selected_tickets(tracer_repeticao)
    selecoes_lf09a_repeticao = {cfg.name: select_portfolio_lf09a(pool_repeticao, cfg) for cfg in RESEARCH_CONFIGS}
    selecao_random_repeticao = select_portfolio_random(pool_repeticao, seed=20260909)

    assert pool == pool_repeticao
    assert original == original_repeticao
    assert selecoes_lf09a == selecoes_lf09a_repeticao
    assert selecao_random == selecao_random_repeticao


def test_gerar_jogos_v2_e_selectors_nao_tem_parametro_de_resultado_alvo() -> None:
    import inspect

    from src.backtest.portfolio_selector_lf09a import select_portfolio_lf09a, select_portfolio_random

    proibidos = {"target_result", "winning_numbers", "resultado_real", "resultado_alvo", "future_contests"}
    for funcao in (gerar_jogos_v2, select_portfolio_lf09a, select_portfolio_random):
        assert proibidos.isdisjoint(inspect.signature(funcao).parameters)
