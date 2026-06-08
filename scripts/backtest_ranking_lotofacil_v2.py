from __future__ import annotations

from collections import Counter, deque
from datetime import datetime
from heapq import heappush, heapreplace
from itertools import combinations
from pathlib import Path
import random

import pandas as pd


RAIZ = Path(__file__).resolve().parents[1]
CAMINHO_BASE = RAIZ / "dados" / "lotofacil_historico.csv"
PASTA_EXPORTS = RAIZ / "exports"
CAMINHO_RESUMO_V1 = PASTA_EXPORTS / "resumo_backtest_lotofacil_v1.csv"

COLUNAS_DEZENAS = [f"Bola{i}" for i in range(1, 16)]
TODAS_DEZENAS = list(range(1, 26))
MOLDURA = {1, 2, 3, 4, 5, 6, 10, 11, 15, 16, 20, 21, 22, 23, 24, 25}
CENTRO = set(TODAS_DEZENAS) - MOLDURA
LIMITES_TOP = (1, 5, 10)


def carregar_base() -> pd.DataFrame:
    df = pd.read_csv(CAMINHO_BASE, encoding="utf-8-sig")
    df = df[["Concurso", "Data", *COLUNAS_DEZENAS]].copy()
    for coluna in ["Concurso", *COLUNAS_DEZENAS]:
        df[coluna] = pd.to_numeric(df[coluna], errors="coerce").astype(int)
    return df.sort_values("Concurso").reset_index(drop=True)


def carregar_resumo_v1() -> pd.DataFrame:
    if not CAMINHO_RESUMO_V1.exists():
        raise FileNotFoundError("Execute primeiro scripts/backtest_lotofacil_v1.py.")
    resumo = pd.read_csv(CAMINHO_RESUMO_V1, encoding="utf-8-sig")
    resumo["Motor"] = resumo["Motor"].replace({"Motor Elite Lotofacil": "Motor Elite V1"})
    return resumo


