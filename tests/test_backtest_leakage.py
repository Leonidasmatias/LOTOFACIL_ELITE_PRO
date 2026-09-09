"""Testes adversariais de vazamento temporal (LF-04, Fase 10 -- obrigatorios).

Cada teste aqui PROVA (nao apenas documenta) que uma forma especifica de
vazamento e impossivel ou e detectada e rejeitada pelo harness:

A. concurso-alvo presente no historico entregue ao engine;
B. history_max_contest >= target_contest;
C. resultado-alvo consultado antes do freeze;
D. engine adapter recebendo o resultado-alvo;
E. alterar o resultado real do alvo ANTES do score nao pode alterar os
   tickets ja congelados (so a fase SCORE pode mudar).
"""
from __future__ import annotations

from dataclasses import dataclass

import pytest

from src.backtest.contracts import (
    ContestSnapshot,
    LeakageError,
    PredictionBatch,
    ResultNotYetOpenedError,
    SealedContestResult,
)
from src.backtest.engine_adapter import ReferenceRandomEngine
from src.backtest.harness import predict_for_contest
from src.backtest.metrics import score_batch


def _concurso(numero: int, dezenas: tuple[int, ...] | None = None) -> ContestSnapshot:
    dezenas = dezenas or tuple(sorted((((numero + i) % 25) + 1 for i in range(15))))
    # garante 15 unicas mesmo com a formula simples acima
    usadas: list[int] = []
    cursor = 1
    for d in sorted(dezenas):
        while d in usadas:
            d = cursor
            cursor += 1
            if cursor > 25:
                cursor = 1
        usadas.append(d)
    return ContestSnapshot(number=numero, date="01/01/2026", numbers=tuple(sorted(usadas)))


def _base(quantidade: int) -> list[ContestSnapshot]:
    return [_concurso(n) for n in range(1, quantidade + 1)]


# --- A. concurso-alvo presente no historico entregue ao engine -----------


def test_A_rejeita_target_contest_presente_no_history() -> None:
    base = _base(30)
    target = 25
    history_contaminado = [c for c in base if c.number <= target]  # inclui o proprio 25
    with pytest.raises(LeakageError):
        predict_for_contest(ReferenceRandomEngine(), history_contaminado, target, number_of_tickets=3, seed=1)


# --- B. history_max_contest >= target_contest -----------------------------


def test_B_rejeita_history_com_concurso_posterior_ao_alvo() -> None:
    base = _base(30)
    target = 20
    # historico contem concursos ATE 25 -- muito alem do alvo 20.
    history_contaminado = [c for c in base if c.number <= 25]
    with pytest.raises(LeakageError):
        predict_for_contest(ReferenceRandomEngine(), history_contaminado, target, number_of_tickets=3, seed=1)


def test_B_prediction_batch_construido_manualmente_tambem_e_bloqueado() -> None:
    # Mesmo contornando predict_for_contest e tentando construir o
    # PredictionBatch diretamente, o invariante e verificado no proprio
    # __post_init__ do contrato -- nao ha como escapar por um caminho
    # alternativo de construcao.
    from src.backtest.contracts import FrozenTicket

    with pytest.raises(LeakageError):
        PredictionBatch(
            target_contest=20,
            history_max_contest=25,
            engine_name="x",
            engine_version="1",
            seed=None,
            number_of_tickets=1,
            tickets=(FrozenTicket(label="t", numbers=tuple(range(1, 16))),),
            generated_at="2026-01-01T00:00:00+00:00",
            data_fingerprint="abc",
        )


# --- C. resultado-alvo consultado antes do freeze --------------------------


def test_C_resultado_alvo_nao_pode_ser_consultado_antes_do_freeze() -> None:
    base = _base(30)
    target = 25
    alvo_real = next(c for c in base if c.number == target)
    sealed = SealedContestResult(alvo_real)

    # Tentativa de "espiar" o resultado ANTES de qualquer freeze/predict.
    with pytest.raises(ResultNotYetOpenedError):
        sealed.peek()

    # Mesmo depois de fazer o predict (freeze), o sealed ainda nao foi
    # aberto -- so abrimos explicitamente na fase SCORE.
    history = [c for c in base if c.number < target]
    predict_for_contest(ReferenceRandomEngine(), history, target, number_of_tickets=3, seed=1)
    with pytest.raises(ResultNotYetOpenedError):
        sealed.peek()

    # Somente agora, explicitamente, o resultado e aberto.
    resultado = sealed.open()
    assert resultado.number == target
    assert sealed.peek() == resultado


