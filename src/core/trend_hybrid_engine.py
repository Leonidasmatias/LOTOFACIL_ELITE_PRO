"""Trend Hybrid Engine (9+6): geracao de bilhete por Trend Score.

Fase Trend Hybrid V1. Camada de regras de negocio puras (``core``): sem
Streamlit, sem I/O de arquivo/rede, 100% deterministico -- a mesma base
historica e os mesmos pesos sempre produzem o mesmo Trend Score e o mesmo
bilhete.

Ideia central (especificacao "Trend Hybrid Engine 9+6"):

  1. Calcula um Trend Score (0-100) para cada uma das 25 dezenas, combinando
     frequencia em varias janelas (10/20/50/100 concursos), frequencia
     historica, atraso, regularidade de aparicao, momentum (tendencia
     recente vs. historica), sequencia de aparicoes consecutivas e
     persistencia ao longo do historico (ver ``PesosTendencia`` em
     ``src/models/trend_hybrid.py`` para os pesos).
  2. Separa as 25 dezenas em Grupo A (as 15 do ultimo concurso conhecido) e
     Grupo B (as 10 que nao saiu).
  3. Seleciona as N melhores de cada grupo pelo Trend Score (divisao padrao
     9+6, configuravel) e monta o bilhete de 15 dezenas, validando com as
     mesmas regras ja usadas pelo Motor Elite (``ConfiguracaoMotor``/
     ``validar_jogo`` -- nao duplica nenhuma regra de validacao).

Sem vazamento temporal: toda a logica de indicadores e alimentada por um
estado incremental (``_EstadoTendencia``) processado em uma UNICA passada
O(n) sobre o historico (mesmo padrao de ``preparar_estados`` em
``scripts/backtest_elite_score_v35.py``), nunca usando o concurso-alvo nos
proprios indicadores. Isso permite reaproveitar exatamente a mesma logica
tanto para gerar o bilhete "de hoje" (``gerar_bilhete_trend_hybrid``) quanto
para o backtest historico (``core.trend_hybrid_backtest``), sem duplicar
codigo.

Pronto para IA futura (Fase 10 da especificacao): os indicadores brutos
(``IndicadoresDezena``) e os pesos (``PesosTendencia``) sao a superficie de
extensao pensada para um modelo de Machine Learning substituir o calculo
manual do Trend Score no futuro -- ver ``docs/TREND_HYBRID_ENGINE.md``. Nada
disso e implementado nesta fase.
"""
from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass, field
from itertools import combinations

import pandas as pd

from .estatisticas import TODAS_DEZENAS
from ..models.trend_hybrid import BilheteTrendHybrid, DezenaPontuada, IndicadoresDezena, PesosTendencia
from ..repository.base_repository import COLUNAS_DEZENAS
from ..validacao_jogos import ConfiguracaoMotor, validar_jogo


MOTOR_TREND_HYBRID = "TREND_HYBRID_ENGINE_V1"

JANELAS_FREQUENCIA = (10, 20, 50, 100)
TAMANHO_BLOCO_PERSISTENCIA = 50

DIVISAO_PADRAO: tuple[int, int] = (9, 6)
DIVISOES_SUPORTADAS: tuple[tuple[int, int], ...] = ((8, 7), (9, 6), (10, 5), (11, 4))