def linha_coluna(dezena: int) -> tuple[int, int]:
    return ((dezena - 1) // 5) + 1, ((dezena - 1) % 5) + 1


def aplicar_penalidade(base: float, pares: int, centro: int, linhas: list[int], colunas: list[int]) -> float:
    penalidade = 0.0
    if not (6 <= pares <= 9):
        penalidade += 12.0
    penalidade += abs(centro - 5) * 5.0
    penalidade += sum(max(0, qtd - 4) for qtd in linhas) * 3.0
    penalidade += sum(max(0, qtd - 4) for qtd in colunas) * 3.0
    return round(base - penalidade, 6)


def montar_scores_v2(
    concurso: int,
    freq_geral: Counter,
    freq_5: Counter,
    freq_10: Counter,
    freq_20: Counter,
    ultimo_por_dezena: dict[int, int],
    ultimo_jogo: set[int],
) -> dict[int, float]:
    scores = {}
    for dezena in TODAS_DEZENAS:
        atraso = concurso - ultimo_por_dezena.get(dezena, 0)
        repetiu = 1 if dezena in ultimo_jogo else 0
        scores[dezena] = (
            freq_geral[dezena] * 0.16
            + freq_5[dezena] * 3.40
            + freq_10[dezena] * 2.40
            + freq_20[dezena] * 1.30
            + atraso * 0.10
            + repetiu * 3.50
        )
    return scores


def top_jogos_v2(score_dezenas: dict[int, float], limite: int = 10) -> list[tuple[float, tuple[int, ...]]]:
    top20 = sorted(TODAS_DEZENAS, key=lambda d: (-score_dezenas[d], d))[:20]
    score_total = sum(score_dezenas[d] for d in top20)
    pares_total = sum(1 for d in top20 if d % 2 == 0)
    centro_total = sum(1 for d in top20 if d in CENTRO)
    linhas_total = [0, 0, 0, 0, 0]
    colunas_total = [0, 0, 0, 0, 0]
    meta = {}
    for dezena in top20:
        linha, coluna = linha_coluna(dezena)
        linhas_total[linha - 1] += 1
        colunas_total[coluna - 1] += 1
        meta[dezena] = (score_dezenas[dezena], int(dezena % 2 == 0), int(dezena in CENTRO), linha - 1, coluna - 1)

    heap: list[tuple[float, tuple[int, ...], tuple[int, ...]]] = []
    top20_set = set(top20)
    for excluidas in combinations(top20, 5):
        excl_score = 0.0
        excl_pares = 0
        excl_centro = 0
        linhas = linhas_total.copy()
        colunas = colunas_total.copy()
        for dezena in excluidas:
            dez_score, dez_par, dez_centro, linha, coluna = meta[dezena]
            excl_score += dez_score
            excl_pares += dez_par
            excl_centro += dez_centro
            linhas[linha] -= 1
            colunas[coluna] -= 1
        score = aplicar_penalidade(
            score_total - excl_score,
            pares_total - excl_pares,
            centro_total - excl_centro,
            linhas,
            colunas,
        )
        jogo = tuple(sorted(top20_set - set(excluidas)))
        item = (score, tuple(-d for d in jogo), jogo)
        if len(heap) < limite:
            heappush(heap, item)
        elif item > heap[0]:
            heapreplace(heap, item)

    melhores = sorted(heap, reverse=True)
    return [(score, jogo) for score, _, jogo in melhores]


def registrar_resultado(
    registros: list[dict],
    motor: str,
    concurso: int,
    data: str,
    jogos: list[tuple[float, tuple[int, ...]]],
    sorteadas: set[int],
) -> None:
    for posicao, (score, jogo) in enumerate(jogos, start=1):
        acertos = len(set(jogo) & sorteadas)
        registros.append(
            {
                "Motor": motor,
                "Concurso": concurso,
                "Data": data,
                "Ranking": posicao,
                "Jogo": " - ".join(f"{d:02d}" for d in jogo),
                "Elite Score V2": round(float(score), 6),
                "Acertos": acertos,
            }
        )


def resumir_motor(motor: str, total_concursos: int, detalhe: pd.DataFrame, jogos_por_concurso: int) -> dict:
    grupo = detalhe[detalhe["Motor"] == motor]
    total = int(len(grupo))
    melhor = grupo.sort_values(["Acertos", "Elite Score V2"], ascending=[False, False]).iloc[0]
    linha = {
        "Motor": motor,
        "Jogos por concurso": jogos_por_concurso,
        "Concursos auditados": total_concursos,
        "Total de jogos auditados": total,
        "Melhor acerto": int(grupo["Acertos"].max()),
        "Concurso do melhor resultado": int(melhor["Concurso"]),
        "Melhor jogo encontrado": melhor["Jogo"],
    }
    for ponto in range(11, 16):
        quantidade = int((grupo["Acertos"] == ponto).sum())
        linha[f"Jogos com {ponto} pontos"] = quantidade
        linha[f"Taxa {ponto} pontos (%)"] = round((quantidade / total) * 100, 6) if total else 0.0
    return linha


def resumo_v1_e_aleatorio(resumo_v1: pd.DataFrame) -> list[dict]:
    linhas = []
    for motor in ("Motor Elite V1", "Aleatorio"):
        row = resumo_v1[resumo_v1["Motor"] == motor].iloc[0].to_dict()
        linha = {
            "Motor": motor,
            "Jogos por concurso": int(row["Jogos por concurso"]),
            "Concursos auditados": int(row["Total de jogos auditados"]),
            "Total de jogos auditados": int(row["Total de jogos auditados"]),
            "Melhor acerto": int(row["Melhor acerto"]),
            "Concurso do melhor resultado": int(row["Concurso do melhor resultado"]),
            "Melhor jogo encontrado": row["Melhor jogo encontrado"],
        }
        for ponto in range(11, 16):
            linha[f"Jogos com {ponto} pontos"] = int(row[f"Jogos com {ponto} pontos"])
            linha[f"Taxa {ponto} pontos (%)"] = float(row[f"Taxa {ponto} pontos (%)"])
        linhas.append(linha)
    return linhas


def executar_backtest_ranking(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    freq_geral = Counter()
    freq_5 = Counter()
    freq_10 = Counter()
    freq_20 = Counter()
    janela_5: deque[list[int]] = deque(maxlen=5)
    janela_10: deque[list[int]] = deque(maxlen=10)
    janela_20: deque[list[int]] = deque(maxlen=20)
    ultimo_por_dezena = {dezena: 0 for dezena in TODAS_DEZENAS}
    ultimo_jogo: set[int] = set()
    registros = []

    def atualizar_janela(janela: deque[list[int]], freq: Counter, dezenas: list[int]) -> None:
        if len(janela) == janela.maxlen:
            for dezena in janela[0]:
                freq[dezena] -= 1
        janela.append(dezenas)
        for dezena in dezenas:
            freq[dezena] += 1

    for indice, row in df.iterrows():
        concurso = int(row["Concurso"])
        dezenas = [int(row[coluna]) for coluna in COLUNAS_DEZENAS]
        sorteadas = set(dezenas)
        if indice > 0:
            scores = montar_scores_v2(concurso, freq_geral, freq_5, freq_10, freq_20, ultimo_por_dezena, ultimo_jogo)
            melhores_10 = top_jogos_v2(scores, max(LIMITES_TOP))
            for limite in LIMITES_TOP:
                registrar_resultado(
                    registros,
                    f"Elite V2 Top {limite}",
                    concurso,
                    row["Data"],
                    melhores_10[:limite],
                    sorteadas,
                )

        for dezena in dezenas:
            freq_geral[dezena] += 1
            ultimo_por_dezena[dezena] = concurso
        atualizar_janela(janela_5, freq_5, dezenas)
        atualizar_janela(janela_10, freq_10, dezenas)
        atualizar_janela(janela_20, freq_20, dezenas)
        ultimo_jogo = set(dezenas)

    detalhe = pd.DataFrame(registros)
    total_concursos = len(df) - 1
    resumo_v2 = pd.DataFrame(
        [
            resumir_motor(f"Elite V2 Top {limite}", total_concursos, detalhe, limite)
            for limite in LIMITES_TOP
        ]
    )
    return detalhe, resumo_v2


def gerar_aleatorio_top10(df: pd.DataFrame) -> pd.DataFrame:
    registros = []
    for indice, row in df.iterrows():
        if indice == 0:
            continue
        concurso = int(row["Concurso"])
        sorteadas = {int(row[coluna]) for coluna in COLUNAS_DEZENAS}
        rng = random.Random(330000 + concurso)
        jogos = [(0.0, tuple(sorted(rng.sample(TODAS_DEZENAS, 15)))) for _ in range(10)]
        registrar_resultado(registros, "Aleatorio Top 10", concurso, row["Data"], jogos, sorteadas)
    return pd.DataFrame(registros)


def montar_comparativo(resumo_v1: pd.DataFrame, resumo_v2: pd.DataFrame) -> pd.DataFrame:
    linhas = resumo_v1_e_aleatorio(resumo_v1)
    linhas.extend(resumo_v2.to_dict("records"))
    comparativo = pd.DataFrame(linhas)
    ordem = {
        "Motor Elite V1": 1,
        "Elite V2 Top 1": 2,
        "Elite V2 Top 5": 3,
        "Elite V2 Top 10": 4,
        "Aleatorio": 5,
    }
    comparativo["_ordem"] = comparativo["Motor"].map(ordem)
    return comparativo.sort_values("_ordem").drop(columns=["_ordem"]).reset_index(drop=True)


def gerar_relatorio(df: pd.DataFrame, comparativo: pd.DataFrame) -> str:
    linhas = [
        "# BACKTEST RANKING TOP1 TOP5 TOP10",
        "",
        f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Objetivo",
        "",
        "Medir se o ranking do Motor Elite V2 coloca os melhores jogos no topo.",
        "",
        "## Base",
        "",
        f"- Arquivo: `{CAMINHO_BASE}`",
        f"- Total de concursos oficiais: {len(df)}",
        f"- Concursos auditados: {len(df) - 1}",
        f"- Menor concurso: {int(df['Concurso'].min())}",
        f"- Maior concurso: {int(df['Concurso'].max())}",
        "",
        "## Metodologia",
        "",
        "- Para cada concurso, o historico anterior foi usado para gerar o ranking.",
        "- Foram auditados apenas Elite V2 Top 1, Elite V2 Top 5 e Elite V2 Top 10.",
        "- Motor Elite V1 e Aleatorio usam o resumo do backtest V1 como referencia de 1 jogo por concurso.",
        "",
        "## Comparativo",
        "",
        "| Motor | Jogos/concurso | Total jogos | Melhor acerto | 11 pts | Taxa 11 | 12 pts | Taxa 12 | 13 pts | Taxa 13 | 14 pts | Taxa 14 | 15 pts | Taxa 15 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for _, row in comparativo.iterrows():
        linhas.append(
            f"| {row['Motor']} | {row['Jogos por concurso']} | {row['Total de jogos auditados']} | "
            f"{row['Melhor acerto']} | {row['Jogos com 11 pontos']} | {row['Taxa 11 pontos (%)']}% | "
            f"{row['Jogos com 12 pontos']} | {row['Taxa 12 pontos (%)']}% | "
            f"{row['Jogos com 13 pontos']} | {row['Taxa 13 pontos (%)']}% | "
            f"{row['Jogos com 14 pontos']} | {row['Taxa 14 pontos (%)']}% | "
            f"{row['Jogos com 15 pontos']} | {row['Taxa 15 pontos (%)']}% |"
        )

    top1 = comparativo[comparativo["Motor"] == "Elite V2 Top 1"].iloc[0]
    top5 = comparativo[comparativo["Motor"] == "Elite V2 Top 5"].iloc[0]
    top10 = comparativo[comparativo["Motor"] == "Elite V2 Top 10"].iloc[0]
    v1 = comparativo[comparativo["Motor"] == "Motor Elite V1"].iloc[0]
    conclusao = (
        "O ranking V2 concentrou vantagem real no topo em relacao ao V1."
        if (
            float(top1["Taxa 13 pontos (%)"]) > float(v1["Taxa 13 pontos (%)"])
            and int(top10["Jogos com 14 pontos"]) > int(v1["Jogos com 14 pontos"])
            and int(top10["Jogos com 15 pontos"]) > int(v1["Jogos com 15 pontos"])
        )
        else (
            "O ranking V2 ainda nao coloca os melhores jogos no topo. "
            "O portfolio amplo V2 encontrou 14 e 15 pontos, mas esses picos nao aparecem no Top 1, Top 5 ou Top 10. "
            "No Top 1, o V2 fez menos jogos de 13 pontos que o V1 e que o aleatorio; no Top 5/Top 10, "
            "a contagem bruta aumenta porque ha mais jogos, mas a taxa de 13 pontos fica abaixo do V1."
        )
    )
    linhas += [
        "",
        "## Leitura do ranking",
        "",
        f"- Elite V2 Top 1 com 13 pontos: {int(top1['Jogos com 13 pontos'])}",
        f"- Elite V2 Top 5 com 13 pontos: {int(top5['Jogos com 13 pontos'])}",
        f"- Elite V2 Top 10 com 13 pontos: {int(top10['Jogos com 13 pontos'])}",
        f"- Elite V2 Top 10 com 14 pontos: {int(top10['Jogos com 14 pontos'])}",
        f"- Elite V2 Top 10 com 15 pontos: {int(top10['Jogos com 15 pontos'])}",
        "",
        "## Conclusao",
        "",
        conclusao,
        "",
        "## Arquivos gerados",
        "",
        "- `exports/BACKTEST_RANKING_TOP1_TOP5_TOP10.md`",
        "- `exports/comparativo_ranking.csv`",
        "- `exports/backtest_ranking_top1_top5_top10.csv`",
    ]
    return "\n".join(linhas)


def main() -> None:
    PASTA_EXPORTS.mkdir(parents=True, exist_ok=True)
    df = carregar_base()
    resumo_v1 = carregar_resumo_v1()
    detalhe, resumo_v2 = executar_backtest_ranking(df)
    comparativo = montar_comparativo(resumo_v1, resumo_v2)
    detalhe.to_csv(PASTA_EXPORTS / "backtest_ranking_top1_top5_top10.csv", index=False, encoding="utf-8-sig")
    comparativo.to_csv(PASTA_EXPORTS / "comparativo_ranking.csv", index=False, encoding="utf-8-sig")
    (PASTA_EXPORTS / "BACKTEST_RANKING_TOP1_TOP5_TOP10.md").write_text(
        gerar_relatorio(df, comparativo),
        encoding="utf-8",
    )
    print("BACKTEST_RANKING_OK")
    print(comparativo.to_string(index=False))


if __name__ == "__main__":
    main()
