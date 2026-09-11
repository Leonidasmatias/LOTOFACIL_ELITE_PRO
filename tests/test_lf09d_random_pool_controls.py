"""Testes dos controles aleatorios G0/G1 (LF-09D, Fase 24)."""
from __future__ import annotations

import random

import pytest

from src.backtest.random_pool_controls import generate_g0_pool, generate_g1_pool
from src.validacao_jogos import ConfiguracaoMotor, validar_jogo


def test_g0_pool_tamanho_e_tickets_validos() -> None:
    pool = generate_g0_pool(100, seed=1)
    assert len(pool) == 100
    for ticket in pool:
        assert len(ticket) == 15
        assert len(set(ticket)) == 15
        assert all(1 <= d <= 25 for d in ticket)


def test_g0_pool_e_deterministico_por_seed() -> None:
    assert generate_g0_pool(50, seed=42) == generate_g0_pool(50, seed=42)


def test_g0_pool_seeds_diferentes_produzem_pools_diferentes() -> None:
    assert generate_g0_pool(50, seed=1) != generate_g0_pool(50, seed=2)


def test_g0_pool_nao_usa_nenhuma_restricao_estrutural() -> None:
    """G0 nao deve estar sistematicamente confinado as faixas de
    soma/pares do motor -- prova indireta de ausencia de filtro:
    somas fora da faixa configurada [165,225] devem poder ocorrer."""
    pool = generate_g0_pool(2000, seed=7)
    somas = [sum(t) for t in pool]
    assert min(somas) < 165 or max(somas) > 225  # alta probabilidade estatistica


def test_g1_pool_tamanho_e_tickets_validos() -> None:
    config = ConfiguracaoMotor()
    ultimo = frozenset(range(1, 16))
    pool = generate_g1_pool(100, seed=1, ultimo=ultimo, configuracao=config)
    assert len(pool) == 100
    for ticket in pool:
        validar_jogo(ticket, config, ultimo)  # nao deve levantar


def test_g1_pool_e_deterministico_por_seed() -> None:
    ultimo = frozenset(range(1, 16))
    r1 = generate_g1_pool(80, seed=42, ultimo=ultimo)
    r2 = generate_g1_pool(80, seed=42, ultimo=ultimo)
    assert r1 == r2


def test_g1_pool_seeds_diferentes_produzem_pools_diferentes() -> None:
    ultimo = frozenset(range(1, 16))
    assert generate_g1_pool(80, seed=1, ultimo=ultimo) != generate_g1_pool(80, seed=2, ultimo=ultimo)


def test_g1_usa_a_mesma_funcao_validar_jogo_de_producao() -> None:
    """Confirma que G1 nao duplica a logica de validacao -- reusa o
    mesmo simbolo importado de producao."""
    from src.backtest.random_pool_controls import validar_jogo as validar_jogo_importado

    assert validar_jogo_importado is validar_jogo


def test_g0_e_g1_usam_rng_independente_do_motor() -> None:
    """G0/G1 nao devem consumir nem depender do estado de nenhum RNG
    global compartilhado -- cada chamada cria seu proprio
    ``random.Random`` local, comprovado indiretamente: chamar
    ``random.seed(...)`` globalmente ANTES nao muda o resultado."""
    ultimo = frozenset(range(1, 16))
    random.seed(99999)
    esperado_g0 = generate_g0_pool(30, seed=5)
    esperado_g1 = generate_g1_pool(30, seed=5, ultimo=ultimo)
    random.seed(1)  # muda o estado do RNG global
    assert generate_g0_pool(30, seed=5) == esperado_g0
    assert generate_g1_pool(30, seed=5, ultimo=ultimo) == esperado_g1


def test_g1_levanta_erro_se_nao_atingir_n_no_limite() -> None:
    # candidatos_por_perfil nao usado aqui, mas config com faixa de
    # soma impossivelmente estreita forca taxa de aceitacao ~0.
    config = ConfiguracaoMotor(soma_minima=195, soma_maxima=195)
    ultimo = frozenset(range(1, 16))
    with pytest.raises(RuntimeError):
        generate_g1_pool(50, seed=1, ultimo=ultimo, configuracao=config, max_tentativas_multiplicador=5)
