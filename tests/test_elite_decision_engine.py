"""Testes do Elite Decision Engine (Fase V1.5 - src/ai/elite_decision_engine.py).

Cobrem: classificacao correta por faixa de score, definicao correta da
estrategia (perfil/risco) para diferentes distribuicoes de jogos,
consistencia deterministica (mesma entrada -> mesma saida) e integracao com
o Elite Score real (via ``core.elite_score``), sem alterar nenhum valor do
score original.
"""
from __future__ import annotations

import unittest

from src.ai import elite_decision_engine as ede
from src.core import elite_score as es
from src.models.elite_score import ComponenteEliteScore, EliteScoreResultado
from src.repository import base_repository
from src.repository.base_repository import COLUNAS_DEZENAS


def _resultado(total: float) -> EliteScoreResultado:
    """Constroi um EliteScoreResultado sintetico com um total fixo, para
    testar a camada de decisao isoladamente do calculo real do Elite Score."""
    componente = ComponenteEliteScore(
        nome="Componente sintetico",
        descricao="uso interno de teste",
        valor_jogo=1.0,
        faixa_tipica=(0.0, 10.0),
        sub_score=total,
        peso=1.0,
        contribuicao=total,
    )
    return EliteScoreResultado(total=total, componentes=(componente,))


class TestClassificarScore(unittest.TestCase):
    def test_elite_premium_no_limite_e_acima(self) -> None:
        self.assertEqual(ede.classificar_score(90.0), ede.CLASSIFICACAO_ELITE_PREMIUM)
        self.assertEqual(ede.classificar_score(100.0), ede.CLASSIFICACAO_ELITE_PREMIUM)

    def test_alto_potencial_no_limite_e_logo_abaixo_do_premium(self) -> None:
        self.assertEqual(ede.classificar_score(75.0), ede.CLASSIFICACAO_ALTO_POTENCIAL)
        self.assertEqual(ede.classificar_score(89.9), ede.CLASSIFICACAO_ALTO_POTENCIAL)

    def test_neutro_no_limite_e_logo_abaixo_do_alto_potencial(self) -> None:
        self.assertEqual(ede.classificar_score(50.0), ede.CLASSIFICACAO_NEUTRO)
        self.assertEqual(ede.classificar_score(74.9), ede.CLASSIFICACAO_NEUTRO)

    def test_fraco_abaixo_de_50(self) -> None:
        self.assertEqual(ede.classificar_score(49.9), ede.CLASSIFICACAO_FRACO)
        self.assertEqual(ede.classificar_score(0.0), ede.CLASSIFICACAO_FRACO)


class TestClassificarJogos(unittest.TestCase):
    def test_classifica_cada_jogo_sem_alterar_o_score_original(self) -> None:
        resultados = [_resultado(95.0), _resultado(80.0), _resultado(60.0), _resultado(30.0)]
        classificados = ede.classificar_jogos(resultados)
        self.assertEqual([c.classificacao for c in classificados], [
            ede.CLASSIFICACAO_ELITE_PREMIUM,
            ede.CLASSIFICACAO_ALTO_POTENCIAL,
            ede.CLASSIFICACAO_NEUTRO,
            ede.CLASSIFICACAO_FRACO,
        ])
        self.assertEqual([c.score for c in classificados], [95.0, 80.0, 60.0, 30.0])
        # Nao deve alterar os resultados originais.
        self.assertEqual([r.total for r in resultados], [95.0, 80.0, 60.0, 30.0])

    def test_indices_preservam_a_ordem_original(self) -> None:
        resultados = [_resultado(10.0), _resultado(20.0), _resultado(30.0)]
        classificados = ede.classificar_jogos(resultados)
        self.assertEqual([c.indice for c in classificados], [0, 1, 2])

    def test_lista_vazia_devolve_lista_vazia(self) -> None:
        self.assertEqual(ede.classificar_jogos([]), [])


