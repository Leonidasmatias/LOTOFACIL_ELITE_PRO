"""Backtest temporal e otimizacao de divisao do Trend Hybrid Engine.

Fase Trend Hybrid V1 (Passos 7 e 8 da especificacao: Backtest e Otimizacao).
Usa exclusivamente ``core.trend_hybrid_engine`` -- nenhuma formula de Trend
Score ou de selecao de bilhete e duplicada aqui. Cada concurso historico e
previsto usando SOMENTE concursos anteriores a ele (mesma garantia de
"sem vazamento temporal" do restante do projeto, ver
``laboratorio_estatistico.executar_laboratorio`` e
``scripts/backtest_elite_score_v35.py``), atraves de uma unica passada O(n)
sobre a base (``iterar_estados_trend_hybrid``).

100% local e deterministico: mesma base + mesma divisao + mesmos pesos ->
mesmo resultado sempre, sem nenhuma chamada de rede ou modelo de IA.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .trend_hybrid_engine import (
    DIVISAO_PADRAO,
    DIVISOES_SUPORTADAS,
    calcular_trend_scores,
    iterar_estados_trend_hybrid,
    selecionar_bilhete,
)
from ..models.trend_hybrid import PesosTendencia
from ..repository.base_repository import COLUNAS_DEZENAS
from ..validacao_jogos import ConfiguracaoMotor

LIMIAR_ACERTO_PREMIADO = 11
FAIXAS_PREMIACAO = (11, 12, 13, 14, 15)


@dataclass(frozen=True, slots=True)
class ResultadoBacktestTrendHybrid:
    """Resultado do backtest temporal do Trend Hybrid Engine para UMA
    divisao (ex.: 9+6)."""

    divisao: tuple[int, int]
    detalhes: pd.DataFrame
    resumo: dict

    def csv_bytes(self) -> bytes:
        return self.detalhes.to_csv(index=False).encode("utf-8-sig")


def _maior_sequencia(valores: list[bool]) -> int:
    maior = atual = 0
    for valor in valores:
        atual = atual + 1 if valor else 0
        maior = max(maior, atual)
    return maior


def executar_backtest_trend_hybrid(
    df: pd.DataFrame,
    divisao: tuple[int, int] = DIVISAO_PADRAO,
    pesos: PesosTendencia | None = None,
    configuracao: ConfiguracaoMotor | None = None,
    historico_minimo: int = 100,
    quantidade_concursos: int | None = None,
) -> ResultadoBacktestTrendHybrid:
    """Executa o backtest temporal do Trend Hybrid Engine para uma divisao.

    ``historico_minimo``: quantos concursos iniciais sao pulados antes de
    comecar a avaliar (indicadores como frequencia nos ultimos 100 concursos
    ou persistencia por blocos de 50 exigem alguma profundidade de historico
    para nao ficarem degenerados).
    ``quantidade_concursos``: quando informado, avalia apenas os N concursos
    mais recentes (uso tipico: backtest rapido na UI). Quando ``None``,
    avalia TODO o historico disponivel apos ``historico_minimo`` (uso tipico:
    ``scripts/backtest_trend_hybrid.py``, que roda offline).
    """
    dados = df.sort_values("Concurso").reset_index(drop=True)
    total = len(dados)
    if total <= historico_minimo:
        raise ValueError("Base insuficiente para o backtest do Trend Hybrid Engine.")
    inicio = historico_minimo
    if quantidade_concursos is not None:
        inicio = max(historico_minimo, total - max(1, int(quantidade_concursos)))

    registros = []
    for indice, row, indicadores, ultimo_jogo in iterar_estados_trend_hybrid(dados):
        if indice < inicio:
            continue
        pontuacoes = calcular_trend_scores(indicadores, pesos)
        bilhete = selecionar_bilhete(pontuacoes, ultimo_jogo, divisao, configuracao)
        sorteadas = {int(row[coluna]) for coluna in COLUNAS_DEZENAS}
        acertos = len(set(bilhete.dezenas) & sorteadas)
        registros.append(
            {
                "Concurso": int(row["Concurso"]),
                "Data": row["Data"],
                "Divisão": f"{divisao[0]}+{divisao[1]}",
                "Acertos": acertos,
                "Margem de busca": bilhete.margem_busca,
                "Trend Score total": bilhete.trend_score_total,
                "Dezenas": "-".join(f"{d:02d}" for d in bilhete.dezenas),
            }
        )
    if not registros:
        raise ValueError("Nenhum concurso avaliado -- ajuste historico_minimo/quantidade_concursos.")

    detalhes = pd.DataFrame(registros)
    acertos_serie = detalhes["Acertos"]
    sequencia_premiada = _maior_sequencia((acertos_serie >= LIMIAR_ACERTO_PREMIADO).tolist())
    sequencia_sem_premio = _maior_sequencia((acertos_serie < LIMIAR_ACERTO_PREMIADO).tolist())
    resumo = {
        "Divisão": f"{divisao[0]}+{divisao[1]}",
        "Concursos avaliados": int(len(detalhes)),
        "Melhor acerto": int(acertos_serie.max()),
        "Pior acerto": int(acertos_serie.min()),
        "Média de acertos": round(float(acertos_serie.mean()), 4),
        "Desvio padrão": round(float(acertos_serie.std(ddof=0)), 4),
        **{f"Jogos {faixa}+": int((acertos_serie >= faixa).sum()) for faixa in FAIXAS_PREMIACAO},
        **{f"Taxa {faixa}+ (%)": round(float((acertos_serie >= faixa).mean() * 100), 4) for faixa in FAIXAS_PREMIACAO},
        "Maior sequência premiada (11+)": int(sequencia_premiada),
        "Maior sequência sem prêmio (<11)": int(sequencia_sem_premio),
        "Margem de busca média": round(float(detalhes["Margem de busca"].mean()), 4),
    }
    return ResultadoBacktestTrendHybrid(divisao=divisao, detalhes=detalhes, resumo=resumo)


def otimizar_divisao(
    df: pd.DataFrame,
    divisoes: tuple[tuple[int, int], ...] = DIVISOES_SUPORTADAS,
    pesos: PesosTendencia | None = None,
    configuracao: ConfiguracaoMotor | None = None,
    historico_minimo: int = 100,
    quantidade_concursos: int | None = None,
) -> tuple[pd.DataFrame, tuple[int, int], dict[tuple[int, int], ResultadoBacktestTrendHybrid]]:
    """Compara o desempenho historico de varias divisoes Grupo A / Grupo B
    (Passo 8 da especificacao: 8+7, 9+6, 10+5, 11+4 por padrao) e devolve:

    - a tabela comparativa (uma linha por divisao);
    - a divisao com melhor desempenho medio (criterio: maior "Média de
      acertos"; empate resolvido por maior "Taxa 13+ (%)", depois maior
      "Taxa 14+ (%)");
    - o resultado completo do backtest de cada divisao, para permitir
      inspecionar os detalhes da divisao vencedora sem reprocessar.
    """
    resultados: dict[tuple[int, int], ResultadoBacktestTrendHybrid] = {}
    for divisao in divisoes:
        resultados[divisao] = executar_backtest_trend_hybrid(
            df,
            divisao=divisao,
            pesos=pesos,
            configuracao=configuracao,
            historico_minimo=historico_minimo,
            quantidade_concursos=quantidade_concursos,
        )
    comparativo = pd.DataFrame([resultado.resumo for resultado in resultados.values()])
    comparativo = comparativo.sort_values(
        ["Média de acertos", "Taxa 13+ (%)", "Taxa 14+ (%)"], ascending=[False, False, False]
    ).reset_index(drop=True)
    melhor_divisao = divisoes[0]
    melhor_chave = None
    for divisao, resultado in resultados.items():
        chave = (
            resultado.resumo["Média de acertos"],
            resultado.resumo["Taxa 13+ (%)"],
            resultado.resumo["Taxa 14+ (%)"],
        )
        if melhor_chave is None or chave > melhor_chave:
            melhor_chave = chave
            melhor_divisao = divisao
    return comparativo, melhor_divisao, resultados
