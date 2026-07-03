"""Elite Decision Engine (Fase V1.5).

Camada estrategica construida ACIMA do Elite Score (Phoenix V2) e da
Explainable AI (V1.4). Este modulo NAO recalcula nem altera nenhum valor de
score: le apenas os totais ja produzidos por
``core.elite_score.calcular_elite_score`` (via ``EliteScoreResultado.total``,
tipicamente obtidos de ``elite_score_service.calcular_scores``) e agrega
essas informacoes numa recomendacao de estrategia para o conjunto de jogos
gerado.

Regras respeitadas nesta fase:
  - NAO altera ``src/core/motor_elite.py`` nem qualquer regra do Motor Elite;
  - NAO altera ``src/core/elite_score.py`` nem nenhuma formula de scoring;
  - NAO gera jogos novos -- apenas le e agrega dados ja existentes
    (``EliteScoreResultado.total`` de jogos ja gerados e ja pontuados);
  - 100% local e deterministico: mesma lista de scores -> mesmo relatorio,
    sem nenhuma chamada de rede, API externa ou modelo de IA generativa.

Classificacao por jogo (faixas dadas pela especificacao desta fase):

    ELITE PREMIUM   : score >= 90
    ALTO POTENCIAL  : 75 <= score < 90
    NEUTRO          : 50 <= score < 75
    FRACO           : score < 50

Perfil de estrategia (CONSERVADOR / EQUILIBRADO / AGRESSIVO):

A decisao usa apenas dois numeros ja calculaveis a partir da classificacao
acima -- a media dos scores do lote e a proporcao de jogos fortes
(ELITE PREMIUM + ALTO POTENCIAL) / fracos (FRACO) -- comparados contra os
MESMOS limiares 50/75/90 usados na classificacao por jogo, para nao
introduzir um segundo conjunto de numeros para a mesma escala:

  - AGRESSIVO: media do lote >= 75 (faixa "Alto potencial" ou melhor) E pelo
    menos 60% dos jogos sao fortes (maioria clara, nao apenas simples).
  - CONSERVADOR: media do lote < 50 (faixa "Fraco") OU pelo menos metade dos
    jogos do lote sao FRACO.
  - EQUILIBRADO: qualquer outro caso (situacao mista, sem um sinal claro em
    nenhuma direcao).

O "nivel de risco" e definido pela mesma decisao de perfil (nao e um eixo
independente com novos cortes): CONSERVADOR -> BAIXO, EQUILIBRADO -> MEDIO,
AGRESSIVO -> ALTO. O "potencial teorico" e simplesmente a media dos scores do
lote, ja calculada para a decisao -- reexibida, nao recalculada.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from ..models.elite_score import EliteScoreResultado

LIMIAR_NEUTRO = 50.0
LIMIAR_ALTO_POTENCIAL = 75.0
LIMIAR_ELITE_PREMIUM = 90.0

CLASSIFICACAO_ELITE_PREMIUM = "ELITE PREMIUM"
CLASSIFICACAO_ALTO_POTENCIAL = "ALTO POTENCIAL"
CLASSIFICACAO_NEUTRO = "NEUTRO"
CLASSIFICACAO_FRACO = "FRACO"

CLASSIFICACOES_FORTES = frozenset({CLASSIFICACAO_ELITE_PREMIUM, CLASSIFICACAO_ALTO_POTENCIAL})

PERFIL_CONSERVADOR = "CONSERVADOR"
PERFIL_EQUILIBRADO = "EQUILIBRADO"
PERFIL_AGRESSIVO = "AGRESSIVO"

RISCO_BAIXO = "BAIXO"
RISCO_MEDIO = "MÉDIO"
RISCO_ALTO = "ALTO"
RISCO_INDEFINIDO = "INDEFINIDO"

# "Maioria clara" de jogos fortes exigida para recomendar postura agressiva
# (barra mais alta do que 50%, de proposito: exigimos mais confianca para
# recomendar uma postura de maior exposicao do que para recomendar cautela).
PROPORCAO_FORTE_PARA_AGRESSIVO = 0.60
# Metade ou mais de jogos fracos ja e suficiente para recomendar cautela.
PROPORCAO_FRACO_PARA_CONSERVADOR = 0.50


@dataclass(frozen=True, slots=True)
class JogoClassificado:
    """Classificacao de um jogo ja pontuado pelo Elite Score."""

    indice: int
    score: float
    classificacao: str


@dataclass(frozen=True, slots=True)
class EstrategiaRecomendada:
    """Estrategia recomendada para o lote de jogos analisado."""

    perfil: str
    nivel_risco: str
    justificativa: str
    potencial_teorico: float


@dataclass(frozen=True, slots=True)
class RelatorioEstrategico:
    """Relatorio estrategico completo sobre um lote de jogos ja pontuados."""

    distribuicao: dict[str, int]
    estrategia: EstrategiaRecomendada
    jogos_classificados: tuple[JogoClassificado, ...]


def classificar_score(score: float) -> str:
    """Classifica um Elite Score total (0-100) em uma das 4 faixas desta fase."""
    if score >= LIMIAR_ELITE_PREMIUM:
        return CLASSIFICACAO_ELITE_PREMIUM
    if score >= LIMIAR_ALTO_POTENCIAL:
        return CLASSIFICACAO_ALTO_POTENCIAL
    if score >= LIMIAR_NEUTRO:
        return CLASSIFICACAO_NEUTRO
    return CLASSIFICACAO_FRACO


def classificar_jogos(jogos: list[EliteScoreResultado]) -> list[JogoClassificado]:
    """Classifica cada jogo ja pontuado (``EliteScoreResultado``) numa das 4
    faixas de qualidade. Nao recalcula o Elite Score: usa apenas
    ``resultado.total``, ja produzido por ``core.elite_score``."""
    return [
        JogoClassificado(indice=indice, score=resultado.total, classificacao=classificar_score(resultado.total))
        for indice, resultado in enumerate(jogos)
    ]


def _justificativa(
    perfil: str,
    media: float,
    proporcao_fortes: float,
    proporcao_fracos: float,
    total_jogos: int,
) -> str:
    fortes_pct = f"{proporcao_fortes * 100:.0f}%"
    fracos_pct = f"{proporcao_fracos * 100:.0f}%"
    base = f"Media do Elite Score do lote: {media:.1f}/100 ({total_jogos} jogo(s) analisado(s))."

    if perfil == PERFIL_AGRESSIVO:
        return (
            f"{base} {fortes_pct} dos jogos estao em Elite Premium ou Alto Potencial, "
            f"uma maioria clara -- postura AGRESSIVA recomendada, aproveitando a forca do lote."
        )
    if perfil == PERFIL_CONSERVADOR:
        return (
            f"{base} {fracos_pct} dos jogos estao classificados como Fraco (ou a media do lote "
            f"esta abaixo de {LIMIAR_NEUTRO:.0f}) -- postura CONSERVADORA recomendada, priorizando cautela."
        )
    return (
        f"{base} Distribuicao mista entre os jogos (fortes: {fortes_pct}, fracos: {fracos_pct}), sem "
        f"sinal claro para uma postura mais agressiva ou mais conservadora -- postura EQUILIBRADA recomendada."
    )


def montar_estrategia(jogos_classificados: list[JogoClassificado]) -> EstrategiaRecomendada:
    """Define o perfil de estrategia (CONSERVADOR/EQUILIBRADO/AGRESSIVO) a
    partir da distribuicao dos scores ja classificados. Ver a docstring do
    modulo para a derivacao completa da regra de decisao."""
    total_jogos = len(jogos_classificados)

    if total_jogos == 0:
        return EstrategiaRecomendada(
            perfil=PERFIL_EQUILIBRADO,
            nivel_risco=RISCO_INDEFINIDO,
            justificativa="Nenhum jogo informado para analise -- nao ha dados suficientes para recomendar uma estrategia.",
            potencial_teorico=0.0,
        )

    media = sum(jc.score for jc in jogos_classificados) / total_jogos
    qtd_fortes = sum(1 for jc in jogos_classificados if jc.classificacao in CLASSIFICACOES_FORTES)
    qtd_fracos = sum(1 for jc in jogos_classificados if jc.classificacao == CLASSIFICACAO_FRACO)
    proporcao_fortes = qtd_fortes / total_jogos
    proporcao_fracos = qtd_fracos / total_jogos

    if media >= LIMIAR_ALTO_POTENCIAL and proporcao_fortes >= PROPORCAO_FORTE_PARA_AGRESSIVO:
        perfil = PERFIL_AGRESSIVO
        nivel_risco = RISCO_ALTO
    elif media < LIMIAR_NEUTRO or proporcao_fracos >= PROPORCAO_FRACO_PARA_CONSERVADOR:
        perfil = PERFIL_CONSERVADOR
        nivel_risco = RISCO_BAIXO
    else:
        perfil = PERFIL_EQUILIBRADO
        nivel_risco = RISCO_MEDIO

    justificativa = _justificativa(perfil, media, proporcao_fortes, proporcao_fracos, total_jogos)

    return EstrategiaRecomendada(
        perfil=perfil,
        nivel_risco=nivel_risco,
        justificativa=justificativa,
        potencial_teorico=round(media, 2),
    )


def gerar_relatorio_estrategico(jogos: list[EliteScoreResultado]) -> RelatorioEstrategico:
    """Gera o relatorio estrategico completo (distribuicao, perfil
    recomendado, justificativa, nivel de risco e potencial teorico) a partir
    de uma lista de jogos ja pontuados pelo Elite Score existente.

    Nao recalcula nenhum score nem gera jogos novos -- apenas le e agrega os
    totais ja produzidos por ``core.elite_score``/``elite_score_service``.
    """
    jogos_classificados = classificar_jogos(jogos)
    estrategia = montar_estrategia(jogos_classificados)

    distribuicao = {
        CLASSIFICACAO_ELITE_PREMIUM: 0,
        CLASSIFICACAO_ALTO_POTENCIAL: 0,
        CLASSIFICACAO_NEUTRO: 0,
        CLASSIFICACAO_FRACO: 0,
    }
    distribuicao.update(Counter(jc.classificacao for jc in jogos_classificados))

    return RelatorioEstrategico(
        distribuicao=distribuicao,
        estrategia=estrategia,
        jogos_classificados=tuple(jogos_classificados),
    )
