"""Consumidor de trace de candidatos do MOTOR_ELITE_V2 (LF-08).

``CandidateTracer`` implementa estruturalmente o ``CandidateTraceSink``
definido em ``src/motor_elite_v2.py`` (Protocol, sem import cruzado --
motor_elite_v2.py NAO importa este modulo, evitando qualquer acoplamento
novo de producao para pesquisa). Este objeto e puramente um COLETOR
read-only: cada metodo apenas grava um registro imutavel numa lista
interna, nunca consome RNG, nunca muta os argumentos recebidos, nunca
influencia a execucao de ``gerar_jogos_v2``.

Nao ha nenhuma logica de geracao, pontuacao ou selecao de candidatos
aqui -- apenas observacao passiva de valores ja computados por producao.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping


@dataclass(frozen=True, slots=True)
class CandidateEvaluationRecord:
    """Um evento de avaliacao de candidato: uma tentativa que passou em
    ``validar_jogo`` e foi pontuada por ``_score_estrutura`` (producao).
    Tickets duplicados dentro do mesmo perfil geram MULTIPLOS registros
    (um por evento de avaliacao) -- ver ``unique_candidates_so_far`` para
    distinguir de contagem de candidatos UNICOS no dicionario."""

    profile: str
    ticket: tuple[int, ...]
    raw_structure_score: float
    structure_metrics: Mapping
    similarity_to_already_selected: int
    similarity_penalty: float
    final_candidate_score: float
    selected_so_far: tuple[tuple[int, ...], ...]
    candidate_generation_index: int
    unique_candidates_so_far: int


@dataclass(frozen=True, slots=True)
class ProfileTraceSummary:
    """Resumo factual de UM perfil: quantas tentativas ocorreram, quantos
    candidatos validos foram vistos (eventos, incluindo duplicatas),
    quantos candidatos UNICOS restaram no dicionario, por que o laco
    parou, e qual ticket/score final producao selecionou para este
    perfil."""

    profile: str
    attempts: int
    valid_candidates_seen: int
    unique_candidates_stored: int
    early_stop_reason: str
    selected_ticket: tuple[int, ...]
    selected_final_score: float


@dataclass(slots=True)
class CandidateTracer:
    """Implementacao concreta de ``CandidateTraceSink``. Acumula
    ``CandidateEvaluationRecord``/``ProfileTraceSummary`` em listas
    internas; expostas somente como tuplas (read-only) via propriedades."""

    _evaluations: list[CandidateEvaluationRecord] = field(default_factory=list)
    _profile_summaries: list[ProfileTraceSummary] = field(default_factory=list)
    _trace_errors: list[Exception] = field(default_factory=list)

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
    ) -> None:
        self._evaluations.append(
            CandidateEvaluationRecord(
                profile=profile,
                ticket=ticket,
                raw_structure_score=raw_structure_score,
                structure_metrics=MappingProxyType(dict(structure_metrics)),
                similarity_to_already_selected=similarity_to_already_selected,
                similarity_penalty=similarity_penalty,
                final_candidate_score=final_candidate_score,
                selected_so_far=selected_so_far,
                candidate_generation_index=candidate_generation_index,
                unique_candidates_so_far=unique_candidates_so_far,
            )
        )

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
    ) -> None:
        self._profile_summaries.append(
            ProfileTraceSummary(
                profile=profile,
                attempts=attempts,
                valid_candidates_seen=valid_candidates_seen,
                unique_candidates_stored=unique_candidates_stored,
                early_stop_reason=early_stop_reason,
                selected_ticket=selected_ticket,
                selected_final_score=selected_final_score,
            )
        )

    @property
    def evaluations(self) -> tuple[CandidateEvaluationRecord, ...]:
        return tuple(self._evaluations)

    @property
    def profile_summaries(self) -> tuple[ProfileTraceSummary, ...]:
        return tuple(self._profile_summaries)

    def evaluations_for_profile(self, profile: str) -> tuple[CandidateEvaluationRecord, ...]:
        return tuple(e for e in self._evaluations if e.profile == profile)

    def on_trace_error(self, erro: Exception) -> None:
        """Hook OPCIONAL (nao faz parte do contrato minimo de
        ``CandidateTraceSink``): ``gerar_jogos_v2`` o chama, via
        ``_registrar_trace_com_seguranca``, quando ``record_evaluation``/
        ``record_profile_summary`` levanta uma excecao -- nunca afeta a
        execucao de producao, apenas torna a falha observavel aqui."""
        self._trace_errors.append(erro)

    @property
    def trace_errors(self) -> tuple[Exception, ...]:
        return tuple(self._trace_errors)
