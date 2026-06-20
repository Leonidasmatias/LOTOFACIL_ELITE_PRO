from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd
import pytest

import src.backtest_lotofacil as backtest_modulo
from src.backtest_lotofacil import executar_backtest_comparativo
from src.carregar_dados import CAMINHO_BASE_PADRAO, carregar_base
from src.comparador_aleatorio import gerar_carteira_aleatoria
from src.estrategia_inteligente import MAPA_PERFIS, gerar_estrategia_do_dia
from src.jogos_salvos import conferir_jogos_salvos, historico_desempenho_carteiras, salvar_carteira
from src.motor_elite_v2 import PERFIS_V2, gerar_jogos_v2
from src.validacao_jogos import ConfiguracaoMotor, validar_carteira


@pytest.fixture(scope="module")
def base() -> pd.DataFrame:
    return carregar_base(CAMINHO_BASE_PADRAO)


@pytest.mark.parametrize("quantidade", [5, 10, 20, 30])
def test_carteiras_configuraveis_sao_validas(base: pd.DataFrame, quantidade: int) -> None:
    config = ConfiguracaoMotor(candidatos_por_perfil=100)
    jogos = gerar_jogos_v2(base, quantidade=quantidade, configuracao=config, semente=3000 + quantidade)
    carteira = [[int(row[f"Bola{i}"]) for i in range(1, 16)] for _, row in jogos.iterrows()]
    ultimo = [int(base.iloc[-1][f"Bola{i}"]) for i in range(1, 16)]
    assert len(jogos) == quantidade
    validar_carteira(carteira, config, ultimo)
    assert all(len(jogo) == len(set(jogo)) == 15 and all(1 <= dezena <= 25 for dezena in jogo) for jogo in carteira)


def test_comparador_aleatorio_usa_mesma_quantidade(base: pd.DataFrame) -> None:
    config = ConfiguracaoMotor(candidatos_por_perfil=80)
    aleatorios = gerar_carteira_aleatoria(base, 10, config, semente=55)
    ultimo = [int(base.iloc[-1][f"Bola{i}"]) for i in range(1, 16)]
    assert len(aleatorios) == 10
    validar_carteira(aleatorios, config, ultimo)
    resultado = executar_backtest_comparativo(base.tail(130), 2, 10, 100, config, 80)
    assert set(resultado.resumo["Motor"]) == {"Motor Elite", "Aleatório"}
    for coluna in ("Taxa 11+", "Taxa 12+", "Taxa 13+", "Taxa 14+", "Taxa 15", "Vantagem 11"):
        assert coluna in resultado.resumo.columns


def test_relatorio_melhor_estrategia_do_dia(base: pd.DataFrame) -> None:
    resumo = pd.DataFrame([
        {"Perfil": perfil, "Média": 9 + indice / 10, "11+": 20 + indice, "13+": indice, "Melhor": 12}
        for indice, perfil in enumerate(PERFIS_V2)
    ])
    estrategia = gerar_estrategia_do_dia(base, resumo_backtest=resumo)
    assert estrategia.perfil_recomendado in MAPA_PERFIS
    assert estrategia.quantidade_jogos in {5, 10, 20, 30}
    assert len(estrategia.dezenas_fortes) == 8
    assert len(estrategia.dezenas_alerta) == 5
    assert "busca estatística pelos 15 acertos" in estrategia.texto().lower()
    assert "garantia de 15 acertos" not in estrategia.texto().lower()
    assert estrategia.csv_bytes().startswith(b"\xef\xbb\xbf")


def test_historico_de_desempenho_agrega_carteira(base: pd.DataFrame) -> None:
    config = ConfiguracaoMotor(candidatos_por_perfil=80)
    jogos = gerar_jogos_v2(base, quantidade=10, configuracao=config, semente=998)
    with TemporaryDirectory() as pasta:
        caminho = Path(pasta) / "carteiras.csv"
        concurso = int(base.iloc[-1]["Concurso"])
        salvar_carteira(jogos, 4, concurso, caminho)
        conferir_jogos_salvos(base, caminho)
        historico = historico_desempenho_carteiras(caminho)
        assert len(historico) == 1
        assert int(historico.iloc[0]["Quantidade de jogos"]) == 10
        assert historico.iloc[0]["Resultado conferido"] == "SIM"
        assert historico.iloc[0]["Status"] in {"PREMIADO", "SEM PRÊMIO"}
        assert 0 <= float(historico.iloc[0]["Média de acertos"]) <= 15


def test_comparativo_nao_entrega_resultado_futuro_ao_motor(base: pd.DataFrame, monkeypatch) -> None:
    recortes = []
    original_motor = backtest_modulo.gerar_jogos_v2
    original_aleatorio = backtest_modulo.gerar_carteira_aleatoria

    def motor_observado(treino, *args, **kwargs):
        recortes.append(int(treino["Concurso"].max()))
        return original_motor(treino, *args, **kwargs)

    monkeypatch.setattr(backtest_modulo, "gerar_jogos_v2", motor_observado)
    monkeypatch.setattr(backtest_modulo, "gerar_carteira_aleatoria", original_aleatorio)
    amostra = base.tail(110).reset_index(drop=True)
    executar_backtest_comparativo(amostra, 2, 5, 100, ConfiguracaoMotor(candidatos_por_perfil=60), 60)
    alvos = amostra.tail(2)["Concurso"].astype(int).tolist()
    assert all(ultimo_treino < alvo for ultimo_treino, alvo in zip(recortes, alvos))
