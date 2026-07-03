"""Testes de regressao: estatisticas puras (Core).

Fase 0 - Phoenix V1.
"""
from __future__ import annotations

import unittest

from src.core import estatisticas
from src.repository import base_repository


class TestEstatisticas(unittest.TestCase):
    def setUp(self) -> None:
        self.df = base_repository.carregar_base()

    def test_pares_impares_soma_15(self) -> None:
        dezenas = list(range(1, 16))
        resultado = estatisticas.pares_impares(dezenas)
        self.assertEqual(resultado["Pares"] + resultado["Impares"], 15)

    def test_centro_moldura_soma_15(self) -> None:
        dezenas = list(range(1, 16))
        resultado = estatisticas.centro_moldura(dezenas)
        self.assertEqual(resultado["Centro"] + resultado["Moldura"], 15)

    def test_linhas_colunas_soma_15(self) -> None:
        dezenas = list(range(1, 16))
        resultado = estatisticas.linhas_colunas(dezenas)
        self.assertEqual(sum(resultado["Linhas"].values()), 15)
        self.assertEqual(sum(resultado["Colunas"].values()), 15)

    def test_dezenas_quentes_e_frias_cobrem_todas_dezenas_quando_limite_25(self) -> None:
        quentes = estatisticas.dezenas_quentes(self.df, limite=25)
        self.assertEqual(set(quentes["Dezena"]), set(estatisticas.TODAS_DEZENAS))

    def test_dezenas_atrasadas_atraso_nao_negativo(self) -> None:
        atrasadas = estatisticas.dezenas_atrasadas(self.df)
        self.assertTrue((atrasadas["Atraso"] >= 0).all())

    def test_frequencia_dezenas_com_ultimos_menor_ou_igual_geral(self) -> None:
        geral = estatisticas.frequencia_dezenas(self.df).set_index("Dezena")["Frequencia"]
        ultimos_20 = estatisticas.frequencia_dezenas(self.df, 20).set_index("Dezena")["Frequencia"]
        self.assertTrue((ultimos_20 <= geral).all())


if __name__ == "__main__":
    unittest.main()
