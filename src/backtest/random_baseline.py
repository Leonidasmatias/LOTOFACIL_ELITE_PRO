"""Baseline aleatorio justo para o harness de backtest (LF-04, Fase 7).

``FairRandomBaseline`` e apenas um ``ReferenceRandomEngine`` (universo
1..25, 15 dezenas unicas, seed reproduzivel) usado especificamente como
baseline de comparacao -- a garantia de "numero justo de tickets" nao vem
de configuracao manual, e sim estrutural: ``compute_fair_baseline`` sempre
gera exatamente ``batch.number_of_tickets`` tickets, o mesmo numero do
``PredictionBatch`` do motor avaliado, e para o MESMO ``target_contest`` e
``history_max_contest`` -- nunca e possivel comparar quantidades diferentes
de tickets por construcao.
"""
from __future__ import annotations

from .contracts import PredictionBatch
from .engine_adapter import ReferenceRandomEngine
from .harness import predict_for_contest_from_batch_context

FairRandomBaseline = ReferenceRandomEngine


def compute_fair_baseline(
    batch: PredictionBatch,
    history,
    seed: int | None,
) -> PredictionBatch:
    """Gera um ``PredictionBatch`` baseline aleatorio para o MESMO
    ``target_contest``/``history_max_contest`` de ``batch``, com
    EXATAMENTE ``batch.number_of_tickets`` tickets -- nunca menos, nunca
    mais. ``history`` deve ser o mesmo historico (ja filtrado por
    ``target_contest``) usado para gerar ``batch``."""
    baseline_engine = FairRandomBaseline()
    return predict_for_contest_from_batch_context(
        engine=baseline_engine,
        history=history,
        target_contest=batch.target_contest,
        number_of_tickets=batch.number_of_tickets,
        seed=seed,
    )