# --- D. engine adapter recebendo o resultado-alvo --------------------------


@dataclass
class _SpyEngine:
    """Engine espiao: grava exatamente o que recebeu em `generate`, para
    provar que nenhum resultado-alvo (nem o proprio numero do concurso-alvo)
    chega ate o engine -- so o historico, a quantidade e a seed."""

    name: str = "SPY_ENGINE"
    version: str = "1.0"
    historico_recebido: list = None  # type: ignore[assignment]
    seed_recebida: object = "NAO_CHAMADO"
    quantidade_recebida: object = "NAO_CHAMADO"

    def generate(self, history, number_of_tickets, seed):
        self.historico_recebido = list(history)
        self.seed_recebida = seed
        self.quantidade_recebida = number_of_tickets
        return [(f"ticket_{i}", tuple(range(1, 16))) for i in range(number_of_tickets)]


def test_D_engine_generate_nunca_recebe_target_result_nem_target_contest() -> None:
    base = _base(30)
    target = 25
    history = [c for c in base if c.number < target]
    spy = _SpyEngine()

    import inspect

    assinatura = inspect.signature(spy.generate)
    # A propria assinatura do protocolo nao tem parametro para
    # target_contest/target_result -- prova estrutural.
    assert set(assinatura.parameters) == {"history", "number_of_tickets", "seed"}

    predict_for_contest(spy, history, target, number_of_tickets=4, seed=9)

    assert spy.quantidade_recebida == 4
    assert spy.seed_recebida == 9
    # o historico recebido pelo engine e EXATAMENTE o que foi passado --
    # nenhum concurso >= target, e nenhum objeto "resultado" extra.
    assert all(c.number < target for c in spy.historico_recebido)
    assert max(c.number for c in spy.historico_recebido) == target - 1
    assert len(spy.historico_recebido) == len(history)


# --- E. alterar o resultado real do alvo ANTES do score --------------------


@dataclass
class _FixedTicketEngine:
    """Engine de teste que sempre devolve os MESMOS tickets, conhecidos de
    antemao -- usado exclusivamente para poder escolher resultados-alvo
    A/B que produzam max_hits DETERMINISTICAMENTE diferentes (em vez de
    depender de sorte com tickets aleatorios)."""

    ticket_fixo: tuple[int, ...]
    name: str = "FIXED_TICKET_ENGINE"
    version: str = "1.0"

    def generate(self, history, number_of_tickets, seed):
        return [(f"ticket_{i}", self.ticket_fixo) for i in range(number_of_tickets)]


