from __future__ import annotations

from math import comb

import pytest

from src.core.lotofacil_contract import (
    ContratoLotofacilError,
    DEZENAS_POR_JOGO,
    DEZENAS_POR_RESULTADO,
    TOTAL_COMBINACOES_SIMPLES,
    TOTAL_DEZENAS_UNIVERSO,
    UNIVERSO_MAX,
    UNIVERSO_MIN,
    dezenas_em_comum,
    distancia_conjunto,
    normalizar_dezenas,
    probabilidade_15_acertos,
    probabilidade_acertos,
    repetidas_com_concurso_anterior,
    total_combinacoes,
    validar_dezenas_lotofacil,
    validar_jogo,
    validar_resultado,
)


# --- Fase 3: constantes do contrato -------------------------------------


def test_constantes_do_universo_lotofacil() -> None:
    assert UNIVERSO_MIN == 1
    assert UNIVERSO_MAX == 25
    assert TOTAL_DEZENAS_UNIVERSO == 25
    assert DEZENAS_POR_JOGO == 15
    assert DEZENAS_POR_RESULTADO == 15


def test_total_combinacoes_simples_e_derivado_de_math_comb() -> None:
    # Nao aceita o valor hardcoded sem confirmar contra math.comb.
    assert TOTAL_COMBINACOES_SIMPLES == comb(25, 15)
    assert TOTAL_COMBINACOES_SIMPLES == 3_268_760


def test_simetria_combinatoria_c25_15_igual_c25_10() -> None:
    assert comb(25, 15) == comb(25, 10)
    assert TOTAL_COMBINACOES_SIMPLES == comb(25, 10)


# --- Fase 5: invariantes executaveis -- casos VALIDOS -------------------


@pytest.mark.parametrize(
    "dezenas",
    [
        list(range(1, 16)),  # 1..15
        list(range(11, 26)),  # 11..25
        [3, 25, 1, 14, 7, 20, 2, 18, 9, 24, 5, 16, 11, 22, 13],  # conjunto valido nao ordenado
    ],
)
def test_validar_jogo_aceita_conjuntos_validos(dezenas: list[int]) -> None:
    resultado = validar_jogo(dezenas)
    assert resultado == tuple(sorted(dezenas))
    assert len(resultado) == 15
    assert len(set(resultado)) == 15
    assert all(1 <= d <= 25 for d in resultado)


def test_validar_jogo_e_deterministico() -> None:
    dezenas = [5, 3, 1, 25, 10, 8, 14, 2, 19, 22, 7, 11, 16, 20, 24]
    assert validar_jogo(dezenas) == validar_jogo(list(dezenas)) == validar_jogo(tuple(dezenas))


def test_validar_resultado_aceita_mesmo_invariante_que_jogo() -> None:
    dezenas = list(range(1, 16))
    assert validar_resultado(dezenas) == validar_jogo(dezenas) == tuple(dezenas)


def test_validar_dezenas_lotofacil_e_generico_em_quantidade_esperada() -> None:
    # validar_jogo/validar_resultado sao especializacoes fixas (15) deste
    # invariante generico e parametrizavel.
    assert validar_dezenas_lotofacil(list(range(1, 16))) == tuple(range(1, 16))
    assert validar_dezenas_lotofacil(list(range(1, 16))) == validar_jogo(list(range(1, 16)))
    with pytest.raises(ContratoLotofacilError, match="exatamente 15"):
        validar_dezenas_lotofacil(list(range(1, 15)))


def test_normalizar_dezenas_ordena_entrada_valida() -> None:
    entrada = [25, 1, 24, 2, 23, 3, 22, 4, 21, 5, 20, 6, 19, 7, 18]
    assert normalizar_dezenas(entrada) == tuple(sorted(entrada))


# --- Fase 5: invariantes executaveis -- casos INVALIDOS ------------------


def test_validar_jogo_rejeita_14_dezenas() -> None:
    with pytest.raises(ContratoLotofacilError, match="exatamente 15"):
        validar_jogo(list(range(1, 15)))


def test_validar_jogo_rejeita_16_dezenas() -> None:
    with pytest.raises(ContratoLotofacilError, match="exatamente 15"):
        validar_jogo(list(range(1, 17)))


def test_validar_jogo_rejeita_duplicata() -> None:
    with pytest.raises(ContratoLotofacilError, match="duplicadas"):
        validar_jogo([1, *range(1, 15)])


def test_validar_jogo_rejeita_zero() -> None:
    with pytest.raises(ContratoLotofacilError, match="universo"):
        validar_jogo([0, *range(1, 15)])


