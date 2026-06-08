from __future__ import annotations

from collections import Counter, deque
from datetime import datetime
from pathlib import Path
import random

import pandas as pd


RAIZ = Path(__file__).resolve().parents[1]
CAMINHO_BASE = RAIZ / "dados" / "lotofacil_historico.csv"
PASTA_EXPORTS = RAIZ / "exports"
COLUNAS_DEZENAS = [f"Bola{i}" for i in range(1, 16)]
TODAS_DEZENAS = list(range(1, 26))
MOLDURA = {1, 2, 3, 4, 5, 6, 10, 11, 15, 16, 20, 21, 22, 23, 24, 25}
CENTRO = set(TODAS_DEZENAS) - MOLDURA
JOGOS_POR_CONCURSO_POR_MOTOR = 1


def carregar_base() -> pd.DataFrame:
    df = pd.read_csv(CAMINHO_BASE, encoding="utf-8-sig")
    colunas = ["Concurso", "Data", *COLUNAS_DEZENAS]
    faltantes = [c for c in colunas if c not in df.columns]
    if faltantes:
        raise ValueError(f"Base Lotofacil sem colunas obrigatorias: {faltantes}")
    df = df[colunas].copy()
    df["Concurso"] = pd.to_numeric(df["Concurso"], errors="coerce").astype("Int64")
    for coluna in COLUNAS_DEZENAS:
        df[coluna] = pd.to_numeric(df[coluna], errors="coerce").astype("Int64")
    df = df.dropna(subset=["Concurso", *COLUNAS_DEZENAS]).copy()
    for coluna in ["Concurso", *COLUNAS_DEZENAS]:
        df[coluna] = df[coluna].astype(int)
    return df.sort_values("Concurso").reset_index(drop=True)


def pares_impares(jogo: list[int]) -> tuple[int, int]:
    pares = sum(1 for d in jogo if d % 2 == 0)
    return pares, len(jogo) - pares


def centro_moldura(jogo: list[int]) -> tuple[int, int]:
    centro = sum(1 for d in jogo if d in CENTRO)
    moldura = sum(1 for d in jogo if d in MOLDURA)
    return centro, moldura


