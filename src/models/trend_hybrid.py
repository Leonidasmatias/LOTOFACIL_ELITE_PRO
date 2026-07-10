"""Modelos de dominio: Trend Hybrid Engine (indicadores, pesos e bilhete).

Fase Trend Hybrid V1. Segue o mesmo padrao das demais camadas ``models/``:
dataclasses puras, sem I/O e sem regra de negocio -- apenas a forma dos
dados trocados entre ``core``, ``services``, ``ai`` e ``ui``. Nenhum calculo
vive aqui; ver ``src/core/trend_hybrid_engine.py``.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PesosTendencia:
    """Pesos do Trend Score (Fase 2 da especificacao Trend Hybrid 9+6).

    Os pesos-base (tudo exceto ``peso_atraso``) somam 1.0 entre si e seguem
    os valores sugeridos na especificacao (30/20/15/10/10/5/5/5). O peso do
    atraso e o unico "adaptativo" (0 a 10%, conforme pedido): ``pesos_efetivos``
    reescala os pesos-base por ``(1 - peso_atraso)`` para que a soma final dos
    pesos efetivos seja sempre exatamente 1.0, qualquer que seja o valor
    escolhido para o atraso.
    """

    peso_ult10: float = 0.30
    peso_ult20: float = 0.20
    peso_ult50: float = 0.15
    peso_ult100: float = 0.10
    peso_historico: float = 0.10
    peso_regularidade: float = 0.05
    peso_momentum: float = 0.05
    peso_persistencia: float = 0.05
    peso_atraso: float = 0.05

    def validar(self) -> None:
        pesos_base = (
            self.peso_ult10,
            self.peso_ult20,
            self.peso_ult50,
            self.peso_ult100,
            self.peso_historico,
            self.peso_regularidade,
            self.peso_momentum,
            self.peso_persistencia,
        )
        if any(peso < 0 for peso in pesos_base):
            raise ValueError("Nenhum peso-base pode ser negativo.")
        if sum(pesos_base) <= 0:
            raise ValueError("A soma dos pesos-base deve ser positiva.")
        if not 0.0 <= self.peso_atraso <= 0.10:
            raise ValueError("peso_atraso deve estar entre 0.0 e 0.10 (0% a 10%), conforme a faixa adaptativa da especificacao.")

    def pesos_efetivos(self) -> dict[str, float]:
        """Pesos finais (somam exatamente 1.0) usados no Trend Score.

        Aplica o fator ``(1 - peso_atraso) / soma_dos_pesos_base`` a cada
        peso-base e devolve ``atraso`` com o valor escolhido diretamente.
        """
        self.validar()
        base = {
            "ult10": self.peso_ult10,
            "ult20": self.peso_ult20,
            "ult50": self.peso_ult50,
            "ult100": self.peso_ult100,
            "historico": self.peso_historico,
            "regularidade": self.peso_regularidade,
            "momentum": self.peso_momentum,
            "persistencia": self.peso_persistencia,
        }
        soma_base = sum(base.values())
        fator = (1.0 - self.peso_atraso) / soma_base
        efetivos = {chave: valor * fator for chave, valor in base.items()}
        efetivos["atraso"] = self.peso_atraso
        return efetivos


@dataclass(frozen=True, slots=True)
class IndicadoresDezena:
    """Indicadores brutos (nao normalizados) de uma dezena, calculados usando
    apenas concursos anteriores ao concurso-alvo (nunca ha vazamento
    temporal). Ver ``core.trend_hybrid_engine`` para a derivacao de cada
    indicador."""

    dezena: int
    frequencia_ult10: int
    frequencia_ult20: int
    frequencia_ult50: int
    frequencia_ult100: int
    frequencia_geral: int
    atraso: int
    regularidade: float
    momentum: float
    sequencia_consecutiva: int
    persistencia: float
    saiu_no_ultimo: bool


@dataclass(frozen=True, slots=True)
class DezenaPontuada:
    """Uma dezena com seus indicadores brutos, os valores normalizados
    (0-1, min-max entre as 25 dezenas) usados no calculo, e o Trend Score
    final (0-100)."""

    indicadores: IndicadoresDezena
    normalizados: dict[str, float]
    trend_score: float


@dataclass(frozen=True, slots=True)
class BilheteTrendHybrid:
    """Bilhete de 15 dezenas gerado pelo Trend Hybrid Engine: N dezenas do
    Grupo A (saiu no ultimo concurso) + (15-N) dezenas do Grupo B (nao saiu),
    escolhidas pelo maior Trend Score dentro de cada grupo, respeitando as
    regras de ``ConfiguracaoMotor``/``validar_jogo`` ja existentes."""

    dezenas: tuple[int, ...]
    divisao: tuple[int, int]
    grupo_a_selecionadas: tuple[int, ...]
    grupo_b_selecionadas: tuple[int, ...]
    grupo_a_descartadas: tuple[int, ...]
    grupo_b_descartadas: tuple[int, ...]
    margem_busca: int
    trend_score_total: float
    pontuacoes: tuple[DezenaPontuada, ...]

    def __post_init__(self) -> None:
        if len(self.dezenas) != 15:
            raise ValueError("Um bilhete da Lotofacil precisa ter exatamente 15 dezenas.")
        if len(set(self.dezenas)) != 15:
            raise ValueError("O bilhete nao pode conter dezenas duplicadas.")
        if sum(self.divisao) != 15:
            raise ValueError("A divisao (Grupo A + Grupo B) precisa somar 15.")

    def pontuacao_da_dezena(self, dezena: int) -> DezenaPontuada:
        for pontuada in self.pontuacoes:
            if pontuada.indicadores.dezena == dezena:
                return pontuada
        raise KeyError(f"Dezena {dezena} nao encontrada nas pontuacoes do bilhete.")


@dataclass(frozen=True, slots=True)
class BilheteSorteioGrupos:
    """Bilhete sorteado ALEATORIAMENTE dentro dos grupos (Grupo A: as
    dezenas do ultimo concurso; Grupo B: as que nao sairam) -- sem uso do
    Trend Score. Diferente de ``BilheteTrendHybrid`` (sempre a mesma
    recomendacao, pelas de maior score), este modo existe para gerar uma
    combinacao nova a cada clique, mantendo apenas a estrutura de repeticao
    da divisao escolhida (ex.: 9 do ultimo concurso + 6 que nao sairam)."""

    dezenas: tuple[int, ...]
    divisao: tuple[int, int]
    grupo_a_selecionadas: tuple[int, ...]
    grupo_b_selecionadas: tuple[int, ...]
    semente: int | None
    numero_sorteio: int = 0

    def __post_init__(self) -> None:
        if len(self.dezenas) != 15:
            raise ValueError("Um bilhete da Lotofacil precisa ter exatamente 15 dezenas.")
        if len(set(self.dezenas)) != 15:
            raise ValueError("O bilhete nao pode conter dezenas duplicadas.")
        if sum(self.divisao) != 15:
            raise ValueError("A divisao (Grupo A + Grupo B) precisa somar 15.")
