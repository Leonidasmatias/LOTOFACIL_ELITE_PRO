from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd
import pytest

import src.laboratorio_estatistico as laboratorio
from src.carregar_dados import CAMINHO_BASE_PADRAO, carregar_base
from src.laboratorio_estatistico import (
    ESTRATEGIAS_LABORATORIO,
    calcular_roi_simulado,
    dados_heatmap,
    descobrir_padroes,
    executar_laboratorio,
    gerar_carteira_estrategia,
    ler_historico_laboratorio,
    salvar_historico_laboratorio,
)
from src.validacao_jogos import ConfiguracaoMotor, validar_carteira


@pytest.fixture(scope="module")
def base() -> pd.DataFrame:
    return carregar_base(CAMINHO_BASE_PADRAO)


@pytest.mark.parametrize("estrategia", ESTRATEGIAS_LABORATORIO)
def test_estrategias_geram_jogos_validos(base: pd.DataFrame, estrategia: str) -> None:
    config = ConfiguracaoMotor(candidatos_por_perfil=60)
    carteira = gerar_carteira_estrategia(base, estrategia, 5, config, 44)
    ultimo = [int(base.iloc[-1][f"Bola{i}"]) for i in range(1, 16)]
    assert len(carteira) == 5
    validar_carteira(carteira, config, ultimo)
    assert all(len(jogo) == len(set(jogo)) == 15 and all(1 <= d <= 25 for d in jogo) for jogo in carteira)


def test_laboratorio_compara_todas_as_estrategias(base: pd.DataFrame) -> None:
    resultado = executar_laboratorio(
        base.tail(125).reset_index(drop=True),
        quantidade_concursos=2,
        quantidade_jogos=5,
        configuracao=ConfiguracaoMotor(candidatos_por_perfil=60),
        amostra_minima_padrao=2,
    )
    assert set(resultado.resumo["Estratégia"]) == set(ESTRATEGIAS_LABORATORIO)
    assert len(resultado.detalhes_carteiras) == 2 * 5
    assert len(resultado.detalhes_jogos) == 2 * 5 * 5
    for coluna in ("Taxa 11+", "Taxa 12+", "Taxa 13+", "Taxa 14+", "Taxa 15"):
        assert coluna in resultado.resumo
        assert resultado.resumo[coluna].between(0, 100).all()
        assert coluna.replace("Taxa ", "Taxa ") in resultado.melhores_metricas


def test_roi_simulado_calcula_aposta_retorno_saldo_e_percentual() -> None:
    detalhes = pd.DataFrame([
        {"Estratégia": "Motor Elite", "Acertos": 11},
        {"Estratégia": "Motor Elite", "Acertos": 10},
        {"Estratégia": "Aleatório puro", "Acertos": 12},
    ])
    roi = calcular_roi_simulado(detalhes, 3.5, {11: 7.0, 12: 14.0, 13: 35.0, 14: 1000.0, 15: 1_000_000.0})
    elite = roi.set_index("Estratégia").loc["Motor Elite"]
    assert elite["Total apostado"] == 7.0
    assert elite["Retorno estimado"] == 7.0
    assert elite["Saldo simulado"] == 0.0
    assert elite["ROI (%)"] == 0.0
    assert roi["Observação"].str.contains("não garantidos").all()


def test_heatmap_mapeia_as_25_dezenas_em_grade_5x5(base: pd.DataFrame) -> None:
    heatmap = dados_heatmap(base)
    assert len(heatmap) == 25
    assert set(heatmap["Dezena"]) == set(range(1, 26))
    assert set(heatmap["Linha"]) == set(range(1, 6))
    assert set(heatmap["Coluna"]) == set(range(1, 6))
    assert {"Frequência histórica", "Frequência recente", "Atraso", "Score V3"}.issubset(heatmap.columns)


def test_descoberta_de_padroes_descarta_baixa_amostra() -> None:
    detalhes = pd.DataFrame([
        {"Acertos": 14, "Padrão soma": "190-199"},
        {"Acertos": 13, "Padrão soma": "190-199"},
        {"Acertos": 10, "Padrão soma": "170-179"},
    ])
    padroes = descobrir_padroes(detalhes, amostra_minima=2)
    assert set(padroes["Padrão"]) == {"190-199"}
    assert float(padroes.iloc[0]["Taxa 13+"]) == 100.0
    assert float(padroes.iloc[0]["Taxa 14+"]) == 50.0


def test_banco_historico_salva_e_reabre_simulacoes(base: pd.DataFrame) -> None:
    resultado = executar_laboratorio(base.tail(115), 1, 5, ConfiguracaoMotor(candidatos_por_perfil=60), 1)
    roi = calcular_roi_simulado(resultado.detalhes_jogos, 3.5)
    with TemporaryDirectory() as pasta:
        caminho = Path(pasta) / "historico.csv"
        salvo = salvar_historico_laboratorio(resultado, roi, 5, caminho)
        reaberto = ler_historico_laboratorio(caminho)
        assert len(salvo) == len(ESTRATEGIAS_LABORATORIO)
        assert reaberto.equals(salvo)
        assert set(reaberto["Status"]) == {"CONCLUÍDO"}


def test_laboratorio_nao_fornece_resultado_futuro(base: pd.DataFrame, monkeypatch) -> None:
    recortes = []
    original = laboratorio.gerar_carteira_estrategia

    def observado(treino, *args, **kwargs):
        recortes.append(int(treino["Concurso"].max()))
        return original(treino, *args, **kwargs)

    monkeypatch.setattr(laboratorio, "gerar_carteira_estrategia", observado)
    amostra = base.tail(108).reset_index(drop=True)
    executar_laboratorio(amostra, 2, 5, ConfiguracaoMotor(candidatos_por_perfil=50), 1)
    alvos = amostra.tail(2)["Concurso"].astype(int).tolist()
    assert recortes[:5] == [recortes[0]] * 5
    assert recortes[5:] == [recortes[5]] * 5
    assert recortes[0] < alvos[0]
    assert recortes[5] < alvos[1]