@dataclass
class _EstadoTendencia:
    """Estado incremental mutavel usado apenas internamente por este modulo
    (nao e um modelo de dominio -- por isso nao vive em ``src/models``).
    Cada instancia representa "o que se sabe" logo apos processar um
    conjunto de concursos, o suficiente para calcular os indicadores do
    PROXIMO concurso (ainda nao processado)."""

    freq_geral: Counter = field(default_factory=Counter)
    janelas: dict[int, deque] = field(
        default_factory=lambda: {janela: deque(maxlen=janela) for janela in JANELAS_FREQUENCIA}
    )
    freq_janelas: dict[int, Counter] = field(
        default_factory=lambda: {janela: Counter() for janela in JANELAS_FREQUENCIA}
    )
    ultimo_indice_visto: dict[int, int] = field(default_factory=lambda: {d: -1 for d in TODAS_DEZENAS})
    soma_gap: dict[int, float] = field(default_factory=lambda: {d: 0.0 for d in TODAS_DEZENAS})
    soma_gap2: dict[int, float] = field(default_factory=lambda: {d: 0.0 for d in TODAS_DEZENAS})
    n_gaps: dict[int, int] = field(default_factory=lambda: {d: 0 for d in TODAS_DEZENAS})
    streak_atual: dict[int, int] = field(default_factory=lambda: {d: 0 for d in TODAS_DEZENAS})
    streak_maximo: dict[int, int] = field(default_factory=lambda: {d: 0 for d in TODAS_DEZENAS})
    bloco_tem_dezena: dict[int, bool] = field(default_factory=lambda: {d: False for d in TODAS_DEZENAS})
    blocos_completos: int = 0
    blocos_com_dezena: dict[int, int] = field(default_factory=lambda: {d: 0 for d in TODAS_DEZENAS})
    dezenas_anteriores: frozenset[int] = frozenset()

    def indicadores(self, indice_atual: int) -> dict[int, IndicadoresDezena]:
        """Indicadores validos para prever o concurso em ``indice_atual``,
        calculados usando somente os concursos ja processados (0..indice_atual-1)."""
        resultado: dict[int, IndicadoresDezena] = {}
        for dezena in TODAS_DEZENAS:
            visto = self.ultimo_indice_visto[dezena]
            atraso = (indice_atual - 1 - visto) if visto >= 0 else indice_atual
            n_gaps = self.n_gaps[dezena]
            media_gap = (self.soma_gap[dezena] / n_gaps) if n_gaps else 0.0
            if n_gaps >= 1 and media_gap > 0:
                variancia = max(0.0, (self.soma_gap2[dezena] / n_gaps) - media_gap**2)
                coeficiente_variacao = (variancia**0.5) / media_gap
                regularidade = 1.0 / (1.0 + coeficiente_variacao)
            else:
                regularidade = 0.0
            freq10 = self.freq_janelas[10][dezena]
            freq50 = self.freq_janelas[50][dezena]
            momentum = (freq10 / 10.0) - (freq50 / 50.0)
            if self.blocos_completos > 0:
                persistencia = self.blocos_com_dezena[dezena] / self.blocos_completos
            else:
                persistencia = (self.freq_geral[dezena] / indice_atual) if indice_atual else 0.0
            resultado[dezena] = IndicadoresDezena(
                dezena=dezena,
                frequencia_ult10=self.freq_janelas[10][dezena],
                frequencia_ult20=self.freq_janelas[20][dezena],
                frequencia_ult50=self.freq_janelas[50][dezena],
                frequencia_ult100=self.freq_janelas[100][dezena],
                frequencia_geral=self.freq_geral[dezena],
                atraso=atraso,
                regularidade=round(regularidade, 6),
                momentum=round(momentum, 6),
                sequencia_consecutiva=self.streak_maximo[dezena],
                persistencia=round(persistencia, 6),
                saiu_no_ultimo=dezena in self.dezenas_anteriores,
            )
        return resultado

    def processar(self, indice: int, dezenas: set[int]) -> None:
        """Absorve o concurso em ``indice`` (dezenas sorteadas) no estado,
        preparando os indicadores para o PROXIMO concurso."""
        for dezena in TODAS_DEZENAS:
            presente = dezena in dezenas
            if presente:
                visto = self.ultimo_indice_visto[dezena]
                if visto >= 0:
                    gap = indice - visto
                    self.soma_gap[dezena] += gap
                    self.soma_gap2[dezena] += gap * gap
                    self.n_gaps[dezena] += 1
                self.ultimo_indice_visto[dezena] = indice
                self.freq_geral[dezena] += 1
                self.bloco_tem_dezena[dezena] = True
            estava_no_anterior = dezena in self.dezenas_anteriores
            if presente and estava_no_anterior:
                self.streak_atual[dezena] += 1
            elif presente:
                self.streak_atual[dezena] = 1
            else:
                self.streak_atual[dezena] = 0
            self.streak_maximo[dezena] = max(self.streak_maximo[dezena], self.streak_atual[dezena])
        for janela, fila in self.janelas.items():
            if len(fila) == fila.maxlen:
                for dezena in fila[0]:
                    self.freq_janelas[janela][dezena] -= 1
            fila.append(tuple(sorted(dezenas)))
            for dezena in dezenas:
                self.freq_janelas[janela][dezena] += 1
        self.dezenas_anteriores = frozenset(dezenas)
        if (indice + 1) % TAMANHO_BLOCO_PERSISTENCIA == 0:
            self.blocos_completos += 1
            for dezena in TODAS_DEZENAS:
                if self.bloco_tem_dezena[dezena]:
                    self.blocos_com_dezena[dezena] += 1
                self.bloco_tem_dezena[dezena] = False


