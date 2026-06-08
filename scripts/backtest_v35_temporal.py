from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass, field
from datetime import datetime
from heapq import heappush, heapreplace
from itertools import combinations
from pathlib import Path

import pandas as pd


RAIZ = Path(__file__).resolve().parents[1]
PASTA_EXPORTS = RAIZ / "exports"
CAMINHO_BASE = RAIZ / "dados" / "lotofacil_historico.csv"
CAMINHO_COMPARATIVO_V35 = PASTA_EXPORTS / "comparativo_elite_score_v35.csv"

COLUNAS_DEZENAS = [f"Bola{i}" for i in range(1, 16)]
TODAS_DEZENAS = list(range(1, 26))
MOLDURA = {1, 2, 3, 4, 5, 6, 10, 11, 15, 16, 20, 21, 22, 23, 24, 25}
CENTRO = set(TODAS_DEZENAS) - MOLDURA
LIMITES_TOP = (1, 5, 10)


@dataclass
class DnaTemporal:
    total_15: int = 0
    soma_total: list[int] = field(default_factory=list)
    linhas: Counter = field(default_factory=Counter)
    colunas: Counter = field(default_factory=Counter)
    quadrantes: Counter = field(default_factory=Counter)
    soma_bin: Counter = field(default_factory=Counter)
    pares: Counter = field(default_factory=Counter)
    centro: Counter = field(default_factory=Counter)
    repeticao: Counter = field(default_factory=Counter)
    consecutivas: Counter = field(default_factory=Counter)
    dezenas: Counter = field(default_factory=Counter)
    concursos_origem: list[int] = field(default_factory=list)


def carregar_base() -> pd.DataFrame:
    df = pd.read_csv(CAMINHO_BASE, encoding="utf-8-sig")
    df = df[["Concurso", "Data", *COLUNAS_DEZENAS]].copy()
    for coluna in ["Concurso", *COLUNAS_DEZENAS]:
        df[coluna] = pd.to_numeric(df[coluna], errors="coerce").astype(int)
    return df.sort_values("Concurso").reset_index(drop=True)


