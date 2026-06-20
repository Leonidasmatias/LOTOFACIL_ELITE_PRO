from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .carregar_dados import COLUNAS_DEZENAS
from .motor_elite_v2 import gerar_jogos_v2
from .validacao_jogos import ConfiguracaoMotor


@dataclass
class ResultadoBacktest:
    detalhes: pd.DataFrame
    resumo_perfis: pd.DataFrame
    melhor_perfil: str

    def csv_bytes(self) -> bytes:
        return self.detalhes.to_csv(index=False).encode("utf-8-sig")

    def exportar_csv(self, caminho: Path) -> Path:
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_bytes(self.csv_bytes())
        return caminho


def _resumir(detalhes: pd.DataFrame) -> pd.DataFrame:
    if detalhes.empty:
        return pd.DataFrame(columns=["Perfil", "Concursos", "Média", "Melhor", "11+", "12+", "13+", "14+", "15"])
    linhas = []
    for perfil, grupo in detalhes.groupby("Perfil", sort=False):
        total = len(grupo)
        linha = {"Perfil": perfil, "Concursos": total, "Média": round(float(grupo["Acertos"].mean()), 4), "Melhor": int(grupo["Acertos"].max())}
        for faixa in (11, 12, 13, 14, 15):
            quantidade = int((grupo["Acertos"] >= faixa).sum())
            rotulo = f"{faixa}+" if faixa < 15 else "15"
            linha[rotulo] = round(quantidade / total * 100, 4) if faixa < 15 else round(int((grupo["Acertos"] == 15).sum()) / total * 100, 4)
            linha[f"Qtd {rotulo}"] = quantidade if faixa < 15 else int((grupo["Acertos"] == 15).sum())
        linhas.append(linha)
    return pd.DataFrame(linhas).sort_values(["Média", "Melhor", "13+"], ascending=[False, False, False]).reset_index(drop=True)


def executar_backtest(
    df: pd.DataFrame,
    quantidade_concursos: int = 100,
    historico_minimo: int = 100,
    configuracao: ConfiguracaoMotor | None = None,
    candidatos_por_perfil: int = 250,
) -> ResultadoBacktest:
    dados = df.sort_values("Concurso").reset_index(drop=True)
    if len(dados) <= historico_minimo:
        raise ValueError("Base insuficiente para o backtest solicitado.")
    inicio = max(historico_minimo, len(dados) - max(1, int(quantidade_concursos)))
    config_original = configuracao or ConfiguracaoMotor()
    config = ConfiguracaoMotor(**{**config_original.__dict__, "candidatos_por_perfil": max(50, int(candidatos_por_perfil))})
    registros = []
    for indice in range(inicio, len(dados)):
        treino = dados.iloc[:indice].copy()
        alvo = dados.iloc[indice]
        sorteadas = {int(alvo[coluna]) for coluna in COLUNAS_DEZENAS}
        jogos = gerar_jogos_v2(treino, configuracao=config, semente=int(alvo["Concurso"]))
        for _, jogo in jogos.iterrows():
            dezenas = {int(jogo[f"Bola{i}"]) for i in range(1, 16)}
            registros.append({
                "Concurso": int(alvo["Concurso"]),
                "Data": str(alvo["Data"]),
                "Perfil": str(jogo["Perfil"]),
                "Acertos": len(dezenas & sorteadas),
                "Score": float(jogo["Score"]),
                "Dezenas": "-".join(f"{d:02d}" for d in sorted(dezenas)),
            })
    detalhes = pd.DataFrame(registros)
    resumo = _resumir(detalhes)
    melhor = str(resumo.iloc[0]["Perfil"]) if not resumo.empty else "Sem resultado"
    return ResultadoBacktest(detalhes=detalhes, resumo_perfis=resumo, melhor_perfil=melhor)