def test_validar_jogo_rejeita_26() -> None:
    with pytest.raises(ContratoLotofacilError, match="universo"):
        validar_jogo([26, *range(1, 15)])


def test_validar_jogo_rejeita_numero_negativo() -> None:
    with pytest.raises(ContratoLotofacilError, match="universo"):
        validar_jogo([-1, *range(1, 15)])


def test_validar_jogo_rejeita_float() -> None:
    with pytest.raises(ContratoLotofacilError, match="inteiros"):
        validar_jogo([1.0, *range(2, 16)])


def test_validar_jogo_rejeita_float_nao_inteiro() -> None:
    with pytest.raises(ContratoLotofacilError, match="inteiros"):
        validar_jogo([3.5, *range(2, 16)])


def test_validar_jogo_rejeita_string() -> None:
    with pytest.raises(ContratoLotofacilError, match="inteiros"):
        validar_jogo(["5", *range(2, 16)])


def test_validar_jogo_rejeita_string_completa_como_entrada() -> None:
    # Uma string e um Iterable (de caracteres) -- deve ser rejeitada
    # explicitamente antes de qualquer iteracao carater-a-carater.
    with pytest.raises(ContratoLotofacilError, match="string/bytes"):
        validar_jogo("123456789012345")


def test_validar_jogo_rejeita_none() -> None:
    with pytest.raises(ContratoLotofacilError, match="None"):
        validar_jogo(None)


def test_validar_jogo_rejeita_none_como_item() -> None:
    with pytest.raises(ContratoLotofacilError, match="inteiros"):
        validar_jogo([None, *range(2, 16)])


def test_validar_jogo_rejeita_bool_explicitamente() -> None:
    # bool e subclasse de int em Python -- precisa ser rejeitado, nao
    # silenciosamente aceito como 0/1.
    with pytest.raises(ContratoLotofacilError, match="booleanos"):
        validar_jogo([True, *range(2, 16)])
    with pytest.raises(ContratoLotofacilError, match="booleanos"):
        validar_jogo([False, *range(2, 16)])


def test_validar_jogo_rejeita_lista_vazia() -> None:
    with pytest.raises(ContratoLotofacilError, match="exatamente 15"):
        validar_jogo([])


