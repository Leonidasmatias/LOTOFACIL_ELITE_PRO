"""Testes de hardening do observability seam (LF-08A).

Cobrem: (1) isolamento de alias mutavel -- um sink hostil que tenta
mutar todo valor que poderia, em tese, alias-ear estado de producao;
(2) isolamento de excecao do observador -- um sink que sempre lanca
excecao NAO pode alterar o resultado/excecao de producao; (3) prova
direta de equivalencia de RNG -- nao apenas igualdade do DataFrame
final, mas da sequencia exata de estados/chamadas de
``random.Random.choices`` consumida internamente.
"""
from __future__ import annotations

import random as random_module
from typing import Callable, Mapping
from unittest.mock import patch

import pandas as pd
import pytest

from src.backtest.candidate_trace import CandidateTracer
from src.motor_elite_v2 import gerar_jogos_v2
from src.validacao_jogos import ConfiguracaoMotor


def _concurso_sintetico(numero: int) -> dict:
    brutas = sorted(((numero * 7 + i * 3) % 25) + 1 for i in range(15))
    usadas: list[int] = []
    cursor = 1
    for dezena in brutas:
        while dezena in usadas:
            dezena = cursor
            cursor += 1
            if cursor > 25:
                cursor = 1
        usadas.append(dezena)
    linha = {"Concurso": numero, "Data": f"{(numero % 28) + 1:02d}/01/2026"}
    for posicao, dezena in enumerate(sorted(usadas), start=1):
        linha[f"Bola{posicao}"] = dezena
    return linha


def _base_sintetica(quantidade: int) -> pd.DataFrame:
    return pd.DataFrame([_concurso_sintetico(n) for n in range(1, quantidade + 1)])


# ============================================================
# Fase 3: ataque de mutacao adversarial
# ============================================================


class AdversarialMutationSink:
    """Sink hostil: tenta mutar TODO valor recebido que poderia, em
    tese, aliasear estado interno de producao. Nunca deve ter sucesso
    em afetar producao -- as tentativas sao registradas para inspecao,
    mas o proprio ato de tentar nao deve propagar (excecoes de mutacao
    sao esperadas e capturadas aqui mesmo, para nao poluir o teste com
    o mecanismo de isolamento de excecao, testado separadamente)."""

    def __init__(self) -> None:
        self.tentativas: list[str] = []

    def record_evaluation(
        self,
        *,
        profile: str,
        ticket: tuple,
        raw_structure_score: float,
        structure_metrics: Mapping,
        similarity_to_already_selected: int,
        similarity_penalty: float,
        final_candidate_score: float,
        selected_so_far: tuple,
        candidate_generation_index: int,
        unique_candidates_so_far: int,
    ) -> None:
        try:
            structure_metrics["Soma"] = -999  # type: ignore[index]
            self.tentativas.append("structure_metrics_mutado")
        except (TypeError, AttributeError):
            self.tentativas.append("structure_metrics_protegido")
        try:
            structure_metrics.update({"Injetado": True})  # type: ignore[attr-defined]
            self.tentativas.append("structure_metrics_update_mutado")
        except (TypeError, AttributeError):
            self.tentativas.append("structure_metrics_update_protegido")
        try:
            selected_so_far[0] = (99, 99)  # type: ignore[index]
            self.tentativas.append("selected_so_far_mutado")
        except TypeError:
            self.tentativas.append("selected_so_far_protegido")
        try:
            selected_so_far.append((1, 2, 3))  # type: ignore[attr-defined]
            self.tentativas.append("selected_so_far_append_mutado")
        except AttributeError:
            self.tentativas.append("selected_so_far_append_protegido")
        try:
            ticket[0] = 1  # type: ignore[index]
            self.tentativas.append("ticket_mutado")
        except TypeError:
            self.tentativas.append("ticket_protegido")

    def record_profile_summary(self, **kwargs: object) -> None:
        pass


def test_ataque_de_mutacao_nao_altera_output_de_producao() -> None:
    df = _base_sintetica(60)
    esperado = gerar_jogos_v2(df, quantidade=5, semente=42)

    sink = AdversarialMutationSink()
    resultado = gerar_jogos_v2(df, quantidade=5, semente=42, trace=sink)

    assert resultado.equals(esperado)
    # todas as tentativas de mutacao devem ter sido bloqueadas pela
    # propria imutabilidade dos objetos passados -- nenhuma "mutado".
    assert all(t.endswith("protegido") for t in sink.tentativas), sink.tentativas
    assert len(sink.tentativas) > 0  # confirma que o ataque de fato ocorreu


