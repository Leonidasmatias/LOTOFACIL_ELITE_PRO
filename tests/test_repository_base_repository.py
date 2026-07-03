"""Testes de regressao: leitura/validacao da base historica (Repository).

Fase 0 - Phoenix V1. Cobre a leitura de concursos e a validacao da base,
usando a base real do projeto (``dados/lotofacil_historico.csv``).
"""
from __future__ import annotations

import unittest

import pandas as pd

from src.repository import base_repository


class TestBaseRepository(unittest.TestCase):
    def test_carregar_base_retorna_colunas_obrigatorias(self) -> None:
        df = base_repository.carregar_base()
        for coluna in base_repository.COLUNAS_OBRIGATORIAS:
            self.assertIn(coluna, df.columns)

    def test_carregar_base_nao_esta_vazia_e_esta_ordenada(self) -> None:
        df = base_repository.carregar_base()
        self.assertGreater(len(df), 0)
        self.assertTrue(df["Concurso"].is_monotonic_increasing)

    def test_carregar_base_sem_duplicatas_de_concurso(self) -> None:
        df = base_repository.carregar_base()
        self.assertEqual(df["Concurso"].duplicated().sum(), 0)

    def test_validar_base_rejeita_colunas_faltantes(self) -> None:
        df_invalido = pd.DataFrame({"Concurso": [1], "Data": ["01/01/2026"]})
        with self.assertRaises(ValueError):
            base_repository.validar_base(df_invalido)

    def test_resumo_base_contabiliza_primeiro_e_ultimo_concurso(self) -> None:
        df = base_repository.carregar_base()
        resumo = base_repository.resumo_base(df)
        self.assertEqual(resumo["total_concursos"], len(df))
        self.assertEqual(resumo["ultimo_concurso"], int(df["Concurso"].max()))
        self.assertEqual(resumo["primeiro_concurso"], int(df["Concurso"].min()))

    def test_resumo_base_com_dataframe_vazio(self) -> None:
        vazio = pd.DataFrame(columns=base_repository.COLUNAS_OBRIGATORIAS)
        resumo = base_repository.resumo_base(vazio)
        self.assertEqual(resumo, {"total_concursos": 0, "primeiro_concurso": 0, "ultimo_concurso": 0})


if __name__ == "__main__":
    unittest.main()