def iterar_estados_trend_hybrid(df: pd.DataFrame):
    """Gera, em uma UNICA passada O(n), para cada concurso a partir do
    segundo (indice >= 1) da base ordenada, uma tupla
    ``(indice, linha_do_concurso, indicadores, ultimo_jogo)`` calculada
    usando somente os concursos anteriores -- nunca o proprio concurso-alvo.

    Uso tipico: backtest temporal (``core.trend_hybrid_backtest``), onde
    cada concurso historico e previsto usando apenas o passado dele.
    """
    dados = df.sort_values("Concurso").reset_index(drop=True)
    estado = _EstadoTendencia()
    for indice in range(len(dados)):
        if indice >= 1:
            yield indice, dados.iloc[indice], estado.indicadores(indice), estado.dezenas_anteriores
        row = dados.iloc[indice]
        dezenas = {int(row[coluna]) for coluna in COLUNAS_DEZENAS}
        estado.processar(indice, dezenas)


def indicadores_para_proximo_concurso(df: pd.DataFrame) -> tuple[dict[int, IndicadoresDezena], frozenset[int]]:
    """Processa TODA a base historica e devolve os indicadores prontos para
    prever o proximo concurso (ainda nao sorteado), junto com o conjunto de
    dezenas do ultimo concurso conhecido (o Grupo A do Trend Hybrid)."""
    dados = df.sort_values("Concurso").reset_index(drop=True)
    if dados.empty:
        raise ValueError("A base historica esta vazia.")
    estado = _EstadoTendencia()
    for indice in range(len(dados)):
        row = dados.iloc[indice]
        dezenas = {int(row[coluna]) for coluna in COLUNAS_DEZENAS}
        estado.processar(indice, dezenas)
    return estado.indicadores(len(dados)), estado.dezenas_anteriores


def _normalizar(valores: dict[int, float]) -> dict[int, float]:
    minimo, maximo = min(valores.values()), max(valores.values())
    amplitude = maximo - minimo
    return {dezena: ((valor - minimo) / amplitude if amplitude else 0.5) for dezena, valor in valores.items()}