def test_ataque_de_mutacao_nao_afeta_execucoes_subsequentes() -> None:
    """Mesmo apos um ataque, uma segunda execucao (nova instancia de
    sink, mesma seed/historico) continua produzindo o mesmo resultado
    -- prova que nenhum estado global/compartilhado foi corrompido."""
    df = _base_sintetica(60)
    sink1 = AdversarialMutationSink()
    r1 = gerar_jogos_v2(df, quantidade=5, semente=42, trace=sink1)
    r2 = gerar_jogos_v2(df, quantidade=5, semente=42)
    assert r1.equals(r2)


# ============================================================
# Fase 4/5: isolamento de excecao do observador
# ============================================================


class ExplodingTraceSink:
    """Sink hostil: toda chamada de ``record_evaluation`` levanta
    ``RuntimeError`` deterministico. Usado para provar que uma falha do
    observador nunca escapa para o chamador de ``gerar_jogos_v2``."""

    def __init__(self, explode_evaluation: bool = True, explode_summary: bool = False) -> None:
        self.explode_evaluation = explode_evaluation
        self.explode_summary = explode_summary
        self.chamadas_evaluation = 0
        self.chamadas_summary = 0
        self.erros_recebidos: list[Exception] = []

    def record_evaluation(self, **kwargs: object) -> None:
        self.chamadas_evaluation += 1
        if self.explode_evaluation:
            raise RuntimeError("falha deliberada do observador (record_evaluation)")

    def record_profile_summary(self, **kwargs: object) -> None:
        self.chamadas_summary += 1
        if self.explode_summary:
            raise RuntimeError("falha deliberada do observador (record_profile_summary)")

    def on_trace_error(self, erro: Exception) -> None:
        self.erros_recebidos.append(erro)


def test_sink_que_explode_em_record_evaluation_nao_afeta_producao() -> None:
    df = _base_sintetica(60)
    esperado = gerar_jogos_v2(df, quantidade=5, semente=42)

    sink = ExplodingTraceSink(explode_evaluation=True, explode_summary=False)
    resultado = gerar_jogos_v2(df, quantidade=5, semente=42, trace=sink)

    assert resultado.equals(esperado)
    assert sink.chamadas_evaluation > 0
    # o observador foi notificado de cada falha via on_trace_error
    assert len(sink.erros_recebidos) == sink.chamadas_evaluation
    assert all(isinstance(e, RuntimeError) for e in sink.erros_recebidos)


def test_sink_que_explode_em_record_profile_summary_nao_afeta_producao() -> None:
    df = _base_sintetica(60)
    esperado = gerar_jogos_v2(df, quantidade=5, semente=42)

    sink = ExplodingTraceSink(explode_evaluation=False, explode_summary=True)
    resultado = gerar_jogos_v2(df, quantidade=5, semente=42, trace=sink)

    assert resultado.equals(esperado)
    assert sink.chamadas_summary == 5
    assert len(sink.erros_recebidos) == 5


def test_sink_que_explode_em_ambos_nao_afeta_producao() -> None:
    df = _base_sintetica(60)
    esperado = gerar_jogos_v2(df, quantidade=5, semente=42)

    sink = ExplodingTraceSink(explode_evaluation=True, explode_summary=True)
    resultado = gerar_jogos_v2(df, quantidade=5, semente=42, trace=sink)

    assert resultado.equals(esperado)


def test_excecao_legitima_de_producao_nao_e_mascarada_por_sink_que_tambem_explode() -> None:
    """Se producao levantaria ValueError de qualquer forma (config
    impossivel), essa MESMA excecao deve continuar sendo a falha
    observada externamente -- mesmo com um sink que tambem explode."""
    df = _base_sintetica(40)
    config = ConfiguracaoMotor(diferenca_minima_entre_jogos=15, candidatos_por_perfil=50)

    with pytest.raises(ValueError, match="Não foi possível formar carteira diversa") as sem_trace:
        gerar_jogos_v2(df, quantidade=5, configuracao=config, semente=1)

    sink = ExplodingTraceSink(explode_evaluation=True, explode_summary=True)
    with pytest.raises(ValueError, match="Não foi possível formar carteira diversa") as com_trace:
        gerar_jogos_v2(df, quantidade=5, configuracao=config, semente=1, trace=sink)

    assert str(sem_trace.value) == str(com_trace.value)


