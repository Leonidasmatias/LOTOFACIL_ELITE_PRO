"""Testes do Trend Hybrid Explainer (Fase Trend Hybrid V1 - src/ai/trend_hybrid_explainer.py).

Cobrem: cobertura completa das 25 dezenas (15 selecionadas + 10
descartadas), consistencia da explicacao (mesma entrada -> mesma saida),
coerencia entre a explicacao e o bilhete original (sem recalcular nenhum
valor do Trend Score) e presenca de um motivo textual nao vazio para cada
dezena.
"""
from __future__ import annotations

import unittest

from src.ai.trend_hybrid_explainer import explicar_bilhete
from src.core.trend_hybrid_engine import gerar_bilhete_trend_hybrid
from src.repository.base_repository import CAMINHO_BASE_PADRAO, carregar_base


class TestExplicarBilheteComDadosReais(unittest.TestCase):
    """Integra com o Trend Hybrid Engine real, sem alterar nenhum calculo --
    apenas verifica que a explicacao e coerente com o bilhete ja gerado."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.df = carregar_base(CAMINHO_BASE_PADRAO)
        cls.bilhete = gerar_bilhete_trend_hybrid(cls.df)
        cls.explicacao = explicar_bilhete(cls.bilhete)

    def test_total_de_dezenas_explicadas_e_25(self) -> None:
        self.assertEqual(len(self.explicacao.selecionadas) + len(self.explicacao.descartadas), 25)

    def test_dezenas_selecionadas_batem_com_o_bilhete(self) -> None:
        dezenas_explicadas = {e.dezena for e in self.explicacao.selecionadas}
        self.assertEqual(dezenas_explicadas, set(self.bilhete.dezenas))

    def test_dezenas_descartadas_nao_estao_no_bilhete(self) -> None:
        dezenas_descartadas = {e.dezena for e in self.explicacao.descartadas}
        self.assertTrue(dezenas_descartadas.isdisjoint(set(self.bilhete.dezenas)))

    def test_nenhuma_dezena_repetida_entre_selecionadas_e_descartadas(self) -> None:
        selecionadas = {e.dezena for e in self.explicacao.selecionadas}
        descartadas = {e.dezena for e in self.explicacao.descartadas}
        self.assertEqual(selecionadas & descartadas, set())

    def test_todas_as_explicacoes_tem_motivo_nao_vazio(self) -> None:
        for explicacao_dezena in (*self.explicacao.selecionadas, *self.explicacao.descartadas):
            self.assertTrue(explicacao_dezena.motivo.strip())

    def test_resumo_nao_vazio_e_menciona_a_divisao(self) -> None:
        n_a, n_b = self.bilhete.divisao
        self.assertTrue(self.explicacao.resumo.strip())
        self.assertIn(f"{n_a}+{n_b}", self.explicacao.resumo)

    def test_trend_score_da_explicacao_bate_com_a_pontuacao_do_bilhete(self) -> None:
        pontuacoes_por_dezena = {p.indicadores.dezena: p for p in self.bilhete.pontuacoes}
        for explicacao_dezena in (*self.explicacao.selecionadas, *self.explicacao.descartadas):
            pontuada = pontuacoes_por_dezena[explicacao_dezena.dezena]
            self.assertEqual(explicacao_dezena.trend_score, pontuada.trend_score)
            self.assertEqual(explicacao_dezena.atraso, pontuada.indicadores.atraso)
            self.assertEqual(explicacao_dezena.momentum, pontuada.indicadores.momentum)

    def test_repetibilidade_mesma_entrada_mesma_saida(self) -> None:
        outra_explicacao = explicar_bilhete(self.bilhete)
        self.assertEqual(outra_explicacao.resumo, self.explicacao.resumo)
        self.assertEqual(
            [e.motivo for e in outra_explicacao.selecionadas],
            [e.motivo for e in self.explicacao.selecionadas],
        )


if __name__ == "__main__":
    unittest.main()
