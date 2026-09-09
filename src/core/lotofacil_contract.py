"""Contrato matematico central da Lotofacil (Fase LF-02).

Camada pura, aditiva e independente de qualquer motor/estrategia/score
existente: define os invariantes estruturais da Lotofacil (universo de
dezenas, tamanho do jogo/resultado, combinatoria e probabilidade
hipergeometrica exata) como constantes e funcoes verificaveis.

Este modulo:
- NAO altera nenhuma regra de negocio, peso, score, motor ou Trend Hybrid
  existente;
- NAO e importado por nenhum motor de producao (app.py, motor_elite_v2.py,
  core/motor_elite.py, core/trend_hybrid_engine.py, core/elite_score.py);
- e deliberadamente distinto de ``src/validacao_jogos.py::validar_jogo``,
  que alem do invariante matematico tambem aplica regras de ESTRATEGIA
  configuraveis (soma, pares, sequencia, repeticao com o ultimo concurso).
  As funcoes ``validar_jogo``/``validar_resultado`` deste modulo verificam
  SOMENTE o invariante matematico puro da Lotofacil, sem nenhuma regra de
  negocio, e servem de base para os testes de contrato/regressao contra
  contaminacao semantica (ex.: universo ou tamanho de outra loteria).
"""
from __future__ import annotations

from math import comb
from typing import Any, Iterable

UNIVERSO_MIN = 1
UNIVERSO_MAX = 25
TOTAL_DEZENAS_UNIVERSO = UNIVERSO_MAX - UNIVERSO_MIN + 1  # 25
DEZENAS_POR_JOGO = 15
DEZENAS_POR_RESULTADO = 15

# C(25, 15): total de apostas simples distintas possiveis na Lotofacil.
# Derivado via math.comb (nunca hardcoded) -- ver
# tests/test_lotofacil_contract.py para a verificacao == 3_268_760.
TOTAL_COMBINACOES_SIMPLES = comb(TOTAL_DEZENAS_UNIVERSO, DEZENAS_POR_JOGO)

# Quantas dezenas do universo NAO estao em uma aposta/resultado de 15
# (25 - 15 = 10) -- usado na formula hipergeometrica de probabilidade_acertos.
_DEZENAS_FORA_DO_JOGO = TOTAL_DEZENAS_UNIVERSO - DEZENAS_POR_JOGO


class ContratoLotofacilError(ValueError):
    """Violacao de um invariante matematico da Lotofacil."""


def _validar_estrutura(dezenas: Any, quantidade_esperada: int, rotulo: str) -> tuple[int, ...]:
    """Nucleo comum e determinístico de toda validacao deste contrato.

    Rejeita explicitamente (nunca silenciosamente): quantidade errada de
    itens, itens que nao sejam ``int`` (bool, float, str, None inclusive),
    dezenas duplicadas e dezenas fora de ``UNIVERSO_MIN..UNIVERSO_MAX``.
    """
    if dezenas is None:
        raise ContratoLotofacilError(f"{rotulo} nao pode ser None.")
    if isinstance(dezenas, (str, bytes)):
        raise ContratoLotofacilError(
            f"{rotulo} nao pode ser uma string/bytes; esperado um iteravel de inteiros."
        )
    try:
        itens = list(dezenas)
    except TypeError as erro:
        raise ContratoLotofacilError(f"{rotulo} deve ser um iteravel de inteiros.") from erro

    if len(itens) != quantidade_esperada:
        raise ContratoLotofacilError(
            f"{rotulo} deve conter exatamente {quantidade_esperada} dezenas; recebeu {len(itens)}."
        )

    inteiros: list[int] = []
    for item in itens:
        # bool e subclasse de int em Python (isinstance(True, int) == True),
        # por isso precisa ser rejeitado explicitamente ANTES do teste de
        # int -- senao True/False seriam silenciosamente aceitos como 1/0.
        if isinstance(item, bool):
            raise ContratoLotofacilError(f"{rotulo} nao pode conter valores booleanos ({item!r}).")
        if not isinstance(item, int):
            raise ContratoLotofacilError(
                f"{rotulo} deve conter apenas inteiros; recebeu {item!r} ({type(item).__name__})."
            )
        inteiros.append(item)

    if len(set(inteiros)) != quantidade_esperada:
        raise ContratoLotofacilError(f"{rotulo} nao pode conter dezenas duplicadas.")

    fora_de_faixa = sorted(d for d in inteiros if not (UNIVERSO_MIN <= d <= UNIVERSO_MAX))
    if fora_de_faixa:
        raise ContratoLotofacilError(
            f"{rotulo} contem dezena(s) fora do universo {UNIVERSO_MIN}..{UNIVERSO_MAX}: {fora_de_faixa}."
        )

    return tuple(sorted(inteiros))


