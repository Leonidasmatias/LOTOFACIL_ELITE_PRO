from __future__ import annotations

import unittest

import pandas as pd

from app import montar_html_jogos, normalizar_jogos_gerados
from src.motor_elite_lotofacil import NOMES_JOGOS_PRODUCAO


class NormalizacaoJogosTest(unittest.TestCase):
    def test_normaliza_lista_sem_potencial_e_metricas(self) -> None:
        jogos = [
            {"Perfil": nome, "Dezenas": list(range(1, 16)), "Score": 72.5}
            for nome in NOMES_JOGOS_PRODUCAO
        ]
        normalizados = normalizar_jogos_gerados(jogos)
        self.assertTrue((normalizados["Potencial 15"] == 72.5).all())
        self.assertTrue((normalizados["Soma"] == 120).all())
        self.assertTrue((normalizados["Pares"] == 7).all())
        self.assertTrue((normalizados["Ímpares"] == 8).all())
        self.assertEqual(normalizados.loc[0, "Dezenas"], list(range(1, 16)))

    def test_normaliza_dataframe_sem_score(self) -> None:
        jogos = pd.DataFrame(
            [{f"Bola{i}": i for i in range(1, 16)} for _ in NOMES_JOGOS_PRODUCAO]
        )
        normalizados = normalizar_jogos_gerados(jogos)
        self.assertTrue((normalizados["Score"] == 0).all())
        self.assertTrue((normalizados["Potencial 15"] == 0).all())
        self.assertEqual(normalizados["Perfil"].tolist(), NOMES_JOGOS_PRODUCAO)

    def test_html_aceita_jogos_legados_sem_potencial(self) -> None:
        jogos = pd.DataFrame(
            [
                {"Perfil": nome, "Dezenas": list(range(1, 16)), "Score": 50}
                for nome in NOMES_JOGOS_PRODUCAO
            ]
        )
        html = montar_html_jogos(jogos)
        self.assertEqual(html.count("Potencial 15 50.00%"), 5)


if __name__ == "__main__":
    unittest.main()
