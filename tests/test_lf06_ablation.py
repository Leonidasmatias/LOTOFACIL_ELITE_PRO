"""Testes do desenho de ablacao de componentes (LF-06, Fase 11).

Provam que: (1) cada variante de ablacao isola EXATAMENTE o(s) campo(s)
esperado(s) de ``ConfiguracaoMotor``, nunca mais nem menos; (2) toda
variante permanece uma configuracao valida (``validar()`` nao levanta);
(3) ``candidatos_por_perfil`` (K de busca) permanece 700 em toda variante
-- a gate NAO altera esse parametro; (4) nenhuma ablacao toca o motor de
producao (mesma classe/funcao importada, byte-identica)."""
from __future__ import annotations

import pytest

from src.backtest.ablation import (
    ABLATION_EXPECTED_FIELDS,
    ABLATION_VARIANTS,
    BASELINE_CONFIG,
    COMPONENT_CLASSIFICATION,
    INTERDEPENDENT,
    NOT_SAFELY_ISOLATABLE,
    SAFE_TO_ABLATE,
    assert_isolates_component,
)
from src.backtest.engine_adapter import MotorEliteV2Adapter
from src.motor_elite_v2 import gerar_jogos_v2
from src.validacao_jogos import ConfiguracaoMotor


def test_baseline_config_e_a_configuracao_de_producao_real() -> None:
    assert BASELINE_CONFIG == ConfiguracaoMotor()
    assert BASELINE_CONFIG.candidatos_por_perfil == 700


@pytest.mark.parametrize("nome", list(ABLATION_VARIANTS))
def test_cada_variante_isola_exatamente_os_campos_esperados(nome: str) -> None:
    variante = ABLATION_VARIANTS[nome]
    assert_isolates_component(BASELINE_CONFIG, variante, ABLATION_EXPECTED_FIELDS[nome])


@pytest.mark.parametrize("nome", list(ABLATION_VARIANTS))
def test_cada_variante_e_uma_configuracao_valida(nome: str) -> None:
    ABLATION_VARIANTS[nome].validar()  # nao deve levantar


@pytest.mark.parametrize("nome", list(ABLATION_VARIANTS))
def test_candidatos_por_perfil_permanece_700_em_toda_variante(nome: str) -> None:
    assert ABLATION_VARIANTS[nome].candidatos_por_perfil == 700


def test_assert_isolates_component_rejeita_campo_extra_alterado() -> None:
    variante_invalida = ConfiguracaoMotor(pares_minimo=0, pares_maximo=15, sequencia_maxima=15)
    with pytest.raises(ValueError):
        assert_isolates_component(BASELINE_CONFIG, variante_invalida, frozenset({"pares_minimo", "pares_maximo"}))


def test_assert_isolates_component_rejeita_nenhum_campo_alterado() -> None:
    with pytest.raises(ValueError):
        assert_isolates_component(BASELINE_CONFIG, BASELINE_CONFIG, frozenset({"pares_minimo", "pares_maximo"}))


def test_toda_variante_tem_classificacao_registrada_como_safe_to_ablate() -> None:
    for nome in ABLATION_VARIANTS:
        assert COMPONENT_CLASSIFICATION.get(nome) == SAFE_TO_ABLATE, nome


def test_componentes_nao_isolaveis_nao_tem_variante_de_ablacao() -> None:
    for nome, classificacao in COMPONENT_CLASSIFICATION.items():
        if classificacao in (NOT_SAFELY_ISOLATABLE, INTERDEPENDENT):
            assert nome not in ABLATION_VARIANTS


def test_ablacao_usa_o_mesmo_motor_de_producao_sem_modificacao() -> None:
    """O adapter de ablacao (research) DEVE usar o mesmo
    ``MotorEliteV2Adapter``/``gerar_jogos_v2`` de producao -- apenas com
    ``configuracao`` diferente. Nao ha um "motor de pesquisa" separado."""
    adapter = MotorEliteV2Adapter(configuracao=ABLATION_VARIANTS["FILTRO_PARES"])
    assert adapter.name == "MOTOR_ELITE_V2"
    from src.backtest.engine_adapter import gerar_jogos_v2 as gerar_jogos_v2_importado_pelo_adapter

    assert gerar_jogos_v2_importado_pelo_adapter is gerar_jogos_v2
