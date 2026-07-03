"""Testes do modulo Elite Score (Phoenix V2 - core/elite_score.py).

Cobrem: consistencia do calculo, repetibilidade dos resultados, estabilidade
da pontuacao para a mesma entrada, o caso de borda de diversidade com jogos
duplicados no lote (bug corrigido durante o desenvolvimento: o componente de
diversidade deve excluir o jogo avaliado pela POSICAO no lote, nao pelo
VALOR, para nao ignorar duplicatas por engano) e a validacao de entrada
adicionada na Fase Hardening RC (``calcular_elite_score`` deve rejeitar
jogos com numero errado de dezenas, dezenas repetidas ou fora da faixa
1-25).
"""
from __future__ import annotations

import unittest

from src.core import elite_score as es
from src.repository import base_repository


class TestConstruirReferencias(unittest.TestCase):
    def setUp(self) -> None:
        self.df = base_repository.carregar_base()
        self.referencias = es.construir_referencias(self.df)

    def test_faixas_tem_min_p10_p90_max_coerentes(self) -> None:
        for faixa in (
            self.referencias.pares,
            self.referencias.centro,
            self.referencias.max_linha_coluna,
            self.referencias.soma,
            self.referencias.repeticao,
            self.referencias.frequencia_media,
            self.referencias.atraso_medio,
        ):
            self.assertLessEqual(faixa.minimo, faixa.p10)
            self.assertLessEqual(faixa.p10, faixa.p90)
            self.assertLessEqual(faixa.p90, faixa.maximo)

    def test_frequencia_e_atraso_por_dezena_cobrem_as_25_dezenas(self) -> None:
        self.assertEqual(set(self.referencias.frequencia_por_dezena.keys()), set(range(1, 26)))
        self.assertEqual(set(self.referencias.atraso_por_dezena.keys()), set(range(1, 26)))


