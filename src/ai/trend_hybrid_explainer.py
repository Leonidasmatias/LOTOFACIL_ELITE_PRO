"""Trend Hybrid Explainer (Fase Trend Hybrid V1 - Passo 6: Explicabilidade).

Camada de explicacao textual/estruturada sobre um ``BilheteTrendHybrid`` ja
gerado por ``core.trend_hybrid_engine``. Este modulo NAO recalcula nada: le
apenas os indicadores e o Trend Score ja calculados (``DezenaPontuada``) e
traduz esses numeros numa explicacao legivel, por dezena (selecionada ou
descartada) e um resumo do bilhete inteiro.

Regras respeitadas (mesmo espirito de ``src/ai/elite_explainer.py``):
  - NAO altera nenhum valor do Trend Score, do Elite Score ou do bilhete;
  - So le dados ja produzidos por ``core.trend_hybrid_engine``;
  - 100% local e deterministico: mesma entrada -> mesma explicacao sempre,
    sem nenhuma chamada de rede, API externa ou modelo de IA generativa.
    "Explicabilidade" aqui significa "explicacao por regras transparentes e
    reproduziveis" (mesma definicao usada no restante do projeto), nao um
    modelo de machine learning -- ver ``docs/TREND_HYBRID_ENGINE.md`` para os
    pontos de extensao pensados para ML futuro.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..models.trend_hybrid import BilheteTrendHybrid, DezenaPontuada


@dataclass(frozen=True, slots=True)
class ExplicacaoDezena:
    """Explicacao de uma dezena especifica dentro de um bilhete Trend
    Hybrid: por que foi selecionada, ou por que foi descartada."""

    dezena: int
    grupo: str
    selecionada: bool
    trend_score: float
    frequencia_ult10: int
    atraso: int
    momentum: float
    regularidade: float
    motivo: str


@dataclass(frozen=True, slots=True)
class ExplicacaoBilheteTrendHybrid:
    """Explicacao completa de um bilhete: resumo textual + explicacao de
    cada uma das 25 dezenas (15 selecionadas + 10 descartadas)."""

    resumo: str
    selecionadas: tuple[ExplicacaoDezena, ...]
    descartadas: tuple[ExplicacaoDezena, ...]


def _explicacao(pontuada: DezenaPontuada, grupo: str, selecionada: bool, motivo: str) -> ExplicacaoDezena:
    indicador = pontuada.indicadores
    return ExplicacaoDezena(
        dezena=indicador.dezena,
        grupo=grupo,
        selecionada=selecionada,
        trend_score=pontuada.trend_score,
        frequencia_ult10=indicador.frequencia_ult10,
        atraso=indicador.atraso,
        momentum=indicador.momentum,
        regularidade=indicador.regularidade,
        motivo=motivo,
    )


def _motivo_selecao(pontuada: DezenaPontuada, grupo: str, posicao_no_grupo: int) -> str:
    indicador = pontuada.indicadores
    origem = "saiu no último concurso (Grupo A)" if grupo == "A" else "não saiu no último concurso (Grupo B)"
    return (
        f"Selecionada ({posicao_no_grupo}º melhor Trend Score do Grupo {grupo}, {origem}): "
        f"score {pontuada.trend_score:.1f}/100, frequência nos últimos 10 concursos = {indicador.frequencia_ult10}, "
        f"atraso = {indicador.atraso} concurso(s), momentum = {indicador.momentum:+.3f}, "
        f"regularidade = {indicador.regularidade:.3f}."
    )


def _motivo_rejeicao(pontuada: DezenaPontuada, grupo: str, posicao_no_grupo: int, corte: int) -> str:
    return (
        f"Descartada ({posicao_no_grupo}º colocada no Grupo {grupo}, abaixo do corte de {corte} dezena(s) "
        f"exigido pela divisão do bilhete): Trend Score {pontuada.trend_score:.1f}/100, inferior ao das "
        "dezenas selecionadas do mesmo grupo."
    )


def explicar_bilhete(bilhete: BilheteTrendHybrid) -> ExplicacaoBilheteTrendHybrid:
    """Explica cada uma das 25 dezenas de um bilhete Trend Hybrid ja
    gerado (15 selecionadas + 10 descartadas), sem recalcular nenhum valor:
    usa apenas ``bilhete.pontuacoes`` (Trend Score e indicadores já
    calculados por ``core.trend_hybrid_engine``)."""
    por_dezena = {pontuada.indicadores.dezena: pontuada for pontuada in bilhete.pontuacoes}
    n_a, n_b = bilhete.divisao

    selecionadas: list[ExplicacaoDezena] = []
    for posicao, dezena in enumerate(
        sorted(bilhete.grupo_a_selecionadas, key=lambda d: -por_dezena[d].trend_score), start=1
    ):
        pontuada = por_dezena[dezena]
        selecionadas.append(_explicacao(pontuada, "A", True, _motivo_selecao(pontuada, "A", posicao)))
    for posicao, dezena in enumerate(
        sorted(bilhete.grupo_b_selecionadas, key=lambda d: -por_dezena[d].trend_score), start=1
    ):
        pontuada = por_dezena[dezena]
        selecionadas.append(_explicacao(pontuada, "B", True, _motivo_selecao(pontuada, "B", posicao)))

    descartadas: list[ExplicacaoDezena] = []
    for posicao, dezena in enumerate(
        sorted(bilhete.grupo_a_descartadas, key=lambda d: -por_dezena[d].trend_score), start=n_a + 1
    ):
        pontuada = por_dezena[dezena]
        descartadas.append(_explicacao(pontuada, "A", False, _motivo_rejeicao(pontuada, "A", posicao, n_a)))
    for posicao, dezena in enumerate(
        sorted(bilhete.grupo_b_descartadas, key=lambda d: -por_dezena[d].trend_score), start=n_b + 1
    ):
        pontuada = por_dezena[dezena]
        descartadas.append(_explicacao(pontuada, "B", False, _motivo_rejeicao(pontuada, "B", posicao, n_b)))

    if bilhete.margem_busca > 0:
        nota_busca = (
            f"Margem de busca {bilhete.margem_busca}: a combinação pura (top-{n_a} do Grupo A + top-{n_b} do "
            "Grupo B) não satisfez as regras de validação (soma, pares ou sequência), então a busca foi ampliada "
            "até encontrar a combinação de maior Trend Score que respeita todas as regras."
        )
    else:
        nota_busca = (
            f"A combinação pura (top-{n_a} do Grupo A + top-{n_b} do Grupo B) já satisfez todas as regras de "
            "validação (margem de busca 0)."
        )
    resumo = (
        f"Bilhete Trend Hybrid {n_a}+{n_b}: {n_a} dezena(s) do Grupo A (saiu no último concurso) + "
        f"{n_b} dezena(s) do Grupo B (não saiu), Trend Score total {bilhete.trend_score_total:.1f}. {nota_busca}"
    )
    return ExplicacaoBilheteTrendHybrid(resumo=resumo, selecionadas=tuple(selecionadas), descartadas=tuple(descartadas))
