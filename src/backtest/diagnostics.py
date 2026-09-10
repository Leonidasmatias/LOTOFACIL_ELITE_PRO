"""Diagnostico forense do resultado LF-05 (LF-06): estabilidade temporal e
deslocamento da distribuicao de acertos.

Opera sobre ``TargetAggregate`` -- uma linha por concurso-alvo, com o
resultado do motor (1 avaliacao) e o resultado do baseline aleatorio POR
seed (N avaliacoes). Esta estrutura e deliberadamente compativel com o
checkpoint bruto do benchmark LF-05 (mesmos campos), mas nao depende de
nenhum arquivo especifico -- qualquer chamador pode construir
``TargetAggregate`` a partir de ``BenchmarkContestResult`` (LF-05) agrupado
por concurso, ou de uma nova execucao.

Nenhuma funcao aqui decide QUAIS concursos avaliar com base em desempenho
-- particoes cronologicas sao definidas apenas pela contagem/posicao dos
concursos elegiveis, antes de qualquer resultado ser lido.
"""
from __future__ import annotations

from dataclasses import dataclass
import statistics
from typing import Mapping, Sequence

FAIXAS_PREMIACAO = (11, 12, 13, 14, 15)


@dataclass(frozen=True, slots=True)
class TargetAggregate:
    """Uma linha por concurso-alvo: 1 resultado do motor + 1 resultado do
    baseline aleatorio por seed (chave = seed, valor = mean_hits/distribuicao
    daquela seed para este concurso)."""

    target_contest: int
    motor_seed: int | None
    motor_mean_hits: float
    motor_max_hits: int
    motor_distribution: Mapping[int, int]
    random_seed_mean_hits: Mapping[int, float]
    random_seed_distribution: Mapping[int, Mapping[int, int]]

    def random_mean_hits_medio(self) -> float:
        """Media do mean_hits do random entre as seeds, PARA ESTE concurso
        -- e o valor que deve ser pareado contra ``motor_mean_hits`` (unidade
        pareada = CONCURSO, nunca (concurso, seed))."""
        return statistics.fmean(self.random_seed_mean_hits.values())


def freq_ge(distribuicao: Mapping[int, int], faixa: int) -> int:
    return sum(quantidade for hits, quantidade in distribuicao.items() if int(hits) >= faixa)


def chronological_blocks(target_contests: Sequence[int], n_blocks: int) -> list[tuple[int, int]]:
    """Divide ``target_contests`` (unicos, quaisquer que sejam os valores)
    em ``n_blocks`` grupos cronologicos contiguos e aproximadamente iguais,
    definidos SOMENTE pela posicao na lista ordenada -- nunca por
    desempenho. Ultimo bloco absorve o resto da divisao inteira. Cobre cada
    concurso elegivel exatamente uma vez, em ordem, sem descartar nenhum."""
    if n_blocks <= 0:
        raise ValueError("n_blocks deve ser positivo.")
    ordenados = sorted(set(target_contests))
    n = len(ordenados)
    if n < n_blocks:
        raise ValueError(f"Nao ha concursos suficientes ({n}) para {n_blocks} blocos.")
    tamanho_base, resto = divmod(n, n_blocks)
    blocos: list[tuple[int, int]] = []
    inicio = 0
    for indice in range(n_blocks):
        tamanho = tamanho_base + (1 if indice < resto else 0)
        fim = inicio + tamanho
        blocos.append((ordenados[inicio], ordenados[fim - 1]))
        inicio = fim
    return blocos


@dataclass(frozen=True, slots=True)
class BlockReport:
    target_first: int
    target_last: int
    n_contests: int
    motor_mean_hits: float
    random_mean_hits: float
    delta_mean_hits: float
    wins: int
    ties: int
    losses: int
    motor_ge11: int
    motor_ge12: int
    motor_ge13: int
    motor_ge14: int
    motor_eq15: int
    random_ge11_mean: float
    random_ge12_mean: float
    random_ge13_mean: float
    random_ge14_mean: float
    random_eq15_mean: float


