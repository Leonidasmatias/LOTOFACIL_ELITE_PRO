from __future__ import annotations

import functools
import hashlib
import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock
from urllib.error import URLError

import pandas as pd
from streamlit.testing.v1 import AppTest

from src import historico_sqlite, jogos_salvos
from src.repository import base_repository

RAIZ = Path(__file__).resolve().parents[1]
CSV_HISTORICO = RAIZ / "dados" / "lotofacil_historico.csv"
SQLITE_V5 = RAIZ / "dados" / "lotofacil_v5.sqlite3"
JOGOS_SALVOS_CSV = RAIZ / "exports" / "jogos_salvos_lotofacil.csv"


def _hash_arquivo(caminho: Path) -> str | None:
    """Hash do conteudo real em disco, ou None se o arquivo nao existir."""
    if not caminho.exists():
        return None
    return hashlib.sha256(caminho.read_bytes()).hexdigest()


def _git_status_porcelano() -> str | None:
    """`git status --porcelain`, ou None se o git nao estiver disponivel
    (a comparacao de hashes abaixo continua valendo de qualquer forma)."""
    try:
        resultado = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=RAIZ,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return resultado.stdout if resultado.returncode == 0 else None


def _bloquear_rede(*_args, **_kwargs):
    raise URLError(
        "Rede real bloqueada durante os testes de interface (isolamento LF-01A). "
        "Se este teste precisa de uma resposta simulada da CAIXA, adicione o "
        "cenario ao mock em vez de remover o bloqueio."
    )


def _com_caminho_fixo(funcao_original, caminho_fixo: Path):
    """Redireciona uma funcao cujo unico parametro relevante e ``caminho``
    para ``caminho_fixo`` -- funciona tanto quando ela e chamada sem
    argumentos (uso direto em app.py) quanto quando e chamada com o
    posicional ja resolvido por outra funcao desta mesma bateria de patches
    (ex.: ``salvar_carteira_sqlite`` chama ``inicializar_banco(caminho)``
    internamente)."""

    @functools.wraps(funcao_original)
    def wrapper(caminho=None, *args, **kwargs):
        return funcao_original(caminho if caminho is not None else caminho_fixo, *args, **kwargs)

    return wrapper


class InterfacePrincipalTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        # --- Fotografia do estado real ANTES de qualquer execucao do app ---
        # (isolamento LF-01A: garante que nada nesta classe toca rede/dados reais)
        cls._git_status_antes = _git_status_porcelano()
        cls._hash_csv_antes = _hash_arquivo(CSV_HISTORICO)
        cls._hash_sqlite_antes = _hash_arquivo(SQLITE_V5)
        cls._hash_jogos_salvos_antes = _hash_arquivo(JOGOS_SALVOS_CSV)

        # --- Isolamento hermetico: nenhuma chamada de rede, nenhuma escrita real ---
        tmp_dir = TemporaryDirectory()
        cls.addClassCleanup(tmp_dir.cleanup)
        banco_teste = Path(tmp_dir.name) / "lotofacil_teste.sqlite3"
        jogos_salvos_teste = Path(tmp_dir.name) / "jogos_salvos_teste.csv"

        # Fixture sintetica (nao real) de uma carteira ja salva, so para que
        # a aba "Conferir Jogos" renderize seu estado normal (metricas +
        # tabela) em vez do estado vazio -- concurso 999999 nao existe em
        # nenhuma base real, entao o status permanece PENDENTE de forma
        # deterministica, independente de quantos concursos a base historica
        # real tiver na data em que este teste rodar.
        pd.DataFrame(
            [
                {
                    "DataHora": "2020-01-01T00:00:00-03:00",
                    "Carteira": 1,
                    "Concurso Alvo": 999999,
                    "Perfil": "Diamante",
                    "Dezenas": "01-02-03-04-05-06-07-08-09-10-11-12-13-14-15",
                    "Score": "0.000000",
                    "Soma": 120,
                    "Pares": 8,
                    "Impares": 7,
                    "Status": "PENDENTE",
                    "Acertos": "0",
                }
            ]
        ).to_csv(jogos_salvos_teste, index=False, encoding="utf-8-sig")

        cls._rede_chamadas = mock.Mock(side_effect=_bloquear_rede)
        patches = [
            # Unico ponto de saida HTTP real do modulo (usado por
            # buscar_info_concurso, buscar_info_concurso_atual e
            # baixar_base_oficial_completa/atualizar_base_local) --
            # bloquear aqui cobre toda a cadeia de rede de uma vez.
            mock.patch.object(base_repository, "urlopen", cls._rede_chamadas),
            mock.patch.object(
                historico_sqlite,
                "inicializar_banco",
                _com_caminho_fixo(historico_sqlite.inicializar_banco, banco_teste),
            ),
            mock.patch.object(
                historico_sqlite,
                "migrar_historico_csv",
                functools.partial(historico_sqlite.migrar_historico_csv, caminho=banco_teste),
            ),
            mock.patch.object(
                historico_sqlite,
                "registrar_concurso_visto",
                functools.partial(historico_sqlite.registrar_concurso_visto, caminho=banco_teste),
            ),
            mock.patch.object(
                historico_sqlite,
                "salvar_carteira_sqlite",
                functools.partial(historico_sqlite.salvar_carteira_sqlite, caminho=banco_teste),
            ),
            mock.patch.object(
                historico_sqlite,
                "conferir_historico_sqlite",
                functools.partial(historico_sqlite.conferir_historico_sqlite, caminho=banco_teste),
            ),
            mock.patch.object(
                historico_sqlite,
                "listar_historico_sqlite",
                functools.partial(historico_sqlite.listar_historico_sqlite, caminho=banco_teste),
            ),
            mock.patch.object(
                jogos_salvos,
                "ler_jogos_salvos",
                _com_caminho_fixo(jogos_salvos.ler_jogos_salvos, jogos_salvos_teste),
            ),
            mock.patch.object(
                jogos_salvos,
                "salvar_carteira",
                functools.partial(jogos_salvos.salvar_carteira, caminho=jogos_salvos_teste),
            ),
            mock.patch.object(
                jogos_salvos,
                "conferir_jogos_salvos",
                functools.partial(jogos_salvos.conferir_jogos_salvos, caminho=jogos_salvos_teste),
            ),
            mock.patch.object(
                jogos_salvos,
                "historico_desempenho_carteiras",
                functools.partial(jogos_salvos.historico_desempenho_carteiras, caminho=jogos_salvos_teste),
            ),
        ]
        for patcher in patches:
            patcher.start()
            cls.addClassCleanup(patcher.stop)

        cls.app = AppTest.from_file("app.py").run(timeout=60)
        cls.html = "\n".join(element.value for element in cls.app.markdown)

    @classmethod
    def tearDownClass(cls) -> None:
        # Guarda de regressao (roda apos TODOS os testes desta classe,
        # independente da ordem de execucao dos metodos): se qualquer
        # execucao da interface tiver vazado para rede/dados reais, a
        # classe inteira falha aqui.
        cls._verificar_nenhum_efeito_colateral_real()
        super().tearDownClass()

    @classmethod
    def _verificar_nenhum_efeito_colateral_real(cls) -> None:
        assert _hash_arquivo(CSV_HISTORICO) == cls._hash_csv_antes, (
            "dados/lotofacil_historico.csv foi alterado durante os testes de interface "
            "-- vazamento de escrita real (isolamento LF-01A quebrado)."
        )
        assert _hash_arquivo(SQLITE_V5) == cls._hash_sqlite_antes, (
            "dados/lotofacil_v5.sqlite3 foi alterado durante os testes de interface "
            "-- vazamento de escrita real (isolamento LF-01A quebrado)."
        )
        assert _hash_arquivo(JOGOS_SALVOS_CSV) == cls._hash_jogos_salvos_antes, (
            "exports/jogos_salvos_lotofacil.csv foi alterado durante os testes de interface "
            "-- vazamento de escrita real (isolamento LF-01A quebrado)."
        )
        status_depois = _git_status_porcelano()
        if cls._git_status_antes is not None and status_depois is not None:
            assert status_depois == cls._git_status_antes, (
                "git status mudou durante os testes de interface -- algum arquivo "
                f"rastreado foi alterado (isolamento LF-01A quebrado):\n{status_depois}"
            )

    def test_renderiza_cinco_cards_e_75_bolas(self) -> None:
        self.assertFalse(self.app.exception)
        self.assertEqual(self.html.count('class="elite-game-card"'), 5)
        # Escopo estrutural: `class="elite-ball"` e `class="elite-balls"` sao
        # reutilizadas por componentes independentes da pagina (ex.: Trend
        # Hybrid 9+6, renderizado na mesma execucao porque st.tabs desenha
        # todas as abas de uma vez) -- contar no HTML inteiro conta bolas de
        # fora dos 5 cards oficiais. `montar_html_jogos(jogos)` (app.py) e
        # emitido em um unico `st.markdown` que devolve exatamente
        # `<section class="elite-results">` com os 5 `elite-game-card` e
        # nada mais, entao isolar esse elemento isola os cards oficiais de
        # qualquer outro componente da pagina, hoje ou no futuro.
        cards_oficiais = [
            elemento.value
            for elemento in self.app.markdown
            if 'class="elite-results"' in elemento.value
        ]
        self.assertEqual(
            len(cards_oficiais),
            1,
            "Esperava exatamente um bloco `elite-results` (os 5 cards oficiais) "
            "na pagina; a estrutura de montar_html_jogos() pode ter mudado.",
        )
        html_cards_oficiais = cards_oficiais[0]
        self.assertEqual(html_cards_oficiais.count('class="elite-game-card"'), 5)
        self.assertEqual(html_cards_oficiais.count('class="elite-ball"'), 75)
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

        tabela = next(
            tabela.value
            for tabela in self.app.dataframe
            if "Concurso Alvo" in tabela.value.columns
        )
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
        self.assertIn("GERAR / ATUALIZAR CARTEIRA", labels)
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
        pos_botao = trecho.index("GERAR / ATUALIZAR CARTEIRA")
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

    def test_zzz_isolamento_nao_deixa_efeitos_colaterais_reais(self) -> None:
        """Guarda de regressao explicita (LF-01A): falha se a execucao da
        interface (setUpClass + qualquer teste desta classe) tiver, em
        algum momento, tentado rede real ou alterado CSV/SQLite/exports
        reais. Nomeada para rodar por ultimo (ordem alfabetica) e reforcada
        por tearDownClass, que roda de qualquer forma apos todos os
        metodos, independente de ordenacao."""
        self.assertGreaterEqual(
            self._rede_chamadas.call_count,
            1,
            "O mock de rede nunca foi chamado -- a app pode ter parado de tentar "
            "sincronizar com a CAIXA, o que tornaria esta guarda incapaz de provar "
            "que uma tentativa real seria interceptada. Revise o isolamento.",
        )
        self._verificar_nenhum_efeito_colateral_real()


if __name__ == "__main__":
    unittest.main()
