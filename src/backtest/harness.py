"""Harness de backtest walk-forward, ponto de entrada principal (LF-04).

Duas fases explicitas e SEPARADAS (Fase 5 do gate -- "freeze-before-open"):

    A. PREDICT -- ``predict_for_contest``: recebe SOMENTE o historico com
       numero < ``target_contest``, chama o engine, congela o resultado
       num ``PredictionBatch`` imutavel. Nao ha, na assinatura desta
       funcao nem na de ``EngineAdapter.generate``, nenhum parametro para
       o resultado do concurso-alvo -- estruturalmente impossivel de
       passar.

    B. SCORE -- ``metrics.score_batch``: so pode ser chamada DEPOIS que o
       ``PredictionBatch`` ja existe (congelado); abre o resultado real
       via ``SealedContestResult.open()`` e compara.

``run_walk_forward`` executa as duas fases, na ordem certa, para uma lista
de concursos-alvo.
"""
from __future__ import annotations

from datetime import datetime, timezone
import subprocess
from typing import Sequence

import pandas as pd

from .contracts import ContestSnapshot, FrozenTicket, LeakageError, PredictionBatch, SealedContestResult
from .engine_adapter import EngineAdapter
from .fingerprint import data_fingerprint
from .metrics import BacktestResult, score_batch


def load_contests_from_dataframe(df: pd.DataFrame) -> list[ContestSnapshot]:
    """Converte um DataFrame no formato Concurso/Data/Bola1..Bola15 (o
    mesmo formato de ``dados/lotofacil_historico.csv``) numa lista de
    ``ContestSnapshot`` ordenada por numero de concurso. Cada
    ``ContestSnapshot`` valida suas proprias 15 dezenas (contrato LF-02)."""
    colunas_dezenas = [f"Bola{i}" for i in range(1, 16)]
    dados = df.sort_values("Concurso").reset_index(drop=True)
    contests = []
    for _, linha in dados.iterrows():
        numeros = tuple(int(linha[coluna]) for coluna in colunas_dezenas)
        contests.append(ContestSnapshot(number=int(linha["Concurso"]), date=str(linha["Data"]), numbers=numeros))
    return contests


def predict_for_contest(
    engine: EngineAdapter,
    history: Sequence[ContestSnapshot],
    target_contest: int,
    number_of_tickets: int,
    seed: int | None,
) -> PredictionBatch:
    """FASE PREDICT: gera e CONGELA um ``PredictionBatch`` para
    ``target_contest``, usando somente ``history``.

    Verifica, ANTES de chamar o engine, que nenhum concurso do historico
    tem numero >= ``target_contest`` (levanta ``LeakageError`` explicito e
    ruidoso se isso acontecer, em vez de deixar o engine rodar com dado
    contaminado). O engine (``EngineAdapter.generate``) recebe SOMENTE
    ``history``/``number_of_tickets``/``seed`` -- nunca ``target_contest``
    nem qualquer resultado."""
    invasores = [c.number for c in history if c.number >= target_contest]
    if invasores:
        raise LeakageError(
            f"Historico entregue a predict_for_contest contem concurso(s) >= "
            f"target_contest ({target_contest}): {sorted(invasores)[:10]}."
        )
    history_max_contest = max((c.number for c in history), default=0)

    tickets_brutos = engine.generate(history, number_of_tickets, seed)
    tickets = tuple(FrozenTicket(label=rotulo, numbers=tuple(sorted(numeros))) for rotulo, numeros in tickets_brutos)

    return PredictionBatch(
        target_contest=target_contest,
        history_max_contest=history_max_contest,
        engine_name=engine.name,
        engine_version=engine.version,
        seed=seed,
        number_of_tickets=number_of_tickets,
        tickets=tickets,
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        data_fingerprint=data_fingerprint(history),
    )


# Alias publico usado por `random_baseline.py` -- mesma funcao, nome
# alternativo para deixar explicito, no ponto de chamada do baseline, que
# se trata de uma segunda chamada de PREDICT (nao uma funcao diferente).
predict_for_contest_from_batch_context = predict_for_contest


def run_walk_forward(
    engine: EngineAdapter,
    all_contests: Sequence[ContestSnapshot],
    contest_numbers: Sequence[int],
    number_of_tickets: int,
    seed: int | None,
) -> list[BacktestResult]:
    """Executa PREDICT + SCORE, na ordem certa, para cada numero em
    ``contest_numbers``. Para cada concurso-alvo N:

        1. history = todos os concursos de ``all_contests`` com numero < N
           (ordenado, mas a ordem nao importa para o filtro).
        2. batch = predict_for_contest(engine, history, N, ...)  -- freeze.
        3. sealed = SealedContestResult(resultado real de N)
        4. target_result = sealed.open()                         -- so agora abre.
        5. score_batch(batch, target_result).

    ``all_contests`` deve conter o resultado real de cada numero em
    ``contest_numbers`` (para a fase SCORE) alem do historico necessario.
    """
    por_numero = {c.number: c for c in all_contests}
    resultados: list[BacktestResult] = []
    for target_contest in contest_numbers:
        if target_contest not in por_numero:
            raise ValueError(f"Concurso-alvo {target_contest} nao esta em all_contests.")
        history = [c for c in all_contests if c.number < target_contest]
        batch = predict_for_contest(engine, history, target_contest, number_of_tickets, seed)
        sealed = SealedContestResult(por_numero[target_contest])
        target_result = sealed.open()
        resultados.append(score_batch(batch, target_result))
    return resultados


def _git_commit_sha() -> str | None:
    try:
        saida = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=10, check=False
        )
        return saida.stdout.strip() if saida.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def reproducibility_record(
    engine: EngineAdapter,
    seed: int | None,
    number_of_tickets: int,
    contest_numbers: Sequence[int],
    history_fingerprint: str,
) -> dict:
    """Registro de reprodutibilidade (Fase 9): tudo que e necessario para
    provar/repetir uma execucao. Duas execucoes com os mesmos valores aqui
    (exceto ``timestamp``) devem produzir resultados logicamente idênticos
    -- ver teste dedicado."""
    return {
        "git_commit_sha": _git_commit_sha(),
        "engine_name": engine.name,
        "engine_version": engine.version,
        "seed": seed,
        "number_of_tickets": number_of_tickets,
        "contest_range": [min(contest_numbers), max(contest_numbers)] if contest_numbers else None,
        "contests_evaluated": len(contest_numbers),
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "data_fingerprint": history_fingerprint,
    }