class TestMontarEstrategia(unittest.TestCase):
    def test_lote_vazio_e_equilibrado_com_risco_indefinido(self) -> None:
        estrategia = ede.montar_estrategia([])
        self.assertEqual(estrategia.perfil, ede.PERFIL_EQUILIBRADO)
        self.assertEqual(estrategia.nivel_risco, ede.RISCO_INDEFINIDO)
        self.assertEqual(estrategia.potencial_teorico, 0.0)

    def test_lote_majoritariamente_forte_e_agressivo(self) -> None:
        # 4 de 5 jogos (80%) em Alto Potencial/Elite Premium, media >= 75.
        resultados = [_resultado(95.0), _resultado(90.0), _resultado(80.0), _resultado(76.0), _resultado(60.0)]
        classificados = ede.classificar_jogos(resultados)
        estrategia = ede.montar_estrategia(classificados)
        self.assertEqual(estrategia.perfil, ede.PERFIL_AGRESSIVO)
        self.assertEqual(estrategia.nivel_risco, ede.RISCO_ALTO)

    def test_lote_majoritariamente_fraco_e_conservador(self) -> None:
        # 3 de 5 jogos (60%) fracos.
        resultados = [_resultado(10.0), _resultado(20.0), _resultado(40.0), _resultado(80.0), _resultado(85.0)]
        classificados = ede.classificar_jogos(resultados)
        estrategia = ede.montar_estrategia(classificados)
        self.assertEqual(estrategia.perfil, ede.PERFIL_CONSERVADOR)
        self.assertEqual(estrategia.nivel_risco, ede.RISCO_BAIXO)

    def test_media_abaixo_de_50_e_conservador_mesmo_sem_maioria_de_fracos(self) -> None:
        # Apenas 1 de 3 jogos (33%) e FRACO -- nao atinge os 50% exigidos
        # pela regra de "maioria de fracos" isoladamente, mas a media do
        # lote (35.0) fica abaixo de 50 e ja aciona o perfil CONSERVADOR
        # pelo outro criterio (media < LIMIAR_NEUTRO).
        resultados = [_resultado(50.0), _resultado(50.0), _resultado(5.0)]
        classificados = ede.classificar_jogos(resultados)
        estrategia = ede.montar_estrategia(classificados)
        self.assertLess((50.0 + 50.0 + 5.0) / 3, 50.0)
        self.assertEqual(estrategia.perfil, ede.PERFIL_CONSERVADOR)

    def test_lote_misto_sem_maioria_clara_e_equilibrado(self) -> None:
        # 2 de 4 (50%) fortes, 0 fracos, media entre 50 e 75.
        resultados = [_resultado(90.0), _resultado(78.0), _resultado(60.0), _resultado(55.0)]
        classificados = ede.classificar_jogos(resultados)
        estrategia = ede.montar_estrategia(classificados)
        self.assertEqual(estrategia.perfil, ede.PERFIL_EQUILIBRADO)
        self.assertEqual(estrategia.nivel_risco, ede.RISCO_MEDIO)

    def test_potencial_teorico_e_a_media_dos_scores(self) -> None:
        resultados = [_resultado(80.0), _resultado(60.0)]
        classificados = ede.classificar_jogos(resultados)
        estrategia = ede.montar_estrategia(classificados)
        self.assertAlmostEqual(estrategia.potencial_teorico, 70.0, places=2)

    def test_justificativa_nao_vazia_para_qualquer_perfil(self) -> None:
        for resultados in (
            [_resultado(95.0), _resultado(92.0)],
            [_resultado(10.0), _resultado(20.0)],
            [_resultado(60.0), _resultado(65.0)],
        ):
            estrategia = ede.montar_estrategia(ede.classificar_jogos(resultados))
            self.assertTrue(estrategia.justificativa.strip())


