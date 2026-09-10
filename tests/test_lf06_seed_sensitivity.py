"""Testes das politicas de seed do motor para diagnostico de sensibilidade
(LF-06, Fase 13).

Provam que: exatamente 10 politicas pre-registradas; todas as bases sao
distintas; a politica original do LF-05 esta presente e produz EXATAMENTE
a mesma seed que ``benchmark.motor_seed_policy`` (nunca substituida); cada
politica e determinística."""
from __future__ import annotations

import pytest

from src.backtest.benchmark import motor_seed_policy
from src.backtest.seed_sensitivity import SEED_POLICY_BASES, seed_for_policy


def test_existem_exatamente_dez_politicas_pre_registradas() -> None:
    assert len(SEED_POLICY_BASES) == 10


def test_todas_as_bases_sao_distintas() -> None:
    assert len(set(SEED_POLICY_BASES.values())) == 10


def test_politica_original_lf05_esta_presente_e_nunca_substituida() -> None:
    assert "ORIGINAL_LF05" in SEED_POLICY_BASES
    assert SEED_POLICY_BASES["ORIGINAL_LF05"] == 7_000_000


@pytest.mark.parametrize("target", [101, 500, 3725])
def test_politica_original_reproduz_exatamente_motor_seed_policy_do_lf05(target: int) -> None:
    assert seed_for_policy("ORIGINAL_LF05", target) == motor_seed_policy(7_000_000, target)


def test_politicas_alternativas_sao_deterministicas() -> None:
    assert seed_for_policy("ALT_03", 200) == seed_for_policy("ALT_03", 200)


def test_politicas_distintas_produzem_seeds_distintas_para_o_mesmo_alvo() -> None:
    seeds = {seed_for_policy(nome, 500) for nome in SEED_POLICY_BASES}
    assert len(seeds) == 10


def test_seed_for_policy_rejeita_politica_desconhecida() -> None:
    with pytest.raises(ValueError):
        seed_for_policy("POLITICA_INEXISTENTE", 100)