def test_validar_jogo_rejeita_multiplas_violacoes_simultaneas() -> None:
    # 14 dezenas (quantidade errada) + uma duplicata + uma fora de faixa:
    # continua classificado como INVALIDO de forma deterministica.
    entrada = [1, 1, 26, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
    assert len(entrada) == 14
    with pytest.raises(ContratoLotofacilError):
        validar_jogo(entrada)


def test_validar_dezenas_lotofacil_rejeita_nao_iteravel() -> None:
    with pytest.raises(ContratoLotofacilError, match="iteravel"):
        validar_jogo(12345)


# --- Fase 6: helpers combinatorios puros ---------------------------------


def test_total_combinacoes_generico() -> None:
    assert total_combinacoes(25, 15) == comb(25, 15)
    assert total_combinacoes(5, 2) == 10
    assert total_combinacoes(6, 0) == 1


def test_dezenas_em_comum() -> None:
    jogo_a = list(range(1, 16))
    jogo_b = list(range(6, 21))
    assert dezenas_em_comum(jogo_a, jogo_b) == len(set(range(6, 16)))
    assert dezenas_em_comum(jogo_a, jogo_a) == 15
    assert dezenas_em_comum(jogo_a, list(range(16, 26))) == 0


def test_distancia_conjunto_e_par_e_dentro_de_0_30() -> None:
    jogo_a = list(range(1, 16))
    jogo_b = list(range(1, 16))
    assert distancia_conjunto(jogo_a, jogo_b) == 0

    jogo_c = list(range(11, 26))
    distancia = distancia_conjunto(jogo_a, jogo_c)
    assert distancia % 2 == 0
    assert 0 <= distancia <= 30

    # Dois conjuntos totalmente disjuntos de 10 dezenas cada: distancia = 20
    # (10 dezenas de cada lado que nao aparecem no outro).
    assert distancia_conjunto(list(range(1, 11)), list(range(16, 26))) == 20


def test_repetidas_com_concurso_anterior_e_alias_de_dezenas_em_comum() -> None:
    jogo = list(range(1, 16))
    concurso_anterior = list(range(6, 21))
    assert repetidas_com_concurso_anterior(jogo, concurso_anterior) == dezenas_em_comum(jogo, concurso_anterior)


# --- Fase 7: probabilidade hipergeometrica exata -------------------------


@pytest.mark.parametrize("k", [11, 12, 13, 14, 15])
def test_probabilidade_acertos_bate_com_formula_hipergeometrica_independente(k: int) -> None:
    # Formula calculada de forma independente dentro do proprio teste
    # (nao copiada de nenhuma fonte externa), usando apenas math.comb.
    esperado = comb(15, k) * comb(10, 15 - k) / comb(25, 15)
    assert probabilidade_acertos(k) == pytest.approx(esperado, rel=1e-15)


def test_probabilidade_15_acertos_e_inverso_da_combinatoria_total() -> None:
    assert probabilidade_15_acertos() == pytest.approx(1.0 / comb(25, 15), rel=1e-15)
    assert probabilidade_acertos(15) == pytest.approx(probabilidade_15_acertos(), rel=1e-15)


def test_probabilidade_acertos_k_menor_que_5_e_zero() -> None:
    # So existem 10 dezenas fora do jogo; errar mais de 10 e impossivel.
    for k in range(0, 5):
        assert probabilidade_acertos(k) == 0.0


def test_probabilidades_de_11_a_15_somam_menos_que_a_soma_total_de_5_a_15() -> None:
    soma_total = sum(probabilidade_acertos(k) for k in range(5, 16))
    assert soma_total == pytest.approx(1.0, rel=1e-12)


def test_probabilidade_decresce_conforme_k_aumenta_de_11_a_15() -> None:
    valores = [probabilidade_acertos(k) for k in (11, 12, 13, 14, 15)]
    assert valores == sorted(valores, reverse=True)
    assert all(valores[i] > valores[i + 1] for i in range(len(valores) - 1))


def test_probabilidade_acertos_rejeita_k_invalido() -> None:
    with pytest.raises(ContratoLotofacilError):
        probabilidade_acertos(16)
    with pytest.raises(ContratoLotofacilError):
        probabilidade_acertos(-1)
    with pytest.raises(ContratoLotofacilError):
        probabilidade_acertos(3.5)  # type: ignore[arg-type]
    with pytest.raises(ContratoLotofacilError):
        probabilidade_acertos(True)  # type: ignore[arg-type]


# --- Fase 8: guarda contra contaminacao semantica (outra loteria) -------


def test_universo_nunca_se_torna_1_a_60() -> None:
    """Falha se o contrato central regredir para o universo 1..60 (padrao
    de outras loterias, ex.: Mega-Sena)."""
    assert UNIVERSO_MAX == 25
    assert UNIVERSO_MAX != 60
    assert TOTAL_DEZENAS_UNIVERSO == 25
    assert TOTAL_DEZENAS_UNIVERSO != 60


def test_validar_jogo_rejeita_dezena_60() -> None:
    """Falha se o contrato passar a aceitar a dezena 60 (fora do universo
    da Lotofacil, tipica de outra loteria de 6 dezenas em 1..60)."""
    with pytest.raises(ContratoLotofacilError, match="universo"):
        validar_jogo([60, *range(1, 15)])


def test_validar_jogo_rejeita_estrutura_de_6_dezenas() -> None:
    """Falha se o contrato passar a aceitar um 'jogo' de 6 dezenas (padrao
    tipico de Mega-Sena) em vez das 15 exigidas pela Lotofacil."""
    jogo_seis_dezenas = [4, 9, 15, 23, 41, 55]
    assert len(jogo_seis_dezenas) == 6
    with pytest.raises(ContratoLotofacilError, match="exatamente 15"):
        validar_jogo(jogo_seis_dezenas)
    with pytest.raises(ContratoLotofacilError, match="exatamente 15"):
        validar_resultado(jogo_seis_dezenas)


def test_dezenas_por_jogo_e_resultado_nunca_se_tornam_6() -> None:
    assert DEZENAS_POR_JOGO == 15
    assert DEZENAS_POR_JOGO != 6
    assert DEZENAS_POR_RESULTADO == 15
    assert DEZENAS_POR_RESULTADO != 6


def test_total_combinacoes_simples_nunca_se_torna_combinatoria_de_mega_sena() -> None:
    """C(60, 6) e a combinatoria da Mega-Sena (50.063.860); o contrato da
    Lotofacil nunca deve convergir para esse valor."""
    combinatoria_mega_sena = comb(60, 6)
    assert TOTAL_COMBINACOES_SIMPLES != combinatoria_mega_sena
    assert TOTAL_COMBINACOES_SIMPLES == 3_268_760
