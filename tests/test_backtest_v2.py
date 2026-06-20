from __future__ import annotations

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