def test_hook_on_trace_error_ausente_nao_quebra_isolamento() -> None:
    """Um sink que explode e NAO implementa ``on_trace_error`` (hook
    opcional) ainda assim nao pode afetar producao -- a falha e apenas
    engolida silenciosamente nesse caso, por design."""

    class ExplodingSinkSemHook:
        def record_evaluation(self, **kwargs: object) -> None:
            raise RuntimeError("sem hook de observabilidade")

        def record_profile_summary(self, **kwargs: object) -> None:
            raise RuntimeError("sem hook de observabilidade")

    df = _base_sintetica(60)
    esperado = gerar_jogos_v2(df, quantidade=5, semente=42)
    resultado = gerar_jogos_v2(df, quantidade=5, semente=42, trace=ExplodingSinkSemHook())
    assert resultado.equals(esperado)


def test_hook_on_trace_error_que_tambem_explode_nao_afeta_producao() -> None:
    class SinkComHookHostil:
        def record_evaluation(self, **kwargs: object) -> None:
            raise RuntimeError("falha primaria")

        def record_profile_summary(self, **kwargs: object) -> None:
            pass

        def on_trace_error(self, erro: Exception) -> None:
            raise RuntimeError("falha dentro do proprio hook de observabilidade")

    df = _base_sintetica(60)
    esperado = gerar_jogos_v2(df, quantidade=5, semente=42)
    resultado = gerar_jogos_v2(df, quantidade=5, semente=42, trace=SinkComHookHostil())
    assert resultado.equals(esperado)


# ============================================================
# Fase 6: prova direta de equivalencia de RNG
# ============================================================


def _capturar_chamadas_de_choices(rotulo: str, armazenamento: dict) -> Callable:
    original = random_module.Random.choices

    def wrapper(self, *args, **kwargs):
        estado_antes = self.getstate()
        args_copiados = tuple(list(a) if isinstance(a, list) else a for a in args)
        kwargs_copiados = {k: (list(v) if isinstance(v, list) else v) for k, v in kwargs.items()}
        resultado = original(self, *args, **kwargs)
        armazenamento[rotulo].append((estado_antes, args_copiados, kwargs_copiados, list(resultado)))
        return resultado

    return wrapper


def test_prova_direta_rng_sequencia_de_chamadas_identica_com_e_sem_trace() -> None:
    """Instrumenta ``random.Random.choices`` (metodo da stdlib) a partir
    do CODIGO DE TESTE apenas -- nenhuma mudanca de producao para
    viabilizar este teste. Captura, para CADA chamada real de
    ``rng.choices`` dentro de ``gerar_jogos_v2``: o estado do gerador
    IMEDIATAMENTE ANTES da chamada, os argumentos (copiados
    defensivamente) e o resultado. Compara a sequencia INTEIRA entre uma
    execucao trace-disabled e uma trace-enabled com a MESMA seed."""
    df = _base_sintetica(60)
    capturado: dict[str, list] = {"sem_trace": [], "com_trace": []}

    with patch.object(random_module.Random, "choices", _capturar_chamadas_de_choices("sem_trace", capturado)):
        gerar_jogos_v2(df, quantidade=5, semente=42)

    with patch.object(random_module.Random, "choices", _capturar_chamadas_de_choices("com_trace", capturado)):
        gerar_jogos_v2(df, quantidade=5, semente=42, trace=CandidateTracer())

    assert len(capturado["sem_trace"]) > 0
    assert len(capturado["sem_trace"]) == len(capturado["com_trace"])
    assert capturado["sem_trace"] == capturado["com_trace"]

    # estado FINAL do gerador (apos a ultima chamada) tambem identico
    estado_final_sem_trace = capturado["sem_trace"][-1][0]
    estado_final_com_trace = capturado["com_trace"][-1][0]
    assert estado_final_sem_trace == estado_final_com_trace


def test_prova_direta_rng_numero_de_chamadas_igual_ao_numero_de_amostras_ponderadas() -> None:
    """Cada ticket tem 15 dezenas, cada dezena consome exatamente 1
    chamada de ``rng.choices`` (ver ``_amostra_ponderada``) -- o numero
    total de chamadas deve ser exatamente 15 vezes o numero de eventos
    de avaliacao registrados no trace (candidatos validos + invalidos
    tambem passam por ``_amostra_ponderada`` antes de ``validar_jogo``,
    entao usamos ``attempts`` do resumo de perfil, nao so os validos)."""
    df = _base_sintetica(60)
    capturado: dict[str, list] = {"com_trace": []}
    tracer = CandidateTracer()

    with patch.object(random_module.Random, "choices", _capturar_chamadas_de_choices("com_trace", capturado)):
        gerar_jogos_v2(df, quantidade=5, semente=42, trace=tracer)

    total_tentativas = sum(r.attempts for r in tracer.profile_summaries)
    assert len(capturado["com_trace"]) == total_tentativas * 15


