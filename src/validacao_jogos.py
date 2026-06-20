from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Iterable, Sequence


@dataclass(frozen=True)
class ConfiguracaoMotor:
    soma_minima: int = 165
    soma_maxima: int = 225
    pares_minimo: int = 6
    pares_maximo: int = 9
    repetidas_minimo: int = 7
    repetidas_maximo: int = 12
    sequencia_maxima: int = 7
    diferenca_minima_entre_jogos: int = 3
    candidatos_por_perfil: int = 700

    def validar(self) -> None:
        if not 0 <= self.soma_minima <= self.soma_maxima:
            raise ValueError("Faixa de soma inválida.")
        if not 0 <= self.pares_minimo <= self.pares_maximo <= 15:
            raise ValueError("Faixa de pares/ímpares inválida.")
        if not 0 <= self.repetidas_minimo <= self.repetidas_maximo <= 15:
            raise ValueError("Faixa de repetição inválida.")
        if self.sequencia_maxima < 1:
            raise ValueError("A sequência máxima deve ser positiva.")
        if not 1 <= self.diferenca_minima_entre_jogos <= 15:
            raise ValueError("Diversidade mínima inválida.")
        if self.candidatos_por_perfil < 50:
            raise ValueError("Use ao menos 50 candidatos por perfil.")


def sequencia_maxima(dezenas: Sequence[int]) -> int:
    ordenadas = sorted(set(int(d) for d in dezenas))
    maior = atual = 1 if ordenadas else 0
    for anterior, proxima in zip(ordenadas, ordenadas[1:]):
        atual = atual + 1 if proxima == anterior + 1 else 1
        maior = max(maior, atual)
    return maior


def validar_jogo(
    dezenas: Iterable[int],
    configuracao: ConfiguracaoMotor | None = None,
    ultimo_concurso: Iterable[int] | None = None,
) -> tuple[int, ...]:
    config = configuracao or ConfiguracaoMotor()
    config.validar()
    jogo = tuple(sorted(int(d) for d in dezenas))
    if len(jogo) != 15:
        raise ValueError("Todo jogo deve conter exatamente 15 dezenas.")
    if len(set(jogo)) != 15:
        raise ValueError("O jogo não pode conter dezenas duplicadas.")
    if any(d < 1 or d > 25 for d in jogo):
        raise ValueError("As dezenas devem estar entre 1 e 25.")
    soma = sum(jogo)
    if not config.soma_minima <= soma <= config.soma_maxima:
        raise ValueError(f"Soma {soma} fora da faixa configurada.")
    pares = sum(d % 2 == 0 for d in jogo)
    if not config.pares_minimo <= pares <= config.pares_maximo:
        raise ValueError(f"Quantidade de pares {pares} fora da faixa configurada.")
    if sequencia_maxima(jogo) > config.sequencia_maxima:
        raise ValueError("Jogo possui sequência maior que a permitida.")
    if ultimo_concurso is not None:
        repetidas = len(set(jogo) & {int(d) for d in ultimo_concurso})
        if not config.repetidas_minimo <= repetidas <= config.repetidas_maximo:
            raise ValueError(f"Repetição de {repetidas} dezenas fora da faixa configurada.")
    return jogo


def validar_carteira(
    jogos: Iterable[Iterable[int]],
    configuracao: ConfiguracaoMotor | None = None,
    ultimo_concurso: Iterable[int] | None = None,
) -> list[tuple[int, ...]]:
    config = configuracao or ConfiguracaoMotor()
    carteira = [validar_jogo(jogo, config, ultimo_concurso) for jogo in jogos]
    if len(set(carteira)) != len(carteira):
        raise ValueError("Todos os jogos da carteira devem ser diferentes.")
    for jogo_a, jogo_b in combinations(carteira, 2):
        diferenca = len(set(jogo_a) - set(jogo_b))
        if diferenca < config.diferenca_minima_entre_jogos:
            raise ValueError("A carteira contém jogos parecidos demais.")
    return carteira
