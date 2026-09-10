"""Selecao de portfolio a partir do pool AUTENTICO de candidatos do
MOTOR_ELITE_V2 (LF-09A).

Todo candidato usado aqui vem exclusivamente de um ``CandidateTracer``
(LF-08/LF-08A) preenchido por UMA execucao real de ``gerar_jogos_v2`` --
nunca uma segunda geracao, nunca simulacao, nunca inferencia. Nenhuma
funcao aqui cria, modifica ou recombina dezenas: cada selector apenas
ESCOLHE 5 tickets ja existentes no pool.

IMPORTANTE (limitacao documentada, nao escondida): o ``final_candidate_score``
de um candidato do perfil k, tal como capturado pelo trace, ja incorpora a
penalidade de similaridade contra os tickets REALMENTE escolhidos pelo
SELECTOR_ORIGINAL nos perfis 0..k-1 (acoplamento identificado no LF-07).
O pool aqui usa esses scores exatamente como produzidos -- nao os
recalcula, nao os "corrige" para nenhuma sequencia alternativa de
selecao. Qualquer novo selector opera sobre esse sinal path-dependent,
autentico porem imperfeito, tal como ele realmente existe.
"""
from __future__ import annotations

from dataclasses import dataclass
import random
import statistics
from typing import Sequence

from .candidate_trace import CandidateTracer
from .ticket_metrics import overlap_ratio

Ticket = tuple[int, ...]


@dataclass(frozen=True, slots=True)
class CandidatePoolEntry:
    """Uma entrada UNICA (por valor de ticket) do pool autentico,
    derivada do trace de UMA execucao real. Se o mesmo ticket foi
    avaliado mais de uma vez (mesmo perfil com duplicata, ou perfis
    diferentes produzindo o mesmo ticket), o score usado e o da ULTIMA
    avaliacao observada no trace, na ordem em que producao realmente as
    gerou -- mesma semantica de sobrescrita que ``candidatos[jogo]=...``
    em producao, generalizada para o pool inteiro."""

    ticket: Ticket
    final_candidate_score: float
    profiles_seen: tuple[str, ...]
    last_seen_evaluation_index: int


def build_candidate_pool_from_trace(tracer: CandidateTracer) -> tuple[CandidatePoolEntry, ...]:
    """Constroi o pool autentico e unico-por-ticket a partir de
    ``tracer.evaluations`` (LF-08). NAO gera nenhum candidato novo --
    apenas agrega o que ja foi observado."""
    por_ticket: dict[Ticket, dict] = {}
    for indice, evento in enumerate(tracer.evaluations):
        entrada = por_ticket.setdefault(evento.ticket, {"perfis": []})
        entrada["score"] = evento.final_candidate_score
        entrada["indice"] = indice
        if evento.profile not in entrada["perfis"]:
            entrada["perfis"].append(evento.profile)
    return tuple(
        CandidatePoolEntry(
            ticket=ticket,
            final_candidate_score=dados["score"],
            profiles_seen=tuple(dados["perfis"]),
            last_seen_evaluation_index=dados["indice"],
        )
        for ticket, dados in por_ticket.items()
    )


def original_selected_tickets(tracer: CandidateTracer) -> tuple[Ticket, ...]:
    """Os 5 tickets EXATOS que o SELECTOR_ORIGINAL (producao) escolheu
    nesta execucao -- lidos diretamente do resumo de perfil, na ordem
    dos perfis. Nao ha selecao nova aqui, apenas leitura do trace."""
    return tuple(resumo.selected_ticket for resumo in tracer.profile_summaries)


# --- Normalizacao e objetivo parametrizado (Fase 6) -------------------------


def _normalizar_scores(pool: Sequence[CandidatePoolEntry]) -> dict[Ticket, float]:
    scores = [c.final_candidate_score for c in pool]
    minimo, maximo = min(scores), max(scores)
    amplitude = maximo - minimo
    if amplitude == 0:
        return {c.ticket: 0.5 for c in pool}
    return {c.ticket: (c.final_candidate_score - minimo) / amplitude for c in pool}


@dataclass(frozen=True, slots=True)
class LF09AConfig:
    """Uma configuracao FIXA e pre-registrada do objetivo de selecao
    (Fase 7). ``score_floor`` (Fase 8), quando nao None, exige
    norm_score(c) >= score_floor para um candidato ser elegivel (exceto
    o primeiro, que e sempre o de maior score no pool inteiro)."""

    name: str
    lambda_diversity: float
    lambda_overlap: float
    score_floor: float | None


