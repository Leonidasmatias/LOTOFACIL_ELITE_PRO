from __future__ import annotations

import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest


class InterfacePrincipalTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = AppTest.from_file("app.py").run(timeout=60)
        cls.html = "\n".join(element.value for element in cls.app.markdown)

    def test_renderiza_cinco_cards_e_75_bolas(self) -> None:
        self.assertFalse(self.app.exception)
        self.assertEqual(self.html.count('class="elite-game-card"'), 5)
        self.assertEqual(self.html.count('class="elite-ball"'), 75)
        self.assertEqual(self.html.count("Potencial 15"), 5)

    def test_botao_conferir_jogos_salvos_nao_quebra(self) -> None:
        app = AppTest.from_file("app.py").run(timeout=60)
        botao = next(button for button in app.button if button.label == "CONFERIR JOGOS SALVOS")
        botao.click().run(timeout=60)
        self.assertFalse(app.exception)
        mensagens = [alert.value for alert in app.info] + [alert.value for alert in app.success]
        self.assertTrue(
            any(
                mensagem in {
                    "Jogos salvos aguardando resultado oficial.",
                    "Conferência atualizada com base histórica disponível.",
                    "Ainda não existem jogos salvos para conferência.",
                }
                for mensagem in mensagens
            )
        )

    def test_conferencia_exibe_resumo_e_colunas_completas(self) -> None:
        labels_metricas = [metrica.label for metrica in self.app.metric]
        for label in (
            "Total de jogos salvos",
            "Jogos pendentes",
            "Jogos conferidos",
            "Melhor acerto histórico",
            "Média de acertos",
        ):
            self.assertIn(label, labels_metricas)

        tabela = self.app.dataframe[-1].value
        self.assertEqual(
            tabela.columns.tolist(),
            ["Concurso Alvo", "Perfil", "Dezenas", "Score", "Status", "Acertos", "Desempenho"],
        )

    def test_html_dos_cards_nao_esta_formatado_como_codigo(self) -> None:
        self.assertNotIn("\n    <article", self.html)
        self.assertNotIn("```", self.html)

    def test_perfis_e_botao_principal_estao_visiveis(self) -> None:
        for perfil in ["Diamante", "Ouro", "Prata", "Agressivo", "Conservador"]:
            self.assertIn(perfil, self.html)
        labels = [button.label for button in self.app.button]
        self.assertIn("GERAR / ATUALIZAR OS 5 JOGOS", labels)
        self.assertIn("SALVAR JOGOS PARA CONFERÊNCIA", labels)
        self.assertIn("CONFERIR JOGOS SALVOS", labels)
        self.assertNotIn("PREVER PROXIMO SORTEIO", " ".join(labels))

    def test_versao_gratuita_nao_exibe_cobranca_ou_bloqueio(self) -> None:
        labels = [button.label for button in self.app.button]
        self.assertFalse(self.app.text_input)
        self.assertNotIn("PIX", " ".join(labels))
        self.assertNotIn("Área PIX", self.html)
        self.assertNotIn("pagamento", self.html.lower())
        self.assertNotIn("PASSO 1", self.html)
        self.assertNotIn("PASSO 2", self.html)

    def test_comunicacao_busca_15_sem_promessa(self) -> None:
        conteudo = self.html.lower()
        self.assertIn("busca estatística pelos 15 acertos", conteudo)
        self.assertIn("motor preparado para buscar o melhor resultado possível", conteudo)
        self.assertNotIn("garantia de 15 acertos", conteudo)
        self.assertNotIn("certeza de prêmio", conteudo)
        self.assertNotIn("números vencedores garantidos", conteudo)

    def test_interface_nao_exibe_caracteres_corrompidos(self) -> None:
        conteudo = self.html
        conteudo += "\n" + "\n".join(button.label for button in self.app.button)
        conteudo += "\n" + "\n".join(alert.value for alert in self.app.info)
        conteudo += "\n" + "\n".join(caption.value for caption in self.app.caption)
        for sequencia in ("ðŸ", "Ã", "Â"):
            self.assertNotIn(sequencia, conteudo)

    def test_texto_da_versao_gratuita_e_aviso(self) -> None:
        self.assertIn("Previsão estatística para o próximo sorteio", self.html)
        self.assertIn("Números sugeridos pelo Motor Elite", self.html)
        self.assertIn("CARTEIRA ELITE Nº 1", self.html)
        avisos = "\n".join(alert.value for alert in self.app.info)
        self.assertIn("Análise estatística sem garantia de prêmio", avisos)

    def test_comunicacao_e_informacoes_do_motor(self) -> None:
        self.assertIn("Versão gratuita", self.html)
        self.assertIn("Números sugeridos pelo Motor Elite", self.html)
        self.assertIn("Previsão estatística para o próximo concurso da Lotofácil", self.html)
        self.assertIn("ELITE_SCORE_V35_TEMPORAL", self.html)
        self.assertIn("dados/lotofacil_historico.csv", self.html)
        self.assertIn("Resumo estatístico da carteira", self.html)
        self.assertIn("Conferir Jogos Salvos", self.html)
        for titulo in (
            "Diamante — maior score",
            "Ouro — equilíbrio premium",
            "Prata — alternativa forte",
            "Agressivo — maior variação",
            "Conservador — maior estabilidade",
        ):
            self.assertIn(titulo, self.html)

        fonte = Path("app.py").read_text(encoding="utf-8")
        self.assertIn('st.download_button(\n        "DOWNLOAD CSV"', fonte)
        self.assertIn('"BAIXAR JOGOS SALVOS CSV"', fonte)

    def test_ordem_publica_simplificada(self) -> None:
        fonte = Path("app.py").read_text(encoding="utf-8")
        trecho = fonte[fonte.index("def render_resultado"):fonte.index("def main")]
        pos_intro = trecho.index("Previsão estatística para o próximo sorteio")
        pos_botao = trecho.index("GERAR / ATUALIZAR OS 5 JOGOS")
        pos_carteira = trecho.index("CARTEIRA ELITE Nº")
        pos_jogos = trecho.index("montar_html_jogos(jogos)")
        pos_csv = trecho.index("DOWNLOAD CSV")
        pos_aviso = trecho.index("Análise estatística sem garantia de prêmio")
        self.assertLess(pos_intro, pos_botao)
        self.assertLess(pos_botao, pos_carteira)
        self.assertLess(pos_intro, pos_carteira)
        self.assertLess(pos_carteira, pos_jogos)
        self.assertLess(pos_jogos, pos_csv)
        self.assertLess(pos_csv, pos_aviso)
        self.assertLess(pos_jogos, pos_aviso)


if __name__ == "__main__":
    unittest.main()
