from __future__ import annotations

from itertools import combinations

from src.carregar_dados import CAMINHO_BASE_PADRAO, carregar_base
from src.motor_elite_v2 import MOTOR_ELITE_V2, PERFIS_V2, gerar_jogos_v2, ranking_dezenas_v2
from src.validacao_jogos import ConfiguracaoMotor, validar_carteira


def config_teste() -> ConfiguracaoMotor:
    return ConfiguracaoMotor(candidatos_por_perfil=150)


def test_ranking_contem_frequencias_e_atraso() -> None:
    ranking = ranking_dezenas_v2(carregar_base(CAMINHO_BASE_PADRAO))
    assert len(ranking) == 25
    assert ranking["Posição"].tolist() == list(range(1, 26))
    for coluna in ("Frequência histórica", "Últimos 10", "Últimos 25", "Últimos 50", "Últimos 100", "Atraso", "Score da dezena"):
        assert coluna in ranking.columns


def test_motor_v2_gera_cinco_jogos_validos_e_diversos() -> None:
    base = carregar_base(CAMINHO_BASE_PADRAO)
    jogos = gerar_jogos_v2(base, configuracao=config_teste(), semente=20260620)
    assert jogos["Perfil"].tolist() == PERFIS_V2
    assert set(jogos["Motor"]) == {MOTOR_ELITE_V2}
    carteira = [[int(row[f"Bola{i}"]) for i in range(1, 16)] for _, row in jogos.iterrows()]
    ultimo = [int(base.iloc[-1][f"Bola{i}"]) for i in range(1, 16)]
    validar_carteira(carteira, config_teste(), ultimo)
    for jogo_a, jogo_b in combinations(carteira, 2):
        assert len(set(jogo_a) - set(jogo_b)) >= 3
    assert jogos["Score"].notna().all()
    assert jogos["Sequência máxima"].le(config_teste().sequencia_maxima).all()


def test_motor_v2_e_reprodutivel_com_semente() -> None:
    base = carregar_base(CAMINHO_BASE_PADRAO)
    primeiro = gerar_jogos_v2(base, configuracao=config_teste(), semente=77)
    segundo = gerar_jogos_v2(base, configuracao=config_teste(), semente=77)
    colunas = [f"Bola{i}" for i in range(1, 16)]
    assert primeiro[colunas].equals(segundo[colunas])
