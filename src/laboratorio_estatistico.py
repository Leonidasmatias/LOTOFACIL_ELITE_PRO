from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import random

import pandas as pd

from .carregar_dados import COLUNAS_DEZENAS, RAIZ_PROJETO
from .comparador_aleatorio import gerar_carteira_aleatoria
from .motor_elite_v2 import gerar_jogos_v2, ranking_dezenas_v2
from .validacao_jogos import ConfiguracaoMotor, sequencia_maxima, validar_carteira, validar_jogo


ESTRATEGIAS_LABORATORIO = ["Motor Elite", "Aleatório puro", "Dezenas quentes", "Dezenas frias", "Híbrido quente/frio"]
CAMINHO_HISTORICO_LABORATORIO = RAIZ_PROJETO / "exports" / "historico_laboratorio_v4.csv"
COLUNAS_HISTORICO_LABORATORIO = ["Data/hora", "Estratégia", "Concursos avaliados", "Quantidade de jogos", "Melhor acerto", "Média", "ROI (%)", "Status"]


@dataclass
class ResultadoLaboratorio:
    detalhes_carteiras: pd.DataFrame
    detalhes_jogos: pd.DataFrame
    resumo: pd.DataFrame
    melhores_metricas: dict[str, str]
    padroes: pd.DataFrame

    def csv_bytes(self) -> bytes:
        return self.detalhes_carteiras.to_csv(index=False).encode("utf-8-sig")


def _amostra_ponderada(rng: random.Random, pesos: dict[int, float]) -> tuple[int, ...]:
    disponiveis = list(range(1, 26))
    escolhidas = []
    for _ in range(15):
        dezena = rng.choices(disponiveis, weights=[max(0.01, pesos[d]) for d in disponiveis], k=1)[0]
        escolhidas.append(dezena)
        disponiveis.remove(dezena)
    return tuple(sorted(escolhidas))


def _carteira_por_pesos(
    df: pd.DataFrame,
    quantidade: int,
    configuracao: ConfiguracaoMotor,
    pesos: dict[int, float],
    semente: int,
    hibrido: bool = False,
) -> list[tuple[int, ...]]:
    ultimo = {int(valor) for valor in df.sort_values("Concurso").iloc[-1][COLUNAS_DEZENAS]}
    rng = random.Random(semente)
    carteira: list[tuple[int, ...]] = []
    ranking = sorted(range(1, 26), key=lambda d: (-pesos[d], d))
    quentes, frias = ranking[:12], ranking[12:]
    tentativas = 0
    while len(carteira) < quantidade and tentativas < quantidade * 12000:
        tentativas += 1
        if hibrido:
            jogo = tuple(sorted(rng.sample(quentes, 8) + rng.sample(frias, 7)))
        else:
            jogo = _amostra_ponderada(rng, pesos)
        try:
            validar_jogo(jogo, configuracao, ultimo)
        except ValueError:
            continue
        if jogo in carteira or any(len(set(jogo) - set(outro)) < configuracao.diferenca_minima_entre_jogos for outro in carteira):
            continue
        carteira.append(jogo)
    if len(carteira) != quantidade:
        raise ValueError("A estratégia não formou uma carteira diversa com a configuração atual.")
    validar_carteira(carteira, configuracao, ultimo)
    return carteira


def gerar_carteira_estrategia(
    df: pd.DataFrame,
    estrategia: str,
    quantidade: int,
    configuracao: ConfiguracaoMotor | None = None,
    semente: int | None = None,
) -> list[tuple[int, ...]]:
    if estrategia not in ESTRATEGIAS_LABORATORIO:
        raise ValueError(f"Estratégia desconhecida: {estrategia}")
    config = configuracao or ConfiguracaoMotor()
    seed = int(semente or 0)
    if estrategia == "Motor Elite":
        jogos = gerar_jogos_v2(df, quantidade=quantidade, configuracao=config, semente=seed)
        return [tuple(int(row[f"Bola{i}"]) for i in range(1, 16)) for _, row in jogos.iterrows()]
    if estrategia == "Aleatório puro":
        return gerar_carteira_aleatoria(df, quantidade, config, seed)
    ranking = ranking_dezenas_v2(df, "Diamante").set_index("Dezena")["Score da dezena"].to_dict()
    minimo, maximo = min(ranking.values()), max(ranking.values())
    amplitude = max(maximo - minimo, 1.0)
    quente = {d: 1 + ((ranking[d] - minimo) / amplitude) * 10 for d in range(1, 26)}
    frio = {d: 1 + ((maximo - ranking[d]) / amplitude) * 10 for d in range(1, 26)}
    if estrategia == "Dezenas quentes":
        return _carteira_por_pesos(df, quantidade, config, quente, seed)
    if estrategia == "Dezenas frias":
        return _carteira_por_pesos(df, quantidade, config, frio, seed)
    return _carteira_por_pesos(df, quantidade, config, quente, seed, hibrido=True)


