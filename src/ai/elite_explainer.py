"""Elite Score Explainable AI (Fase V1.4).

Camada de explicacao textual/estruturada sobre o Elite Score ja calculado por
``src/core/elite_score.py`` (Phoenix V2). Este modulo NAO recalcula nada: le
apenas os componentes (``ComponenteEliteScore``) e o total
(``EliteScoreResultado.total``) ja produzidos pelo Core, e traduz esses
numeros numa explicacao legivel para o usuario final (classificacao, pontos
fortes, penalidades e um resumo textual).

Regras respeitadas nesta fase:
  - NAO altera ``src/core/motor_elite.py`` nem qualquer regra do Motor Elite;
  - NAO altera nenhuma formula do Elite Score -- ``src/core/elite_score.py``
    permanece intocado nesta fase; os pesos (``PESOS``) e a metodologia de
    sub-score continuam exatamente como na Phoenix V2;
  - Usa SOMENTE metricas ja existentes: os campos de ``ComponenteEliteScore``
    (nome, descricao, valor_jogo, faixa_tipica, sub_score, peso, contribuicao)
    ja calculados por ``core.elite_score.calcular_elite_score``;
  - 100% local e deterministico: mesma entrada -> mesma saida sempre, sem
    nenhuma chamada de rede, API externa ou modelo de IA generativa.
    "Explainable AI" aqui significa "explicacao por regras transparentes e
    reproduziveis", nao um modelo de machine learning.

Classificacao e limiares de "ponto forte" / "penalidade":

As faixas de classificacao (ELITE PREMIUM / ALTO / MEDIO / BAIXO) e os
limiares usados para marcar um componente como ponto forte ou penalidade NAO
sao numeros escolhidos livremente: sao derivados diretamente da escala que
``core.elite_score`` ja usa para os proprios sub-scores (0 a 100, com piso
``PISO_SUB_SCORE = 20`` antes de saturar rumo a 0 alem do extremo historico).
Dividimos o intervalo valido ``[PISO_SUB_SCORE, 100]`` em quartis:

    PISO_SUB_SCORE (20)                      -> limite inferior de BAIXO
    PISO_SUB_SCORE + 25% da faixa (40)        -> limiar BAIXO / MEDIO
    PISO_SUB_SCORE + 50% da faixa (60)        -> limiar MEDIO / ALTO
    PISO_SUB_SCORE + 75% da faixa (80)        -> limiar ALTO / ELITE PREMIUM

Os mesmos limiares de 60 e 80 sao reaproveitados para classificar cada
COMPONENTE individualmente como ponto forte (sub-score >= 80) ou penalidade
(sub-score < 60), em vez de definir um segundo conjunto de numeros arbitrarios
so para essa finalidade.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..core.elite_score import PISO_SUB_SCORE
from ..models.elite_score import ComponenteEliteScore, EliteScoreResultado

_FAIXA_SUB_SCORE = 100.0 - PISO_SUB_SCORE  # 80.0 -- intervalo valido de sub-score

LIMIAR_MEDIO = round(PISO_SUB_SCORE + 0.25 * _FAIXA_SUB_SCORE, 2)  # 40.0
LIMIAR_ALTO = round(PISO_SUB_SCORE + 0.50 * _FAIXA_SUB_SCORE, 2)  # 60.0
LIMIAR_ELITE_PREMIUM = round(PISO_SUB_SCORE + 0.75 * _FAIXA_SUB_SCORE, 2)  # 80.0

CLASSIFICACAO_ELITE_PREMIUM = "ELITE PREMIUM"
CLASSIFICACAO_ALTO = "ALTO"
CLASSIFICACAO_MEDIO = "MÉDIO"
CLASSIFICACAO_BAIXO = "BAIXO"


@dataclass(frozen=True, slots=True)
class PontoDeAtencao:
    """Um componente do Elite Score destacado como ponto forte ou penalidade.

    Reaproveita, sem alterar, os mesmos valores ja calculados em
    ``ComponenteEliteScore`` -- nao recalcula nada.
    """

    componente: str
    descricao: str
    valor_jogo: float
    sub_score: float
    peso: float
    contribuicao: float


@dataclass(frozen=True, slots=True)
class ExplicacaoElite:
    """Explicacao interpretavel do Elite Score de um jogo ja calculado."""

    score: float
    classificacao: str
    pontos_fortes: tuple[PontoDeAtencao, ...]
    penalidades: tuple[PontoDeAtencao, ...]
    resumo: str


def classificar_score(score: float) -> str:
    """Classifica um Elite Score total (0-100) em uma das 4 faixas.

    Ver a docstring do modulo para a derivacao dos limiares (40/60/80) a
    partir de ``core.elite_score.PISO_SUB_SCORE``.
    """
    if score >= LIMIAR_ELITE_PREMIUM:
        return CLASSIFICACAO_ELITE_PREMIUM
    if score >= LIMIAR_ALTO:
        return CLASSIFICACAO_ALTO
    if score >= LIMIAR_MEDIO:
        return CLASSIFICACAO_MEDIO
    return CLASSIFICACAO_BAIXO


def _para_ponto_de_atencao(componente: ComponenteEliteScore) -> PontoDeAtencao:
    return PontoDeAtencao(
        componente=componente.nome,
        descricao=componente.descricao,
        valor_jogo=componente.valor_jogo,
        sub_score=componente.sub_score,
        peso=componente.peso,
        contribuicao=componente.contribuicao,
    )


def _montar_resumo(
    score: float,
    classificacao: str,
    pontos_fortes: tuple[PontoDeAtencao, ...],
    penalidades: tuple[PontoDeAtencao, ...],
) -> str:
    partes = [f"Elite Score {score:.1f}/100 -> classificacao {classificacao}."]
    if pontos_fortes:
        nomes = ", ".join(p.componente for p in pontos_fortes)
        partes.append(f"Pontos fortes: {nomes}.")
    else:
        partes.append("Nenhum componente se destacou fortemente acima da faixa tipica.")
    if penalidades:
        nomes = ", ".join(p.componente for p in penalidades)
        partes.append(f"Pontos de atencao (penalidades): {nomes}.")
    else:
        partes.append("Nenhuma penalidade relevante identificada.")
    return " ".join(partes)


def explicar_jogo(
    jogo: list[int],
    features: tuple[ComponenteEliteScore, ...] | list[ComponenteEliteScore],
    score: float,
) -> ExplicacaoElite:
    """Traduz o Elite Score ja calculado numa explicacao interpretavel.

    ``jogo``: as 15 dezenas do jogo (usado apenas para uma validacao basica
    de forma -- nao entra em nenhum calculo aqui).
    ``features``: os componentes ja calculados (``EliteScoreResultado.componentes``).
    ``score``: o total ja calculado (``EliteScoreResultado.total``).

    Nao recalcula nada do Motor Elite nem do Elite Score: le apenas valores
    ja produzidos por ``core.elite_score.calcular_elite_score``. 100% local,
    deterministico e sem nenhuma chamada externa -- a mesma entrada sempre
    produz a mesma explicacao.
    """
    if len(jogo) != 15:
        raise ValueError(f"Um jogo da Lotofacil precisa ter exatamente 15 dezenas (recebido: {len(jogo)}).")

    classificacao = classificar_score(score)

    pontos_fortes = tuple(
        _para_ponto_de_atencao(c)
        for c in sorted(features, key=lambda c: c.contribuicao, reverse=True)
        if c.sub_score >= LIMIAR_ELITE_PREMIUM
    )
    penalidades = tuple(
        _para_ponto_de_atencao(c)
        for c in sorted(features, key=lambda c: c.sub_score)
        if c.sub_score < LIMIAR_ALTO
    )

    resumo = _montar_resumo(score, classificacao, pontos_fortes, penalidades)

    return ExplicacaoElite(
        score=score,
        classificacao=classificacao,
        pontos_fortes=pontos_fortes,
        penalidades=penalidades,
        resumo=resumo,
    )


def explicar_resultado(jogo: list[int], resultado: EliteScoreResultado) -> ExplicacaoElite:
    """Atalho: recebe diretamente um ``EliteScoreResultado`` ja calculado
    (por ``elite_score_service``/``core.elite_score``) em vez de passar
    ``features``/``score`` separadamente."""
    return explicar_jogo(jogo, resultado.componentes, resultado.total)