def test_E_futuros_diferentes_produzem_scores_diferentes_sem_alterar_tickets() -> None:
    base = _base(30)
    target = 25
    history = [c for c in base if c.number < target]

    # Ticket fixo e conhecido: 1..15. Na Lotofacil (universo de 25, 15
    # dezenas por jogo/resultado), a intersecao MINIMA possivel entre dois
    # conjuntos de 15 dezenas e 5 (|A|+|B|-25 = 15+15-25 = 5 -- ver LF-02,
    # probabilidade_acertos(k)=0 para k<5) e a MAXIMA e 15 (identico).
    # Escolhemos os dois extremos exatos, deterministicamente:
    ticket_fixo = tuple(range(1, 16))  # 1..15
    engine = _FixedTicketEngine(ticket_fixo=ticket_fixo)

    # 1. gera PredictionBatch UMA UNICA VEZ.
    batch = predict_for_contest(engine, history, target, number_of_tickets=3, seed=123)

    # 2. congela referencia do estado ANTES de qualquer resultado existir.
    tickets_antes = batch.tickets

    # 3. resultado_real_A: IDENTICO ao ticket fixo -> 15 acertos garantidos
    # (o maximo matematicamente possivel) para os 3 tickets.
    resultado_real_a = ContestSnapshot(number=target, date="25/01/2026", numbers=ticket_fixo)

    # 4. resultado_real_B: mantem so as 5 primeiras dezenas do ticket fixo e
    # completa com as 10 dezenas FORA dele (16..25) -> intersecao = 5, o
    # MINIMO matematicamente possivel -> 5 acertos garantidos para os 3
    # tickets. Deliberadamente escolhido para garantir uma pontuacao
    # diferente de A (15) em TODOS os tickets, nao por sorte.
    resultado_real_b = ContestSnapshot(
        number=target,
        date="25/01/2026",
        numbers=tuple(sorted((1, 2, 3, 4, 5, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25))),
    )
    assert len(set(ticket_fixo) & set(resultado_real_a.numbers)) == 15
    assert len(set(ticket_fixo) & set(resultado_real_b.numbers)) == 5
    assert resultado_real_a.numbers != resultado_real_b.numbers

    # 5. executa as duas fases SCORE, sobre o MESMO batch congelado.
    score_a = score_batch(batch, resultado_real_a)
    score_b = score_batch(batch, resultado_real_b)

    # 6. provas de imutabilidade: o batch e os tickets sao EXATAMENTE os
    # mesmos de antes, para os dois scores.
    assert batch.tickets == tickets_antes
    assert score_a.batch.tickets == tickets_antes
    assert score_b.batch.tickets == tickets_antes
    assert score_a.batch is batch
    assert score_b.batch is batch

    # 7. evidencia factual (nao tautologica, sem "or True"): os dois
    # futuros produzem scores DETERMINISTICAMENTE diferentes, nas tres
    # dimensoes possiveis.
    assert score_a != score_b
    assert score_a.max_hits == 15
    assert score_b.max_hits == 5
    assert score_a.max_hits != score_b.max_hits
    assert score_a.hit_distribution != score_b.hit_distribution
    assert score_a.ticket_scores != score_b.ticket_scores
    assert all(ticket_score.hits == 15 for ticket_score in score_a.ticket_scores)
    assert all(ticket_score.hits == 5 for ticket_score in score_b.ticket_scores)


def test_E_mutation_independence_resultado_futuro_nao_e_estado_congelado() -> None:
    """Fase 4 (mutation independence): substituir/descartar o objeto que
    representa o resultado futuro, ANTES ou DEPOIS da fase SCORE, nunca
    pode alterar nenhum campo do PredictionBatch ja congelado -- porque o
    resultado futuro nunca fez parte do estado congelado (ver Fase 5:
    PredictionBatch nao tem nenhum campo para ele)."""
    base = _base(30)
    target = 25
    history = [c for c in base if c.number < target]
    ticket_fixo = tuple(range(1, 16))
    engine = _FixedTicketEngine(ticket_fixo=ticket_fixo)

    batch = predict_for_contest(engine, history, target, number_of_tickets=3, seed=456)

    # Snapshot completo do estado congelado ANTES de qualquer resultado existir.
    estado_antes = {
        "tickets": batch.tickets,
        "data_fingerprint": batch.data_fingerprint,
        "target_contest": batch.target_contest,
        "history_max_contest": batch.history_max_contest,
        "seed": batch.seed,
        "engine_name": batch.engine_name,
        "engine_version": batch.engine_version,
        "number_of_tickets": batch.number_of_tickets,
    }

    # "Resultado futuro" e criado, usado, e depois SUBSTITUIDO por um
    # objeto completamente diferente -- simula um caller que troca/descarta
    # a referencia ao resultado real entre duas chamadas de score.
    resultado_futuro = ContestSnapshot(number=target, date="25/01/2026", numbers=ticket_fixo)
    _ = score_batch(batch, resultado_futuro)

    resultado_futuro = ContestSnapshot(  # reatribuicao: objeto NOVO e DIFERENTE
        number=target,
        date="25/01/2026",
        numbers=tuple(sorted((1, 2, 3, 4, 5, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25))),
    )
    _ = score_batch(batch, resultado_futuro)

    del resultado_futuro  # o objeto "resultado futuro" deixa de existir

    estado_depois = {
        "tickets": batch.tickets,
        "data_fingerprint": batch.data_fingerprint,
        "target_contest": batch.target_contest,
        "history_max_contest": batch.history_max_contest,
        "seed": batch.seed,
        "engine_name": batch.engine_name,
        "engine_version": batch.engine_version,
        "number_of_tickets": batch.number_of_tickets,
    }
    assert estado_antes == estado_depois