def _assinatura_distribuicao(jogo: tuple[int, ...], eixo: str) -> str:
    contagens = [0] * 5
    for dezena in jogo:
        indice = (dezena - 1) // 5 if eixo == "linha" else (dezena - 1) % 5
        contagens[indice] += 1
    return "-".join(map(str, contagens))


def _metricas_jogo(jogo: tuple[int, ...], ultimo: set[int]) -> dict:
    moldura = {1, 2, 3, 4, 5, 6, 10, 11, 15, 16, 20, 21, 22, 23, 24, 25}
    pares = sum(d % 2 == 0 for d in jogo)
    quantidade_moldura = len(set(jogo) & moldura)
    soma = sum(jogo)
    return {
        "Padrão soma": f"{(soma // 10) * 10}-{(soma // 10) * 10 + 9}",
        "Padrão pares/ímpares": f"{pares}/{15 - pares}",
        "Padrão repetição": str(len(set(jogo) & ultimo)),
        "Padrão moldura/miolo": f"{quantidade_moldura}/{15 - quantidade_moldura}",
        "Padrão sequência": str(sequencia_maxima(jogo)),
        "Padrão linhas": _assinatura_distribuicao(jogo, "linha"),
        "Padrão colunas": _assinatura_distribuicao(jogo, "coluna"),
    }


def descobrir_padroes(detalhes_jogos: pd.DataFrame, amostra_minima: int = 10) -> pd.DataFrame:
    colunas = [coluna for coluna in detalhes_jogos.columns if coluna.startswith("Padrão ")]
    registros = []
    for coluna in colunas:
        for valor, grupo in detalhes_jogos.groupby(coluna):
            amostra = len(grupo)
            if amostra < amostra_minima:
                continue
            registros.append({
                "Dimensão": coluna.replace("Padrão ", ""),
                "Padrão": str(valor),
                "Amostra": amostra,
                "Média de acertos": round(float(grupo["Acertos"].mean()), 4),
                "Taxa 13+": round(float((grupo["Acertos"] >= 13).mean() * 100), 4),
                "Taxa 14+": round(float((grupo["Acertos"] >= 14).mean() * 100), 4),
            })
    if not registros:
        return pd.DataFrame(columns=["Dimensão", "Padrão", "Amostra", "Média de acertos", "Taxa 13+", "Taxa 14+"])
    return pd.DataFrame(registros).sort_values(["Taxa 14+", "Taxa 13+", "Amostra"], ascending=[False, False, False]).reset_index(drop=True)


def executar_laboratorio(
    df: pd.DataFrame,
    quantidade_concursos: int = 20,
    quantidade_jogos: int = 5,
    configuracao: ConfiguracaoMotor | None = None,
    amostra_minima_padrao: int = 10,
) -> ResultadoLaboratorio:
    dados = df.sort_values("Concurso").reset_index(drop=True)
    historico_minimo = min(100, max(1, len(dados) - 1))
    if len(dados) <= historico_minimo:
        raise ValueError("Base insuficiente para o laboratório temporal.")
    inicio = max(historico_minimo, len(dados) - max(1, int(quantidade_concursos)))
    original = configuracao or ConfiguracaoMotor()
    config = ConfiguracaoMotor(**{**original.__dict__, "candidatos_por_perfil": min(180, original.candidatos_por_perfil)})
    carteiras, jogos_detalhados = [], []
    for indice in range(inicio, len(dados)):
        treino = dados.iloc[:indice].copy()
        alvo = dados.iloc[indice]
        concurso = int(alvo["Concurso"])
        sorteadas = {int(alvo[coluna]) for coluna in COLUNAS_DEZENAS}
        ultimo = {int(treino.iloc[-1][coluna]) for coluna in COLUNAS_DEZENAS}
        for posicao, estrategia in enumerate(ESTRATEGIAS_LABORATORIO):
            carteira = gerar_carteira_estrategia(treino, estrategia, quantidade_jogos, config, concurso + posicao * 1_000_000)
            acertos = []
            for numero, jogo in enumerate(carteira, 1):
                pontos = len(set(jogo) & sorteadas)
                acertos.append(pontos)
                jogos_detalhados.append({"Concurso": concurso, "Estratégia": estrategia, "Jogo": numero, "Acertos": pontos, "Dezenas": "-".join(f"{d:02d}" for d in jogo), **_metricas_jogo(jogo, ultimo)})
            carteiras.append({
                "Concurso": concurso,
                "Estratégia": estrategia,
                "Quantidade de jogos": quantidade_jogos,
                "Melhor acerto": max(acertos),
                "Média de acertos": round(sum(acertos) / len(acertos), 4),
                **{f"Jogos {faixa}+": sum(valor >= faixa for valor in acertos) for faixa in (11, 12, 13, 14)},
                "Jogos 15": sum(valor == 15 for valor in acertos),
            })
    detalhes_carteiras = pd.DataFrame(carteiras)
    detalhes_jogos = pd.DataFrame(jogos_detalhados)
    resumo_linhas = []
    for estrategia, grupo in detalhes_carteiras.groupby("Estratégia", sort=False):
        total = len(grupo)
        linha = {"Estratégia": estrategia, "Concursos": total, "Média do melhor acerto": round(float(grupo["Melhor acerto"].mean()), 4), "Melhor acerto": int(grupo["Melhor acerto"].max())}
        for faixa in (11, 12, 13, 14, 15):
            linha[f"Taxa {faixa}+" if faixa < 15 else "Taxa 15"] = round(float((grupo["Melhor acerto"] >= faixa).mean() * 100), 4) if faixa < 15 else round(float((grupo["Melhor acerto"] == 15).mean() * 100), 4)
        resumo_linhas.append(linha)
    resumo = pd.DataFrame(resumo_linhas)
    metricas = ["Média do melhor acerto", "Melhor acerto", "Taxa 11+", "Taxa 12+", "Taxa 13+", "Taxa 14+", "Taxa 15"]
    melhores = {metrica: str(resumo.sort_values(metrica, ascending=False).iloc[0]["Estratégia"]) for metrica in metricas}
    padroes = descobrir_padroes(detalhes_jogos, amostra_minima_padrao)
    return ResultadoLaboratorio(detalhes_carteiras, detalhes_jogos, resumo, melhores, padroes)