def calcular_trend_scores(
    indicadores: dict[int, IndicadoresDezena],
    pesos: PesosTendencia | None = None,
) -> dict[int, DezenaPontuada]:
    """Normaliza (min-max entre as 25 dezenas) cada indicador bruto e aplica
    os pesos efetivos de ``PesosTendencia`` para obter o Trend Score
    (0-100) de cada dezena. Puro: nao le nem escreve nada, apenas transforma
    os indicadores ja calculados por ``_EstadoTendencia.indicadores``."""
    pesos = pesos or PesosTendencia()
    efetivos = pesos.pesos_efetivos()
    brutos: dict[str, dict[int, float]] = {
        "ult10": {d: float(v.frequencia_ult10) for d, v in indicadores.items()},
        "ult20": {d: float(v.frequencia_ult20) for d, v in indicadores.items()},
        "ult50": {d: float(v.frequencia_ult50) for d, v in indicadores.items()},
        "ult100": {d: float(v.frequencia_ult100) for d, v in indicadores.items()},
        "historico": {d: float(v.frequencia_geral) for d, v in indicadores.items()},
        "regularidade": {d: float(v.regularidade) for d, v in indicadores.items()},
        "momentum": {d: float(v.momentum) for d, v in indicadores.items()},
        "persistencia": {d: float(v.persistencia) for d, v in indicadores.items()},
        "atraso": {d: float(v.atraso) for d, v in indicadores.items()},
    }
    normalizados_por_dezena: dict[int, dict[str, float]] = {d: {} for d in indicadores}
    for chave, valores in brutos.items():
        for dezena, valor_normalizado in _normalizar(valores).items():
            normalizados_por_dezena[dezena][chave] = valor_normalizado
    resultado: dict[int, DezenaPontuada] = {}
    for dezena, indicador in indicadores.items():
        score = sum(normalizados_por_dezena[dezena][chave] * peso for chave, peso in efetivos.items())
        resultado[dezena] = DezenaPontuada(
            indicadores=indicador,
            normalizados=normalizados_por_dezena[dezena],
            trend_score=round(score * 100.0, 4),
        )
    return resultado


def selecionar_bilhete(
    pontuacoes: dict[int, DezenaPontuada],
    ultimo_jogo: set[int] | frozenset[int],
    divisao: tuple[int, int] = DIVISAO_PADRAO,
    configuracao: ConfiguracaoMotor | None = None,
) -> BilheteTrendHybrid:
    """Monta o bilhete de 15 dezenas: as ``divisao[0]`` melhores do Grupo A
    (saiu no ultimo concurso) + as ``divisao[1]`` melhores do Grupo B (nao
    saiu), pelo maior Trend Score.

    Repeticao (dezenas do Grupo A) fica sempre EXATAMENTE em ``divisao[0]``
    por construcao -- por isso a checagem de ``repetidas_minimo``/
    ``repetidas_maximo`` de ``ConfiguracaoMotor`` e automaticamente
    respeitada para qualquer uma das ``DIVISOES_SUPORTADAS`` (7-12 por
    padrao). As demais regras (soma, pares, sequencia maxima) podem, em
    casos raros, nao ser satisfeitas pelo top-N puro; nesse caso a funcao
    amplia a busca em margens crescentes (top-(N+1), top-(N+2), ...) dentro
    de cada grupo e escolhe, entre as combinacoes validas, a de maior Trend
    Score total -- nunca sorteio aleatorio puro, sempre a melhor combinacao
    estatisticamente suportada dentro da margem necessaria."""
    n_a, n_b = divisao
    if n_a + n_b != 15:
        raise ValueError("A divisao (Grupo A + Grupo B) precisa somar 15.")
    if n_a <= 0 or n_b <= 0:
        raise ValueError("Cada grupo precisa contribuir com pelo menos 1 dezena.")
    config = configuracao or ConfiguracaoMotor()
    config.validar()

    ultimo_jogo = frozenset(int(d) for d in ultimo_jogo)
    grupo_a = sorted(ultimo_jogo, key=lambda d: (-pontuacoes[d].trend_score, d))
    grupo_b = sorted((d for d in TODAS_DEZENAS if d not in ultimo_jogo), key=lambda d: (-pontuacoes[d].trend_score, d))
    if len(grupo_a) < n_a or len(grupo_b) < n_b:
        raise ValueError("Grupos insuficientes para a divisao solicitada (o Grupo A precisa ter 15 dezenas e o Grupo B, 10).")

    margem_maxima = max(len(grupo_a) - n_a, len(grupo_b) - n_b)
    for margem in range(margem_maxima + 1):
        pool_a = grupo_a[: min(len(grupo_a), n_a + margem)]
        pool_b = grupo_b[: min(len(grupo_b), n_b + margem)]
        melhor: tuple[float, tuple[int, ...], tuple[int, ...], tuple[int, ...]] | None = None
        for combinacao_a in combinations(pool_a, n_a):
            score_a = sum(pontuacoes[d].trend_score for d in combinacao_a)
            for combinacao_b in combinations(pool_b, n_b):
                jogo = tuple(sorted(combinacao_a + combinacao_b))
                try:
                    validar_jogo(jogo, config, ultimo_jogo)
                except ValueError:
                    continue
                score_total = score_a + sum(pontuacoes[d].trend_score for d in combinacao_b)
                if melhor is None or score_total > melhor[0]:
                    melhor = (score_total, jogo, combinacao_a, combinacao_b)
        if melhor is not None:
            score_total, jogo, escolhidas_a, escolhidas_b = melhor
            conjunto_a, conjunto_b = set(escolhidas_a), set(escolhidas_b)
            todas_pontuacoes = tuple(
                sorted(pontuacoes.values(), key=lambda p: (-p.trend_score, p.indicadores.dezena))
            )
            return BilheteTrendHybrid(
                dezenas=jogo,
                divisao=(n_a, n_b),
                grupo_a_selecionadas=tuple(sorted(conjunto_a)),
                grupo_b_selecionadas=tuple(sorted(conjunto_b)),
                grupo_a_descartadas=tuple(d for d in grupo_a if d not in conjunto_a),
                grupo_b_descartadas=tuple(d for d in grupo_b if d not in conjunto_b),
                margem_busca=margem,
                trend_score_total=round(score_total, 4),
                pontuacoes=todas_pontuacoes,
            )
    raise ValueError(
        "Nao foi possivel formar um bilhete valido para a divisao "
        f"{divisao} mesmo expandindo a busca ao maximo -- revise ConfiguracaoMotor."
    )


