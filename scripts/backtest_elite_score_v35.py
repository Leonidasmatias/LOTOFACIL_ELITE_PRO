from __future__ import annotations

from collections import Counter, deque
from datetime import datetime
from heapq import heappush, heapreplace
from itertools import combinations
from pathlib import Path

import pandas as pd


RAIZ = Path(__file__).resolve().parents[1]
PASTA_EXPORTS = RAIZ / "exports"
CAMINHO_BASE = RAIZ / "dados" / "lotofacil_historico.csv"
CAMINHO_AUDITORIA_15 = PASTA_EXPORTS / "AUDITORIA_15_PONTOS.csv"
CAMINHO_APRENDIZADO = PASTA_EXPORTS / "APRENDIZADO_JOGOS_VENCEDORES.csv"
CAMINHO_COMPARATIVO_V3 = PASTA_EXPORTS / "comparativo_elite_score_v3.csv"

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


def carregar_dna_15() -> dict:
    audit = pd.read_csv(CAMINHO_AUDITORIA_15, encoding="utf-8-sig")
    aprendizado = pd.read_csv(CAMINHO_APRENDIZADO, encoding="utf-8-sig")
    dna = {
        "linhas": Counter(audit["linhas"].astype(str)),
        "colunas": Counter(audit["colunas"].astype(str)),
        "quadrantes": Counter(audit["quadrantes"].astype(str)),
        "pares": Counter(audit["pares"].astype(str)),
        "centro": Counter(audit["centro"].astype(str)),
        "repeticao": Counter(audit["repeticao_anterior"].astype(str)),
        "consecutivas": Counter(audit["consecutivas"].astype(str)),
        "soma": Counter(audit["soma_bin"].astype(str)),
        "perfis": [],
        "assinaturas": Counter(),
        "dezenas": Counter(),
        "v3_comuns": {},
        "v3_comuns_ausentes": {},
    }
    for _, row in audit.iterrows():
        for dezena in str(row["dezenas"]).split():
            dna["dezenas"][int(dezena)] += 1
        assinatura = (
            str(row["soma_bin"]),
            str(row["pares"]),
            str(row["centro"]),
            str(row["repeticao_anterior"]),
            str(row["consecutivas"]),
            str(row["linhas"]),
            str(row["colunas"]),
            str(row["quadrantes"]),
        )
        dna["assinaturas"][assinatura] += 1
    for coluna in ["linhas", "colunas", "quadrantes", "soma_bin", "pares", "centro", "repeticao_anterior", "consecutivas"]:
        dna["v3_comuns"][coluna] = [valor for valor, _ in Counter(aprendizado[coluna].astype(str)).most_common(8)]
    mapa_15 = {
        "linhas": set(dna["linhas"].keys()),
        "colunas": set(dna["colunas"].keys()),
        "quadrantes": set(dna["quadrantes"].keys()),
        "soma_bin": set(dna["soma"].keys()),
        "pares": set(dna["pares"].keys()),
        "centro": set(dna["centro"].keys()),
        "repeticao_anterior": set(dna["repeticao"].keys()),
        "consecutivas": set(dna["consecutivas"].keys()),
    }
    for coluna, valores in dna["v3_comuns"].items():
        dna["v3_comuns_ausentes"][coluna] = set(valores) - mapa_15[coluna]
    return dna


def score_faixa(valor: int, minimo: int, maximo: int, peso: float, queda: float = 0.35) -> float:
    if minimo <= valor <= maximo:
        return peso
    distancia = min(abs(valor - minimo), abs(valor - maximo))
    return max(0.0, peso - (distancia * queda))


