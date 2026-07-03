"""Testes da camada Services (Fase 3 - Phoenix V1 + Fase Phoenix V2 Elite Score).

Services nao contem regra de negocio propria: apenas orquestra Core e
Repository. Estes testes garantem que cada wrapper de service devolve
exatamente o que a camada correspondente (core/repository) devolveria se
chamada diretamente -- inclusive os wrappers de estatisticas introduzidos em
``base_service`` na Fase Hardening RC (reducao de acoplamento UI -> Core),
que devem permanecer 100% equivalentes as chamadas diretas a
``core.estatisticas``, sem alterar nenhum calculo.
"""
from __future__ import annotations

import unittest
from pathlib import Path

from src.core import estatisticas, motor_elite, pagamento_regras
from src.repository import base_repository
from src.services import base_service, elite_score_service, pagamento_service, previsao_service


class TestBaseService(unittest.TestCase):
    def setUp(self) -> None:
        self.df = base_repository.carregar_base()

    def test_carregar_base_atual_equivale_ao_repository(self) -> None:
        self.assertTrue(base_service.carregar_base_atual().equals(base_repository.carregar_base()))

    def test_resumo_equivale_ao_repository(self) -> None:
        self.assertEqual(base_service.resumo(self.df), base_repository.resumo_base(self.df))

    def test_buscar_info_concurso_sempre_devolve_dict(self) -> None:
        info = base_service.buscar_info_concurso()
        self.assertIsInstance(info, dict)

    def test_metadados_publicos_usa_ultimo_concurso_quando_info_incompleta(self) -> None:
        resumo = base_service.resumo(self.df)
        meta = base_service.metadados_publicos(self.df, {})
        self.assertEqual(meta["concurso_alvo"], resumo["ultimo_concurso"] + 1)
        self.assertEqual(meta["data_sorteio"], "Aguardando CAIXA")
        self.assertEqual(meta["fonte"], "fallback_local")

    def test_wrappers_estatisticas_equivalem_as_chamadas_diretas_ao_core(self) -> None:
        ultimo = self.df.iloc[-1][base_repository.COLUNAS_DEZENAS].astype(int).tolist()
        self.assertTrue(base_service.dezenas_quentes(self.df).equals(estatisticas.dezenas_quentes(self.df)))
        self.assertTrue(base_service.dezenas_frias(self.df).equals(estatisticas.dezenas_frias(self.df)))
        self.assertTrue(base_service.dezenas_atrasadas(self.df).equals(estatisticas.dezenas_atrasadas(self.df)))
        self.assertEqual(base_service.pares_impares(ultimo), estatisticas.pares_impares(ultimo))
        self.assertEqual(base_service.centro_moldura(ultimo), estatisticas.centro_moldura(ultimo))
        self.assertEqual(base_service.linhas_colunas(ultimo), estatisticas.linhas_colunas(ultimo))


class TestPrevisaoService(unittest.TestCase):
    def setUp(self) -> None:
        self.df = base_repository.carregar_base()

    def test_gerar_previsoes_producao_equivale_ao_core(self) -> None:
        self.assertTrue(
            previsao_service.gerar_previsoes_producao(self.df).equals(motor_elite.gerar_jogos_producao_v1(self.df))
        )

    def test_gerar_jogos_admin_equivale_ao_core(self) -> None:
        self.assertTrue(
            previsao_service.gerar_jogos_admin(self.df, 3).equals(motor_elite.gerar_varios_jogos(self.df, 3))
        )

    def test_obter_ranking_elite_equivale_ao_core(self) -> None:
        self.assertTrue(
            previsao_service.obter_ranking_elite(self.df).equals(motor_elite.ranking_elite_lotofacil(self.df))
        )

    def test_motor_oficial_nome_equivale_a_constante_do_core(self) -> None:
        self.assertEqual(previsao_service.motor_oficial_nome(), motor_elite.MOTOR_OFICIAL_PRODUCAO)

    def test_exportar_previsoes_gera_arquivo_csv(self) -> None:
        jogos = previsao_service.gerar_previsoes_producao(self.df)
        caminho = previsao_service.exportar_previsoes(jogos, "teste_unitario")
        try:
            self.assertTrue(Path(caminho).exists())
        finally:
            Path(caminho).unlink(missing_ok=True)


class TestEliteScoreService(unittest.TestCase):
    def setUp(self) -> None:
        self.df = base_repository.carregar_base()
        self.jogos = previsao_service.gerar_previsoes_producao(self.df)

    def test_calcular_scores_devolve_um_resultado_por_jogo(self) -> None:
        resultados = elite_score_service.calcular_scores(self.jogos, self.df)
        self.assertEqual(len(resultados), len(self.jogos))

    def test_calcular_scores_lote_vazio_devolve_lista_vazia(self) -> None:
        vazio = self.jogos.iloc[0:0]
        self.assertEqual(elite_score_service.calcular_scores(vazio, self.df), [])

    def test_anexar_elite_score_adiciona_coluna_sem_alterar_as_demais(self) -> None:
        jogos_com_score, resultados = elite_score_service.anexar_elite_score(self.jogos, self.df)
        self.assertIn("Elite Score", jogos_com_score.columns)
        for coluna in self.jogos.columns:
            self.assertTrue(jogos_com_score[coluna].equals(self.jogos[coluna]))
        self.assertEqual(list(jogos_com_score["Elite Score"]), [round(r.total, 1) for r in resultados])

    def test_anexar_elite_score_e_consistente_com_calcular_scores(self) -> None:
        resultados_diretos = elite_score_service.calcular_scores(self.jogos, self.df)
        _, resultados_anexados = elite_score_service.anexar_elite_score(self.jogos, self.df)
        self.assertEqual([r.total for r in resultados_diretos], [r.total for r in resultados_anexados])


class TestPagamentoService(unittest.TestCase):
    def test_valor_padrao_analise_equivale_ao_core(self) -> None:
        self.assertEqual(pagamento_service.valor_padrao_analise(1), pagamento_regras.calcular_valor_pagamento(1))

    def test_email_valido_equivale_ao_core(self) -> None:
        self.assertEqual(
            pagamento_service.email_valido("teste@example.com"),
            pagamento_regras.email_cliente_valido("teste@example.com"),
        )
        self.assertEqual(
            pagamento_service.email_valido("invalido"),
            pagamento_regras.email_cliente_valido("invalido"),
        )


if __name__ == "__main__":
    unittest.main()
