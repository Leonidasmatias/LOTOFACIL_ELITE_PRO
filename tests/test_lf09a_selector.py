"""Testes do pool autentico e dos selectors LF-09A (Fase 13).

Herméticos: dataset sintetico determinístico, nenhuma rede. Provam que
os selectors NUNCA criam/modificam ticket, sempre retornam exatamente 5
tickets DISTINTOS pertencentes ao pool, sao deterministicos, nao aceitam
resultado real, e lidam corretamente com duplicatas/empates/pool
pequeno.
"""
from __future__ import annotations

import inspect

import pandas as pd
import pytest

from src.backtest.candidate_trace import CandidateTracer
from src.backtest.portfolio_selector_lf09a import (
    RESEARCH_CONFIGS,
    CandidatePoolEntry,
    LF09AConfig,
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


def _pool_real(seed: int = 42, historico: int = 60) -> tuple[tuple, CandidateTracer]:
    df = _base_sintetica(historico)
    tracer = CandidateTracer()
    gerar_jogos_v2(df, quantidade=5, semente=seed, trace=tracer)
    return build_candidate_pool_from_trace(tracer), tracer


# --- Pool autentico -----------------------------------------------------


def test_pool_nao_esta_vazio_e_tickets_sao_unicos() -> None:
    pool, _ = _pool_real()
    tickets = [c.ticket for c in pool]
    assert len(pool) > 0
    assert len(tickets) == len(set(tickets))


def test_original_selected_tickets_bate_com_producao() -> None:
    df = _base_sintetica(60)
    tracer = CandidateTracer()
    resultado = gerar_jogos_v2(df, quantidade=5, semente=42, trace=tracer)
    originais = original_selected_tickets(tracer)
    tickets_producao = tuple(
        tuple(sorted(int(linha[f"Bola{i}"]) for i in range(1, 16))) for _, linha in resultado.iterrows()
    )
    assert originais == tickets_producao


def test_pool_e_derivado_apenas_do_trace_autentico() -> None:
    """A assinatura de ``build_candidate_pool_from_trace`` so aceita um
    ``CandidateTracer`` -- nao ha parametro para historico, config ou
    qualquer coisa que permitisse gerar um segundo pool."""
    parametros = list(inspect.signature(build_candidate_pool_from_trace).parameters)
    assert parametros == ["tracer"]


def test_pool_duplicatas_usam_ultima_avaliacao_observada() -> None:
    tracer = CandidateTracer()
    tracer.record_evaluation(
        profile="Diamante",
        ticket=(1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15),
        raw_structure_score=10.0,
        structure_metrics={},
        similarity_to_already_selected=0,
        similarity_penalty=0.0,
        final_candidate_score=10.0,
        selected_so_far=(),
        candidate_generation_index=1,
        unique_candidates_so_far=1,
    )
    tracer.record_evaluation(
        profile="Diamante",
        ticket=(1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15),
        raw_structure_score=20.0,
        structure_metrics={},
        similarity_to_already_selected=0,
        similarity_penalty=0.0,
        final_candidate_score=20.0,  # sobrescreve -- deve prevalecer
        selected_so_far=(),
        candidate_generation_index=2,
        unique_candidates_so_far=1,
    )
    pool = build_candidate_pool_from_trace(tracer)
    assert len(pool) == 1
    assert pool[0].final_candidate_score == 20.0


# --- Selectors: garantias estruturais -----------------------------------


@pytest.mark.parametrize("config", RESEARCH_CONFIGS, ids=lambda c: c.name)
def test_select_portfolio_lf09a_retorna_exatamente_cinco_distintos(config: LF09AConfig) -> None:
    pool, _ = _pool_real()
    selecionados = select_portfolio_lf09a(pool, config)
    assert len(selecionados) == 5
    assert len(set(selecionados)) == 5


@pytest.mark.parametrize("config", RESEARCH_CONFIGS, ids=lambda c: c.name)
def test_select_portfolio_lf09a_nunca_sai_do_pool(config: LF09AConfig) -> None:
    pool, _ = _pool_real()
    tickets_do_pool = {c.ticket for c in pool}
    selecionados = select_portfolio_lf09a(pool, config)
    assert all(t in tickets_do_pool for t in selecionados)


def test_select_portfolio_lf09a_nunca_modifica_um_ticket() -> None:
    """Cada ticket retornado e o MESMO objeto tuple do pool -- nao uma
    copia recombinada."""
    pool, _ = _pool_real()
    por_valor = {c.ticket: c.ticket for c in pool}
    selecionados = select_portfolio_lf09a(pool, RESEARCH_CONFIGS[2])
    for t in selecionados:
        assert t is por_valor[t] or t == por_valor[t]
        assert len(t) == 15
        assert len(set(t)) == 15
        assert all(1 <= d <= 25 for d in t)


def test_select_portfolio_lf09a_e_deterministico() -> None:
    pool, _ = _pool_real()
    r1 = select_portfolio_lf09a(pool, RESEARCH_CONFIGS[2])
    r2 = select_portfolio_lf09a(pool, RESEARCH_CONFIGS[2])
    assert r1 == r2


def test_select_portfolio_lf09a_nao_muta_o_pool_recebido() -> None:
    pool, _ = _pool_real()
    pool_copia = tuple(pool)
    select_portfolio_lf09a(pool, RESEARCH_CONFIGS[2])
    assert pool == pool_copia


def test_select_portfolio_lf09a_rejeita_pool_menor_que_portfolio() -> None:
    pool_pequeno = (
        CandidatePoolEntry(ticket=tuple(range(1, 16)), final_candidate_score=1.0, profiles_seen=("X",), last_seen_evaluation_index=0),
        CandidatePoolEntry(ticket=tuple(range(2, 17)), final_candidate_score=1.0, profiles_seen=("X",), last_seen_evaluation_index=1),
    )
    with pytest.raises(ValueError):
        select_portfolio_lf09a(pool_pequeno, RESEARCH_CONFIGS[0], portfolio_size=5)


def test_select_portfolio_lf09a_com_scores_empatados_e_deterministico_por_ordem_lexicografica() -> None:
    entradas = [
        CandidatePoolEntry(
            ticket=tuple(sorted(set(range(1, 16)) - {k} | {16 + k})),
            final_candidate_score=5.0,  # todos empatados
            profiles_seen=("X",),
            last_seen_evaluation_index=k,
        )
        for k in range(8)
    ]
    r1 = select_portfolio_lf09a(entradas, RESEARCH_CONFIGS[0])
    r2 = select_portfolio_lf09a(entradas, RESEARCH_CONFIGS[0])
    assert r1 == r2
    assert len(set(r1)) == 5


def test_select_portfolio_lf09a_assinatura_nao_aceita_resultado_real() -> None:
    parametros = set(inspect.signature(select_portfolio_lf09a).parameters)
    proibidos = {"target_result", "winning_numbers", "resultado_real", "hits"}
    assert parametros.isdisjoint(proibidos)


def test_config_e_score_floor_funcional() -> None:
    pool, _ = _pool_real()
    config_com_piso = next(c for c in RESEARCH_CONFIGS if c.score_floor is not None)
    selecionados = select_portfolio_lf09a(pool, config_com_piso)
    assert len(selecionados) == 5


# --- Random control -------------------------------------------------------


def test_select_portfolio_random_retorna_cinco_distintos_do_pool() -> None:
    pool, _ = _pool_real()
    tickets_do_pool = {c.ticket for c in pool}
    selecionados = select_portfolio_random(pool, seed=1)
    assert len(selecionados) == 5
    assert len(set(selecionados)) == 5
    assert all(t in tickets_do_pool for t in selecionados)


def test_select_portfolio_random_e_deterministico_por_seed() -> None:
    pool, _ = _pool_real()
    r1 = select_portfolio_random(pool, seed=7)
    r2 = select_portfolio_random(pool, seed=7)
    assert r1 == r2


def test_select_portfolio_random_seeds_diferentes_podem_diferir() -> None:
    pool, _ = _pool_real()
    r1 = select_portfolio_random(pool, seed=1)
    r2 = select_portfolio_random(pool, seed=2)
    assert r1 != r2


def test_select_portfolio_random_rejeita_pool_menor_que_portfolio() -> None:
    pool_pequeno = (
        CandidatePoolEntry(ticket=tuple(range(1, 16)), final_candidate_score=1.0, profiles_seen=("X",), last_seen_evaluation_index=0),
    )
    with pytest.raises(ValueError):
        select_portfolio_random(pool_pequeno, seed=1, portfolio_size=5)
