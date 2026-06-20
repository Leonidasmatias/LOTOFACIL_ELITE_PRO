from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .carregar_dados import COLUNAS_DEZENAS
from .motor_elite_v2 import gerar_jogos_v2
from .comparador_aleatorio import desempenho_carteira, gerar_carteira_aleatoria
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


@dataclass
class ResultadoComparativo:
    detalhes: pd.DataFrame
    resumo: pd.DataFrame
    resumo_perfis: pd.DataFrame
    melhor_carteira: dict

    def csv_bytes(self) -> bytes:
        return self.detalhes.to_csv(index=False).encode("utf-8-sig")


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
    quantidade_jogos: int = 5,
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
        jogos = gerar_jogos_v2(treino, quantidade=quantidade_jogos, configuracao=config, semente=int(alvo["Concurso"]))
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


def executar_backtest_comparativo(
    df: pd.DataFrame,
    quantidade_concursos: int = 50,
    quantidade_jogos: int = 5,
    historico_minimo: int = 100,
    configuracao: ConfiguracaoMotor | None = None,
    candidatos_por_perfil: int = 180,
) -> ResultadoComparativo:
    if quantidade_jogos not in {5, 10, 20, 30}:
        raise ValueError("Selecione 5, 10, 20 ou 30 jogos.")
    dados = df.sort_values("Concurso").reset_index(drop=True)
    if len(dados) <= historico_minimo:
        raise ValueError("Base insuficiente para o backtest comparativo.")
    inicio = max(historico_minimo, len(dados) - max(1, int(quantidade_concursos)))
    original = configuracao or ConfiguracaoMotor()
    config = ConfiguracaoMotor(**{**original.__dict__, "candidatos_por_perfil": max(50, int(candidatos_por_perfil))})
    registros = []
    registros_perfis = []
    melhor_carteira: dict = {}
    for indice in range(inicio, len(dados)):
        treino = dados.iloc[:indice].copy()
        alvo = dados.iloc[indice]
        concurso = int(alvo["Concurso"])
        sorteadas = {int(alvo[coluna]) for coluna in COLUNAS_DEZENAS}
        elite_df = gerar_jogos_v2(treino, quantidade=quantidade_jogos, configuracao=config, semente=concurso)
        elite = [tuple(int(row[f"Bola{i}"]) for i in range(1, 16)) for _, row in elite_df.iterrows()]
        for _, jogo in elite_df.iterrows():
            dezenas = {int(jogo[f"Bola{i}"]) for i in range(1, 16)}
            registros_perfis.append({"Concurso": concurso, "Perfil": str(jogo["Perfil"]), "Acertos": len(dezenas & sorteadas), "Score": float(jogo["Score"])})
        aleatoria = gerar_carteira_aleatoria(treino, quantidade_jogos, config, semente=concurso + 10_000_000)
        for motor, carteira in (("Motor Elite", elite), ("Aleatório", aleatoria)):
            metricas = desempenho_carteira(carteira, sorteadas)
            registro = {"Concurso": concurso, "Motor": motor, "Quantidade de jogos": quantidade_jogos, **metricas}
            registros.append(registro)
            if not melhor_carteira or registro["Melhor acerto"] > melhor_carteira["Melhor acerto"]:
                melhor_carteira = registro.copy()
    detalhes = pd.DataFrame(registros)
    resumo_linhas = []
    for motor, grupo in detalhes.groupby("Motor", sort=False):
        total = len(grupo)
        linha = {
            "Motor": motor,
            "Concursos": total,
            "Média do melhor acerto": round(float(grupo["Melhor acerto"].mean()), 4),
            "Melhor carteira": int(grupo["Melhor acerto"].max()),
        }
        for faixa in (11, 12, 13, 14, 15):
            coluna = f"Taxa {faixa}+" if faixa < 15 else "Taxa 15"
            linha[coluna] = round(float((grupo["Melhor acerto"] >= faixa).mean() * 100), 4) if faixa < 15 else round(float((grupo["Melhor acerto"] == 15).mean() * 100), 4)
        resumo_linhas.append(linha)
    resumo = pd.DataFrame(resumo_linhas)
    if len(resumo) == 2:
        elite = resumo.loc[resumo["Motor"] == "Motor Elite"].iloc[0]
        aleatorio = resumo.loc[resumo["Motor"] == "Aleatório"].iloc[0]
        for faixa in (11, 12, 13, 14, 15):
            coluna = f"Taxa {faixa}+" if faixa < 15 else "Taxa 15"
            vantagem = round(float(elite[coluna] - aleatorio[coluna]), 4)
            resumo.loc[resumo["Motor"] == "Motor Elite", f"Vantagem {faixa}"] = vantagem
            resumo.loc[resumo["Motor"] == "Aleatório", f"Vantagem {faixa}"] = -vantagem
    return ResultadoComparativo(detalhes=detalhes, resumo=resumo, resumo_perfis=_resumir(pd.DataFrame(registros_perfis)), melhor_carteira=melhor_carteira)
