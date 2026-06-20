from __future__ import annotations

import pytest

from src.validacao_jogos import ConfiguracaoMotor, sequencia_maxima, validar_carteira, validar_jogo


def test_validador_rejeita_quantidade_duplicidade_e_intervalo() -> None:
    with pytest.raises(ValueError, match="exatamente 15"):
        validar_jogo(range(1, 15))
    with pytest.raises(ValueError, match="duplicadas"):
        validar_jogo([1] * 15)
    with pytest.raises(ValueError, match="entre 1 e 25"):
        validar_jogo([0, *range(1, 15)])


def test_validador_respeita_soma_e_paridade_configuraveis() -> None:
    jogo = list(range(1, 16))
    with pytest.raises(ValueError, match="Soma"):
        validar_jogo(jogo, ConfiguracaoMotor(soma_minima=180, soma_maxima=220))
    with pytest.raises(ValueError, match="pares"):
        validar_jogo(jogo, ConfiguracaoMotor(soma_minima=100, soma_maxima=220, pares_minimo=8, pares_maximo=9))


def test_carteira_rejeita_jogos_iguais_ou_parecidos() -> None:
    jogo = list(range(1, 16))
    config = ConfiguracaoMotor(soma_minima=100, soma_maxima=230, repetidas_minimo=0, repetidas_maximo=15, sequencia_maxima=15)
    with pytest.raises(ValueError, match="diferentes"):
        validar_carteira([jogo, jogo], config)
    parecido = list(range(1, 15)) + [16]
    with pytest.raises(ValueError, match="parecidos"):
        validar_carteira([jogo, parecido], config)


def test_sequencia_maxima() -> None:
    assert sequencia_maxima([1, 2, 3, 7, 8, 10]) == 3
