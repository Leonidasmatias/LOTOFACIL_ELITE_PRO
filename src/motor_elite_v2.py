from __future__ import annotations

from collections import Counter
from itertools import combinations
import math
import random
from types import MappingProxyType
from typing import Mapping, Protocol

import pandas as pd

from .carregar_dados import COLUNAS_DEZENAS
from .estatisticas_lotofacil import CENTRO, MOLDURA, TODAS_DEZENAS, linhas_colunas
from .validacao_jogos import ConfiguracaoMotor, sequencia_maxima, validar_carteira, validar_jogo


MOTOR_ELITE_V2 = "MOTOR_ELITE_LOTOFACIL_V2_FUNCIONAL"
PERFIS_V2 = ["Diamante", "Ouro", "Prata", "Agressivo", "Conservador"]

PESOS_PERFIS = {
    "Diamante": {"geral": 0.25, "10": 0.15, "25": 0.20, "50": 0.15, "100": 0.15, "atraso": 0.05, "ultimo": 0.05},
    "Ouro": {"geral": 0.45, "10": 0.05, "25": 0.10, "50": 0.15, "100": 0.20, "atraso": 0.03, "ultimo": 0.02},
    "Prata": {"geral": 0.10, "10": 0.30, "25": 0.25, "50": 0.15, "100": 0.10, "atraso": 0.03, "ultimo": 0.07},
    "Agressivo": {"geral": 0.15, "10": 0.08, "25": 0.12, "50": 0.12, "100": 0.13, "atraso": 0.35, "ultimo": 0.05},
    "Conservador": {"geral": 0.16, "10": 0.16, "25": 0.16, "50": 0.16, "100": 0.16, "atraso": 0.10, "ultimo": 0.10},
}


def _frequencias(df: pd.DataFrame, janela: int | None = None) -> Counter:
    dados = df.tail(janela) if janela else df
    return Counter(int(valor) for valor in dados[COLUNAS_DEZENAS].to_numpy().ravel()) if not dados.empty else Counter()


def _normalizar(valores: dict[int, float]) -> dict[int, float]:
    minimo, maximo = min(valores.values()), max(valores.values())
    amplitude = maximo - minimo
    return {d: (v - minimo) / amplitude if amplitude else 0.5 for d, v in valores.items()}


def ranking_dezenas_v2(df: pd.DataFrame, perfil: str = "Diamante") -> pd.DataFrame:
    if perfil not in PESOS_PERFIS:
        raise ValueError(f"Perfil desconhecido: {perfil}")
    dados = df.sort_values("Concurso").reset_index(drop=True)
    frequencias = {str(j): _frequencias(dados, j) for j in (10, 25, 50, 100)}
    frequencia_geral = _frequencias(dados)
    ultimo = set(int(v) for v in dados.iloc[-1][COLUNAS_DEZENAS]) if not dados.empty else set()
    atrasos = {}
    for dezena in TODAS_DEZENAS:
        indices = dados.index[dados[COLUNAS_DEZENAS].eq(dezena).any(axis=1)]
        atrasos[dezena] = len(dados) - 1 - int(indices.max()) if len(indices) else len(dados)
    normalizados = {
        "geral": _normalizar({d: float(frequencia_geral[d]) for d in TODAS_DEZENAS}),
        **{janela: _normalizar({d: float(freq[d]) for d in TODAS_DEZENAS}) for janela, freq in frequencias.items()},
        "atraso": _normalizar({d: float(atrasos[d]) for d in TODAS_DEZENAS}),
    }
    pesos = PESOS_PERFIS[perfil]
    linhas = []
    for dezena in TODAS_DEZENAS:
        score = sum(normalizados[chave][dezena] * peso for chave, peso in pesos.items() if chave != "ultimo")
        score += pesos["ultimo"] * int(dezena in ultimo)
        linhas.append({
            "Dezena": dezena,
            "Frequência histórica": int(frequencia_geral[dezena]),
            "Últimos 10": int(frequencias["10"][dezena]),
            "Últimos 25": int(frequencias["25"][dezena]),
            "Últimos 50": int(frequencias["50"][dezena]),
            "Últimos 100": int(frequencias["100"][dezena]),
            "Atraso": int(atrasos[dezena]),
            "Saiu no último": bool(dezena in ultimo),
            "Score da dezena": round(score * 100, 4),
        })
    ranking = pd.DataFrame(linhas).sort_values(["Score da dezena", "Dezena"], ascending=[False, True]).reset_index(drop=True)
    ranking.insert(0, "Posição", range(1, len(ranking) + 1))
    return ranking