def score_dna_15_pontos(features: dict, dna: dict, bonus_assinatura: bool = True) -> float:
    score = 0.0
    score += score_faixa(features["soma_total"], 190, 210, 18.0, 0.7)
    score += score_faixa(features["repeticao"], 9, 11, 20.0, 2.5)
    score += score_faixa(features["consecutivas"], 8, 10, 16.0, 2.0)
    score += score_faixa(features["centro"], 5, 6, 15.0, 4.0)
    score += score_faixa(features["pares"], 7, 8, 10.0, 2.5)

    score += dna["linhas"][features["linhas"]] * 9.0
    score += dna["colunas"][features["colunas"]] * 9.0
    score += dna["quadrantes"][features["quadrantes"]] * 8.0
    score += dna["soma"].get(features["soma_bin"], 0) * 4.0
    score += dna["repeticao"].get(str(features["repeticao"]), 0) * 5.0
    score += dna["consecutivas"].get(str(features["consecutivas"]), 0) * 4.0

    assinatura = (
        features["soma_bin"],
        str(features["pares"]),
        str(features["centro"]),
        str(features["repeticao"]),
        str(features["consecutivas"]),
        features["linhas"],
        features["colunas"],
        features["quadrantes"],
    )
    if bonus_assinatura:
        score += dna["assinaturas"][assinatura] * 85.0

    if features["linhas"] == "3-3-3-3-3":
        score -= 35.0
    if features["colunas"] == "3-3-3-3-3":
        score -= 35.0
    for coluna, valor in (
        ("linhas", features["linhas"]),
        ("colunas", features["colunas"]),
        ("quadrantes", features["quadrantes"]),
        ("soma_bin", features["soma_bin"]),
        ("pares", str(features["pares"])),
        ("centro", str(features["centro"])),
        ("repeticao_anterior", str(features["repeticao"])),
        ("consecutivas", str(features["consecutivas"])),
    ):
        if valor in dna["v3_comuns_ausentes"][coluna]:
            score -= 6.0
    return round(score, 6)


def top_jogos_v35(score_dezenas: dict[int, float], dna: dict, ultimo_jogo: set[int], limite: int = 10) -> list[tuple[float, tuple[int, ...]]]:
    top20 = sorted(TODAS_DEZENAS, key=lambda d: (-score_dezenas[d], d))[:20]
    top20_set = set(top20)
    soma_total = sum(top20)
    pares_total = sum(1 for d in top20 if d % 2 == 0)
    centro_total = sum(1 for d in top20 if d in CENTRO)
    repeticao_total = len(top20_set & ultimo_jogo)
    dna_dezena_total = sum(dna["dezenas"][d] for d in top20)
    linhas_total = [0, 0, 0, 0, 0]
    colunas_total = [0, 0, 0, 0, 0]
    quadrantes_total = [0, 0, 0, 0]
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
            "par": int(dezena % 2 == 0),
            "centro": int(dezena in CENTRO),
            "repeticao": int(dezena in ultimo_jogo),
            "linha": linha - 1,
            "coluna": coluna - 1,
            "quadrante": quad - 1,
            "dna_dezena": dna["dezenas"][dezena],
        }

    heap_exato: list[tuple[float, tuple[int, ...], tuple[int, ...]]] = []
    heap_amplo: list[tuple[float, tuple[int, ...], tuple[int, ...]]] = []
    for excluidas in combinations(top20, 5):
        excl_soma = 0
        excl_pares = 0
        excl_centro = 0
        excl_repeticao = 0
        excl_dna_dezena = 0
        excl_mask = 0
        linhas = linhas_total.copy()
        colunas = colunas_total.copy()
        quadrantes = quadrantes_total.copy()
        for dezena in excluidas:
            dados = meta[dezena]
            excl_soma += dezena
            excl_pares += dados["par"]
            excl_centro += dados["centro"]
            excl_repeticao += dados["repeticao"]
            excl_dna_dezena += dados["dna_dezena"]
            excl_mask |= 1 << dezena
            linhas[dados["linha"]] -= 1
            colunas[dados["coluna"]] -= 1
            quadrantes[dados["quadrante"]] -= 1

        included_mask = top20_mask & ~excl_mask
        soma = soma_total - excl_soma
        features = {
            "soma_total": soma,
            "soma_bin": f"{(soma // 10) * 10}-{((soma // 10) * 10) + 9}",
            "pares": pares_total - excl_pares,
            "centro": centro_total - excl_centro,
            "repeticao": repeticao_total - excl_repeticao,
            "consecutivas": (included_mask & (included_mask >> 1)).bit_count(),
            "linhas": "-".join(map(str, linhas)),
            "colunas": "-".join(map(str, colunas)),
            "quadrantes": "-".join(map(str, quadrantes)),
        }
        bonus_dezenas = (dna_dezena_total - excl_dna_dezena) * 1.85
        score_exato = score_dna_15_pontos(features, dna, bonus_assinatura=True) + bonus_dezenas
        score_amplo = score_dna_15_pontos(features, dna, bonus_assinatura=False) + bonus_dezenas
        item_exato = (score_exato, tuple(-d for d in excluidas), tuple(excluidas))
        item_amplo = (score_amplo, tuple(-d for d in excluidas), tuple(excluidas))
        if len(heap_exato) < limite:
            heappush(heap_exato, item_exato)
        elif item_exato > heap_exato[0]:
            heapreplace(heap_exato, item_exato)
        if len(heap_amplo) < limite:
            heappush(heap_amplo, item_amplo)
        elif item_amplo > heap_amplo[0]:
            heapreplace(heap_amplo, item_amplo)

    ordenado_exato = sorted(heap_exato, reverse=True)
    ordenado_amplo = sorted(heap_amplo, reverse=True)
    cotas = {1: (1, 0), 5: (3, 2), 10: (3, 7)}
    qtd_exato, qtd_amplo = cotas.get(limite, (min(3, limite), max(0, limite - 3)))
    saida = []
    usados = set()

    def adicionar(origem: list[tuple[float, tuple[int, ...], tuple[int, ...]]], quantidade: int, fator: float) -> None:
        for score, _, excluidas in origem:
            jogo = tuple(sorted(top20_set - set(excluidas)))
            if jogo in usados:
                continue
            usados.add(jogo)
            saida.append((round(score * fator, 6), jogo))
            if len(saida) >= quantidade:
                break

    adicionar(ordenado_exato, qtd_exato, 1.0)
    alvo = qtd_exato + qtd_amplo
    adicionar(ordenado_amplo, alvo, 0.92)
    if len(saida) < limite:
        adicionar(ordenado_exato + ordenado_amplo, limite, 0.85)
    return saida[:limite]


