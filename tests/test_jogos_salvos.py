from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import pandas as pd

from src.carregar_dados import CAMINHO_BASE_PADRAO, COLUNAS_DEZENAS, carregar_base
from src.jogos_salvos import (
    COLUNAS_JOGOS_SALVOS,
    conferir_jogos_salvos,
    ler_jogos_salvos,
    normalizar_colunas_jogos_salvos,
    salvar_carteira,
)
from src.motor_elite_lotofacil import gerar_jogos_producao_v1


class JogosSalvosTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.base = carregar_base(CAMINHO_BASE_PADRAO)
        cls.jogos = gerar_jogos_producao_v1(cls.base, semente=987654)

    def test_salva_cinco_registros_no_esquema_padrao(self) -> None:
        with TemporaryDirectory() as pasta:
            caminho = Path(pasta) / "jogos.csv"
            salvar_carteira(
                self.jogos,
                numero_carteira=7,
                concurso_alvo=999999,
                caminho=caminho,
                data_hora=datetime(2026, 6, 12, 12, 30, tzinfo=timezone.utc),
            )
            salvos = ler_jogos_salvos(caminho)
            self.assertEqual(salvos.columns.tolist(), COLUNAS_JOGOS_SALVOS)
            self.assertEqual(len(salvos), 5)
            self.assertEqual(set(salvos["Status"]), {"PENDENTE"})
            self.assertTrue((salvos["Acertos"] == "0").all())
            self.assertTrue(all(len(valor.split("-")) == 15 for valor in salvos["Dezenas"]))
            self.assertTrue(all(" " not in valor for valor in salvos["Dezenas"]))

    def test_conferencia_mantem_concurso_futuro_pendente(self) -> None:
        with TemporaryDirectory() as pasta:
            caminho = Path(pasta) / "jogos.csv"
            salvar_carteira(self.jogos, 1, 999999, caminho)
            conferidos = conferir_jogos_salvos(self.base, caminho)
            self.assertEqual(set(conferidos["Status"]), {"PENDENTE"})
            self.assertTrue((conferidos["Acertos"] == "0").all())

    def test_conferencia_calcula_acertos_para_concurso_existente(self) -> None:
        with TemporaryDirectory() as pasta:
            caminho = Path(pasta) / "jogos.csv"
            concurso = int(self.base.iloc[-1]["Concurso"])
            salvar_carteira(self.jogos, 2, concurso, caminho)
            conferidos = conferir_jogos_salvos(self.base, caminho)
            sorteadas = {int(self.base.iloc[-1][coluna]) for coluna in COLUNAS_DEZENAS}
            for _, row in conferidos.iterrows():
                geradas = {int(item) for item in row["Dezenas"].split("-")}
                self.assertEqual(row["Status"], "CONFERIDO")
                self.assertEqual(int(row["Acertos"]), len(geradas & sorteadas))

    def test_csv_legado_e_migrado_automaticamente(self) -> None:
        colunas_legadas = ["Status" + " de Conferência", "Status" + " Conferencia"]
        for posicao, coluna_legada in enumerate(colunas_legadas):
            with self.subTest(coluna_legada=coluna_legada), TemporaryDirectory() as pasta:
                caminho = Path(pasta) / f"legado_{posicao}.csv"
                pd.DataFrame(
                    [
                        {
                            "Data/Hora da Geracao": "2026-06-12T10:00:00-03:00",
                            "Numero da Carteira": "4",
                            "Concurso Alvo": "999999",
                            "Perfil": "Diamante",
                            "Dezenas Geradas": "01 02 03 04 05 06 07 08 09 10 11 12 13 14 15",
                            "Score": "100.0",
                            "Soma": "120",
                            "Pares": "7",
                            "Impares": "8",
                            coluna_legada: "",
                        }
                    ]
                ).to_csv(caminho, index=False, encoding="utf-8-sig")

                migrados = conferir_jogos_salvos(self.base, caminho)
                self.assertEqual(migrados.columns.tolist(), COLUNAS_JOGOS_SALVOS)
                self.assertEqual(migrados.loc[0, "Carteira"], "4")
                self.assertEqual(migrados.loc[0, "Dezenas"].split("-")[0], "01")
                self.assertEqual(migrados.loc[0, "Status"], "PENDENTE")
                self.assertEqual(migrados.loc[0, "Acertos"], "0")
                self.assertEqual(pd.read_csv(caminho, encoding="utf-8-sig").columns.tolist(), COLUNAS_JOGOS_SALVOS)

    def test_csv_sem_status_ou_acertos_recebe_padrao(self) -> None:
        with TemporaryDirectory() as pasta:
            caminho = Path(pasta) / "incompleto.csv"
            pd.DataFrame([{"Concurso Alvo": "999999", "Perfil": "Ouro", "Dezenas": "01 02 03"}]).to_csv(
                caminho, index=False, encoding="utf-8-sig"
            )
            salvos = ler_jogos_salvos(caminho)
            self.assertEqual(salvos.loc[0, "Status"], "PENDENTE")
            self.assertEqual(salvos.loc[0, "Acertos"], "0")

    def test_normalizacao_defensiva_cria_colunas_da_conferencia(self) -> None:
        cenarios = [
            pd.DataFrame([{"Perfil": "Diamante"}]),
            pd.DataFrame([{"Perfil": "Ouro", "Status": "PENDENTE"}]),
            pd.DataFrame([{"Perfil": "Prata", "Acertos": "0"}]),
        ]
        for dados in cenarios:
            with self.subTest(colunas=dados.columns.tolist()):
                normalizados = normalizar_colunas_jogos_salvos(dados)
                self.assertEqual(normalizados.columns.tolist(), COLUNAS_JOGOS_SALVOS)
                self.assertEqual(normalizados.loc[0, "Status"], "PENDENTE")
                self.assertEqual(normalizados.loc[0, "Acertos"], "0")

    def test_csv_vazio_ou_inexistente_retorna_esquema_completo(self) -> None:
        with TemporaryDirectory() as pasta:
            inexistente = Path(pasta) / "inexistente.csv"
            vazio = Path(pasta) / "vazio.csv"
            vazio.touch()
            for caminho in (inexistente, vazio):
                with self.subTest(caminho=caminho.name):
                    salvos = ler_jogos_salvos(caminho)
                    self.assertTrue(salvos.empty)
                    self.assertEqual(salvos.columns.tolist(), COLUNAS_JOGOS_SALVOS)


if __name__ == "__main__":
    unittest.main()