def block_report(aggregates: Sequence[TargetAggregate], block: tuple[int, int]) -> BlockReport:
    """Relatorio factual de UM bloco cronologico pre-definido (Fase 7).
    Nao escolhe o bloco -- recebe as fronteiras ja definidas por
    ``chronological_blocks``."""
    primeiro, ultimo = block
    linhas = [a for a in aggregates if primeiro <= a.target_contest <= ultimo]
    if not linhas:
        raise ValueError(f"Nenhum TargetAggregate no intervalo [{primeiro}, {ultimo}].")

    deltas = [linha.motor_mean_hits - linha.random_mean_hits_medio() for linha in linhas]
    wins = sum(1 for d in deltas if d > 0)
    ties = sum(1 for d in deltas if d == 0)
    losses = sum(1 for d in deltas if d < 0)

    random_ge_por_seed: dict[int, dict[int, int]] = {}
    for linha in linhas:
        for seed, distribuicao in linha.random_seed_distribution.items():
            acumulador = random_ge_por_seed.setdefault(seed, {faixa: 0 for faixa in FAIXAS_PREMIACAO})
            for faixa in FAIXAS_PREMIACAO:
                acumulador[faixa] += freq_ge(distribuicao, faixa)

    def _media_random_ge(faixa: int) -> float:
        valores = [totais[faixa] for totais in random_ge_por_seed.values()]
        return statistics.fmean(valores) if valores else 0.0

    motor_dist_total: dict[int, int] = {}
    for linha in linhas:
        for hits, quantidade in linha.motor_distribution.items():
            motor_dist_total[int(hits)] = motor_dist_total.get(int(hits), 0) + quantidade

    return BlockReport(
        target_first=primeiro,
        target_last=ultimo,
        n_contests=len(linhas),
        motor_mean_hits=statistics.fmean(linha.motor_mean_hits for linha in linhas),
        random_mean_hits=statistics.fmean(linha.random_mean_hits_medio() for linha in linhas),
        delta_mean_hits=statistics.fmean(deltas),
        wins=wins,
        ties=ties,
        losses=losses,
        motor_ge11=freq_ge(motor_dist_total, 11),
        motor_ge12=freq_ge(motor_dist_total, 12),
        motor_ge13=freq_ge(motor_dist_total, 13),
        motor_ge14=freq_ge(motor_dist_total, 14),
        motor_eq15=motor_dist_total.get(15, 0),
        random_ge11_mean=_media_random_ge(11),
        random_ge12_mean=_media_random_ge(12),
        random_ge13_mean=_media_random_ge(13),
        random_ge14_mean=_media_random_ge(14),
        random_eq15_mean=_media_random_ge(15),
    )


@dataclass(frozen=True, slots=True)
class HitDistributionReport:
    """Distribuicao completa de acertos, MOTOR vs RANDOM, sobre todos os
    concursos e (para o random) todas as seeds recebidas (Fase 8)."""

    p_motor: Mapping[int, float]
    p_random: Mapping[int, float]
    delta: Mapping[int, float]
    cumulative_motor: Mapping[int, float]
    cumulative_random: Mapping[int, float]
    cumulative_delta: Mapping[int, float]


CUMULATIVE_THRESHOLDS = (10, 11, 12, 13, 14, 15)


def hit_distribution_report(aggregates: Sequence[TargetAggregate]) -> HitDistributionReport:
    motor_total: dict[int, int] = {k: 0 for k in range(16)}
    random_total: dict[int, int] = {k: 0 for k in range(16)}
    motor_tickets = 0
    random_tickets = 0
    for linha in aggregates:
        for hits, quantidade in linha.motor_distribution.items():
            motor_total[int(hits)] += quantidade
            motor_tickets += quantidade
        for distribuicao in linha.random_seed_distribution.values():
            for hits, quantidade in distribuicao.items():
                random_total[int(hits)] += quantidade
                random_tickets += quantidade
    if motor_tickets == 0 or random_tickets == 0:
        raise ValueError("Nenhum ticket para calcular distribuicao de acertos.")

    p_motor = {k: motor_total[k] / motor_tickets for k in range(16)}
    p_random = {k: random_total[k] / random_tickets for k in range(16)}
    delta = {k: p_motor[k] - p_random[k] for k in range(16)}

    def _cumulativo(p: Mapping[int, float]) -> dict[int, float]:
        return {limiar: sum(p[k] for k in range(limiar, 16)) for limiar in CUMULATIVE_THRESHOLDS}

    cumulative_motor = _cumulativo(p_motor)
    cumulative_random = _cumulativo(p_random)
    cumulative_delta = {limiar: cumulative_motor[limiar] - cumulative_random[limiar] for limiar in CUMULATIVE_THRESHOLDS}

    return HitDistributionReport(
        p_motor=p_motor,
        p_random=p_random,
        delta=delta,
        cumulative_motor=cumulative_motor,
        cumulative_random=cumulative_random,
        cumulative_delta=cumulative_delta,
    )
