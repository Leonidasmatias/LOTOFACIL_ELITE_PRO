"""Testes do modulo Elite Score Explainable AI (Fase V1.4 - src/ai/elite_explainer.py).

Cobrem: consistencia da explicacao (mesma entrada -> mesma saida),
classificacao correta por faixa de score (incluindo os limites exatos das
faixas) e a selecao correta de pontos fortes/penalidades a partir dos
componentes ja calculados pelo Core -- sem recalcular nenhum valor do Elite
Score.
"""
from __future__ import annotations

import unittest

from src.ai import elite_explainer as ee
from src.core import elite_score as es
from src.models.elite_score import ComponenteEliteScore
from src.repository import base_repository
from src.repository.base_repository import COLUNAS_DEZENAS


def _componente(nome: str, sub_score: float, peso: float = 0.1, contribuicao: float | None = None) -> ComponenteEliteScore:
    return ComponenteEliteScore(
        nome=nome,
        descricao=f"descricao de {nome}",
        valor_jogo=1.0,
        faixa_tipica=(0.0, 10.0),
        sub_score=sub_score,
        peso=peso,
        contribuicao=contribuicao if contribuicao is not None else peso * sub_score,
    )


class TestClassificarScore(unittest.TestCase):
    def test_limiares_sao_derivados_de_piso_sub_score(self) -> None:
        # 20 + 25%*80 = 40 ; 20 + 50%*80 = 60 ; 20 + 75%*80 = 80
        self.assertEqual(ee.LIMIAR_MEDIO, 40.0)
        self.assertEqual(ee.LIMIAR_ALTO, 60.0)
        self.assertEqual(ee.LIMIAR_ELITE_PREMIUM, 80.0)

    def test_classificacao_elite_premium_no_limite_e_acima(self) -> None:
        self.assertEqual(ee.classificar_score(80.0), ee.CLASSIFICACAO_ELITE_PREMIUM)
        self.assertEqual(ee.classificar_score(100.0), ee.CLASSIFICACAO_ELITE_PREMIUM)

    def test_classificacao_alto_no_limite_e_logo_abaixo_do_premium(self) -> None:
        self.assertEqual(ee.classificar_score(60.0), ee.CLASSIFICACAO_ALTO)
        self.assertEqual(ee.classificar_score(79.9), ee.CLASSIFICACAO_ALTO)

    def test_classificacao_medio_no_limite_e_logo_abaixo_do_alto(self) -> None:
        self.assertEqual(ee.classificar_score(40.0), ee.CLASSIFICACAO_MEDIO)
        self.assertEqual(ee.classificar_score(59.9), ee.CLASSIFICACAO_MEDIO)

    def test_classificacao_baixo_abaixo_do_limiar_medio(self) -> None:
        self.assertEqual(ee.classificar_score(39.9), ee.CLASSIFICACAO_BAIXO)
        self.assertEqual(ee.classificar_score(0.0), ee.CLASSIFICACAO_BAIXO)


