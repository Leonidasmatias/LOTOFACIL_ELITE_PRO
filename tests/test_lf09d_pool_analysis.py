"""Testes das metricas puras de analise de pool (LF-09D, Fase 24)."""
from __future__ import annotations

import pytest

from src.backtest.pool_analysis import (
    best_candidate_per_profile,
    incremental_portfolio_metrics,
    jaccard_pool,
    mean_pairwise_intersection,
    number_coverage,
    pool_hit_stats,
    selection_with_sequential_gate,
    selection_without_diversity_gate,
)


def test_pool_hit_stats_exato() -> None:
    hits = [8, 9, 9, 10, 11, 13]
    st = pool_hit_stats(hits)
    assert st.n == 6
    assert st.mean_hits == pytest.approx(60 / 6)
    assert st.median_hits == pytest.approx(9.5)
    assert st.max_hits == 13
    assert st.p_ge[10] == pytest.approx(3 / 6)
    assert st.p_ge[11] == pytest.approx(2 / 6)
    assert st.p_ge[13] == pytest.approx(1 / 6)
    assert st.p_ge[14] == pytest.approx(0.0)


def test_pool_hit_stats_rejeita_vazio() -> None:
    with pytest.raises(ValueError):
        pool_hit_stats([])


def test_jaccard_pool_identicos() -> None:
    pool = [(1, 2, 3), (4, 5, 6)]
    assert jaccard_pool(pool, pool) == pytest.approx(1.0)


def test_jaccard_pool_disjuntos() -> None:
    a = [(1, 2, 3)]
    b = [(4, 5, 6)]
    assert jaccard_pool(a, b) == pytest.approx(0.0)


def test_jaccard_pool_parcial() -> None:
    a = [(1, 2, 3), (4, 5, 6)]
    b = [(1, 2, 3), (7, 8, 9)]
    # intersecao={ (1,2,3) } tam1; uniao tam3 -> 1/3
    assert jaccard_pool(a, b) == pytest.approx(1 / 3)


def test_number_coverage_exato() -> None:
    pool = [(1, 2, 3), (3, 4, 5)]
    assert number_coverage(pool) == 5


def test_incremental_portfolio_metrics_exato() -> None:
    tickets = [(1, 2, 3), (3, 4, 5), (6, 7, 8)]
    hits = [8, 10, 9]
    passos = incremental_portfolio_metrics(tickets, hits)
    assert len(passos) == 3
    assert passos[0].k == 1
    assert passos[0].best_of_k == 8
    assert passos[0].unique_coverage_k == 3
    assert passos[1].best_of_k == 10  # max(8,10)
    assert passos[1].marginal_best_gain == 2
    assert passos[1].unique_coverage_k == 5  # {1,2,3,4,5}
    assert passos[1].marginal_coverage_gain == 2
    assert passos[2].best_of_k == 10  # max(8,10,9)
    assert passos[2].marginal_best_gain == 0
    assert passos[2].unique_coverage_k == 8
    assert passos[2].marginal_coverage_gain == 3


def test_incremental_portfolio_metrics_rejeita_tamanhos_diferentes() -> None:
    with pytest.raises(ValueError):
        incremental_portfolio_metrics([(1, 2)], [1, 2])


def test_best_candidate_per_profile() -> None:
    tickets_por_perfil = {"A": [(1, 2), (3, 4)], "B": [(5, 6)]}
    hits_lookup: dict[tuple[int, ...], int] = {(1, 2): 8, (3, 4): 12, (5, 6): 9}
    resultado = best_candidate_per_profile(tickets_por_perfil, hits_lookup)
    assert resultado["A"] == ((3, 4), 12)
    assert resultado["B"] == ((5, 6), 9)


def test_selection_without_diversity_gate_escolhe_maior_score() -> None:
    pool_por_perfil = {
        "A": [((1, 2, 3), 10.0), ((4, 5, 6), 15.0), ((7, 8, 9), 12.0)],
    }
    resultado = selection_without_diversity_gate(pool_por_perfil)
    assert resultado["A"] == (4, 5, 6)


def test_selection_without_diversity_gate_desempate_lexicografico() -> None:
    pool_por_perfil = {
        "A": [((5, 6, 7), 10.0), ((1, 2, 3), 10.0)],
    }
    resultado = selection_without_diversity_gate(pool_por_perfil)
    # ambos empatados em score -- desempate deve ser deterministico
    assert resultado["A"] in [(5, 6, 7), (1, 2, 3)]
    # repetir produz o mesmo resultado (determinismo)
    assert selection_without_diversity_gate(pool_por_perfil)["A"] == resultado["A"]


def test_mean_pairwise_intersection_exato() -> None:
    a = tuple(range(1, 16))
    b = tuple(range(1, 16))
    c = tuple(range(11, 26))
    # pares: (a,b)=15, (a,c)=5, (b,c)=5 -> media=25/3
    assert mean_pairwise_intersection([a, b, c]) == pytest.approx(25 / 3)


def test_mean_pairwise_intersection_rejeita_um_ticket() -> None:
    with pytest.raises(ValueError):
        mean_pairwise_intersection([(1, 2, 3)])


# --- selection_with_sequential_gate (Pendencia 2 / mecanismo G) -------------


def test_selection_with_sequential_gate_por_final_score_reproduz_producao_real() -> None:
    """Reconstrucao critica: usar final_candidate_score (a MESMA
    quantidade que producao usa) com o MESMO gate sequencial deve
    reproduzir EXATAMENTE a selecao real do motor -- prova que a
    reconstrucao esta correta antes de trocar para raw_score."""
    import pandas as pd

    from src.backtest.candidate_trace import CandidateTracer
    from src.motor_elite_v2 import PERFIS_V2, gerar_jogos_v2

    def _concurso(numero: int) -> dict:
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

    df = pd.DataFrame([_concurso(n) for n in range(1, 61)])
    tracer = CandidateTracer()
    gerar_jogos_v2(df, quantidade=5, semente=42, trace=tracer)

    pool_por_perfil_final = [
        (perfil, [(e.ticket, e.final_candidate_score) for e in tracer.evaluations_for_profile(perfil)])
        for perfil in PERFIS_V2
    ]
    reconstruido = selection_with_sequential_gate(pool_por_perfil_final, diferenca_minima=3)
    reais = [(resumo.profile, resumo.selected_ticket) for resumo in tracer.profile_summaries]
    assert reconstruido == reais


def test_selection_with_sequential_gate_deterministico() -> None:
    pool_por_perfil = [
        ("A", [((1, 2, 3), 10.0), ((4, 5, 6), 8.0)]),
        ("B", [((1, 2, 7), 9.0), ((8, 9, 10), 5.0)]),
    ]
    r1 = selection_with_sequential_gate(pool_por_perfil, diferenca_minima=2)
    r2 = selection_with_sequential_gate(pool_por_perfil, diferenca_minima=2)
    assert r1 == r2


def test_selection_with_sequential_gate_aplica_gate_entre_perfis() -> None:
    # perfil A escolhe (1,2,3); perfil B teria (1,2,4) como melhor mas
    # diferenca com (1,2,3) e so 1 (<2) -- gate deve forcar (5,6,7).
    pool_por_perfil = [
        ("A", [((1, 2, 3), 10.0)]),
        ("B", [((1, 2, 4), 9.0), ((5, 6, 7), 8.0)]),
    ]
    resultado = selection_with_sequential_gate(pool_por_perfil, diferenca_minima=2)
    assert resultado == [("A", (1, 2, 3)), ("B", (5, 6, 7))]
