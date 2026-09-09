"""Adaptadores de motor para o harness de backtest walk-forward (LF-04).

Cada adapter implementa o protocolo ``EngineAdapter``: recebe SOMENTE o
historico permitido (concursos com numero < concurso-alvo, ja filtrado por
``src/backtest/harness.py``), a quantidade de tickets e uma seed -- NUNCA o
resultado do concurso-alvo. A assinatura do protocolo nem declara esse
parametro, entao nao ha como um adapter "esquecer" de nao usa-lo.

NAO altera nenhum motor existente. ``MotorEliteV2Adapter`` chama
``src.motor_elite_v2.gerar_jogos_v2`` -- o motor de producao real (ver
FASE 3 do relatorio LF-04) -- exatamente como ele ja e, sem modificar seu
codigo.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import random
from typing import Protocol, Sequence

import pandas as pd

from ..motor_elite_v2 import MOTOR_ELITE_V2, gerar_jogos_v2
from ..validacao_jogos import ConfiguracaoMotor
from .contracts import ContestSnapshot

Ticket = tuple[str, tuple[int, ...]]


class EngineAdapter(Protocol):
    """Protocolo que todo motor precisa satisfazer para ser avaliado pelo
    harness. Note que a assinatura NAO tem parametro para o concurso-alvo
    nem para o resultado-alvo -- estruturalmente impossivel de vazar."""

    name: str
    version: str

    def generate(
        self,
        history: Sequence[ContestSnapshot],
        number_of_tickets: int,
        seed: int | None,
    ) -> list[Ticket]:
        ...


@dataclass
class ReferenceRandomEngine:
    """Motor de referencia, puramente aleatorio e determinístico (mesma
    seed -> mesmos tickets), usado para provar que o HARNESS em si
    funciona corretamente antes de avaliar qualquer motor real (Fase 11).
    Ignora deliberadamente o historico -- nao e uma estrategia, e um
    test-double."""

    name: str = "REFERENCE_RANDOM_ENGINE"
    version: str = "1.0"

    def generate(
        self,
        history: Sequence[ContestSnapshot],
        number_of_tickets: int,
        seed: int | None,
    ) -> list[Ticket]:
        rng = random.Random(seed)
        tickets: list[Ticket] = []
        for indice in range(number_of_tickets):
            numeros = tuple(sorted(rng.sample(range(1, 26), 15)))
            tickets.append((f"ticket_{indice}", numeros))
        return tickets


def _history_para_dataframe(history: Sequence[ContestSnapshot]) -> pd.DataFrame:
    """Converte a lista de ``ContestSnapshot`` (ja filtrada pelo harness
    para conter somente concursos < alvo) no formato de DataFrame que
    ``gerar_jogos_v2`` espera (Concurso, Data, Bola1..Bola15). Contem
    EXATAMENTE os concursos recebidos -- nenhum dado extra, nenhuma leitura
    de arquivo/rede."""
    linhas = []
    for concurso in history:
        linha = {"Concurso": concurso.number, "Data": concurso.date}
        for posicao, dezena in enumerate(concurso.numbers, start=1):
            linha[f"Bola{posicao}"] = dezena
        linhas.append(linha)
    colunas = ["Concurso", "Data", *[f"Bola{i}" for i in range(1, 16)]]
    return pd.DataFrame(linhas, columns=colunas)


@dataclass
class MotorEliteV2Adapter:
    """Adapter fino para o motor de producao real
    (``src.motor_elite_v2.gerar_jogos_v2``). NAO altera o motor -- apenas
    traduz ``Sequence[ContestSnapshot]`` para o ``DataFrame`` que ele
    espera e traduz a saida de volta para tickets rotulados.

    Recebe SOMENTE historico/quantidade/seed/configuracao -- nunca o
    concurso-alvo nem o resultado-alvo (nem sequer haveria como, dado o
    protocolo ``EngineAdapter``)."""

    configuracao: ConfiguracaoMotor | None = None
    name: str = "MOTOR_ELITE_V2"
    version: str = field(default=MOTOR_ELITE_V2)

    def generate(
        self,
        history: Sequence[ContestSnapshot],
        number_of_tickets: int,
        seed: int | None,
    ) -> list[Ticket]:
        if not history:
            raise ValueError("MotorEliteV2Adapter precisa de pelo menos 1 concurso de historico.")
        df_historico = _history_para_dataframe(history)
        jogos = gerar_jogos_v2(
            df_historico,
            quantidade=number_of_tickets,
            configuracao=self.configuracao,
            semente=seed,
        )
        tickets: list[Ticket] = []
        for _, linha in jogos.iterrows():
            numeros = tuple(sorted(int(linha[f"Bola{i}"]) for i in range(1, 16)))
            tickets.append((str(linha["Perfil"]), numeros))
        return tickets
