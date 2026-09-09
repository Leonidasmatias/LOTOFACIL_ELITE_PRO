"""Dry-run real do harness de backtest walk-forward (LF-04, Fase 12).

Le a base historica real SOMENTE EM LEITURA (nunca escreve, nunca chama
rede) e roda o harness nos ultimos 20 concursos elegiveis, usando o motor
de producao real (``MotorEliteV2Adapter``) atraves do adapter -- ja
comprovadamente walk-forward safe por leitura de codigo (ver relatorio
LF-04, Fase 3/13: `gerar_jogos_v2` recebe o DataFrame como parametro
explicito, sem nenhuma leitura global).

Objetivo EXCLUSIVO: provar que o pipeline funciona ponta a ponta contra
dados reais. Isto NAO e uma alegacao de desempenho do motor -- apenas uma
prova de execucao. ``candidatos_por_perfil`` e reduzido so para manter o
teste rapido (nao altera nenhuma regra do motor, e um parametro de
configuracao ja suportado por ``ConfiguracaoMotor``).
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd

from src.backtest.engine_adapter import MotorEliteV2Adapter
from src.backtest.harness import load_contests_from_dataframe, reproducibility_record, run_walk_forward
from src.backtest.metrics import aggregate
from src.validacao_jogos import ConfiguracaoMotor

CAMINHO_BASE_REAL = Path(__file__).resolve().parents[1] / "dados" / "lotofacil_historico.csv"
NUMERO_DE_CONCURSOS_DRY_RUN = 20
SEED_DRY_RUN = 20260909


def _hash_arquivo(caminho: Path) -> str:
    return hashlib.sha256(caminho.read_bytes()).hexdigest()


def test_dry_run_real_prova_pipeline_sem_promessa_de_desempenho() -> None:
    hash_antes = _hash_arquivo(CAMINHO_BASE_REAL)

    df = pd.read_csv(CAMINHO_BASE_REAL, encoding="utf-8-sig")
    contests = load_contests_from_dataframe(df)
    assert len(contests) > NUMERO_DE_CONCURSOS_DRY_RUN + 100  # historico de sobra

    alvos = [c.number for c in contests[-NUMERO_DE_CONCURSOS_DRY_RUN:]]

    config_rapida = ConfiguracaoMotor(candidatos_por_perfil=50)
    engine = MotorEliteV2Adapter(configuracao=config_rapida)

    resultados = run_walk_forward(engine, contests, alvos, number_of_tickets=5, seed=SEED_DRY_RUN)

    assert len(resultados) == NUMERO_DE_CONCURSOS_DRY_RUN
    for resultado, alvo in zip(resultados, alvos):
        assert resultado.batch.target_contest == alvo
        assert resultado.batch.history_max_contest == alvo - 1  # walk-forward puro, sem gaps
        assert resultado.batch.engine_name == "MOTOR_ELITE_V2"
        assert len(resultado.batch.tickets) == 5

    agregado = aggregate(resultados)
    registro = reproducibility_record(
        engine,
        seed=SEED_DRY_RUN,
        number_of_tickets=5,
        contest_numbers=alvos,
        history_fingerprint=resultados[0].batch.data_fingerprint,
    )

    # Registro factual do dry-run (sem interpretacao promocional) -- fica
    # visivel no relatorio LF-04 e no output do pytest (-s / -v).
    print("\n--- LF-04 REAL DRY RUN (somente leitura, sem promessa de desempenho) ---")
    print(f"target range: {alvos[0]}..{alvos[-1]}")
    print("number_of_tickets por concurso: 5")
    print(f"seed: {SEED_DRY_RUN}")
    print(f"engine: {registro['engine_name']} ({registro['engine_version']})")
    print(f"git_commit_sha: {registro['git_commit_sha']}")
    print(f"max_hits (agregado): {agregado.max_hits}")
    print(f"mean_hits (agregado): {agregado.mean_hits}")
    print(f"hit_distribution: {agregado.hit_distribution}")
    print(f"frequency_ge: {agregado.frequency_ge}")

    # NAO fazemos nenhuma asserção sobre "o motor e bom"/"o motor acerta X" --
    # so confirmamos que o pipeline produziu numeros no intervalo fisicamente
    # possivel, provando que a execucao completou corretamente.
    assert 0 <= agregado.max_hits <= 15
    assert 0 <= agregado.mean_hits <= 15

    hash_depois = _hash_arquivo(CAMINHO_BASE_REAL)
    assert hash_depois == hash_antes, "Dry-run alterou o arquivo real -- violacao read-only."
