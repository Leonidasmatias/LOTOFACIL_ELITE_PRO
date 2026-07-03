"""Modelos de dominio do Elite Score (Phoenix V2).

O Elite Score e um indice de 0 a 100 que avalia a aderencia estatistica de um
jogo ja gerado ao padrao historico observado na base de concursos, mais um
componente de diversidade em relacao aos outros jogos do mesmo lote. Ele NAO
influencia a geracao de jogos (Motor Elite) nem altera nenhuma regra
matematica existente -- e uma camada de analise que roda depois do jogo ja
estar pronto.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FaixaHistorica:
    """Estatisticas empiricas (min, p10, p90, max) de uma metrica, calculadas
    a partir da base de concursos ja sorteados."""

    minimo: float
    p10: float
    p90: float
    maximo: float


@dataclass(frozen=True, slots=True)
class ReferenciasEliteScore:
    """Faixas historicas usadas como referencia para pontuar um jogo.

    Calculadas uma unica vez por base de dados (``construir_referencias``em
    ``src/core/elite_score.py``) e reaproveitadas para pontuar todos os jogos
    de um mesmo lote, evitando recalculo repetido."""

    pares: FaixaHistorica
    centro: FaixaHistorica
    max_linha_coluna: FaixaHistorica
    soma: FaixaHistorica
    repeticao: FaixaHistorica
    frequencia_media: FaixaHistorica
    atraso_medio: FaixaHistorica
    # Valores por dezena (1-25), necessarios para calcular a media de
    # frequencia/atraso das 15 dezenas de um jogo especifico.
    frequencia_por_dezena: dict[int, float]
    atraso_por_dezena: dict[int, float]


@dataclass(frozen=True, slots=True)
class ComponenteEliteScore:
    """Um dos componentes que formam o Elite Score de um jogo."""

    nome: str
    descricao: str
    valor_jogo: float
    faixa_tipica: tuple[float, float]  # (p10, p90) da metrica na base historica
    sub_score: float  # 0-100
    peso: float  # 0-1
    contribuicao: float  # peso * sub_score, em pontos (0-100 * peso)


@dataclass(frozen=True, slots=True)
class EliteScoreResultado:
    """Resultado completo do Elite Score de um jogo: total + detalhamento."""

    total: float  # 0-100
    componentes: tuple[ComponenteEliteScore, ...]

    def explicacao_resumida(self) -> str:
        """Texto curto listando os componentes que mais e menos contribuiram
        em PONTOS (peso x sub-score) para o total -- e nao apenas o sub-score
        isolado, para nao dar a impressao enganosa de que um componente com
        sub-score 100 mas peso baixo "foi mal" (ele so pesa pouco no total)."""
        ordenados = sorted(self.componentes, key=lambda c: c.contribuicao, reverse=True)
        partes = [f"Elite Score {self.total:.1f}/100."]

        def _fmt(c: ComponenteEliteScore) -> str:
            return f"{c.nome} ({c.contribuicao:.1f} pts = {c.peso * 100:.0f}% peso x {c.sub_score:.0f}/100 sub-score)"

        melhores = ordenados[:2]
        piores = ordenados[-2:]
        partes.append("Maiores contribuicoes: " + ", ".join(_fmt(c) for c in melhores) + ".")
        partes.append("Menores contribuicoes: " + ", ".join(_fmt(c) for c in piores) + ".")
        return " ".join(partes)