# ============================================================
# Fase 3F: isolamento de estado em sequencias alternadas OFF/ON
# ============================================================


def test_sequencia_off_on_off_produz_resultados_equivalentes() -> None:
    """OFF -> ON -> OFF: uma chamada sem trace, seguida de uma chamada
    COM trace (mesma seed/historico), seguida de outra chamada sem
    trace -- todas as tres devem produzir o MESMO resultado (mesma
    seed/historico => mesmo resultado sempre, independente de chamadas
    tracadas terem ocorrido entre elas)."""
    df = _base_sintetica(60)

    r_off_1 = gerar_jogos_v2(df, quantidade=5, semente=42)
    r_on = gerar_jogos_v2(df, quantidade=5, semente=42, trace=CandidateTracer())
    r_off_2 = gerar_jogos_v2(df, quantidade=5, semente=42)

    assert r_off_1.equals(r_on)
    assert r_on.equals(r_off_2)
    assert r_off_1.equals(r_off_2)


def test_sequencia_on_off_on_produz_resultados_equivalentes() -> None:
    """ON -> OFF -> ON: mesma logica, ordem invertida. Cada execucao
    tracada usa uma instancia NOVA de ``CandidateTracer`` -- os dois
    traces resultantes tambem devem ser identicos entre si, provando
    que a chamada OFF intermediaria nao deixou nenhum residuo capaz de
    alterar a proxima execucao tracada."""
    df = _base_sintetica(60)

    tracer_1 = CandidateTracer()
    r_on_1 = gerar_jogos_v2(df, quantidade=5, semente=42, trace=tracer_1)
    r_off = gerar_jogos_v2(df, quantidade=5, semente=42)
    tracer_2 = CandidateTracer()
    r_on_2 = gerar_jogos_v2(df, quantidade=5, semente=42, trace=tracer_2)

    assert r_on_1.equals(r_off)
    assert r_off.equals(r_on_2)
    assert tracer_1.evaluations == tracer_2.evaluations
    assert tracer_1.profile_summaries == tracer_2.profile_summaries


def test_sequencia_alternada_com_seeds_diferentes_por_chamada() -> None:
    """Alterna OFF/ON com seeds DIFERENTES a cada chamada, depois repete
    a mesma sequencia de seeds e confirma que cada posicao na sequencia
    produz exatamente o mesmo resultado que produziu na primeira
    passada -- nenhum acoplamento entre chamadas sucessivas, tracadas
    ou nao."""
    df = _base_sintetica(60)
    seeds = [1, 42, 999, 7000101, 20260909]

    def rodar_sequencia() -> list:
        resultados = []
        for indice, seed in enumerate(seeds):
            if indice % 2 == 0:
                resultados.append(gerar_jogos_v2(df, quantidade=5, semente=seed))
            else:
                resultados.append(gerar_jogos_v2(df, quantidade=5, semente=seed, trace=CandidateTracer()))
        return resultados

    primeira_passada = rodar_sequencia()
    segunda_passada = rodar_sequencia()

    assert len(primeira_passada) == len(segunda_passada) == len(seeds)
    for r1, r2 in zip(primeira_passada, segunda_passada):
        assert r1.equals(r2)


# ============================================================
# Fase 3G: determinismo sob execucao repetida
# ============================================================


def test_execucao_repetida_traced_e_untraced_permanecem_iguais_20x() -> None:
    """Repete 20 vezes, alternando trace ON/OFF, com a MESMA
    seed/historico -- todas as 20 execucoes devem produzir resultado
    idêntico entre si (determinismo puro por seed, trace nunca
    introduz variancia)."""
    df = _base_sintetica(60)
    resultados = []
    for i in range(20):
        if i % 2 == 0:
            resultados.append(gerar_jogos_v2(df, quantidade=5, semente=42))
        else:
            resultados.append(gerar_jogos_v2(df, quantidade=5, semente=42, trace=CandidateTracer()))

    referencia = resultados[0]
    for resultado in resultados[1:]:
        assert resultado.equals(referencia)


def test_traces_repetidos_com_mesma_seed_sao_todos_identicos_entre_si() -> None:
    df = _base_sintetica(60)
    tracers = [CandidateTracer() for _ in range(5)]
    for tracer in tracers:
        gerar_jogos_v2(df, quantidade=5, semente=42, trace=tracer)

    referencia = tracers[0]
    for tracer in tracers[1:]:
        assert tracer.evaluations == referencia.evaluations
        assert tracer.profile_summaries == referencia.profile_summaries
