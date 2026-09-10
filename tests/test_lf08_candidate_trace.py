"""Testes do seam de observabilidade de candidatos do MOTOR_ELITE_V2
(LF-08).

Objetivo primario: provar EQUIVALENCIA EXATA de comportamento entre
``gerar_jogos_v2`` com e sem ``trace`` -- a instrumentacao e estritamente
aditiva/observacional (Fase 2/9 do gate). Nenhum teste aqui avalia
desempenho contra resultado real de concurso -- LF-08 e apenas
arquitetural/observabilidade.
"""
from __future__ import annotations

import dataclasses
import inspect

import pandas as pd
import pytest

from src.backtest.candidate_trace import (
    CandidateEvaluationRecord,
    CandidateTracer,
    ProfileTraceSummary,
)
from src.motor_elite_v2 import CandidateTraceSink, PERFIS_V2, gerar_jogos_v2
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


SEMENTES_MATRIZ = [1, 42, 999, 20260909, 7000101]
TAMANHOS_HISTORICO = [30, 60, 120]


# --- B/A: equivalencia exata trace-disabled vs trace-enabled ----------------


@pytest.mark.parametrize("semente", SEMENTES_MATRIZ)
@pytest.mark.parametrize("tamanho_historico", TAMANHOS_HISTORICO)
def test_trace_enabled_produz_output_identico_a_trace_disabled(semente: int, tamanho_historico: int) -> None:
    df = _base_sintetica(tamanho_historico)
    sem_trace = gerar_jogos_v2(df, quantidade=5, semente=semente)
    tracer = CandidateTracer()
    com_trace = gerar_jogos_v2(df, quantidade=5, semente=semente, trace=tracer)
    assert sem_trace.equals(com_trace)
    # o unico artefato adicional deve ser o proprio trace, nao mudanca de output
    assert len(tracer.evaluations) > 0
    assert len(tracer.profile_summaries) == 5


def test_trace_explicito_none_e_identico_a_omitir_o_parametro() -> None:
    df = _base_sintetica(60)
    r1 = gerar_jogos_v2(df, quantidade=5, semente=42)
    r2 = gerar_jogos_v2(df, quantidade=5, semente=42, trace=None)
    assert r1.equals(r2)


# --- C: mesma seed -> mesmo trace (determinismo) ----------------------------


def test_mesma_seed_produz_trace_identico() -> None:
    df = _base_sintetica(60)
    t1, t2 = CandidateTracer(), CandidateTracer()
    gerar_jogos_v2(df, quantidade=5, semente=42, trace=t1)
    gerar_jogos_v2(df, quantidade=5, semente=42, trace=t2)
    assert t1.evaluations == t2.evaluations
    assert t1.profile_summaries == t2.profile_summaries


# --- D: seeds diferentes podem produzir trace diferente ---------------------


def test_seeds_diferentes_produzem_traces_diferentes() -> None:
    df = _base_sintetica(60)
    t1, t2 = CandidateTracer(), CandidateTracer()
    gerar_jogos_v2(df, quantidade=5, semente=1, trace=t1)
    gerar_jogos_v2(df, quantidade=5, semente=999, trace=t2)
    assert t1.profile_summaries != t2.profile_summaries


# --- E/F: nenhum resultado-alvo na API --------------------------------------


def test_assinatura_gerar_jogos_v2_nao_aceita_resultado_alvo() -> None:
    parametros = set(inspect.signature(gerar_jogos_v2).parameters)
    proibidos = {"target_result", "winning_numbers", "future_contests", "future_statistics", "resultado_alvo"}
    assert parametros.isdisjoint(proibidos)


def test_trace_records_nao_tem_campo_de_resultado_futuro() -> None:
    campos_evaluation = {f.name for f in dataclasses.fields(CandidateEvaluationRecord)}
    campos_summary = {f.name for f in dataclasses.fields(ProfileTraceSummary)}
    proibidos = {"target_result", "winning_numbers", "future_contests", "hits", "score_real"}
    assert campos_evaluation.isdisjoint(proibidos)
    assert campos_summary.isdisjoint(proibidos)


# --- G: exatamente 5 resumos de perfil num run bem-sucedido -----------------


def test_exatamente_cinco_resumos_de_perfil() -> None:
    df = _base_sintetica(60)
    tracer = CandidateTracer()
    gerar_jogos_v2(df, quantidade=5, semente=42, trace=tracer)
    assert len(tracer.profile_summaries) == 5
    assert [r.profile for r in tracer.profile_summaries] == PERFIS_V2


# --- H: ticket selecionado esta no estado autentico do candidato -----------


def test_ticket_selecionado_esta_nas_avaliacoes_autenticas_do_perfil() -> None:
    df = _base_sintetica(60)
    tracer = CandidateTracer()
    gerar_jogos_v2(df, quantidade=5, semente=42, trace=tracer)
    for resumo in tracer.profile_summaries:
        eventos_perfil = tracer.evaluations_for_profile(resumo.profile)
        tickets_avaliados = {e.ticket for e in eventos_perfil}
        assert resumo.selected_ticket in tickets_avaliados
        eventos_do_ticket = [e for e in eventos_perfil if e.ticket == resumo.selected_ticket]
        assert eventos_do_ticket[-1].final_candidate_score == pytest.approx(resumo.selected_final_score)


# --- I: semantica de duplicatas ----------------------------------------------


