from __future__ import annotations

import unittest

from src.carregar_dados import CAMINHO_BASE_PADRAO, carregar_base
from src.motor_elite_lotofacil import (
    MOTOR_OFICIAL_PRODUCAO,
    NOMES_JOGOS_PRODUCAO,
    assinatura_portfolio,
    gerar_jogos_producao_v1,
    validar_jogos_producao,
)


class JogosProducaoTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.jogos = gerar_jogos_producao_v1(carregar_base(CAMINHO_BASE_PADRAO))

    def test_cinco_perfis_oficiais(self) -> None:
        self.assertEqual(self.jogos["Perfil"].tolist(), NOMES_JOGOS_PRODUCAO)
        self.assertEqual(set(self.jogos["Motor"]), {MOTOR_OFICIAL_PRODUCAO})

    def test_cada_jogo_tem_15_dezenas_validas(self) -> None:
        for _, row in self.jogos.iterrows():
            dezenas = [int(row[f"Bola{i}"]) for i in range(1, 16)]
            self.assertEqual(len(dezenas), 15)
            self.assertEqual(len(set(dezenas)), 15)
            self.assertTrue(all(1 <= dezena <= 25 for dezena in dezenas))

    def test_jogos_sao_diferentes(self) -> None:
        combinacoes = {
            tuple(int(row[f"Bola{i}"]) for i in range(1, 16))
            for _, row in self.jogos.iterrows()
        }
        self.assertEqual(len(combinacoes), 5)
        for jogo_a, jogo_b in __import__("itertools").combinations(combinacoes, 2):
            self.assertGreaterEqual(len(set(jogo_a) - set(jogo_b)), 3)

    def test_todos_exibem_potencial_15_e_estrategia(self) -> None:
        for coluna in ("Perfil", "Dezenas", "Score", "Potencial 15", "Soma", "Pares", "Ímpares"):
            self.assertIn(coluna, self.jogos.columns)
        self.assertTrue(self.jogos["Potencial 15"].between(0, 100).all())
        self.assertTrue(self.jogos["Estrategia"].astype(str).str.len().gt(20).all())
        self.assertTrue(self.jogos["Faixas"].str.match(r"^\d-\d-\d-\d-\d$").all())

    def test_assinatura_portfolio_e_estavel_e_unica(self) -> None:
        assinatura = assinatura_portfolio(self.jogos)
        self.assertEqual(len(assinatura), 5)
        self.assertEqual(len(set(assinatura)), 5)
        self.assertEqual(assinatura, assinatura_portfolio(self.jogos.copy()))

    def test_validador_rejeita_jogo_duplicado(self) -> None:
        duplicados = self.jogos.copy()
        for i in range(1, 16):
            duplicados.loc[1, f"Bola{i}"] = duplicados.loc[0, f"Bola{i}"]
        with self.assertRaisesRegex(ValueError, "repete uma combinacao"):
            validar_jogos_producao(duplicados)

    def test_dez_geracoes_produzem_carteiras_novas(self) -> None:
        base = carregar_base(CAMINHO_BASE_PADRAO)
        historico = {
            tuple(sorted(int(row[f"Bola{i}"]) for i in range(1, 16)))
            for _, row in base.iterrows()
        }
        assinaturas = []
        anterior = None
        for semente in range(101, 111):
            jogos = gerar_jogos_producao_v1(base, semente=semente, assinatura_anterior=anterior)
            validar_jogos_producao(jogos)
            anterior = assinatura_portfolio(jogos)
            self.assertTrue(all(jogo not in historico for jogo in anterior))
            self.assertTrue(jogos["Soma"].between(165, 225).all())
            self.assertTrue(jogos["Pares"].between(6, 9).all())
            assinaturas.append(anterior)
            self.assertTrue((jogos["Elite Score Temporal"] > 0).all())
            self.assertTrue((jogos["DNA temporal 15 pontos"] > 0).all())
        self.assertEqual(len(set(assinaturas)), 10)


if __name__ == "__main__":
    unittest.main()
