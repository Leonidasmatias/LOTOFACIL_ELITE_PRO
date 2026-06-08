from __future__ import annotations

from collections import Counter, defaultdict, deque
from datetime import datetime
from heapq import heappush, heapreplace
from itertools import combinations
from math import log1p
from pathlib import Path

import pandas as pd


RAIZ = Path(__file__).resolve().parents[1]
CAMINHO_BASE = RAIZ / "dados" / "lotofacil_historico.csv"
PASTA_EXPORTS = RAIZ / "exports"
CAMINHO_COMPARATIVO_RANKING = PASTA_EXPORTS / "comparativo_ranking.csv"

COLUNAS_DEZENAS = [f"Bola{i}" for i in range(1, 16)]
TODAS_DEZENAS = list(range(1, 26))
MOLDURA = {1, 2, 3, 4, 5, 6, 10, 11, 15, 16, 20, 21, 22, 23, 24, 25}
CENTRO = set(TODAS_DEZENAS) - MOLDURA
LIMITES_TOP = (1, 5, 10)
PESO_ACERTO = {13: 1.0, 14: 7.5, 15: 35.0}


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


def binar(valor: int, passo: int) -> str:
    inicio = (valor // passo) * passo
    return f"{inicio}-{inicio + passo - 1}"


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


def features_jogo(
    jogo: tuple[int, ...],
    ultimo_jogo: set[int],
    freq_geral: Counter,
    freq_5: Counter,
    freq_20: Counter,
) -> dict[str, str]:
    dezenas = sorted(jogo)
    soma = sum(dezenas)
    pares = sum(1 for d in dezenas if d % 2 == 0)
    centro = sum(1 for d in dezenas if d in CENTRO)
    repeticao = len(set(dezenas) & ultimo_jogo)
    consecutivas = sum(1 for a, b in zip(dezenas, dezenas[1:]) if b == a + 1)
    linhas = [0, 0, 0, 0, 0]
    colunas = [0, 0, 0, 0, 0]
    quadrantes = [0, 0, 0, 0]
    for dezena in dezenas:
        linha, coluna = linha_coluna(dezena)
        linhas[linha - 1] += 1
        colunas[coluna - 1] += 1
        quadrantes[quadrante(dezena) - 1] += 1
    freq_curta = sum(freq_5[d] for d in dezenas)
    freq_longa = sum(freq_geral[d] for d in dezenas)
    freq_20_total = sum(freq_20[d] for d in dezenas)
    return {
        "soma_bin": binar(soma, 10),
        "soma_total": str(soma),
        "pares": str(pares),
        "impares": str(15 - pares),
        "centro": str(centro),
        "moldura": str(15 - centro),
        "repeticao_anterior": str(repeticao),
        "consecutivas": str(consecutivas),
        "linhas": "-".join(map(str, linhas)),
        "colunas": "-".join(map(str, colunas)),
        "quadrantes": "-".join(map(str, quadrantes)),
        "freq_curta_bin": binar(freq_curta, 5),
        "freq_20_bin": binar(freq_20_total, 10),
        "freq_longa_bin": binar(freq_longa, 100),
    }


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
            yield (
                row,
                concurso,
                set(dezenas),
                freq_geral.copy(),
                freq_5.copy(),
                freq_10.copy(),
                freq_20.copy(),
                ultimo_por_dezena.copy(),
                ultimo_jogo.copy(),
            )
        for dezena in dezenas:
            freq_geral[dezena] += 1
            ultimo_por_dezena[dezena] = concurso
        atualizar_janela(janela_5, freq_5, dezenas)
        atualizar_janela(janela_10, freq_10, dezenas)
        atualizar_janela(janela_20, freq_20, dezenas)
        ultimo_jogo = set(dezenas)


def minerar_jogos_vencedores(df: pd.DataFrame) -> pd.DataFrame:
    registros = []
    for row, concurso, sorteadas, freq_geral, freq_5, freq_10, freq_20, ultimo_por_dezena, ultimo_jogo in preparar_estados(df):
        scores = montar_scores_v2(concurso, freq_geral, freq_5, freq_10, freq_20, ultimo_por_dezena, ultimo_jogo)
        top20 = sorted(TODAS_DEZENAS, key=lambda d: (-scores[d], d))[:20]
        top20_set = set(top20)
        sorteadas_top20 = top20_set & sorteadas
        if len(sorteadas_top20) < 13:
            continue
        for excluidas in combinations(top20, 5):
            jogo = tuple(sorted(top20_set - set(excluidas)))
            acertos = len(set(jogo) & sorteadas)
            if acertos < 13:
                continue
            feats = features_jogo(jogo, ultimo_jogo, freq_geral, freq_5, freq_20)
            registros.append(
                {
                    "Concurso": concurso,
                    "Data": row["Data"],
                    "Acertos": acertos,
                    "Jogo": " - ".join(f"{d:02d}" for d in jogo),
                    **feats,
                }
            )
    return pd.DataFrame(registros)


def construir_modelo_aprendizado(aprendizado: pd.DataFrame) -> dict[str, Counter]:
    modelo: dict[str, Counter] = defaultdict(Counter)
    if aprendizado.empty:
        return modelo
    colunas = [
        "soma_bin",
        "pares",
        "centro",
        "repeticao_anterior",
        "consecutivas",
        "linhas",
        "colunas",
        "quadrantes",
        "freq_curta_bin",
        "freq_20_bin",
        "freq_longa_bin",
    ]
    for _, row in aprendizado.iterrows():
        peso = PESO_ACERTO.get(int(row["Acertos"]), 0.0)
        for coluna in colunas:
            modelo[coluna][str(row[coluna])] += peso
        for dezena in str(row["Jogo"]).split(" - "):
            modelo["dezena"][dezena] += peso
    return modelo


def score_aprendizado_historico(features: dict[str, str], jogo: tuple[int, ...], modelo: dict[str, Counter]) -> float:
    pesos = {
        "soma_bin": 1.4,
        "pares": 1.1,
        "centro": 1.25,
        "repeticao_anterior": 1.7,
        "consecutivas": 0.8,
        "linhas": 1.9,
        "colunas": 1.9,
        "quadrantes": 1.5,
        "freq_curta_bin": 1.2,
        "freq_20_bin": 1.0,
        "freq_longa_bin": 0.8,
    }
    score = 0.0
    for coluna, peso in pesos.items():
        score += log1p(modelo[coluna][features[coluna]]) * peso
    score += sum(log1p(modelo["dezena"][f"{d:02d}"]) * 0.18 for d in jogo)
    return round(score, 6)


def score_geometrico_v2(jogo: tuple[int, ...], score_dezenas: dict[int, float]) -> float:
    base = sum(score_dezenas[d] for d in jogo)
    pares = sum(1 for d in jogo if d % 2 == 0)
    centro = sum(1 for d in jogo if d in CENTRO)
    linhas = [0, 0, 0, 0, 0]
    colunas = [0, 0, 0, 0, 0]
    for dezena in jogo:
        linha, coluna = linha_coluna(dezena)
        linhas[linha - 1] += 1
        colunas[coluna - 1] += 1
    penalidade = 0.0
    if not (6 <= pares <= 9):
        penalidade += 12.0
    penalidade += abs(centro - 5) * 5.0
    penalidade += sum(max(0, qtd - 4) for qtd in linhas) * 3.0
    penalidade += sum(max(0, qtd - 4) for qtd in colunas) * 3.0
    return round(base - penalidade, 6)


def top_jogos_v3(
    score_dezenas: dict[int, float],
    modelo: dict[str, Counter],
    ultimo_jogo: set[int],
    freq_geral: Counter,
    freq_5: Counter,
    freq_20: Counter,
    limite: int = 10,
) -> list[tuple[float, tuple[int, ...]]]:
    top20 = sorted(TODAS_DEZENAS, key=lambda d: (-score_dezenas[d], d))[:20]
    top20_set = set(top20)
    score_total = sum(score_dezenas[d] for d in top20)
    soma_total = sum(top20)
    pares_total = sum(1 for d in top20 if d % 2 == 0)
    centro_total = sum(1 for d in top20 if d in CENTRO)
    repeticao_total = len(top20_set & ultimo_jogo)
    freq_geral_total = sum(freq_geral[d] for d in top20)
    freq_5_total = sum(freq_5[d] for d in top20)
    freq_20_total = sum(freq_20[d] for d in top20)
    linhas_total = [0, 0, 0, 0, 0]
    colunas_total = [0, 0, 0, 0, 0]
    quadrantes_total = [0, 0, 0, 0]
    learned_dezena_total = sum(log1p(modelo["dezena"][f"{d:02d}"]) * 0.18 for d in top20)
    top20_mask = 0
    meta = {}
    for dezena in top20:
        linha, coluna = linha_coluna(dezena)
        quad = quadrante(dezena)
        linhas_total[linha - 1] += 1
        colunas_total[coluna - 1] += 1
        quadrantes_total[quad - 1] += 1
        top20_mask |= 1 << dezena
        meta[dezena] = {
            "score": score_dezenas[dezena],
            "par": int(dezena % 2 == 0),
            "centro": int(dezena in CENTRO),
            "repeticao": int(dezena in ultimo_jogo),
            "freq_geral": freq_geral[dezena],
            "freq_5": freq_5[dezena],
            "freq_20": freq_20[dezena],
            "linha": linha - 1,
            "coluna": coluna - 1,
            "quadrante": quad - 1,
            "learned_dezena": log1p(modelo["dezena"][f"{dezena:02d}"]) * 0.18,
        }

    pesos = {
        "soma_bin": 1.4,
        "pares": 1.1,
        "centro": 1.25,
        "repeticao_anterior": 1.7,
        "consecutivas": 0.8,
        "linhas": 1.9,
        "colunas": 1.9,
        "quadrantes": 1.5,
        "freq_curta_bin": 1.2,
        "freq_20_bin": 1.0,
        "freq_longa_bin": 0.8,
    }
    heap: list[tuple[float, tuple[int, ...], tuple[int, ...]]] = []
    for excluidas in combinations(top20, 5):
        excl_score = 0.0
        excl_soma = 0
        excl_pares = 0
        excl_centro = 0
        excl_repeticao = 0
        excl_freq_geral = 0
        excl_freq_5 = 0
        excl_freq_20 = 0
        excl_learned_dezena = 0.0
        excl_mask = 0
        linhas = linhas_total.copy()
        colunas = colunas_total.copy()
        quadrantes = quadrantes_total.copy()
        for dezena in excluidas:
            dados = meta[dezena]
            excl_score += dados["score"]
            excl_soma += dezena
            excl_pares += dados["par"]
            excl_centro += dados["centro"]
            excl_repeticao += dados["repeticao"]
            excl_freq_geral += dados["freq_geral"]
            excl_freq_5 += dados["freq_5"]
            excl_freq_20 += dados["freq_20"]
            excl_learned_dezena += dados["learned_dezena"]
            excl_mask |= 1 << dezena
            linhas[dados["linha"]] -= 1
            colunas[dados["coluna"]] -= 1
            quadrantes[dados["quadrante"]] -= 1

        soma = soma_total - excl_soma
        pares = pares_total - excl_pares
        centro = centro_total - excl_centro
        repeticao = repeticao_total - excl_repeticao
        included_mask = top20_mask & ~excl_mask
        consecutivas = (included_mask & (included_mask >> 1)).bit_count()
        valores = {
            "soma_bin": binar(soma, 10),
            "pares": str(pares),
            "centro": str(centro),
            "repeticao_anterior": str(repeticao),
            "consecutivas": str(consecutivas),
            "linhas": "-".join(map(str, linhas)),
            "colunas": "-".join(map(str, colunas)),
            "quadrantes": "-".join(map(str, quadrantes)),
            "freq_curta_bin": binar(freq_5_total - excl_freq_5, 5),
            "freq_20_bin": binar(freq_20_total - excl_freq_20, 10),
            "freq_longa_bin": binar(freq_geral_total - excl_freq_geral, 100),
        }
        aprendido = sum(log1p(modelo[coluna][valor]) * pesos[coluna] for coluna, valor in valores.items())
        aprendido += learned_dezena_total - excl_learned_dezena

        geometrico = score_total - excl_score
        penalidade = 0.0
        if not (6 <= pares <= 9):
            penalidade += 12.0
        penalidade += abs(centro - 5) * 5.0
        penalidade += sum(max(0, qtd - 4) for qtd in linhas) * 3.0
        penalidade += sum(max(0, qtd - 4) for qtd in colunas) * 3.0
        geometrico = round(geometrico - penalidade, 6)
        score = round((aprendido * 120.0) + (geometrico * 0.015), 6)
        item = (score, tuple(-d for d in excluidas), tuple(excluidas))
        if len(heap) < limite:
            heappush(heap, item)
        elif item > heap[0]:
            heapreplace(heap, item)
    melhores = sorted(heap, reverse=True)
    return [(score, tuple(sorted(top20_set - set(excluidas)))) for score, _, excluidas in melhores]


def executar_backtest_v3(df: pd.DataFrame, modelo: dict[str, Counter]) -> tuple[pd.DataFrame, pd.DataFrame]:
    registros = []
    for row, concurso, sorteadas, freq_geral, freq_5, freq_10, freq_20, ultimo_por_dezena, ultimo_jogo in preparar_estados(df):
        scores = montar_scores_v2(concurso, freq_geral, freq_5, freq_10, freq_20, ultimo_por_dezena, ultimo_jogo)
        melhores_10 = top_jogos_v3(scores, modelo, ultimo_jogo, freq_geral, freq_5, freq_20, max(LIMITES_TOP))
        for limite in LIMITES_TOP:
            for posicao, (score, jogo) in enumerate(melhores_10[:limite], start=1):
                acertos = len(set(jogo) & sorteadas)
                registros.append(
                    {
                        "Motor": f"Elite Score V3 Top {limite}",
                        "Concurso": concurso,
                        "Data": row["Data"],
                        "Ranking": posicao,
                        "Jogo": " - ".join(f"{d:02d}" for d in jogo),
                        "Elite Score V3": score,
                        "Acertos": acertos,
                    }
                )
    detalhe = pd.DataFrame(registros)
    resumo = []
    for limite in LIMITES_TOP:
        motor = f"Elite Score V3 Top {limite}"
        grupo = detalhe[detalhe["Motor"] == motor]
        melhor = grupo.sort_values(["Acertos", "Elite Score V3"], ascending=[False, False]).iloc[0]
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
    return detalhe, pd.DataFrame(resumo)


def gerar_elite_score_v3(aprendizado: pd.DataFrame, modelo: dict[str, Counter]) -> str:
    linhas = [
        "# ELITE SCORE V3",
        "",
        f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Objetivo",
        "",
        "Recriar o ranking usando aprendizado historico dos jogos de 13, 14 e 15 pontos encontrados no portfolio V2.",
        "",
        "## Jogos vencedores minerados",
        "",
        f"- Total de jogos 13+: {len(aprendizado)}",
    ]
    for ponto in range(13, 16):
        linhas.append(f"- Jogos com {ponto} pontos: {int((aprendizado['Acertos'] == ponto).sum()) if not aprendizado.empty else 0}")
    linhas += [
        "",
        "## Variaveis analisadas",
        "",
        "- Soma total",
        "- Pares e impares",
        "- Centro x moldura",
        "- Linhas",
        "- Colunas",
        "- Repeticao do concurso anterior",
        "- Frequencia curta",
        "- Frequencia longa",
        "- Dezenas consecutivas",
        "- Distribuicao por quadrantes",
        "",
        "## Score",
        "",
        "`score_aprendizado_historico()` soma evidencias historicas ponderadas por resultado: 13 pontos, 14 pontos e 15 pontos.",
        "O score final combina aprendizado historico com uma pequena parcela do score geometrico/frequencial V2.",
        "",
        "## Principais padroes minerados",
        "",
    ]
    for chave in ("soma_bin", "pares", "centro", "repeticao_anterior", "linhas", "colunas", "quadrantes", "consecutivas"):
        top = modelo[chave].most_common(5)
        valores = ", ".join(f"{valor} ({round(peso, 2)})" for valor, peso in top)
        linhas.append(f"- {chave}: {valores}")
    linhas += [
        "",
        "## Arquivo de aprendizado",
        "",
        "- `exports/APRENDIZADO_JOGOS_VENCEDORES.csv`",
    ]
    return "\n".join(linhas)


def montar_comparativo_final(resumo_v3: pd.DataFrame) -> pd.DataFrame:
    comparativo_base = pd.read_csv(CAMINHO_COMPARATIVO_RANKING, encoding="utf-8-sig")
    comparativo = pd.concat([comparativo_base, resumo_v3], ignore_index=True)
    ordem = {
        "Motor Elite V1": 1,
        "Elite V2 Top 1": 2,
        "Elite V2 Top 5": 3,
        "Elite V2 Top 10": 4,
        "Elite Score V3 Top 1": 5,
        "Elite Score V3 Top 5": 6,
        "Elite Score V3 Top 10": 7,
        "Aleatorio": 8,
    }
    comparativo["_ordem"] = comparativo["Motor"].map(ordem)
    return comparativo.sort_values("_ordem").drop(columns=["_ordem"]).reset_index(drop=True)


def gerar_relatorio_backtest(df: pd.DataFrame, comparativo: pd.DataFrame) -> str:
    linhas = [
        "# BACKTEST ELITE SCORE V3",
        "",
        f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Base",
        "",
        f"- Arquivo: `{CAMINHO_BASE}`",
        f"- Total de concursos oficiais: {len(df)}",
        f"- Concursos auditados: {len(df) - 1}",
        "",
        "## Comparativo",
        "",
        "| Motor | Jogos/concurso | Melhor | 11 pts | Taxa 11 | 12 pts | Taxa 12 | 13 pts | Taxa 13 | 14 pts | Taxa 14 | 15 pts | Taxa 15 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for _, row in comparativo.iterrows():
        linhas.append(
            f"| {row['Motor']} | {row['Jogos por concurso']} | {row['Melhor acerto']} | "
            f"{row['Jogos com 11 pontos']} | {row['Taxa 11 pontos (%)']}% | "
            f"{row['Jogos com 12 pontos']} | {row['Taxa 12 pontos (%)']}% | "
            f"{row['Jogos com 13 pontos']} | {row['Taxa 13 pontos (%)']}% | "
            f"{row['Jogos com 14 pontos']} | {row['Taxa 14 pontos (%)']}% | "
            f"{row['Jogos com 15 pontos']} | {row['Taxa 15 pontos (%)']}% |"
        )
    v1 = comparativo[comparativo["Motor"] == "Motor Elite V1"].iloc[0]
    aleatorio = comparativo[comparativo["Motor"] == "Aleatorio"].iloc[0]
    v3top10 = comparativo[comparativo["Motor"] == "Elite Score V3 Top 10"].iloc[0]
    meta_13_v1 = int(v3top10["Jogos com 13 pontos"]) > int(v1["Jogos com 13 pontos"])
    meta_13_aleatorio = int(v3top10["Jogos com 13 pontos"]) > int(aleatorio["Jogos com 13 pontos"])
    meta_14 = int(v3top10["Jogos com 14 pontos"]) > 0
    meta_15 = int(v3top10["Jogos com 15 pontos"]) > 0
    linhas += [
        "",
        "## Meta",
        "",
        f"- Superar 13 pontos do V1 no Top 10: {'SIM' if meta_13_v1 else 'NAO'}",
        f"- Superar 13 pontos do Aleatorio no Top 10: {'SIM' if meta_13_aleatorio else 'NAO'}",
        f"- Encontrar 14 pontos no Top 10: {'SIM' if meta_14 else 'NAO'}",
        f"- Encontrar 15 pontos no Top 10: {'SIM' if meta_15 else 'NAO'}",
        "",
        "## Observacao",
        "",
        "Este V3 usa aprendizado historico global dos jogos vencedores minerados no portfolio V2.",
        "O objetivo e diagnosticar e reconstruir o ranking; a proxima etapa recomendada e validar uma versao sem vazamento temporal por janela de treino.",
        "",
        "## Arquivos gerados",
        "",
        "- `exports/ELITE_SCORE_V3.md`",
        "- `exports/BACKTEST_ELITE_SCORE_V3.md`",
        "- `exports/APRENDIZADO_JOGOS_VENCEDORES.csv`",
        "- `exports/backtest_elite_score_v3.csv`",
    ]
    return "\n".join(linhas)


def main() -> None:
    PASTA_EXPORTS.mkdir(parents=True, exist_ok=True)
    df = carregar_base()
    caminho_aprendizado = PASTA_EXPORTS / "APRENDIZADO_JOGOS_VENCEDORES.csv"
    if caminho_aprendizado.exists():
        aprendizado = pd.read_csv(caminho_aprendizado, encoding="utf-8-sig")
    else:
        aprendizado = minerar_jogos_vencedores(df)
        aprendizado.to_csv(caminho_aprendizado, index=False, encoding="utf-8-sig")
    modelo = construir_modelo_aprendizado(aprendizado)
    detalhe_v3, resumo_v3 = executar_backtest_v3(df, modelo)
    detalhe_v3.to_csv(PASTA_EXPORTS / "backtest_elite_score_v3.csv", index=False, encoding="utf-8-sig")
    comparativo = montar_comparativo_final(resumo_v3)
    comparativo.to_csv(PASTA_EXPORTS / "comparativo_elite_score_v3.csv", index=False, encoding="utf-8-sig")
    (PASTA_EXPORTS / "ELITE_SCORE_V3.md").write_text(gerar_elite_score_v3(aprendizado, modelo), encoding="utf-8")
    (PASTA_EXPORTS / "BACKTEST_ELITE_SCORE_V3.md").write_text(
        gerar_relatorio_backtest(df, comparativo),
        encoding="utf-8",
    )
    print("BACKTEST_ELITE_SCORE_V3_OK")
    print(comparativo.to_string(index=False))


if __name__ == "__main__":
    main()