def _amostra_ponderada(rng: random.Random, pesos: dict[int, float]) -> tuple[int, ...]:
    disponiveis = list(TODAS_DEZENAS)
    escolhidas = []
    for _ in range(15):
        valores = [max(0.01, pesos[d]) for d in disponiveis]
        escolha = rng.choices(disponiveis, weights=valores, k=1)[0]
        escolhidas.append(escolha)
        disponiveis.remove(escolha)
    return tuple(sorted(escolhidas))


def _score_estrutura(jogo: tuple[int, ...], ultimo: set[int], ranking: dict[int, float], config: ConfiguracaoMotor) -> tuple[float, dict]:
    soma = sum(jogo)
    pares = sum(d % 2 == 0 for d in jogo)
    repetidas = len(set(jogo) & ultimo)
    centro = len(set(jogo) & CENTRO)
    moldura = len(set(jogo) & MOLDURA)
    distribuicao = linhas_colunas(list(jogo))
    linhas = list(distribuicao["Linhas"].values())
    colunas = list(distribuicao["Colunas"].values())
    sequencia = sequencia_maxima(jogo)
    score_dezenas = sum(ranking[d] for d in jogo) / 15
    centro_soma = (config.soma_minima + config.soma_maxima) / 2
    score = score_dezenas
    score -= abs(soma - centro_soma) * 0.30
    score -= abs(pares - 7.5) * 2.0
    score -= abs(repetidas - 9) * 1.4
    score -= abs(centro - 5) * 1.6
    score -= sum(max(0, qtd - 4) for qtd in [*linhas, *colunas]) * 2.5
    score -= max(0, sequencia - 5) * 2.0
    return round(score, 4), {"Soma": soma, "Pares": pares, "Ímpares": 15 - pares, "Repetidas": repetidas, "Moldura": moldura, "Miolo": centro, "Linhas": "-".join(map(str, linhas)), "Colunas": "-".join(map(str, colunas)), "Sequência máxima": sequencia}


def _similaridade_maxima(jogo: tuple[int, ...], escolhidos: list[tuple[int, ...]]) -> int:
    return max((len(set(jogo) & set(outro)) for outro in escolhidos), default=0)


class CandidateTraceSink(Protocol):
    """Contrato estrutural (Protocol) para observadores READ-ONLY do
    processo de geracao/selecao de candidatos (LF-08). Uma implementacao
    desta interface NUNCA deve influenciar RNG, ordem de insercao, score
    ou selecao -- ela apenas RECEBE valores ja computados por
    ``gerar_jogos_v2``. Quando ``trace=None`` (padrao), nenhum metodo
    aqui e chamado e o comportamento de ``gerar_jogos_v2`` e
    identico ao anterior a esta interface existir.

    ``structure_metrics`` e sempre um ``Mapping`` congelado
    (``MappingProxyType`` sobre uma copia), nunca o dict mutavel interno
    de producao -- um observador nao tem como alterar o estado de
    candidatos de producao atraves deste parametro (LF-08A, Fase 2).

    Qualquer excecao levantada por ``record_evaluation``/
    ``record_profile_summary`` e isolada por ``gerar_jogos_v2`` -- nunca
    interrompe nem altera a execucao de producao (LF-08A, Fase 4). Um
    sink pode OPCIONALMENTE implementar ``on_trace_error(erro)`` (fora
    deste Protocol minimo) para ser notificado dessas falhas sem afetar
    producao."""

    def record_evaluation(
        self,
        *,
        profile: str,
        ticket: tuple[int, ...],
        raw_structure_score: float,
        structure_metrics: Mapping,
        similarity_to_already_selected: int,
        similarity_penalty: float,
        final_candidate_score: float,
        selected_so_far: tuple[tuple[int, ...], ...],
        candidate_generation_index: int,
        unique_candidates_so_far: int,
    ) -> None: ...

    def record_profile_summary(
        self,
        *,
        profile: str,
        attempts: int,
        valid_candidates_seen: int,
        unique_candidates_stored: int,
        early_stop_reason: str,
        selected_ticket: tuple[int, ...],
        selected_final_score: float,
    ) -> None: ...


def _registrar_trace_com_seguranca(trace: object, nome_metodo: str, **kwargs: object) -> None:
    """Chama um metodo do observador (``trace``) isolando qualquer
    excecao levantada por ele da execucao de producao (LF-08A, Fase 4):
    producao SEMPRE continua e retorna o mesmo resultado, com ou sem
    trace, com ou sem falha do observador. Se o observador expuser um
    hook opcional ``on_trace_error(erro)``, ele e notificado -- mas uma
    falha nesse hook tambem nunca pode afetar producao."""
    metodo = getattr(trace, nome_metodo)
    try:
        metodo(**kwargs)
    except Exception as erro:  # noqa: BLE001 -- isolamento deliberado do observador
        hook = getattr(trace, "on_trace_error", None)
        if callable(hook):
            try:
                hook(erro)
            except Exception:  # noqa: BLE001 -- o hook tambem nao pode afetar producao
                pass