def linha_coluna(dezena: int) -> tuple[int, int]:
    return ((dezena - 1) // 5) + 1, ((dezena - 1) % 5) + 1


def quadrante(dezena: int) -> int:
    linha, coluna = linha_coluna(dezena)
    if linha <= 2 and coluna <= 3:
        return 1
    if linha <= 2 and coluna >= 4:
        return 2
    if linha >= 3 and coluna <= 3:
        return 3
    return 4


def binar_soma(soma: int) -> str:
    inicio = (soma // 10) * 10
    return f"{inicio}-{inicio + 9}"


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
        scores[dezena] = (
            freq_geral[dezena] * 0.16
            + freq_5[dezena] * 3.40
            + freq_10[dezena] * 2.40
            + freq_20[dezena] * 1.30
            + atraso * 0.10
            + (3.50 if dezena in ultimo_jogo else 0.0)
        )
    return scores


def atualizar_janela(janela: deque[list[int]], freq: Counter, dezenas: list[int]) -> None:
    if len(janela) == janela.maxlen:
        for dezena in janela[0]:
            freq[dezena] -= 1
    janela.append(dezenas)
    for dezena in dezenas:
        freq[dezena] += 1


def preparar_estados(df: pd.DataFrame):
    freq_geral = Counter()
    freq_5 = Counter()
    freq_10 = Counter()
    freq_20 = Counter()
    janela_5: deque[list[int]] = deque(maxlen=5)
    janela_10: deque[list[int]] = deque(maxlen=10)
    janela_20: deque[list[int]] = deque(maxlen=20)
    ultimo_por_dezena = {dezena: 0 for dezena in TODAS_DEZENAS}
    ultimo_jogo: set[int] = set()

    for indice, row in df.iterrows():
        concurso = int(row["Concurso"])
        dezenas = [int(row[coluna]) for coluna in COLUNAS_DEZENAS]
        if indice > 0:
            yield row, concurso, set(dezenas), freq_geral.copy(), freq_5.copy(), freq_10.copy(), freq_20.copy(), ultimo_por_dezena.copy(), ultimo_jogo.copy()
        for dezena in dezenas:
            freq_geral[dezena] += 1
            ultimo_por_dezena[dezena] = concurso
        atualizar_janela(janela_5, freq_5, dezenas)
        atualizar_janela(janela_10, freq_10, dezenas)
        atualizar_janela(janela_20, freq_20, dezenas)
        ultimo_jogo = set(dezenas)


def features_dezenas(dezenas: tuple[int, ...], ultimo_jogo: set[int]) -> dict:
    soma = sum(dezenas)
    pares = sum(1 for d in dezenas if d % 2 == 0)
    centro = sum(1 for d in dezenas if d in CENTRO)
    linhas = [0, 0, 0, 0, 0]
    colunas = [0, 0, 0, 0, 0]
    quadrantes = [0, 0, 0, 0]
    for dezena in dezenas:
        linha, coluna = linha_coluna(dezena)
        linhas[linha - 1] += 1
        colunas[coluna - 1] += 1
        quadrantes[quadrante(dezena) - 1] += 1
    return {
        "soma_total": soma,
        "soma_bin": binar_soma(soma),
        "pares": pares,
        "centro": centro,
        "repeticao": len(set(dezenas) & ultimo_jogo),
        "consecutivas": sum(1 for a, b in zip(dezenas, dezenas[1:]) if b == a + 1),
        "linhas": "-".join(map(str, linhas)),
        "colunas": "-".join(map(str, colunas)),
        "quadrantes": "-".join(map(str, quadrantes)),
    }


def atualizar_dna_temporal(dna: DnaTemporal, concurso: int, sorteadas: set[int], top20: set[int], ultimo_jogo: set[int]) -> None:
    if len(sorteadas & top20) < 15:
        return
    dezenas = tuple(sorted(sorteadas))
    features = features_dezenas(dezenas, ultimo_jogo)
    dna.total_15 += 1
    dna.concursos_origem.append(concurso)
    dna.soma_total.append(features["soma_total"])
    dna.soma_bin[features["soma_bin"]] += 1
    dna.pares[str(features["pares"])] += 1
    dna.centro[str(features["centro"])] += 1
    dna.repeticao[str(features["repeticao"])] += 1
    dna.consecutivas[str(features["consecutivas"])] += 1
    dna.linhas[features["linhas"]] += 1
    dna.colunas[features["colunas"]] += 1
    dna.quadrantes[features["quadrantes"]] += 1
    for dezena in dezenas:
        dna.dezenas[dezena] += 1


def score_faixa_temporal(valor: int, valores: list[int], peso: float, queda: float) -> float:
    if not valores:
        return 0.0
    media = sum(valores) / len(valores)
    distancia = abs(valor - media)
    return max(0.0, peso - (distancia * queda))


def score_dna_15_pontos_temporal(features: dict, jogo: tuple[int, ...], dna: DnaTemporal) -> float:
    if dna.total_15 == 0:
        score = 0.0
    else:
        score = score_faixa_temporal(features["soma_total"], dna.soma_total, 18.0, 0.45)
        score += dna.soma_bin[features["soma_bin"]] * 5.0
        score += dna.pares[str(features["pares"])] * 6.0
        score += dna.centro[str(features["centro"])] * 7.0
        score += dna.repeticao[str(features["repeticao"])] * 8.0
        score += dna.consecutivas[str(features["consecutivas"])] * 6.0
        score += dna.linhas[features["linhas"]] * 11.0
        score += dna.colunas[features["colunas"]] * 11.0
        score += dna.quadrantes[features["quadrantes"]] * 9.0
        score += sum(dna.dezenas[d] for d in jogo) * 1.4

    if features["linhas"] == "3-3-3-3-3":
        score -= 25.0
    if features["colunas"] == "3-3-3-3-3":
        score -= 25.0
    return round(score, 6)


def top_jogos_temporal(score_dezenas: dict[int, float], dna: DnaTemporal, ultimo_jogo: set[int], limite: int = 10) -> list[tuple[float, tuple[int, ...]]]:
    top20 = sorted(TODAS_DEZENAS, key=lambda d: (-score_dezenas[d], d))[:20]
    top20_set = set(top20)
    heap: list[tuple[float, tuple[int, ...], tuple[int, ...]]] = []
    for excluidas in combinations(top20, 5):
        jogo = tuple(sorted(top20_set - set(excluidas)))
        features = features_dezenas(jogo, ultimo_jogo)
        dna_score = score_dna_15_pontos_temporal(features, jogo, dna)
        v2_score = sum(score_dezenas[d] for d in jogo) * 0.015
        score = round(dna_score + v2_score, 6)
        item = (score, tuple(-d for d in jogo), jogo)
        if len(heap) < limite:
            heappush(heap, item)
        elif item > heap[0]:
            heapreplace(heap, item)
    melhores = sorted(heap, reverse=True)
    return [(score, jogo) for score, _, jogo in melhores]


def executar_backtest_temporal(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, DnaTemporal]:
    dna = DnaTemporal()
    registros = []
    for row, concurso, sorteadas, freq_geral, freq_5, freq_10, freq_20, ultimo_por_dezena, ultimo_jogo in preparar_estados(df):
        scores = montar_scores_v2(concurso, freq_geral, freq_5, freq_10, freq_20, ultimo_por_dezena, ultimo_jogo)
        melhores_10 = top_jogos_temporal(scores, dna, ultimo_jogo, max(LIMITES_TOP))
        for limite in LIMITES_TOP:
            for posicao, (score, jogo) in enumerate(melhores_10[:limite], start=1):
                acertos = len(set(jogo) & sorteadas)
                registros.append(
                    {
                        "Motor": f"Elite Score V3.5 Temporal Top {limite}",
                        "Concurso": concurso,
                        "Data": row["Data"],
                        "Ranking": posicao,
                        "Jogo": " - ".join(f"{d:02d}" for d in jogo),
                        "Elite Score V3.5 Temporal": score,
                        "DNA 15 disponivel antes do concurso": dna.total_15,
                        "Concursos DNA usados": " - ".join(str(c) for c in dna.concursos_origem),
                        "Acertos": acertos,
                    }
                )
        top20 = set(sorted(TODAS_DEZENAS, key=lambda d: (-scores[d], d))[:20])
        atualizar_dna_temporal(dna, concurso, sorteadas, top20, ultimo_jogo)

    detalhe = pd.DataFrame(registros)
    resumo = []
    for limite in LIMITES_TOP:
        motor = f"Elite Score V3.5 Temporal Top {limite}"
        grupo = detalhe[detalhe["Motor"] == motor]
        melhor = grupo.sort_values(["Acertos", "Elite Score V3.5 Temporal"], ascending=[False, False]).iloc[0]
        linha = {
            "Motor": motor,
            "Jogos por concurso": limite,
            "Concursos auditados": len(df) - 1,
            "Total de jogos auditados": len(grupo),
            "Melhor acerto": int(grupo["Acertos"].max()),
            "Concurso do melhor resultado": int(melhor["Concurso"]),
            "Melhor jogo encontrado": melhor["Jogo"],
        }
        for ponto in range(11, 16):
            quantidade = int((grupo["Acertos"] == ponto).sum())
            linha[f"Jogos com {ponto} pontos"] = quantidade
            linha[f"Taxa {ponto} pontos (%)"] = round((quantidade / len(grupo)) * 100, 6)
        resumo.append(linha)
    return detalhe, pd.DataFrame(resumo), dna


def montar_comparativo(resumo_temporal: pd.DataFrame) -> pd.DataFrame:
    base = pd.read_csv(CAMINHO_COMPARATIVO_V35, encoding="utf-8-sig")
    manter = [
        "Motor Elite V1",
        "Elite Score V3 Top 1",
        "Elite Score V3 Top 5",
        "Elite Score V3 Top 10",
        "Elite Score V3.5 Top 1",
        "Elite Score V3.5 Top 5",
        "Elite Score V3.5 Top 10",
        "Aleatorio",
    ]
    comparativo = pd.concat([base[base["Motor"].isin(manter)], resumo_temporal], ignore_index=True)
    ordem = {motor: i for i, motor in enumerate(
        [
            "Motor Elite V1",
            "Elite Score V3 Top 1",
            "Elite Score V3 Top 5",
            "Elite Score V3 Top 10",
            "Elite Score V3.5 Top 1",
            "Elite Score V3.5 Top 5",
            "Elite Score V3.5 Top 10",
            "Elite Score V3.5 Temporal Top 1",
            "Elite Score V3.5 Temporal Top 5",
            "Elite Score V3.5 Temporal Top 10",
            "Aleatorio",
        ],
        start=1,
    )}
    comparativo["_ordem"] = comparativo["Motor"].map(ordem)
    return comparativo.sort_values("_ordem").drop(columns=["_ordem"]).reset_index(drop=True)


def classificar_modelo(comparativo: pd.DataFrame) -> str:
    temporal_top10 = comparativo[comparativo["Motor"] == "Elite Score V3.5 Temporal Top 10"].iloc[0]
    v1 = comparativo[comparativo["Motor"] == "Motor Elite V1"].iloc[0]
    aleatorio = comparativo[comparativo["Motor"] == "Aleatorio"].iloc[0]
    global_top10 = comparativo[comparativo["Motor"] == "Elite Score V3.5 Top 10"].iloc[0]
    if int(temporal_top10["Jogos com 15 pontos"]) > 0 and int(temporal_top10["Jogos com 14 pontos"]) > 0:
        return "APROVADO PARA PRODUCAO"
    if (
        int(temporal_top10["Jogos com 13 pontos"]) > int(v1["Jogos com 13 pontos"])
        and int(temporal_top10["Jogos com 13 pontos"]) > int(aleatorio["Jogos com 13 pontos"])
        and int(temporal_top10["Jogos com 15 pontos"]) < int(global_top10["Jogos com 15 pontos"])
    ):
        return "CANDIDATO EXPERIMENTAL"
    return "REPROVADO POR OVERFITTING"


def gerar_relatorio(df: pd.DataFrame, comparativo: pd.DataFrame, dna_final: DnaTemporal) -> str:
    classificacao = classificar_modelo(comparativo)
    linhas = [
        "# BACKTEST V3.5 SEM VAZAMENTO TEMPORAL",
        "",
        f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Regra temporal aplicada",
        "",
        "- Para cada concurso alvo, foram usados somente concursos anteriores.",
        "- Nao foi usado `APRENDIZADO_JOGOS_VENCEDORES.csv` global.",
        "- Nao foi usada `AUDITORIA_15_PONTOS.csv`.",
        "- O DNA temporal comeca vazio e so recebe jogos de 15 pontos encontrados em concursos ja passados.",
        "",
        "## Base",
        "",
        f"- Concursos oficiais na base: {len(df)}",
        f"- Concursos auditados: {len(df) - 1}",
        f"- Jogos de 15 pontos incorporados ao DNA temporal ao final: {dna_final.total_15}",
        f"- Concursos que alimentaram o DNA temporal: {' - '.join(str(c) for c in dna_final.concursos_origem) if dna_final.concursos_origem else 'Nenhum'}",
        "",
        "## Comparativo",
        "",
        "| Motor | Jogos/concurso | Melhor | 11 pts | 12 pts | 13 pts | 14 pts | 15 pts |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for _, row in comparativo.iterrows():
        linhas.append(
            f"| {row['Motor']} | {row['Jogos por concurso']} | {row['Melhor acerto']} | "
            f"{row['Jogos com 11 pontos']} | {row['Jogos com 12 pontos']} | {row['Jogos com 13 pontos']} | "
            f"{row['Jogos com 14 pontos']} | {row['Jogos com 15 pontos']} |"
        )
    linhas += [
        "",
        "## Conclusao",
        "",
        f"Classificacao: **{classificacao}**",
        "",
        "A diferenca entre o V3.5 Global e o V3.5 Temporal indica o quanto o resultado dependia de informacao futura. Se o temporal nao sustentar os 15 pontos e/ou perder muita forca nas faixas altas, o V3.5 global deve ser tratado como overfitting.",
        "",
        "## Arquivos gerados",
        "",
        "- `exports/BACKTEST_V35_SEM_VAZAMENTO_TEMPORAL.md`",
        "- `exports/comparativo_v35_temporal.csv`",
        "- `exports/backtest_v35_temporal.csv`",
    ]
    return "\n".join(linhas)


def main() -> None:
    PASTA_EXPORTS.mkdir(parents=True, exist_ok=True)
    df = carregar_base()
    detalhe, resumo, dna_final = executar_backtest_temporal(df)
    detalhe.to_csv(PASTA_EXPORTS / "backtest_v35_temporal.csv", index=False, encoding="utf-8-sig")
    comparativo = montar_comparativo(resumo)
    comparativo.to_csv(PASTA_EXPORTS / "comparativo_v35_temporal.csv", index=False, encoding="utf-8-sig")
    (PASTA_EXPORTS / "BACKTEST_V35_SEM_VAZAMENTO_TEMPORAL.md").write_text(
        gerar_relatorio(df, comparativo, dna_final),
        encoding="utf-8",
    )
    print("BACKTEST_V35_TEMPORAL_OK")
    print(comparativo.to_string(index=False))


if __name__ == "__main__":
    main()