def validar_dezenas_lotofacil(
    dezenas: Any,
    quantidade_esperada: int = DEZENAS_POR_JOGO,
    rotulo: str = "Conjunto de dezenas",
) -> tuple[int, ...]:
    """Invariante matematico puro e generico: exatamente ``quantidade_esperada``
    inteiros unicos, nao-booleanos, dentro de ``UNIVERSO_MIN..UNIVERSO_MAX``.

    Deterministico: a mesma entrada sempre produz a mesma tupla ordenada de
    saida, ou sempre a mesma excecao ``ContratoLotofacilError``.
    """
    return _validar_estrutura(dezenas, quantidade_esperada, rotulo)


def normalizar_dezenas(
    dezenas: Any,
    quantidade_esperada: int = DEZENAS_POR_JOGO,
) -> tuple[int, ...]:
    """Valida e normaliza (ordena) um conjunto de dezenas. Mesma semantica
    de ``validar_dezenas_lotofacil``; nome documental para uso em pontos que
    normalizam um conjunto antes de compara-lo ou persisti-lo."""
    return _validar_estrutura(dezenas, quantidade_esperada, "Conjunto de dezenas")


def validar_jogo(dezenas: Any) -> tuple[int, ...]:
    """Uma aposta simples da Lotofacil: exatamente ``DEZENAS_POR_JOGO`` (15)
    dezenas unicas, inteiras, em ``UNIVERSO_MIN..UNIVERSO_MAX`` (1..25).

    Contrato puramente matematico -- nao aplica nenhuma regra de estrategia
    (soma, pares, sequencia). Ver ``src/validacao_jogos.py::validar_jogo``
    para as regras de negocio configuraveis do Motor Elite.
    """
    return _validar_estrutura(dezenas, DEZENAS_POR_JOGO, "Jogo")


def validar_resultado(dezenas: Any) -> tuple[int, ...]:
    """O resultado oficial de um concurso da Lotofacil: exatamente
    ``DEZENAS_POR_RESULTADO`` (15) dezenas unicas, inteiras, em 1..25."""
    return _validar_estrutura(dezenas, DEZENAS_POR_RESULTADO, "Resultado")


# --- Combinatoria pura ---------------------------------------------------

def total_combinacoes(n: int, k: int) -> int:
    """C(n, k) generico -- delega para math.comb, nao reimplementa combinatoria."""
    return comb(n, k)


def dezenas_em_comum(jogo_a: Iterable[int], jogo_b: Iterable[int]) -> int:
    """Quantidade de dezenas presentes em ambos os conjuntos."""
    return len(set(jogo_a) & set(jogo_b))


def distancia_conjunto(jogo_a: Iterable[int], jogo_b: Iterable[int]) -> int:
    """Distancia de Hamming equivalente para conjuntos: quantas dezenas
    diferem entre os dois jogos (uniao menos intersecao). Para dois jogos de
    15 dezenas cada, e sempre um inteiro par entre 0 (identicos) e 30
    (totalmente disjuntos)."""
    conjunto_a, conjunto_b = set(jogo_a), set(jogo_b)
    return len(conjunto_a - conjunto_b) + len(conjunto_b - conjunto_a)


def repetidas_com_concurso_anterior(jogo: Iterable[int], concurso_anterior: Iterable[int]) -> int:
    """Quantidade de dezenas do ``jogo`` que tambem sairam no
    ``concurso_anterior`` -- alias semantico de ``dezenas_em_comum`` para o
    caso de uso especifico de comparar contra o sorteio anterior."""
    return dezenas_em_comum(jogo, concurso_anterior)


# --- Probabilidade hipergeometrica exata --------------------------------

def probabilidade_acertos(k: int) -> float:
    """P(X = k acertos) para UMA aposta simples de 15 dezenas contra um
    resultado de 15 dezenas sorteadas de um universo de 25, pela
    distribuicao hipergeometrica exata:

        P(X = k) = C(15, k) * C(10, 15 - k) / C(25, 15)

    ``k`` deve ser um inteiro entre 0 e 15. Para k < 5, o resultado exato e
    0.0 (matematicamente impossivel: so existem 10 dezenas fora do jogo, e
    errar mais de 10 delas nao e possivel com apenas 15 dezenas apostadas).

    Funcao puramente matematica/documental: NAO representa nem promete
    desempenho de nenhum motor ou estrategia deste projeto.
    """
    if isinstance(k, bool) or not isinstance(k, int):
        raise ContratoLotofacilError(f"k deve ser um inteiro; recebeu {k!r}.")
    if not (0 <= k <= DEZENAS_POR_JOGO):
        raise ContratoLotofacilError(f"k deve estar entre 0 e {DEZENAS_POR_JOGO}; recebeu {k}.")

    erros = DEZENAS_POR_JOGO - k
    if erros > _DEZENAS_FORA_DO_JOGO:
        return 0.0
    numerador = comb(DEZENAS_POR_JOGO, k) * comb(_DEZENAS_FORA_DO_JOGO, erros)
    return numerador / TOTAL_COMBINACOES_SIMPLES


def probabilidade_15_acertos() -> float:
    """P(15 acertos) para uma unica aposta simples = 1 / C(25, 15)."""
    return 1.0 / TOTAL_COMBINACOES_SIMPLES
