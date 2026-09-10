"""Funcoes puras de calibracao/analise estatistica entre perfis (LF-09C).

Nenhuma funcao aqui gera, modifica ou seleciona candidatos, nem altera
producao. Operam exclusivamente sobre pares (score, hits) ja observados
-- a maioria reaproveita ou espelha utilitarios ja existentes e testados
em gates anteriores (``benchmark_stats._percentile``,
``portfolio_diagnostics.pearson_association``) para nao duplicar logica
material.
"""
from __future__ import annotations

from dataclasses import dataclass
import statistics
from typing import Sequence

from .portfolio_diagnostics import pearson_association


def percentile(valores_ordenados: Sequence[float], p: float) -> float:
    """Percentil por interpolacao linear (mesma formula ja usada e
    testada em ``benchmark_stats._percentile``/LF-05)."""
    if not valores_ordenados:
        raise ValueError("Lista vazia nao tem percentil.")
    if len(valores_ordenados) == 1:
        return valores_ordenados[0]
    posicao = p * (len(valores_ordenados) - 1)
    indice_baixo = int(posicao)
    indice_alto = min(indice_baixo + 1, len(valores_ordenados) - 1)
    fracao = posicao - indice_baixo
    return valores_ordenados[indice_baixo] + (valores_ordenados[indice_alto] - valores_ordenados[indice_baixo]) * fracao


def quantile_boundaries(valores: Sequence[float], n_quantis: int) -> list[float]:
    """``n_quantis+1`` fronteiras (incluindo min e max) que dividem
    ``valores`` em ``n_quantis`` grupos de tamanho aproximadamente
    igual."""
    if n_quantis <= 0:
        raise ValueError("n_quantis deve ser positivo.")
    if not valores:
        raise ValueError("Nenhum valor para calcular quantis.")
    ordenados = sorted(valores)
    return [percentile(ordenados, i / n_quantis) for i in range(n_quantis + 1)]


def assign_decile(valor: float, boundaries: Sequence[float]) -> int:
    """Indice do decil (0-based, 0..len(boundaries)-2) ao qual ``valor``
    pertence, dado um conjunto de fronteiras de ``quantile_boundaries``.
    Valores no limite superior exato entram no ultimo decil."""
    if len(boundaries) < 2:
        raise ValueError("Sao necessarias pelo menos 2 fronteiras.")
    n = len(boundaries) - 1
    for indice in range(n):
        limite_inferior = boundaries[indice]
        limite_superior = boundaries[indice + 1]
        if indice == n - 1:
            if limite_inferior <= valor <= limite_superior:
                return indice
        elif limite_inferior <= valor < limite_superior:
            return indice
    # valor fora do range observado (nao deveria ocorrer para valores
    # que fizeram parte do calculo das fronteiras) -- clampa nas pontas.
    if valor < boundaries[0]:
        return 0
    return n - 1


def rank_percentile(valores: Sequence[float]) -> list[float]:
    """Para cada posicao i, devolve o percentil de rank (0.0=pior,
    1.0=melhor) de ``valores[i]`` DENTRO da propria lista. Empates
    recebem o rank MEDIO (metodo padrao para lidar com empates sem
    favorecer arbitrariamente nenhum lado)."""
    n = len(valores)
    if n == 0:
        raise ValueError("Lista vazia nao tem rank percentile.")
    if n == 1:
        return [0.5]
    ordenados = sorted(range(n), key=lambda i: valores[i])
    ranks = [0.0] * n
    indice = 0
    while indice < n:
        fim = indice
        while fim + 1 < n and valores[ordenados[fim + 1]] == valores[ordenados[indice]]:
            fim += 1
        rank_medio = (indice + fim) / 2
        for k in range(indice, fim + 1):
            ranks[ordenados[k]] = rank_medio / (n - 1)
        indice = fim + 1
    return ranks


def z_score(valores: Sequence[float]) -> list[float]:
    """Z-score dentro da propria lista (media 0, desvio padrao
    populacional 1). Lista com desvio zero devolve todos 0.0."""
    if not valores:
        raise ValueError("Lista vazia nao tem z-score.")
    media = statistics.fmean(valores)
    desvio = statistics.pstdev(valores)
    if desvio == 0:
        return [0.0 for _ in valores]
    return [(v - media) / desvio for v in valores]