def gerar_jogos_v2(
    df: pd.DataFrame,
    quantidade: int = 5,
    configuracao: ConfiguracaoMotor | None = None,
    semente: int | None = None,
    trace: CandidateTraceSink | None = None,
) -> pd.DataFrame:
    config = configuracao or ConfiguracaoMotor()
    config.validar()
    if df.empty:
        raise ValueError("A base histórica está vazia.")
    dados = df.sort_values("Concurso").reset_index(drop=True)
    ultimo = {int(v) for v in dados.iloc[-1][COLUNAS_DEZENAS]}
    rng = random.Random(semente)
    escolhidos: list[tuple[int, ...]] = []
    registros = []
    perfis = (PERFIS_V2 * math.ceil(quantidade / len(PERFIS_V2)))[:quantidade]
    for indice, perfil in enumerate(perfis):
        ranking_df = ranking_dezenas_v2(dados, perfil)
        ranking = ranking_df.set_index("Dezena")["Score da dezena"].to_dict()
        pesos = {d: max(1.0, ranking[d]) ** 1.35 for d in TODAS_DEZENAS}
        candidatos: dict[tuple[int, ...], tuple[float, dict]] = {}
        tentativas = max(config.candidatos_por_perfil, 100) * 3
        tentativas_realizadas = 0
        eventos_avaliacao = 0
        atingiu_limite_candidatos = False
        for _ in range(tentativas):
            tentativas_realizadas += 1
            jogo = _amostra_ponderada(rng, pesos)
            try:
                validar_jogo(jogo, config, ultimo)
            except ValueError:
                continue
            score, metricas = _score_estrutura(jogo, ultimo, ranking, config)
            similaridade = _similaridade_maxima(jogo, escolhidos)
            penalidade_similaridade = max(0, similaridade - (15 - config.diferenca_minima_entre_jogos)) * 12
            candidatos[jogo] = (score - penalidade_similaridade, metricas)
            eventos_avaliacao += 1
            if trace is not None:
                _registrar_trace_com_seguranca(
                    trace,
                    "record_evaluation",
                    profile=perfil,
                    ticket=jogo,
                    raw_structure_score=score,
                    structure_metrics=MappingProxyType(dict(metricas)),
                    similarity_to_already_selected=similaridade,
                    similarity_penalty=penalidade_similaridade,
                    final_candidate_score=score - penalidade_similaridade,
                    selected_so_far=tuple(escolhidos),
                    candidate_generation_index=tentativas_realizadas,
                    unique_candidates_so_far=len(candidatos),
                )
            if len(candidatos) >= config.candidatos_por_perfil:
                atingiu_limite_candidatos = True
                break
        ordenados = sorted(candidatos.items(), key=lambda item: (-item[1][0], item[0]))
        escolha = next((item for item in ordenados if all(len(set(item[0]) - set(outro)) >= config.diferenca_minima_entre_jogos for outro in escolhidos)), None)
        if escolha is None:
            raise ValueError(f"Não foi possível formar carteira diversa no perfil {perfil}.")
        jogo, (score, metricas) = escolha
        escolhidos.append(jogo)
        if trace is not None:
            _registrar_trace_com_seguranca(
                trace,
                "record_profile_summary",
                profile=perfil,
                attempts=tentativas_realizadas,
                valid_candidates_seen=eventos_avaliacao,
                unique_candidates_stored=len(candidatos),
                early_stop_reason="CANDIDATOS_POR_PERFIL_REACHED" if atingiu_limite_candidatos else "TENTATIVAS_EXHAUSTED",
                selected_ticket=jogo,
                selected_final_score=score,
            )
        linha = {"Perfil": perfil, "Motor": MOTOR_ELITE_V2, "Score": round(score, 4), "Dezenas": list(jogo), **metricas}
        linha["Penalidade de similaridade"] = max(0, _similaridade_maxima(jogo, escolhidos[:-1]) - 10) * 12
        for posicao, dezena in enumerate(jogo, 1):
            linha[f"Bola{posicao}"] = dezena
        registros.append(linha)
    validar_carteira(escolhidos, config, ultimo)
    return pd.DataFrame(registros)


def score_jogo_v2(jogo: list[int], df: pd.DataFrame, perfil: str = "Diamante", configuracao: ConfiguracaoMotor | None = None) -> float:
    config = configuracao or ConfiguracaoMotor()
    ultimo = {int(v) for v in df.sort_values("Concurso").iloc[-1][COLUNAS_DEZENAS]}
    ranking = ranking_dezenas_v2(df, perfil).set_index("Dezena")["Score da dezena"].to_dict()
    validar_jogo(jogo, config, ultimo)
    return _score_estrutura(tuple(sorted(jogo)), ultimo, ranking, config)[0]
