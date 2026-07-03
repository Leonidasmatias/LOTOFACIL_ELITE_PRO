"""Testes de regressao: geracao/ranqueamento de jogos (Motor Elite - Core).

Fase 0 - Phoenix V1. Garante que o algoritmo oficial de producao continua
gerando 5 jogos validos (15 dezenas distintas, entre 1 e 25) e que o ranking
oficial devolve as 25 dezenas.
"""
from __future__ import annotations

import unittest

from src.core import motor_elite
from src.repository import base_repository


class TestMotorElite(unittest.TestCase):
    def setUp(self) -> None:
        self.df = base_repository.carregar_base()

    def test_ranking_elite_lotofacil_cobre_25_dezenas(self) -> None:
        ranking = motor_elite.ranking_elite_lotofacil(self.df)
        self.assertEqual(len(ranking), 25)
        self.assertEqual(set(ranking["Dezena"]), set(range(1, 26)))

    def test_gerar_jogos_producao_v1_gera_5_perfis_validos(self) -> None:
        jogos = motor_elite.gerar_jogos_producao_v1(self.df)
        self.assertEqual(len(jogos), len(motor_elite.NOMES_JOGOS_PRODUCAO))
        for _, row in jogos.iterrows():
            dezenas = [int(row[f"Bola{i}"]) for i in range(1, 16)]
            self.assertEqual(len(set(dezenas)), 15, "Jogo deve ter 15 dezenas distintas")
            self.assertTrue(all(1 <= d <= 25 for d in dezenas))

    def test_gerar_varios_jogos_e_deterministico_por_semente(self) -> None:
        jogos_a = motor_elite.gerar_varios_jogos(self.df, 5)
        jogos_b = motor_elite.gerar_varios_jogos(self.df, 5)
        self.assertTrue(jogos_a.equals(jogos_b), "Mesma semente deve gerar o mesmo resultado")

    def test_score_jogo_penaliza_fora_da_faixa_pares(self) -> None:
        ranking = motor_elite.ranking_elite_lotofacil(self.df)
        todos_impares = [1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23, 25, 2, 4]
        score_com_penalidade = motor_elite.score_jogo(todos_impares, ranking)
        base_sem_penalidade = sum(
            ranking.set_index("Dezena")["Elite Score"].get(d, 0) for d in todos_impares
        )
        self.assertLess(score_com_penalidade, base_sem_penalidade)


if __name__ == "__main__":
    unittest.main()