def calcular_roi_simulado(
    detalhes_jogos: pd.DataFrame,
    valor_unitario: float,
    premios_estimados: dict[int, float] | None = None,
) -> pd.DataFrame:
    premios = premios_estimados or {11: 7.0, 12: 14.0, 13: 35.0, 14: 1500.0, 15: 1_500_000.0}
    registros = []
    for estrategia, grupo in detalhes_jogos.groupby("Estratégia", sort=False):
        apostado = len(grupo) * float(valor_unitario)
        retorno = sum(float(premios.get(int(acertos), 0.0)) for acertos in grupo["Acertos"])
        saldo = retorno - apostado
        registros.append({"Estratégia": estrategia, "Jogos simulados": len(grupo), "Total apostado": round(apostado, 2), "Retorno estimado": round(retorno, 2), "Saldo simulado": round(saldo, 2), "ROI (%)": round((saldo / apostado * 100) if apostado else 0.0, 4), "Observação": "Valores estimados, não garantidos."})
    return pd.DataFrame(registros)


def dados_heatmap(df: pd.DataFrame) -> pd.DataFrame:
    ranking = ranking_dezenas_v2(df, "Diamante")
    resultado = ranking[["Dezena", "Frequência histórica", "Últimos 25", "Atraso", "Score da dezena"]].copy()
    resultado = resultado.rename(columns={"Últimos 25": "Frequência recente", "Score da dezena": "Score V3"})
    resultado["Linha"] = ((resultado["Dezena"] - 1) // 5) + 1
    resultado["Coluna"] = ((resultado["Dezena"] - 1) % 5) + 1
    return resultado.sort_values("Dezena").reset_index(drop=True)


def salvar_historico_laboratorio(
    resultado: ResultadoLaboratorio,
    roi: pd.DataFrame,
    quantidade_jogos: int,
    caminho: Path = CAMINHO_HISTORICO_LABORATORIO,
) -> pd.DataFrame:
    agora = datetime.now().astimezone().isoformat(timespec="seconds")
    roi_por_estrategia = roi.set_index("Estratégia")["ROI (%)"].to_dict()
    linhas = []
    for _, registro in resultado.resumo.iterrows():
        linhas.append({"Data/hora": agora, "Estratégia": registro["Estratégia"], "Concursos avaliados": int(registro["Concursos"]), "Quantidade de jogos": int(quantidade_jogos), "Melhor acerto": int(registro["Melhor acerto"]), "Média": float(registro["Média do melhor acerto"]), "ROI (%)": float(roi_por_estrategia.get(registro["Estratégia"], 0.0)), "Status": "CONCLUÍDO"})
    anteriores = ler_historico_laboratorio(caminho)
    atual = pd.concat([anteriores, pd.DataFrame(linhas)], ignore_index=True)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    atual.to_csv(caminho, index=False, encoding="utf-8-sig")
    return ler_historico_laboratorio(caminho)


def ler_historico_laboratorio(caminho: Path = CAMINHO_HISTORICO_LABORATORIO) -> pd.DataFrame:
    if not caminho.exists() or caminho.stat().st_size == 0:
        return pd.DataFrame(columns=COLUNAS_HISTORICO_LABORATORIO)
    dados = pd.read_csv(caminho, encoding="utf-8-sig")
    if "Data" in dados.columns and "Data/hora" not in dados.columns:
        dados = dados.rename(columns={"Data": "Data/hora"})
    for coluna in COLUNAS_HISTORICO_LABORATORIO:
        if coluna not in dados.columns:
            dados[coluna] = ""
    return dados[COLUNAS_HISTORICO_LABORATORIO]