def executar_backtest_v35(df: pd.DataFrame, dna: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    registros = []
    for row, concurso, sorteadas, freq_geral, freq_5, freq_10, freq_20, ultimo_por_dezena, ultimo_jogo in preparar_estados(df):
        scores = montar_scores_v2(concurso, freq_geral, freq_5, freq_10, freq_20, ultimo_por_dezena, ultimo_jogo)
        melhores_10 = top_jogos_v35(scores, dna, ultimo_jogo, max(LIMITES_TOP))
        for limite in LIMITES_TOP:
            for posicao, (score, jogo) in enumerate(melhores_10[:limite], start=1):
                acertos = len(set(jogo) & sorteadas)
                registros.append(
                    {
                        "Motor": f"Elite Score V3.5 Top {limite}",
                        "Concurso": concurso,
                        "Data": row["Data"],
                        "Ranking": posicao,
                        "Jogo": " - ".join(f"{d:02d}" for d in jogo),
                        "Elite Score V3.5": score,
                        "Acertos": acertos,
                    }
                )
    detalhe = pd.DataFrame(registros)
    resumo = []
    for limite in LIMITES_TOP:
        motor = f"Elite Score V3.5 Top {limite}"
        grupo = detalhe[detalhe["Motor"] == motor]
        melhor = grupo.sort_values(["Acertos", "Elite Score V3.5"], ascending=[False, False]).iloc[0]
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


def montar_comparativo(resumo_v35: pd.DataFrame) -> pd.DataFrame:
    base = pd.read_csv(CAMINHO_COMPARATIVO_V3, encoding="utf-8-sig")
    comparativo = pd.concat([base, resumo_v35], ignore_index=True)
    ordem = {
        "Motor Elite V1": 1,
        "Elite V2 Top 1": 2,
        "Elite V2 Top 5": 3,
        "Elite V2 Top 10": 4,
        "Elite Score V3 Top 1": 5,
        "Elite Score V3 Top 5": 6,
        "Elite Score V3 Top 10": 7,
        "Elite Score V3.5 Top 1": 8,
        "Elite Score V3.5 Top 5": 9,
        "Elite Score V3.5 Top 10": 10,
        "Aleatorio": 11,
    }
    comparativo["_ordem"] = comparativo["Motor"].map(ordem)
    return comparativo.sort_values("_ordem").drop(columns=["_ordem"]).reset_index(drop=True)


def gerar_relatorio(comparativo: pd.DataFrame, dna: dict) -> str:
    v3_top10 = comparativo[comparativo["Motor"] == "Elite Score V3 Top 10"].iloc[0]
    v35_top10 = comparativo[comparativo["Motor"] == "Elite Score V3.5 Top 10"].iloc[0]
    linhas = [
        "# ELITE SCORE V3.5",
        "",
        f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Objetivo",
        "",
        "Criar um ranking especializado para 14 e 15 pontos usando exclusivamente os 15 jogos perfeitos auditados.",
        "",
        "## score_dna_15_pontos()",
        "",
        "- Soma ideal: 190-210",
        "- Repeticao ideal: 9-11",
        "- Consecutivas ideal: 8-10",
        "- Centro ideal: 5-6",
        "- Bonus para linhas, colunas e quadrantes mais frequentes nos 15 pontos",
        "- Penalizacao para 3-3-3-3-3 e para padroes muito comuns do V3 ausentes nos 15 pontos",
        "",
        "## DNA usado",
        "",
        f"- Linhas mais frequentes: {dna['linhas'].most_common(5)}",
        f"- Colunas mais frequentes: {dna['colunas'].most_common(5)}",
        f"- Quadrantes mais frequentes: {dna['quadrantes'].most_common(5)}",
        "",
        "## Comparativo",
        "",
        "| Motor | Jogos/concurso | Melhor | 13 pts | 14 pts | 15 pts |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for _, row in comparativo.iterrows():
        linhas.append(
            f"| {row['Motor']} | {row['Jogos por concurso']} | {row['Melhor acerto']} | "
            f"{row['Jogos com 13 pontos']} | {row['Jogos com 14 pontos']} | {row['Jogos com 15 pontos']} |"
        )
    linhas += [
        "",
        "## Meta",
        "",
        f"- Aumentar 14 pontos vs V3 Top 10: {'SIM' if int(v35_top10['Jogos com 14 pontos']) > int(v3_top10['Jogos com 14 pontos']) else 'NAO'}",
        f"- Encontrar 15 pontos no Top 10: {'SIM' if int(v35_top10['Jogos com 15 pontos']) > 0 else 'NAO'}",
        f"- Ocorrencias adicionais de 15 pontos vs V3 Top 10: {int(v35_top10['Jogos com 15 pontos']) - int(v3_top10['Jogos com 15 pontos'])}",
        "",
        "## Arquivos gerados",
        "",
        "- `exports/ELITE_SCORE_V35.md`",
        "- `exports/BACKTEST_ELITE_SCORE_V35.md`",
        "- `exports/comparativo_elite_score_v35.csv`",
        "- `exports/backtest_elite_score_v35.csv`",
    ]
    return "\n".join(linhas)


def main() -> None:
    PASTA_EXPORTS.mkdir(parents=True, exist_ok=True)
    df = carregar_base()
    dna = carregar_dna_15()
    detalhe, resumo = executar_backtest_v35(df, dna)
    detalhe.to_csv(PASTA_EXPORTS / "backtest_elite_score_v35.csv", index=False, encoding="utf-8-sig")
    comparativo = montar_comparativo(resumo)
    comparativo.to_csv(PASTA_EXPORTS / "comparativo_elite_score_v35.csv", index=False, encoding="utf-8-sig")
    relatorio = gerar_relatorio(comparativo, dna)
    (PASTA_EXPORTS / "ELITE_SCORE_V35.md").write_text(relatorio, encoding="utf-8")
    (PASTA_EXPORTS / "BACKTEST_ELITE_SCORE_V35.md").write_text(relatorio, encoding="utf-8")
    print("BACKTEST_ELITE_SCORE_V35_OK")
    print(comparativo.to_string(index=False))


if __name__ == "__main__":
    main()