def distribuicao_linhas_colunas(jogo: list[int]) -> tuple[Counter, Counter]:
    linhas = Counter()
    colunas = Counter()
    for dezena in jogo:
        linhas[((dezena - 1) // 5) + 1] += 1
        colunas[((dezena - 1) % 5) + 1] += 1
    return linhas, colunas


def score_jogo(jogo: list[int], score_dezenas: dict[int, float]) -> float:
    score = sum(score_dezenas.get(dezena, 0.0) for dezena in jogo)
    pares, _ = pares_impares(jogo)
    centro, _ = centro_moldura(jogo)
    linhas, colunas = distribuicao_linhas_colunas(jogo)
    penalidade = 0.0
    if not (6 <= pares <= 9):
        penalidade += 10.0
    if not (4 <= centro <= 7):
        penalidade += 8.0
    if max(linhas.values()) > 5:
        penalidade += 6.0
    if max(colunas.values()) > 5:
        penalidade += 6.0
    return round(score - penalidade, 4)


def gerar_jogo_elite(
    concurso_alvo: int,
    frequencia_geral: Counter,
    frequencia_20: Counter,
    ultimo_concurso_por_dezena: dict[int, int],
) -> tuple[list[int], float]:
    score_dezenas = {}
    for dezena in TODAS_DEZENAS:
        atraso = concurso_alvo - ultimo_concurso_por_dezena.get(dezena, 0)
        score_dezenas[dezena] = (
            frequencia_geral[dezena] * 0.45
            + frequencia_20[dezena] * 1.80
            + atraso * 0.25
        )
    top20 = sorted(TODAS_DEZENAS, key=lambda d: (-score_dezenas[d], d))[:20]
    rng = random.Random(910000 + concurso_alvo)
    candidatos = []
    candidato_base = sorted(top20[:15])
    candidatos.append(candidato_base)
    for _ in range(120):
        candidatos.append(sorted(rng.sample(top20, 15)))
    melhor = max(candidatos, key=lambda jogo: score_jogo(jogo, score_dezenas))
    return melhor, score_jogo(melhor, score_dezenas)


def gerar_jogo_aleatorio(concurso_alvo: int) -> list[int]:
    return sorted(random.Random(220000 + concurso_alvo).sample(TODAS_DEZENAS, 15))


def registrar_linha(concurso: int, data: str, motor: str, jogo: list[int], sorteadas: set[int], score: float) -> dict:
    acertos = len(set(jogo) & sorteadas)
    linha = {
        "Concurso": concurso,
        "Data": data,
        "Motor": motor,
        "Jogo": " - ".join(f"{d:02d}" for d in jogo),
        "Acertos": acertos,
        "Elite Score": score,
    }
    for ponto in range(11, 16):
        linha[f"Fez {ponto} pontos"] = int(acertos == ponto)
    return linha


def resumir(detalhe: pd.DataFrame) -> pd.DataFrame:
    linhas = []
    for motor, grupo in detalhe.groupby("Motor"):
        total = int(len(grupo))
        melhor_acerto = int(grupo["Acertos"].max())
        melhor = grupo.sort_values(["Acertos", "Elite Score"], ascending=[False, False]).iloc[0]
        linha = {
            "Motor": motor,
            "Jogos por concurso": JOGOS_POR_CONCURSO_POR_MOTOR,
            "Total de jogos auditados": total,
            "Melhor acerto": melhor_acerto,
            "Concurso do melhor resultado": int(melhor["Concurso"]),
            "Melhor jogo encontrado": melhor["Jogo"],
        }
        for ponto in range(11, 16):
            quantidade = int((grupo["Acertos"] == ponto).sum())
            linha[f"Jogos com {ponto} pontos"] = quantidade
            linha[f"Taxa {ponto} pontos (%)"] = round((quantidade / total) * 100, 4) if total else 0.0
        linhas.append(linha)
    return pd.DataFrame(linhas).sort_values("Motor").reset_index(drop=True)


def gerar_relatorio(df: pd.DataFrame, detalhe: pd.DataFrame, resumo: pd.DataFrame) -> str:
    elite = resumo[resumo["Motor"] == "Motor Elite Lotofacil"].iloc[0].to_dict()
    aleatorio = resumo[resumo["Motor"] == "Aleatorio"].iloc[0].to_dict()
    comparacao_13 = elite["Jogos com 13 pontos"] - aleatorio["Jogos com 13 pontos"]
    comparacao_14 = elite["Jogos com 14 pontos"] - aleatorio["Jogos com 14 pontos"]
    comparacao_15 = elite["Jogos com 15 pontos"] - aleatorio["Jogos com 15 pontos"]
    conclusao = (
        "Motor Elite apresentou vantagem sobre aleatorio nas faixas altas."
        if (comparacao_13 + comparacao_14 + comparacao_15) > 0
        else "Motor Elite nao superou o aleatorio nas faixas altas neste backtest inicial."
    )
    linhas = [
        "# BACKTEST LOTOFACIL ELITE PRO V1",
        "",
        f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Base",
        "",
        f"- Arquivo: `{CAMINHO_BASE}`",
        f"- Total de concursos na base: {len(df)}",
        f"- Menor concurso: {int(df['Concurso'].min())}",
        f"- Maior concurso: {int(df['Concurso'].max())}",
        "",
        "## Configuracao",
        "",
        f"- Jogos gerados por concurso por motor: {JOGOS_POR_CONCURSO_POR_MOTOR}",
        f"- Total de jogos auditados por motor: {int(elite['Total de jogos auditados'])}",
        f"- Motores auditados: Motor Elite Lotofacil e Aleatorio",
        "",
        "## Resultado Motor Elite Lotofacil",
        "",
        f"- Melhor acerto: {elite['Melhor acerto']}",
        f"- Concurso do melhor resultado: {elite['Concurso do melhor resultado']}",
        f"- Melhor jogo encontrado: {elite['Melhor jogo encontrado']}",
    ]
    for ponto in range(11, 16):
        linhas.append(f"- Jogos com {ponto} pontos: {elite[f'Jogos com {ponto} pontos']} ({elite[f'Taxa {ponto} pontos (%)']}%)")
    linhas += [
        "",
        "## Comparacao com aleatorio",
        "",
        f"- Melhor acerto aleatorio: {aleatorio['Melhor acerto']}",
        f"- Jogos aleatorios com 13 pontos: {aleatorio['Jogos com 13 pontos']}",
        f"- Jogos aleatorios com 14 pontos: {aleatorio['Jogos com 14 pontos']}",
        f"- Jogos aleatorios com 15 pontos: {aleatorio['Jogos com 15 pontos']}",
        f"- Diferenca Elite vs aleatorio em 13 pontos: {comparacao_13}",
        f"- Diferenca Elite vs aleatorio em 14 pontos: {comparacao_14}",
        f"- Diferenca Elite vs aleatorio em 15 pontos: {comparacao_15}",
        "",
        "## Conclusao",
        "",
        conclusao,
        "",
        "## Arquivos gerados",
        "",
        "- `exports/backtest_lotofacil_v1.csv`",
        "- `exports/resumo_backtest_lotofacil_v1.csv`",
        "- `exports/BACKTEST_LOTOFACIL_ELITE_PRO_V1.md`",
    ]
    return "\n".join(linhas)


def executar_backtest() -> tuple[pd.DataFrame, pd.DataFrame]:
    df = carregar_base()
    frequencia_geral = Counter()
    janela_20: deque[list[int]] = deque(maxlen=20)
    frequencia_20 = Counter()
    ultimo_concurso_por_dezena = {dezena: 0 for dezena in TODAS_DEZENAS}
    registros = []

    for indice, row in df.iterrows():
        concurso = int(row["Concurso"])
        sorteadas = [int(row[col]) for col in COLUNAS_DEZENAS]
        if indice > 0:
            sorteadas_set = set(sorteadas)
            jogo_elite, score_elite = gerar_jogo_elite(concurso, frequencia_geral, frequencia_20, ultimo_concurso_por_dezena)
            registros.append(registrar_linha(concurso, row["Data"], "Motor Elite Lotofacil", jogo_elite, sorteadas_set, score_elite))
            jogo_random = gerar_jogo_aleatorio(concurso)
            registros.append(registrar_linha(concurso, row["Data"], "Aleatorio", jogo_random, sorteadas_set, 0.0))

        for dezena in sorteadas:
            frequencia_geral[dezena] += 1
            ultimo_concurso_por_dezena[dezena] = concurso
        if len(janela_20) == janela_20.maxlen:
            for dezena in janela_20[0]:
                frequencia_20[dezena] -= 1
        janela_20.append(sorteadas)
        for dezena in sorteadas:
            frequencia_20[dezena] += 1

    detalhe = pd.DataFrame(registros)
    resumo = resumir(detalhe)
    return detalhe, resumo


def main() -> None:
    PASTA_EXPORTS.mkdir(parents=True, exist_ok=True)
    df = carregar_base()
    detalhe, resumo = executar_backtest()
    detalhe.to_csv(PASTA_EXPORTS / "backtest_lotofacil_v1.csv", index=False, encoding="utf-8-sig")
    resumo.to_csv(PASTA_EXPORTS / "resumo_backtest_lotofacil_v1.csv", index=False, encoding="utf-8-sig")
    (PASTA_EXPORTS / "BACKTEST_LOTOFACIL_ELITE_PRO_V1.md").write_text(
        gerar_relatorio(df, detalhe, resumo),
        encoding="utf-8",
    )
    print("BACKTEST_OK")
    print(resumo.to_string(index=False))


if __name__ == "__main__":
    main()