class TestGerarRelatorioEstrategico(unittest.TestCase):
    def test_distribuicao_soma_o_total_de_jogos_e_cobre_as_4_faixas(self) -> None:
        resultados = [_resultado(95.0), _resultado(80.0), _resultado(60.0), _resultado(30.0), _resultado(96.0)]
        relatorio = ede.gerar_relatorio_estrategico(resultados)
        self.assertEqual(set(relatorio.distribuicao.keys()), {
            ede.CLASSIFICACAO_ELITE_PREMIUM,
            ede.CLASSIFICACAO_ALTO_POTENCIAL,
            ede.CLASSIFICACAO_NEUTRO,
            ede.CLASSIFICACAO_FRACO,
        })
        self.assertEqual(sum(relatorio.distribuicao.values()), len(resultados))
        self.assertEqual(relatorio.distribuicao[ede.CLASSIFICACAO_ELITE_PREMIUM], 2)
        self.assertEqual(relatorio.distribuicao[ede.CLASSIFICACAO_ALTO_POTENCIAL], 1)
        self.assertEqual(relatorio.distribuicao[ede.CLASSIFICACAO_NEUTRO], 1)
        self.assertEqual(relatorio.distribuicao[ede.CLASSIFICACAO_FRACO], 1)

    def test_relatorio_com_lista_vazia_nao_quebra(self) -> None:
        relatorio = ede.gerar_relatorio_estrategico([])
        self.assertEqual(sum(relatorio.distribuicao.values()), 0)
        self.assertEqual(relatorio.estrategia.perfil, ede.PERFIL_EQUILIBRADO)
        self.assertEqual(relatorio.jogos_classificados, ())

    def test_repetibilidade_mesma_entrada_mesma_saida(self) -> None:
        resultados = [_resultado(95.0), _resultado(40.0), _resultado(65.0)]
        r1 = ede.gerar_relatorio_estrategico(resultados)
        r2 = ede.gerar_relatorio_estrategico(resultados)
        self.assertEqual(r1, r2)

    def test_nao_gera_jogos_novos_nem_altera_os_resultados_originais(self) -> None:
        resultados = [_resultado(70.0), _resultado(85.0)]
        totais_antes = [r.total for r in resultados]
        ede.gerar_relatorio_estrategico(resultados)
        self.assertEqual([r.total for r in resultados], totais_antes)


class TestIntegracaoComEliteScoreReal(unittest.TestCase):
    """Integra com o Elite Score real (core.elite_score/elite_score_service),
    sem alterar nenhum calculo -- apenas verifica que o relatorio estrategico
    e coerente com os resultados ja produzidos pelo Core."""

    def setUp(self) -> None:
        self.df = base_repository.carregar_base()
        self.referencias = es.construir_referencias(self.df)

    def test_relatorio_sobre_lote_real_de_jogos_historicos(self) -> None:
        linhas = self.df[COLUNAS_DEZENAS].values.tolist()[-5:]
        jogos = [[int(d) for d in linha] for linha in linhas]
        resultados = es.calcular_elite_score_lote(jogos, self.df)

        relatorio = ede.gerar_relatorio_estrategico(resultados)

        self.assertEqual(len(relatorio.jogos_classificados), len(resultados))
        self.assertEqual(sum(relatorio.distribuicao.values()), len(resultados))
        for classificado, resultado in zip(relatorio.jogos_classificados, resultados):
            self.assertEqual(classificado.score, resultado.total)
            self.assertEqual(classificado.classificacao, ede.classificar_score(resultado.total))
        self.assertIn(relatorio.estrategia.perfil, {ede.PERFIL_CONSERVADOR, ede.PERFIL_EQUILIBRADO, ede.PERFIL_AGRESSIVO})
        self.assertIn(relatorio.estrategia.nivel_risco, {ede.RISCO_BAIXO, ede.RISCO_MEDIO, ede.RISCO_ALTO})

    def test_repetibilidade_com_dados_reais(self) -> None:
        linhas = self.df[COLUNAS_DEZENAS].values.tolist()[-3:]
        jogos = [[int(d) for d in linha] for linha in linhas]
        resultados = es.calcular_elite_score_lote(jogos, self.df)
        r1 = ede.gerar_relatorio_estrategico(resultados)
        r2 = ede.gerar_relatorio_estrategico(resultados)
        self.assertEqual(r1, r2)


if __name__ == "__main__":
    unittest.main()
