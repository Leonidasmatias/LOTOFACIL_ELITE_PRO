"""Testes do service de orquestracao do Trend Hybrid Engine
(Fase Trend Hybrid V1 - src/services/trend_hybrid_service.py).

Cobrem apenas a orquestracao (o service nao contem nenhuma formula): garante
que cada funcao delega corretamente para core/ai e devolve os tipos
esperados para a camada de apresentacao (``src/ui``/``app.py``).
"""
from __future__ import annotations

from src.ai.trend_hybrid_explainer import ExplicacaoBilheteTrendHybrid
from src.core.trend_hybrid_engine import DIVISOES_SUPORTADAS
from src.models.trend_hybrid import BilheteSorteioGrupos, BilheteTrendHybrid, PesosTendencia
from src.repository.base_repository import CAMINHO_BASE_PADRAO, carregar_base
from src.services import trend_hybrid_service


def _base():
    return carregar_base(CAMINHO_BASE_PADRAO)


def test_motor_trend_hybrid_nome_nao_vazio() -> None:
    assert trend_hybrid_service.motor_trend_hybrid_nome()


def test_divisoes_suportadas_bate_com_o_core() -> None:
    assert trend_hybrid_service.divisoes_suportadas() == DIVISOES_SUPORTADAS


def test_gerar_bilhete_do_dia_devolve_bilhete_valido() -> None:
    bilhete = trend_hybrid_service.gerar_bilhete_do_dia(_base())
    assert isinstance(bilhete, BilheteTrendHybrid)
    assert len(bilhete.dezenas) == 15


def test_gerar_bilhete_do_dia_respeita_divisao_e_pesos_customizados() -> None:
    bilhete = trend_hybrid_service.gerar_bilhete_do_dia(
        _base(), divisao=(8, 7), pesos=PesosTendencia(peso_atraso=0.10)
    )
    assert bilhete.divisao == (8, 7)
    assert len(bilhete.grupo_a_selecionadas) == 8
    assert len(bilhete.grupo_b_selecionadas) == 7


def test_gerar_ranking_trend_score_tem_25_linhas() -> None:
    ranking = trend_hybrid_service.gerar_ranking_trend_score(_base())
    assert len(ranking) == 25


def test_explicar_devolve_explicacao_do_bilhete() -> None:
    bilhete = trend_hybrid_service.gerar_bilhete_do_dia(_base())
    explicacao = trend_hybrid_service.explicar(bilhete)
    assert isinstance(explicacao, ExplicacaoBilheteTrendHybrid)
    assert len(explicacao.selecionadas) == 15
    assert len(explicacao.descartadas) == 10


def test_executar_backtest_devolve_resultado_com_resumo() -> None:
    resultado = trend_hybrid_service.executar_backtest(_base(), quantidade_concursos=15, historico_minimo=100)
    assert resultado.resumo["Concursos avaliados"] == 15


def test_otimizar_divisao_devolve_comparativo_e_melhor_divisao() -> None:
    comparativo, melhor_divisao, resultados = trend_hybrid_service.otimizar_divisao(
        _base(), quantidade_concursos=10, historico_minimo=100
    )
    assert len(comparativo) == len(DIVISOES_SUPORTADAS)
    assert melhor_divisao in DIVISOES_SUPORTADAS
    assert set(resultados.keys()) == set(DIVISOES_SUPORTADAS)


def test_sortear_bilhete_aleatorio_devolve_bilhete_de_sorteio_valido() -> None:
    bilhete = trend_hybrid_service.sortear_bilhete_aleatorio(_base(), semente=123, numero_sorteio=1)
    assert isinstance(bilhete, BilheteSorteioGrupos)
    assert len(bilhete.dezenas) == 15
    assert len(bilhete.grupo_a_selecionadas) == 9
    assert len(bilhete.grupo_b_selecionadas) == 6
    assert bilhete.semente == 123
    assert bilhete.numero_sorteio == 1


def test_sortear_bilhete_aleatorio_muda_a_cada_chamada_sem_semente_fixa() -> None:
    df = _base()
    resultados = {trend_hybrid_service.sortear_bilhete_aleatorio(df, semente=s).dezenas for s in range(1, 8)}
    assert len(resultados) > 1


def test_sortear_bilhete_aleatorio_repete_com_a_mesma_semente() -> None:
    df = _base()
    primeiro = trend_hybrid_service.sortear_bilhete_aleatorio(df, semente=55, numero_sorteio=1)
    segundo = trend_hybrid_service.sortear_bilhete_aleatorio(df, semente=55, numero_sorteio=2)
    assert primeiro.dezenas == segundo.dezenas
