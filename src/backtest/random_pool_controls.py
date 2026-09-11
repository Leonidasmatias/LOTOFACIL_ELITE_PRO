"""Controles aleatorios para comparacao contra o pool autentico do motor
(LF-09D, Fase 6).

Ambos usam RNG PROPRIO e independente -- nunca consomem nem alteram o
``random.Random`` interno de ``gerar_jogos_v2``. Nenhum dos dois gera
candidatos usando qualquer informacao do motor (pesos, ranking, score).

G0: uniforme em C(25,15) -- nenhuma restricao estrutural.
G1: uniforme em C(25,15) condicionado a passar em ``validar_jogo``
(rejection sampling) -- reusa a MESMA funcao publica de producao,
inalterada, apenas como filtro sobre uma amostra independente. Isola o
efeito de "ser estruturalmente valido" do efeito especifico do gerador
ponderado por score (LF-09D, mecanismo A').
"""
from __future__ import annotations

import random

from ..validacao_jogos import ConfiguracaoMotor, validar_jogo

Ticket = tuple[int, ...]


def generate_g0_pool(n: int, seed: int) -> tuple[Ticket, ...]:
    """``n`` tickets uniformes independentes em C(25,15), sem nenhuma
    restricao estrutural. RNG proprio, seed determinística."""
    rng = random.Random(seed)
    return tuple(tuple(sorted(rng.sample(range(1, 26), 15))) for _ in range(n))


def generate_g1_pool(
    n: int,
    seed: int,
    ultimo: frozenset[int],
    configuracao: ConfiguracaoMotor | None = None,
    max_tentativas_multiplicador: int = 50,
) -> tuple[Ticket, ...]:
    """``n`` tickets uniformes que passam em ``validar_jogo`` (mesma
    funcao de producao, inalterada) -- rejection sampling com RNG
    proprio e independente. Levanta ``RuntimeError`` se o limite de
    tentativas for excedido sem completar ``n`` tickets (protecao
    contra loop infinito, nao deveria ocorrer na pratica -- taxa de
    aceitacao empirica ~76%)."""
    config = configuracao or ConfiguracaoMotor()
    rng = random.Random(seed)
    aceitos: list[Ticket] = []
    tentativas = 0
    limite = max(n * max_tentativas_multiplicador, 1000)
    while len(aceitos) < n and tentativas < limite:
        tentativas += 1
        candidato = tuple(sorted(rng.sample(range(1, 26), 15)))
        try:
            validar_jogo(candidato, config, ultimo)
        except ValueError:
            continue
        aceitos.append(candidato)
    if len(aceitos) < n:
        raise RuntimeError(f"G1: apenas {len(aceitos)}/{n} tickets validos apos {tentativas} tentativas.")
    return tuple(aceitos)