class TestCalcularEliteScore(unittest.TestCase):
    def setUp(self) -> None:
        self.df = base_repository.carregar_base()
        self.referencias = es.construir_referencias(self.df)
        self.jogo_valido = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]

    def test_pesos_somam_um(self) -> None:
        self.assertAlmostEqual(sum(es.PESOS.values()), 1.0, places=9)

    def test_resultado_tem_8_componentes(self) -> None:
        resultado = es.calcular_elite_score(self.jogo_valido, self.referencias)
        self.assertEqual(len(resultado.componentes), 8)

    def test_total_dentro_de_0_a_100(self) -> None:
        resultado = es.calcular_elite_score(self.jogo_valido, self.referencias)
        self.assertGreaterEqual(resultado.total, 0.0)
        self.assertLessEqual(resultado.total, 100.0)

    def test_contribuicao_de_cada_componente_bate_com_peso_vezes_subscore(self) -> None:
        resultado = es.calcular_elite_score(self.jogo_valido, self.referencias)
        for c in resultado.componentes:
            self.assertAlmostEqual(c.contribuicao, c.peso * c.sub_score, places=6)

    def test_total_e_a_soma_das_contribuicoes(self) -> None:
        resultado = es.calcular_elite_score(self.jogo_valido, self.referencias)
        soma_contribuicoes = sum(c.contribuicao for c in resultado.componentes)
        self.assertAlmostEqual(resultado.total, round(soma_contribuicoes, 2), places=2)

    def test_repetibilidade_mesma_entrada_mesma_saida(self) -> None:
        r1 = es.calcular_elite_score(self.jogo_valido, self.referencias, ultimo_concurso=[1, 2, 3, 4, 5])
        r2 = es.calcular_elite_score(self.jogo_valido, self.referencias, ultimo_concurso=[1, 2, 3, 4, 5])
        self.assertEqual(r1.total, r2.total)
        for c1, c2 in zip(r1.componentes, r2.componentes):
            self.assertEqual(c1.sub_score, c2.sub_score)
            self.assertEqual(c1.contribuicao, c2.contribuicao)

    def test_estabilidade_repetindo_calculo_10_vezes(self) -> None:
        totais = {
            es.calcular_elite_score(self.jogo_valido, self.referencias, ultimo_concurso=[1, 2, 3]).total
            for _ in range(10)
        }
        self.assertEqual(len(totais), 1, "o mesmo jogo deve sempre gerar o mesmo total")

    def test_sem_ultimo_concurso_componente_repeticao_fica_neutro(self) -> None:
        resultado = es.calcular_elite_score(self.jogo_valido, self.referencias, ultimo_concurso=None)
        repeticao = next(c for c in resultado.componentes if c.nome.startswith("Repeticao"))
        self.assertEqual(repeticao.sub_score, 100.0)

    def test_sem_lote_componente_diversidade_fica_neutro(self) -> None:
        resultado = es.calcular_elite_score(self.jogo_valido, self.referencias, lote=None)
        diversidade = next(c for c in resultado.componentes if c.nome.startswith("Diversidade"))
        self.assertEqual(diversidade.sub_score, 100.0)

    def test_valor_alem_do_extremo_historico_satura_proximo_de_zero(self) -> None:
        # 15 dezenas todas impares e consecutivas de menor soma possivel, para
        # forcar pares muito abaixo do minimo/faixa tipica historica.
        jogo_extremo = [1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23, 25, 2, 4]  # 2 pares apenas
        resultado = es.calcular_elite_score(jogo_extremo, self.referencias)
        pares = next(c for c in resultado.componentes if c.nome == "Pares/Impares")
        self.assertLess(pares.sub_score, 20.0)

    def test_sub_score_nunca_sai_da_faixa_0_100(self) -> None:
        resultado = es.calcular_elite_score(self.jogo_valido, self.referencias, ultimo_concurso=[1, 2, 3])
        for c in resultado.componentes:
            self.assertGreaterEqual(c.sub_score, 0.0)
            self.assertLessEqual(c.sub_score, 100.0)

    def test_jogo_com_numero_errado_de_dezenas_levanta_value_error(self) -> None:
        with self.assertRaises(ValueError):
            es.calcular_elite_score([1, 2, 3], self.referencias)

    def test_jogo_com_dezena_repetida_levanta_value_error(self) -> None:
        jogo_com_repetida = [1, 1, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
        with self.assertRaises(ValueError):
            es.calcular_elite_score(jogo_com_repetida, self.referencias)

    def test_jogo_com_dezena_fora_da_faixa_1_a_25_levanta_value_error(self) -> None:
        jogo_fora_da_faixa = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 26]
        with self.assertRaises(ValueError):
            es.calcular_elite_score(jogo_fora_da_faixa, self.referencias)


class TestDiversidadeEntreJogosDoLote(unittest.TestCase):
    """Caso de borda que motivou a correcao: exclusao por posicao, nao por valor."""

    def setUp(self) -> None:
        self.df = base_repository.carregar_base()
        self.referencias = es.construir_referencias(self.df)
        self.jogo_a = [1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23, 25, 2, 4]
        self.jogo_b = list(self.jogo_a)  # mesmo valor, jogo "duplicado" no lote
        self.jogo_c = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 16]

    def test_jogos_duplicados_no_lote_sao_penalizados_por_diversidade(self) -> None:
        lote = [self.jogo_a, self.jogo_b, self.jogo_c]
        resultados = es.calcular_elite_score_lote(lote, self.df)
        diversidade = [
            next(c for c in r.componentes if c.nome.startswith("Diversidade")).sub_score for r in resultados
        ]
        # jogo_a e jogo_b sao identicos entre si -> diversidade baixa para ambos.
        self.assertLess(diversidade[0], 50.0)
        self.assertLess(diversidade[1], 50.0)
        self.assertEqual(diversidade[0], diversidade[1])
        # jogo_c e diferente dos outros dois -> diversidade maior que a de a/b.
        self.assertGreater(diversidade[2], diversidade[0])

    def test_lote_com_jogo_unico_fica_neutro(self) -> None:
        resultados = es.calcular_elite_score_lote([self.jogo_a], self.df)
        diversidade = next(c for c in resultados[0].componentes if c.nome.startswith("Diversidade"))
        self.assertEqual(diversidade.sub_score, 100.0)


if __name__ == "__main__":
    unittest.main()