def min_max_normalize(valores: Sequence[float]) -> list[float]:
    """Normalizacao min-max para [0, 1] dentro da propria lista. Lista
    com amplitude zero devolve todos 0.5 (mesma convencao ja usada em
    ``motor_elite_v2._normalizar``/LF-09A)."""
    if not valores:
        raise ValueError("Lista vazia nao tem min-max.")
    minimo, maximo = min(valores), max(valores)
    amplitude = maximo - minimo
    if amplitude == 0:
        return [0.5 for _ in valores]
    return [(v - minimo) / amplitude for v in valores]


def spearman_correlation(x: Sequence[float], y: Sequence[float]) -> float:
    """Correlacao de Spearman = Pearson sobre os ranks (percentile,
    0..1) de cada serie -- reaproveita ``pearson_association`` (LF-06),
    ja testada, sem duplicar a formula de correlacao."""
    if len(x) != len(y):
        raise ValueError("As duas series precisam ter o mesmo tamanho.")
    return pearson_association(rank_percentile(x), rank_percentile(y))


@dataclass(frozen=True, slots=True)
class DecileReport:
    decile: int
    score_min: float
    score_max: float
    n: int
    mean_hits: float
    p_ge10: float
    p_ge11: float
    p_ge12: float
    p_ge13: float


def decile_calibration(scores: Sequence[float], hits: Sequence[int], n_deciles: int = 10) -> list[DecileReport]:
    """Divide ``scores`` em ``n_deciles`` grupos de tamanho aprox. igual
    e reporta, para cada grupo, a media de ``hits`` e as probabilidades
    de atingir os limiares 10/11/12/13 -- puramente descritivo."""
    if len(scores) != len(hits):
        raise ValueError("scores e hits precisam ter o mesmo tamanho.")
    if not scores:
        raise ValueError("Nenhum dado para calibracao por decil.")
    fronteiras = quantile_boundaries(scores, n_deciles)
    grupos: list[list[int]] = [[] for _ in range(n_deciles)]
    grupos_scores: list[list[float]] = [[] for _ in range(n_deciles)]
    for s, h in zip(scores, hits):
        indice = assign_decile(s, fronteiras)
        grupos[indice].append(h)
        grupos_scores[indice].append(s)
    relatorios = []
    for indice in range(n_deciles):
        hits_grupo = grupos[indice]
        if not hits_grupo:
            continue
        n = len(hits_grupo)
        relatorios.append(
            DecileReport(
                decile=indice,
                score_min=min(grupos_scores[indice]),
                score_max=max(grupos_scores[indice]),
                n=n,
                mean_hits=statistics.fmean(hits_grupo),
                p_ge10=sum(1 for h in hits_grupo if h >= 10) / n,
                p_ge11=sum(1 for h in hits_grupo if h >= 11) / n,
                p_ge12=sum(1 for h in hits_grupo if h >= 12) / n,
                p_ge13=sum(1 for h in hits_grupo if h >= 13) / n,
            )
        )
    return relatorios


@dataclass(frozen=True, slots=True)
class TopBottomLift:
    top_fraction: float
    top_mean_hits: float
    bottom_mean_hits: float
    lift: float
    top_n: int
    bottom_n: int


def top_bottom_lift(scores: Sequence[float], hits: Sequence[int], top_fraction: float) -> TopBottomLift:
    """Diferenca de mean_hits entre o top ``top_fraction`` (por score) e
    o bottom ``top_fraction`` da mesma populacao -- sinal saudavel
    esperado: lift > 0."""
    if len(scores) != len(hits):
        raise ValueError("scores e hits precisam ter o mesmo tamanho.")
    if not 0 < top_fraction < 0.5:
        raise ValueError("top_fraction deve estar em (0, 0.5).")
    pares = sorted(zip(scores, hits), key=lambda par: par[0])
    n = len(pares)
    corte = max(1, round(n * top_fraction))
    bottom = pares[:corte]
    top = pares[-corte:]
    top_mean = statistics.fmean(h for _, h in top)
    bottom_mean = statistics.fmean(h for _, h in bottom)
    return TopBottomLift(
        top_fraction=top_fraction,
        top_mean_hits=top_mean,
        bottom_mean_hits=bottom_mean,
        lift=top_mean - bottom_mean,
        top_n=len(top),
        bottom_n=len(bottom),
    )
