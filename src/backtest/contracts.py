"""Contratos puros do harness de backtest walk-forward (LF-04).

Dataclasses imutaveis (``frozen=True``) que representam, sem nenhuma logica
de motor/score, os tres momentos de uma avaliacao walk-forward:

1. ``ContestSnapshot``  -- um concurso conhecido (historico OU resultado-alvo).
2. ``PredictionBatch``  -- um lote de tickets CONGELADO para um concurso-alvo,
   construido usando somente concursos anteriores a ele. Imutavel: uma vez
   criado, nenhum campo pode mudar.
3. ``BacktestResult``   -- o resultado de comparar um ``PredictionBatch`` ja
   congelado contra o resultado real (aberto so depois do freeze).

Reutiliza ``validar_resultado`` (contrato LF-02) para o invariante
matematico das dezenas -- nao duplica 1..25/15/unicidade aqui.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..core.lotofacil_contract import validar_resultado


class LeakageError(RuntimeError):
    """Violacao de um invariante anti-vazamento temporal do harness."""


class ResultNotYetOpenedError(RuntimeError):
    """Tentativa de consultar o resultado real de um concurso-alvo antes de
    ``SealedContestResult.open()`` ter sido chamado explicitamente -- ou
    seja, antes do freeze do ``PredictionBatch`` correspondente."""


@dataclass(frozen=True, slots=True)
class ContestSnapshot:
    """Um concurso conhecido da Lotofacil: numero, data e as 15 dezenas
    sorteadas. Usado tanto como HISTORICO (entrada legitima de um engine)
    quanto como RESULTADO-ALVO (aberto somente apos o freeze)."""

    number: int
    date: str
    numbers: tuple[int, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.number, int) or isinstance(self.number, bool):
            raise ValueError(f"ContestSnapshot.number deve ser int; recebeu {self.number!r}.")
        if self.number <= 0:
            raise ValueError(f"ContestSnapshot.number deve ser positivo; recebeu {self.number}.")
        dezenas_validadas = validar_resultado(self.numbers)
        object.__setattr__(self, "numbers", dezenas_validadas)


@dataclass(frozen=True, slots=True)
class FrozenTicket:
    """Um jogo/bilhete congelado dentro de um ``PredictionBatch``."""

    label: str
    numbers: tuple[int, ...]

    def __post_init__(self) -> None:
        dezenas_validadas = validar_resultado(self.numbers)
        object.__setattr__(self, "numbers", dezenas_validadas)


@dataclass(frozen=True, slots=True)
class PredictionBatch:
    """Um lote de tickets CONGELADO para ``target_contest``, produzido
    usando somente concursos com numero < ``target_contest``.

    Imutavel apos a criacao (``frozen=True`` + apenas tuplas/primitivos nos
    campos -- nenhum campo mutavel escondido). O invariante
    ``history_max_contest < target_contest`` e verificado no
    ``__post_init__`` e falha ruidosamente (``LeakageError``) se violado --
    nunca silenciosamente.
    """

    target_contest: int
    history_max_contest: int
    engine_name: str
    engine_version: str
    seed: int | None
    number_of_tickets: int
    tickets: tuple[FrozenTicket, ...]
    generated_at: str
    data_fingerprint: str
    metadata: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.history_max_contest >= self.target_contest:
            raise LeakageError(
                f"history_max_contest ({self.history_max_contest}) >= "
                f"target_contest ({self.target_contest}) -- vazamento temporal detectado; "
                "o historico entregue ao engine nao pode conter o concurso-alvo nem nenhum "
                "concurso posterior a ele."
            )
        if len(self.tickets) != self.number_of_tickets:
            raise ValueError(
                f"PredictionBatch declara number_of_tickets={self.number_of_tickets} mas "
                f"contem {len(self.tickets)} tickets."
            )
        if self.number_of_tickets <= 0:
            raise ValueError("PredictionBatch precisa de pelo menos 1 ticket.")


@dataclass(frozen=True, slots=True)
class TicketScore:
    """Resultado de comparar UM ticket congelado contra o resultado real."""

    label: str
    numbers: tuple[int, ...]
    hits: int


@dataclass(frozen=True, slots=True)
class BacktestResult:
    """Resultado de UMA rodada de SCORE: um ``PredictionBatch`` ja
    congelado, comparado contra o ``target_result`` (aberto so agora)."""

    batch: PredictionBatch
    target_result: ContestSnapshot
    ticket_scores: tuple[TicketScore, ...]
    max_hits: int
    mean_hits: float
    hit_distribution: dict[int, int]

    def __post_init__(self) -> None:
        if self.target_result.number != self.batch.target_contest:
            raise ValueError(
                f"target_result.number ({self.target_result.number}) != "
                f"batch.target_contest ({self.batch.target_contest})."
            )


class SealedContestResult:
    """Encapsula o resultado real de UM concurso, mantendo-o inacessivel
    (levanta ``ResultNotYetOpenedError``) até ``open()`` ser chamado
    explicitamente. Usado pelo harness para provar, em TEMPO DE EXECUCAO --
    nao so por convencao de codigo -- que nenhuma etapa de previsao
    consultou o resultado antes do freeze do ``PredictionBatch``."""

    __slots__ = ("_result", "_opened")

    def __init__(self, result: ContestSnapshot) -> None:
        self._result = result
        self._opened = False

    @property
    def is_opened(self) -> bool:
        return self._opened

    def open(self) -> ContestSnapshot:
        self._opened = True
        return self._result

    def peek(self) -> ContestSnapshot:
        if not self._opened:
            raise ResultNotYetOpenedError(
                f"Tentativa de acessar o resultado do concurso {self._result.number} "
                "antes de open() ser chamado -- freeze-before-open violado."
            )
        return self._result
