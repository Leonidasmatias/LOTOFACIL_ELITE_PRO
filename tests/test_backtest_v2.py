from __future__ import annotations

import pandas as pd

import src.backtest_lotofacil as backtest_modulo
from src.backtest_lotofacil import executar_backtest
from src.carregar_dados import CAMINHO_BASE_PADRAO, carregar_base
from src.motor_elite_v2 import PERFIS_V2
from src.validacao_jogos import ConfiguracaoMotor


def test_backtest_calcula_metricas_por_perfil_sem_vazamento() -> None:
    base = carregar_base(CAMINHO_BASE_PADRAO).tail(140).reset_index(drop=True)
    resultado = executar_backtest(
        base,
        quantidade_concursos=4,
        historico_minimo=100,
        configuracao=ConfiguracaoMotor(candidatos_por_perfil=80),
        candidatos_por_perfil=80,
    )
    assert len(resultado.detalhes) == 4 * 5
    assert set(resultado.resumo_perfis["Perfil"]) == set(PERFIS_V2)
    assert resultado.melhor_perfil in PERFIS_V2
    for coluna in ("Média", "Melhor", "11+", "12+", "13+", "14+", "15"):
        assert coluna in resultado.resumo_perfis.columns
    assert resultado.resumo_perfis[["11+", "12+", "13+", "14+", "15"]].apply(lambda serie: serie.between(0, 100).all()).all()
    assert resultado.csv_bytes().startswith(b"\xef\xbb\xbf")


def test_backtest_entrega_ao_motor_apenas_concursos_anteriores(monkeypatch) -> None:
    base = carregar_base(CAMINHO_BASE_PADRAO).tail(110).reset_index(drop=True)
    maiores_concursos_treino = []

    def motor_controlado(treino, **_kwargs):
        maiores_concursos_treino.append(int(treino["Concurso"].max()))
        linhas = []
        for perfil in PERFIS_V2:
            linha = {"Perfil": perfil, "Score": 1.0}
            linha.update({f"Bola{i}": i for i in range(1, 16)})
            linhas.append(linha)
        return pd.DataFrame(linhas)

    monkeypatch.setattr(backtest_modulo, "gerar_jogos_v2", motor_controlado)
    backtest_modulo.executar_backtest(base, quantidade_concursos=3, historico_minimo=100)
    alvos = base.tail(3)["Concurso"].astype(int).tolist()
    assert len(maiores_concursos_treino) == 3
    assert all(treino < alvo for treino, alvo in zip(maiores_concursos_treino, alvos))
