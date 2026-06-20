from __future__ import annotations

import random

import pandas as pd

from .carregar_dados import COLUNAS_DEZENAS
from .validacao_jogos import ConfiguracaoMotor, validar_carteira, validar_jogo


def gerar_carteira_aleatoria(
    df: pd.DataFrame,
    quantidade: int,
    configuracao: ConfiguracaoMotor | None = None,
    semente: int | None = None,
) -> list[tuple[int, ...]]:
    if quantidade not in {5, 10, 20, 30}:
        raise ValueError("A carteira deve conter 5, 10, 20 ou 30 jogos.")
    config = configuracao or ConfiguracaoMotor()
    ultimo = {int(valor) for valor in df.sort_values("Concurso").iloc[-1][COLUNAS_DEZENAS]}
    rng = random.Random(semente)
    carteira: list[tuple[int, ...]] = []
    tentativas = 0
    while len(carteira) < quantidade and tentativas < quantidade * 10000:
        tentativas += 1
        jogo = tuple(sorted(rng.sample(range(1, 26), 15)))
        try:
            validar_jogo(jogo, config, ultimo)
        except ValueError:
            continue
        if jogo in carteira:
            continue
        if any(len(set(jogo) - set(outro)) < config.diferenca_minima_entre_jogos for outro in carteira):
            continue
        carteira.append(jogo)
    if len(carteira) != quantidade:
        raise ValueError("Não foi possível gerar a carteira aleatória com a diversidade configurada.")
    validar_carteira(carteira, config, ultimo)
    return carteira


def desempenho_carteira(carteira: list[tuple[int, ...]], sorteadas: set[int]) -> dict:
    acertos = [len(set(jogo) & sorteadas) for jogo in carteira]
    return {
        "Melhor acerto": max(acertos, default=0),
        "Média de acertos": round(sum(acertos) / len(acertos), 4) if acertos else 0.0,
        "Jogos 11+": sum(valor >= 11 for valor in acertos),
        "Jogos 12+": sum(valor >= 12 for valor in acertos),
        "Jogos 13+": sum(valor >= 13 for valor in acertos),
        "Jogos 14+": sum(valor >= 14 for valor in acertos),
        "Jogos 15": sum(valor == 15 for valor in acertos),
    }