class TestExplicarJogoComComponentesSinteticos(unittest.TestCase):
    """Usa componentes sinteticos (nao vindos do Core) para isolar a logica
    de selecao de pontos fortes/penalidades do calculo real do Elite Score."""

    def setUp(self) -> None:
        self.jogo = list(range(1, 16))
        self.features = [
            _componente("Alto A", sub_score=95.0),
            _componente("Alto B", sub_score=80.0),
            _componente("Neutro", sub_score=70.0),
            _componente("Baixo A", sub_score=55.0),
            _componente("Baixo B", sub_score=10.0),
        ]

    def test_pontos_fortes_sao_apenas_sub_score_maior_ou_igual_ao_limiar_elite_premium(self) -> None:
        explicacao = ee.explicar_jogo(self.jogo, self.features, score=72.0)
        nomes_fortes = {p.componente for p in explicacao.pontos_fortes}
        self.assertEqual(nomes_fortes, {"Alto A", "Alto B"})

    def test_penalidades_sao_apenas_sub_score_menor_que_limiar_alto(self) -> None:
        explicacao = ee.explicar_jogo(self.jogo, self.features, score=72.0)
        nomes_penalidades = {p.componente for p in explicacao.penalidades}
        self.assertEqual(nomes_penalidades, {"Baixo A", "Baixo B"})

    def test_componente_neutro_nao_aparece_em_nenhuma_lista(self) -> None:
        explicacao = ee.explicar_jogo(self.jogo, self.features, score=72.0)
        nomes = {p.componente for p in explicacao.pontos_fortes} | {p.componente for p in explicacao.penalidades}
        self.assertNotIn("Neutro", nomes)

    def test_pontos_fortes_ordenados_por_contribuicao_decrescente(self) -> None:
        features = [
            _componente("Menor contribuicao", sub_score=90.0, peso=0.05),
            _componente("Maior contribuicao", sub_score=90.0, peso=0.5),
        ]
        explicacao = ee.explicar_jogo(self.jogo, features, score=90.0)
        nomes = [p.componente for p in explicacao.pontos_fortes]
        self.assertEqual(nomes, ["Maior contribuicao", "Menor contribuicao"])

    def test_penalidades_ordenadas_por_sub_score_crescente_pior_primeiro(self) -> None:
        explicacao = ee.explicar_jogo(self.jogo, self.features, score=72.0)
        nomes = [p.componente for p in explicacao.penalidades]
        self.assertEqual(nomes, ["Baixo B", "Baixo A"])

    def test_sem_pontos_fortes_nem_penalidades_quando_tudo_neutro(self) -> None:
        features = [_componente("Neutro A", sub_score=65.0), _componente("Neutro B", sub_score=75.0)]
        explicacao = ee.explicar_jogo(self.jogo, features, score=70.0)
        self.assertEqual(explicacao.pontos_fortes, ())
        self.assertEqual(explicacao.penalidades, ())
        self.assertIn("Nenhum componente se destacou", explicacao.resumo)
        self.assertIn("Nenhuma penalidade relevante", explicacao.resumo)

    def test_score_e_classificacao_repassados_sem_alteracao(self) -> None:
        explicacao = ee.explicar_jogo(self.jogo, self.features, score=63.5)
        self.assertEqual(explicacao.score, 63.5)
        self.assertEqual(explicacao.classificacao, ee.classificar_score(63.5))

    def test_jogo_com_numero_errado_de_dezenas_levanta_value_error(self) -> None:
        with self.assertRaises(ValueError):
            ee.explicar_jogo([1, 2, 3], self.features, score=50.0)

    def test_repetibilidade_mesma_entrada_mesma_saida(self) -> None:
        e1 = ee.explicar_jogo(self.jogo, self.features, score=72.0)
        e2 = ee.explicar_jogo(self.jogo, self.features, score=72.0)
        self.assertEqual(e1, e2)


class TestExplicarResultadoComElitScoreReal(unittest.TestCase):
    """Integra com o Elite Score real (core.elite_score), sem alterar nenhum
    calculo -- apenas verifica que a explicacao e coerente com o resultado
    ja produzido pelo Core."""

    def setUp(self) -> None:
        self.df = base_repository.carregar_base()
        self.referencias = es.construir_referencias(self.df)
        self.jogo = self.df.iloc[-1][COLUNAS_DEZENAS].astype(int).tolist()

    def test_explicar_resultado_usa_o_mesmo_total_do_core(self) -> None:
        resultado = es.calcular_elite_score(self.jogo, self.referencias)
        explicacao = ee.explicar_resultado(self.jogo, resultado)
        self.assertEqual(explicacao.score, resultado.total)
        self.assertEqual(explicacao.classificacao, ee.classificar_score(resultado.total))

    def test_todos_os_componentes_do_resultado_aparecem_em_forte_penalidade_ou_nenhum(self) -> None:
        resultado = es.calcular_elite_score(self.jogo, self.referencias)
        explicacao = ee.explicar_resultado(self.jogo, resultado)
        nomes_fortes = {p.componente for p in explicacao.pontos_fortes}
        nomes_penalidades = {p.componente for p in explicacao.penalidades}
        self.assertEqual(nomes_fortes & nomes_penalidades, set())
        for componente in resultado.componentes:
            if componente.sub_score >= ee.LIMIAR_ELITE_PREMIUM:
                self.assertIn(componente.nome, nomes_fortes)
            elif componente.sub_score < ee.LIMIAR_ALTO:
                self.assertIn(componente.nome, nomes_penalidades)

    def test_repetibilidade_com_dados_reais(self) -> None:
        resultado = es.calcular_elite_score(self.jogo, self.referencias, ultimo_concurso=[1, 2, 3])
        e1 = ee.explicar_resultado(self.jogo, resultado)
        e2 = ee.explicar_resultado(self.jogo, resultado)
        self.assertEqual(e1, e2)

    def test_nao_altera_o_resultado_original_do_core(self) -> None:
        resultado = es.calcular_elite_score(self.jogo, self.referencias)
        total_antes = resultado.total
        componentes_antes = resultado.componentes
        ee.explicar_resultado(self.jogo, resultado)
        self.assertEqual(resultado.total, total_antes)
        self.assertEqual(resultado.componentes, componentes_antes)


if __name__ == "__main__":
    unittest.main()
