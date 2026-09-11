"""Captura de candidatos PRE-FILTRO (antes de ``validar_jogo``) via
instrumentacao de pesquisa (LF-09D, Pendencia 1 / mecanismo B).

Usa EXATAMENTE a mesma tecnica ja aprovada e comprovada no LF-08A
(``tests/test_lf08a_hardening.py::test_prova_direta_rng_sequencia_de_chamadas_identica_com_e_sem_trace``):
monkeypatch de ``random.Random.choices`` (metodo da stdlib) a partir de
CODIGO DE PESQUISA -- nunca de producao. O wrapper chama o metodo
ORIGINAL sem alterar argumentos nem resultado; apenas observa o valor
ja produzido. Zero RNG adicional, zero mudanca de sequencia, zero
mudanca de ticket/selecao.

``_amostra_ponderada`` (motor_elite_v2.py) consome EXATAMENTE 15
chamadas de ``rng.choices`` por ticket tentado, incondicionalmente
(passe ou nao em ``validar_jogo`` depois). Isso permite reconstruir
TODOS os tickets brutos tentados -- aceitos e rejeitados -- agrupando
as escolhas capturadas em blocos de 15, na ordem em que ocorreram.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import random
from typing import Iterator, Sequence

from .candidate_trace import CandidateTracer
from .contracts import ContestSnapshot, LeakageError
from .engine_adapter import _history_para_dataframe
from ..motor_elite_v2 import gerar_jogos_v2
from ..validacao_jogos import ConfiguracaoMotor, validar_jogo

Ticket = tuple[int, ...]


@contextmanager
def capturar_draws_brutos() -> Iterator[list[int]]:
    """Intercepta ``random.Random.choices`` e devolve a lista de
    escolhas individuais, na ordem exata em que ocorreram. NAO altera o
    comportamento do metodo -- delega ao original e apenas observa o
    resultado ja produzido."""
    original = random.Random.choices
    escolhas: list[int] = []

    def wrapper(self: random.Random, *args: object, **kwargs: object) -> list:
        resultado: list = original(self, *args, **kwargs)  # type: ignore[arg-type]
        escolhas.append(resultado[0])
        return resultado

    random.Random.choices = wrapper  # type: ignore[method-assign]
    try:
        yield escolhas
    finally:
        random.Random.choices = original  # type: ignore[method-assign]


@dataclass(frozen=True, slots=True)
class RawCandidate:
    profile: str
    ticket: Ticket
    accepted: bool
    hits: int


@dataclass(frozen=True, slots=True)
class StructuralFilterCapture:
    contest: int
    motor_seed: int
    raw_candidates: tuple[RawCandidate, ...]  # TODOS os tentados (aceitos + rejeitados)
    post_filter_hits: tuple[int, ...]  # apenas os aceitos (deve bater com o trace)


def motor_seed_policy(base_seed: int, target_contest: int) -> int:
    return base_seed + target_contest


def run_structural_filter_target(
    all_contests: Sequence[ContestSnapshot],
    target_contest: int,
    motor_base_seed: int,
    configuracao: ConfiguracaoMotor | None = None,
) -> StructuralFilterCapture:
    """Executa UMA geracao real, capturando TODOS os tickets brutos
    tentados (via interceptacao de RNG, nao de producao) e classifica
    cada um como aceito/rejeitado reaplicando ``validar_jogo`` --
    a MESMA funcao publica e inalterada que producao usa."""
    por_numero = {c.number: c for c in all_contests}
    if target_contest not in por_numero:
        raise ValueError(f"Concurso-alvo {target_contest} nao esta em all_contests.")
    history = [c for c in all_contests if c.number < target_contest]
    invasores = [c.number for c in history if c.number >= target_contest]
    if invasores:
        raise LeakageError(f"Historico contem concurso(s) >= alvo {target_contest}: {sorted(invasores)[:5]}")
    if not history:
        raise ValueError("Historico vazio.")

    df_historico = _history_para_dataframe(history)
    motor_seed = motor_seed_policy(motor_base_seed, target_contest)
    config = configuracao or ConfiguracaoMotor()
    ultimo = frozenset(max(history, key=lambda c: c.number).numbers)

    tracer = CandidateTracer()
    with capturar_draws_brutos() as escolhas:
        gerar_jogos_v2(df_historico, quantidade=5, configuracao=config, semente=motor_seed, trace=tracer)

    tickets_brutos = [tuple(sorted(escolhas[i : i + 15])) for i in range(0, len(escolhas), 15)]

    por_perfil: dict[str, list[Ticket]] = {}
    cursor = 0
    for resumo in tracer.profile_summaries:
        fim = cursor + resumo.attempts
        por_perfil[resumo.profile] = tickets_brutos[cursor:fim]
        cursor = fim

    resultado_real = set(por_numero[target_contest].numbers)

    raw_candidates = []
    for perfil, tickets in por_perfil.items():
        for ticket in tickets:
            try:
                validar_jogo(ticket, config, ultimo)
                aceito = True
            except ValueError:
                aceito = False
            raw_candidates.append(
                RawCandidate(profile=perfil, ticket=ticket, accepted=aceito, hits=len(set(ticket) & resultado_real))
            )

    post_filter_hits = tuple(len(set(evento.ticket) & resultado_real) for evento in tracer.evaluations)

    return StructuralFilterCapture(
        contest=target_contest,
        motor_seed=motor_seed,
        raw_candidates=tuple(raw_candidates),
        post_filter_hits=post_filter_hits,
    )