def test_duplicatas_sao_representadas_como_multiplos_eventos_mesmo_ticket() -> None:
    df = _base_sintetica(60)
    tracer = CandidateTracer()
    gerar_jogos_v2(df, quantidade=5, semente=42, trace=tracer)
    for resumo in tracer.profile_summaries:
        assert resumo.valid_candidates_seen >= resumo.unique_candidates_stored
        if resumo.valid_candidates_seen > resumo.unique_candidates_stored:
            eventos = tracer.evaluations_for_profile(resumo.profile)
            tickets = [e.ticket for e in eventos]
            assert len(tickets) != len(set(tickets))  # ao menos uma duplicata real


# --- J: selected_so_far reflete estado sequencial autentico -----------------


def test_selected_so_far_reflete_perfis_ja_concluidos() -> None:
    df = _base_sintetica(60)
    tracer = CandidateTracer()
    gerar_jogos_v2(df, quantidade=5, semente=42, trace=tracer)
    for indice, perfil in enumerate(PERFIS_V2):
        eventos = tracer.evaluations_for_profile(perfil)
        assert eventos, f"nenhum evento para perfil {perfil}"
        for evento in eventos:
            assert len(evento.selected_so_far) == indice


# --- K: imutabilidade dos registros -----------------------------------------


def test_registros_de_trace_sao_frozen() -> None:
    df = _base_sintetica(60)
    tracer = CandidateTracer()
    gerar_jogos_v2(df, quantidade=5, semente=42, trace=tracer)
    evento = tracer.evaluations[0]
    with pytest.raises(dataclasses.FrozenInstanceError):
        evento.raw_structure_score = 999.0  # type: ignore[misc]
    resumo = tracer.profile_summaries[0]
    with pytest.raises(dataclasses.FrozenInstanceError):
        resumo.attempts = 999  # type: ignore[misc]


def test_structure_metrics_armazenado_e_genuinamente_imutavel() -> None:
    df = _base_sintetica(60)
    tracer = CandidateTracer()
    gerar_jogos_v2(df, quantidade=5, semente=42, trace=tracer)
    with pytest.raises(TypeError):
        tracer.evaluations[0].structure_metrics["Soma"] = -1  # type: ignore[index]


def test_record_evaluation_copia_defensivamente_o_dict_recebido() -> None:
    """``CandidateTracer.record_evaluation`` recebe ``structure_metrics``
    por parametro e o envolve em copia imutavel propria -- mutar o dict
    original ANTES de armazenar nao pode ser refletido no registro."""
    tracer = CandidateTracer()
    metricas_mutavel = {"Soma": 174, "Pares": 8}
    tracer.record_evaluation(
        profile="Diamante",
        ticket=(1, 2, 3),
        raw_structure_score=1.0,
        structure_metrics=metricas_mutavel,
        similarity_to_already_selected=0,
        similarity_penalty=0.0,
        final_candidate_score=1.0,
        selected_so_far=(),
        candidate_generation_index=1,
        unique_candidates_so_far=1,
    )
    metricas_mutavel["Soma"] = -999
    assert tracer.evaluations[0].structure_metrics["Soma"] == 174


# --- L: excecoes preservadas identicamente -----------------------------------


def _config_forca_impossibilidade() -> ConfiguracaoMotor:
    # Identidade combinatoria: a intersecao MINIMA entre dois subconjuntos
    # de 15 elementos de um universo de 25 e |A|+|B|-25 = 5, logo a
    # diferenca MAXIMA possivel entre dois jogos e 15-5=10. Exigir
    # diferenca_minima_entre_jogos=15 torna o 2o perfil matematicamente
    # impossivel, sempre e deterministicamente.
    return ConfiguracaoMotor(diferenca_minima_entre_jogos=15, candidatos_por_perfil=50)


def test_excecao_identica_com_e_sem_trace() -> None:
    df = _base_sintetica(40)
    config = _config_forca_impossibilidade()

    with pytest.raises(ValueError, match="Não foi possível formar carteira diversa") as exc_sem_trace:
        gerar_jogos_v2(df, quantidade=5, configuracao=config, semente=1)

    tracer = CandidateTracer()
    with pytest.raises(ValueError, match="Não foi possível formar carteira diversa") as exc_com_trace:
        gerar_jogos_v2(df, quantidade=5, configuracao=config, semente=1, trace=tracer)

    assert str(exc_sem_trace.value) == str(exc_com_trace.value)
    # o primeiro perfil deve ter sido tracado com sucesso antes da falha no segundo
    assert len(tracer.profile_summaries) == 1
    assert tracer.profile_summaries[0].profile == "Diamante"


# --- Overhead diagnostico (nao normativo) ------------------------------------


def test_trace_nao_falha_em_run_maior_e_produz_contagens_plausiveis() -> None:
    df = _base_sintetica(120)
    tracer = CandidateTracer()
    resultado = gerar_jogos_v2(df, quantidade=5, semente=20260909, trace=tracer)
    assert len(resultado) == 5
    total_eventos = len(tracer.evaluations)
    total_unicos = sum(r.unique_candidates_stored for r in tracer.profile_summaries)
    assert total_eventos >= total_unicos > 0


# --- Compatibilidade com o Protocol estrutural -------------------------------


def test_candidate_tracer_satisfaz_protocol_estruturalmente() -> None:
    tracer: CandidateTraceSink = CandidateTracer()
    assert hasattr(tracer, "record_evaluation")
    assert hasattr(tracer, "record_profile_summary")