def gerar_trend_scores(df: pd.DataFrame, pesos: PesosTendencia | None = None) -> pd.DataFrame:
    """Ranking das 25 dezenas pelo Trend Score, pronto para exibicao (mesmo
    formato de ``motor_elite_v2.ranking_dezenas_v2``): usa toda a base para
    prever o proximo concurso ainda nao sorteado."""
    indicadores, _ = indicadores_para_proximo_concurso(df)
    pontuacoes = calcular_trend_scores(indicadores, pesos)
    linhas = []
    for dezena, pontuada in pontuacoes.items():
        indicador = pontuada.indicadores
        linhas.append(
            {
                "Dezena": dezena,
                "Trend Score": pontuada.trend_score,
                "Frequência últimos 10": indicador.frequencia_ult10,
                "Frequência últimos 20": indicador.frequencia_ult20,
                "Frequência últimos 50": indicador.frequencia_ult50,
                "Frequência últimos 100": indicador.frequencia_ult100,
                "Frequência histórica": indicador.frequencia_geral,
                "Atraso": indicador.atraso,
                "Regularidade": indicador.regularidade,
                "Momentum": indicador.momentum,
                "Sequência consecutiva": indicador.sequencia_consecutiva,
                "Persistência": indicador.persistencia,
                "Saiu no último": indicador.saiu_no_ultimo,
            }
        )
    ranking = pd.DataFrame(linhas).sort_values(["Trend Score", "Dezena"], ascending=[False, True]).reset_index(drop=True)
    ranking.insert(0, "Posição", range(1, len(ranking) + 1))
    return ranking


def gerar_bilhete_trend_hybrid(
    df: pd.DataFrame,
    divisao: tuple[int, int] = DIVISAO_PADRAO,
    pesos: PesosTendencia | None = None,
    configuracao: ConfiguracaoMotor | None = None,
) -> BilheteTrendHybrid:
    """Ponto de entrada principal: gera o bilhete Trend Hybrid para o
    proximo concurso (ainda nao sorteado), usando toda a base historica
    disponivel."""
    indicadores, ultimo_jogo = indicadores_para_proximo_concurso(df)
    pontuacoes = calcular_trend_scores(indicadores, pesos)
    return selecionar_bilhete(pontuacoes, ultimo_jogo, divisao, configuracao)
