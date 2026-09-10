"""Desenho de ablacao de componentes existentes do MOTOR_ELITE_V2 (LF-06,
Fase 11).

NAO modifica ``src/motor_elite_v2.py``. Cada variante de ablacao e apenas
uma instancia alternativa de ``ConfiguracaoMotor`` (ja um parametro publico
de ``gerar_jogos_v2``/``MotorEliteV2Adapter`` desde o LF-04) com EXATAMENTE
um campo relaxado ao limite matematicamente permissivo -- nunca ao valor
"otimo", apenas ao valor que torna aquele filtro um no-op. Tudo o mais
(motor, harness, seed policy, candidatos_por_perfil=700, K) permanece
identico ao benchmark primario.

Componentes cujo mecanismo esta hard-coded dentro de ``gerar_jogos_v2``
(pesos por perfil, geracao de candidatos por amostragem ponderada) NAO tem
um parametro exposto para ablacao sem duplicar logica de producao -- sao
classificados como NAO isolaveis nesta gate, nao ablacionados.
"""
from __future__ import annotations

from dataclasses import fields, replace

from ..validacao_jogos import ConfiguracaoMotor

# --- Classificacao dos componentes mapeados na Fase 4 -----------------------

SAFE_TO_ABLATE = "SAFE_TO_ABLATE_IN_ISOLATED_RESEARCH_ADAPTER"
NOT_SAFELY_ISOLATABLE = "NOT_SAFELY_ISOLATABLE_WITHOUT_PRODUCTION_CHANGE"
INTERDEPENDENT = "INTERDEPENDENT_ABLATION_NOT_INTERPRETABLE"

COMPONENT_CLASSIFICATION: dict[str, str] = {
    "FREQUENCIA_GERAL_E_JANELAS": NOT_SAFELY_ISOLATABLE,
    "ATRASO": NOT_SAFELY_ISOLATABLE,
    "SAIU_NO_ULTIMO": NOT_SAFELY_ISOLATABLE,
    "PESOS_POR_PERFIL": NOT_SAFELY_ISOLATABLE,
    "AMOSTRAGEM_PONDERADA_CANDIDATOS": INTERDEPENDENT,
    "FILTRO_SOMA": SAFE_TO_ABLATE,
    "FILTRO_PARES": SAFE_TO_ABLATE,
    "FILTRO_REPETIDAS": SAFE_TO_ABLATE,
    "FILTRO_SEQUENCIA_MAXIMA": SAFE_TO_ABLATE,
    "PENALIDADE_SIMILARIDADE_SCORE": INTERDEPENDENT,
    "DIVERSIDADE_MINIMA_ENTRE_JOGOS": SAFE_TO_ABLATE,
    "SCORE_ESTRUTURA_CENTRO_MOLDURA_LINHAS_COLUNAS": NOT_SAFELY_ISOLATABLE,
}

BASELINE_CONFIG = ConfiguracaoMotor()

# Limites matematicos exatos para 15 dezenas distintas em 1..25 (usados
# para tornar o filtro de soma um no-op real, nao apenas "bem largo"):
# soma minima possivel = 1+2+...+15 = 120; soma maxima possivel =
# 11+12+...+25 = 270.
_SOMA_MIN_MATEMATICA = sum(range(1, 16))
_SOMA_MAX_MATEMATICA = sum(range(11, 26))

ABLATION_VARIANTS: dict[str, ConfiguracaoMotor] = {
    "FILTRO_SOMA": replace(BASELINE_CONFIG, soma_minima=_SOMA_MIN_MATEMATICA, soma_maxima=_SOMA_MAX_MATEMATICA),
    "FILTRO_PARES": replace(BASELINE_CONFIG, pares_minimo=0, pares_maximo=15),
    "FILTRO_REPETIDAS": replace(BASELINE_CONFIG, repetidas_minimo=0, repetidas_maximo=15),
    "FILTRO_SEQUENCIA_MAXIMA": replace(BASELINE_CONFIG, sequencia_maxima=15),
    "DIVERSIDADE_MINIMA_ENTRE_JOGOS": replace(BASELINE_CONFIG, diferenca_minima_entre_jogos=1),
}

# Um "fator" pode envolver mais de um campo do dataclass quando o
# mecanismo de producao e um INTERVALO (ex.: soma_minima/soma_maxima sao
# as duas pontas do MESMO filtro de soma -- ablacionar o filtro exige
# relaxar as duas, nao e dois fatores independentes).
ABLATION_EXPECTED_FIELDS: dict[str, frozenset[str]] = {
    "FILTRO_SOMA": frozenset({"soma_minima", "soma_maxima"}),
    "FILTRO_PARES": frozenset({"pares_minimo", "pares_maximo"}),
    "FILTRO_REPETIDAS": frozenset({"repetidas_minimo", "repetidas_maximo"}),
    "FILTRO_SEQUENCIA_MAXIMA": frozenset({"sequencia_maxima"}),
    "DIVERSIDADE_MINIMA_ENTRE_JOGOS": frozenset({"diferenca_minima_entre_jogos"}),
}


def assert_isolates_component(
    baseline: ConfiguracaoMotor, variant: ConfiguracaoMotor, expected_fields: frozenset[str]
) -> None:
    """Confirma que ``variant`` difere de ``baseline`` em EXATAMENTE os
    campos de ``expected_fields`` -- nem mais, nem menos. Levanta
    ``ValueError`` caso contrario -- garante que cada ablacao isola SOMENTE
    o fator pretendido (Fase 11: 'one-factor-at-a-time'), mesmo quando esse
    fator e representado por mais de um campo do dataclass (ex.: os dois
    limites de um mesmo filtro de intervalo)."""
    diferentes = frozenset(f.name for f in fields(baseline) if getattr(baseline, f.name) != getattr(variant, f.name))
    if diferentes != expected_fields:
        raise ValueError(f"Esperado {sorted(expected_fields)} diferente; encontrado {sorted(diferentes)}.")
