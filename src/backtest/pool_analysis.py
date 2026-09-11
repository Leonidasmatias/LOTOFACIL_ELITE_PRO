"""Metricas puras de analise de pool (LF-09D).

Operam sobre pools/tickets ja existentes (autenticos ou de controle) e
seus hits ja calculados -- nenhuma funcao aqui gera, seleciona ou
modifica ticket para producao. Reusa ``ticket_metrics`` (LF-09A) sem
duplicar formulas ja testadas.
"""
from __future__ import annotations

from dataclasses import dataclass
import statistics
from typing import Mapping, Sequence

from .ticket_metrics import intersection_size

Ticket = tuple[int, ...]

FAIXAS = (10, 11, 12, 13, 14, 15)


@dataclass(frozen=True, slots=True)
class PoolHitStats:
    n: int
    mean_hits: float
    median_hits: float
    max_hits: int
    p_ge: dict[int, float]


def pool_hit_stats(hits: Sequence[int]) -> PoolHitStats:
    if not hits:
        raise ValueError("Pool vazio nao tem estatisticas de hits.")
    n = len(hits)
    return PoolHitStats(
        n=n,
        mean_hits=statistics.fmean(hits),
        median_hits=statistics.median(hits),
        max_hits=max(hits),
        p_ge={faixa: sum(1 for h in hits if h >= faixa) / n for faixa in FAIXAS},
    )


def jaccard_pool(pool_a: Sequence[Ticket], pool_b: Sequence[Ticket]) -> float:
    """Jaccard EM NIVEL DE TICKET (nao de dezena): |A ∩ B| / |A ∪ B|
    tratando cada pool como um CONJUNTO de tickets distintos."""
    set_a, set_b = set(pool_a), set(pool_b)
    uniao = set_a | set_b
    if not uniao:
        return 0.0
    return len(set_a & set_b) / len(uniao)


def number_coverage(pool: Sequence[Ticket]) -> int:
    """Quantidade de dezenas distintas (1..25) que aparecem em ALGUM
    ticket do pool."""
    cobertas: set[int] = set()
    for ticket in pool:
        cobertas |= set(ticket)
    return len(cobertas)


@dataclass(frozen=True, slots=True)
class IncrementalStep:
    k: int
    best_of_k: int
    mean_of_k: float
    unique_coverage_k: int
    marginal_coverage_gain: int
    marginal_best_gain: int


def incremental_portfolio_metrics(tickets_em_ordem: Sequence[Ticket], hits_em_ordem: Sequence[int]) -> list[IncrementalStep]:
    """Metricas construidas INCREMENTALMENTE na ordem REAL de selecao
    (perfil 1, perfil 1+2, ...) -- nao testa reordenacao (exigiria
    contrafactual de RNG, fora de escopo)."""
    if len(tickets_em_ordem) != len(hits_em_ordem):
        raise ValueError("tickets e hits precisam ter o mesmo tamanho.")
    passos = []
    cobertura_anterior = 0
    melhor_anterior = 0
    for k in range(1, len(tickets_em_ordem) + 1):
        tickets_ate_k = tickets_em_ordem[:k]
        hits_ate_k = hits_em_ordem[:k]
        cobertura = number_coverage(tickets_ate_k)
        melhor = max(hits_ate_k)
        passos.append(
            IncrementalStep(
                k=k,
                best_of_k=melhor,
                mean_of_k=statistics.fmean(hits_ate_k),
                unique_coverage_k=cobertura,
                marginal_coverage_gain=cobertura - cobertura_anterior,
                marginal_best_gain=melhor - melhor_anterior,
            )
        )
        cobertura_anterior = cobertura
        melhor_anterior = melhor
    return passos


def best_candidate_per_profile(tickets_por_perfil: Mapping[str, Sequence[Ticket]], hits_lookup: Mapping[Ticket, int]) -> dict[str, tuple[Ticket, int]]:
    """Para cada perfil, o ticket com MAIOR hits dentro do seu proprio
    pool (oracle retrospectivo, so para medir complementaridade --
    nunca usado para selecao)."""
    resultado = {}
    for perfil, tickets in tickets_por_perfil.items():
        melhor = max(tickets, key=lambda t: hits_lookup[t])
        resultado[perfil] = (melhor, hits_lookup[melhor])
    return resultado


def selection_without_diversity_gate(
    pool_por_perfil: Mapping[str, Sequence[tuple[Ticket, float]]],
) -> dict[str, Ticket]:
    """Contrafactual: para cada perfil, o ticket de MAIOR
    final_candidate_score, IGNORANDO o gate rigido de diversidade entre
    perfis (mas ainda respeitando o desempate lexicografico, igual a
    producao). Nao gera nenhum ticket novo -- escolhe apenas entre os
    JA existentes no pool autentico daquele perfil."""
    resultado = {}
    for perfil, candidatos in pool_por_perfil.items():
        melhor = max(candidatos, key=lambda par: (par[1], tuple(-d for d in par[0])))
        resultado[perfil] = melhor[0]
    return resultado


def selection_with_sequential_gate(
    pool_por_perfil_em_ordem: Sequence[tuple[str, Sequence[tuple[Ticket, float]]]],
    diferenca_minima: int,
) -> list[tuple[str, Ticket]]:
    """Reconstroi o MESMO algoritmo sequencial de selecao de producao
    (ordena por score desc + desempate lexicografico; percorre ate achar
    o primeiro que satisfaz o gate de diferenca minima contra TODOS os
    ja escolhidos NESTA propria reconstrucao) -- parametrizavel por QUAL
    score usar no ranking (LF-09D, mecanismo G/Pendencia 2). Usar
    ``final_score`` deve reproduzir EXATAMENTE a selecao real de
    producao; usar ``raw_score`` isola o efeito especifico da
    penalidade de similaridade no ranking, mantendo o MESMO gate.

    ``pool_por_perfil_em_ordem`` deve estar na ordem real dos perfis
    (Diamante..Conservador) -- a dependencia sequencial (``escolhidos``
    crescendo a cada perfil) e reconstruida aqui, nao reutiliza o
    ``escolhidos`` real de producao."""
    escolhidos: list[Ticket] = []
    resultado: list[tuple[str, Ticket]] = []
    for perfil, candidatos in pool_por_perfil_em_ordem:
        ordenados = sorted(candidatos, key=lambda par: (-par[1], par[0]))
        escolha = next(
            (ticket for ticket, _ in ordenados if all(len(set(ticket) - set(outro)) >= diferenca_minima for outro in escolhidos)),
            None,
        )
        if escolha is None:
            escolha = ordenados[0][0]
        escolhidos.append(escolha)
        resultado.append((perfil, escolha))
    return resultado


def mean_pairwise_intersection(tickets: Sequence[Ticket]) -> float:
    from itertools import combinations

    pares = list(combinations(tickets, 2))
    if not pares:
        raise ValueError("Sao necessarios pelo menos 2 tickets.")
    return statistics.fmean(intersection_size(a, b) for a, b in pares)