# Grid pre-registrado ANTES de qualquer resultado real (Fase 7). Nenhum
# valor aqui foi ou sera ajustado apos observar concursos ganhos/perdidos.
RESEARCH_CONFIGS: tuple[LF09AConfig, ...] = (
    LF09AConfig(name="CONFIG_A_SCORE_PURO", lambda_diversity=0.0, lambda_overlap=0.0, score_floor=None),
    LF09AConfig(name="CONFIG_B_DIVERSIDADE_LEVE", lambda_diversity=0.10, lambda_overlap=0.05, score_floor=None),
    LF09AConfig(name="CONFIG_C_DIVERSIDADE_MODERADA", lambda_diversity=0.30, lambda_overlap=0.15, score_floor=None),
    LF09AConfig(name="CONFIG_D_DIVERSIDADE_FORTE", lambda_diversity=0.60, lambda_overlap=0.30, score_floor=None),
    LF09AConfig(name="CONFIG_E_DIVERSIDADE_MAXIMA_COM_PISO", lambda_diversity=1.0, lambda_overlap=0.5, score_floor=0.90),
)


def _diversity_component(candidato: Ticket, selecionados: Sequence[Ticket]) -> float:
    """Media, sobre os ja selecionados, de (1 - overlap_ratio) -- quanto
    maior, mais diverso o candidato e EM MEDIA em relacao ao portfolio
    ja formado. 1.0 quando nao ha nenhum selecionado ainda (primeiro
    pick nao tem redundancia por definicao)."""
    if not selecionados:
        return 1.0
    return statistics.fmean(1.0 - overlap_ratio(candidato, s) for s in selecionados)


def _redundancy_component(candidato: Ticket, selecionados: Sequence[Ticket]) -> float:
    """Pior caso (maximo) de overlap_ratio contra qualquer ja
    selecionado -- penaliza especificamente o par mais redundante."""
    if not selecionados:
        return 0.0
    return max(overlap_ratio(candidato, s) for s in selecionados)


def select_portfolio_lf09a(
    pool: Sequence[CandidatePoolEntry],
    config: LF09AConfig,
    portfolio_size: int = 5,
) -> tuple[Ticket, ...]:
    """Selector guloso, deterministico (Fase 5): escolhe
    ``portfolio_size`` tickets DISTINTOS do pool autentico, maximizando
    a cada passo ``norm_score + lambda_diversity*diversidade -
    lambda_overlap*redundancia`` contra o que ja foi selecionado.

    NUNCA cria, modifica ou recombina um ticket -- todo valor retornado
    e um ``entry.ticket`` literal do ``pool`` recebido."""
    if len(pool) < portfolio_size:
        raise ValueError(f"Pool tem {len(pool)} candidatos, insuficiente para portfolio de {portfolio_size}.")

    norm = _normalizar_scores(pool)
    elegveis = list(pool)
    if config.score_floor is not None:
        elegveis = [c for c in elegveis if norm[c.ticket] >= config.score_floor]
        if len(elegveis) < portfolio_size:
            # piso deixou candidatos insuficientes -- cai de volta ao pool
            # inteiro (nunca inventamos ticket para preencher a cota).
            elegveis = list(pool)

    ordenados_por_score = sorted(elegveis, key=lambda c: (-norm[c.ticket], c.ticket))
    selecionados: list[Ticket] = [ordenados_por_score[0].ticket]
    restantes = [c for c in ordenados_por_score[1:]]

    while len(selecionados) < portfolio_size and restantes:
        def objetivo(c: CandidatePoolEntry) -> tuple[float, float, Ticket]:
            valor = (
                norm[c.ticket]
                + config.lambda_diversity * _diversity_component(c.ticket, selecionados)
                - config.lambda_overlap * _redundancy_component(c.ticket, selecionados)
            )
            return (-valor, -norm[c.ticket], c.ticket)

        restantes.sort(key=objetivo)
        escolhido = restantes.pop(0)
        selecionados.append(escolhido.ticket)

    return tuple(selecionados)


def select_portfolio_random(
    pool: Sequence[CandidatePoolEntry],
    seed: int,
    portfolio_size: int = 5,
) -> tuple[Ticket, ...]:
    """Controle (Fase 12): amostra ``portfolio_size`` tickets DISTINTOS
    uniformemente do MESMO pool autentico, sem usar score algum --
    nunca gera ticket fora do pool."""
    if len(pool) < portfolio_size:
        raise ValueError(f"Pool tem {len(pool)} candidatos, insuficiente para portfolio de {portfolio_size}.")
    rng = random.Random(seed)
    escolhidos = rng.sample([c.ticket for c in pool], portfolio_size)
    return tuple(escolhidos)
