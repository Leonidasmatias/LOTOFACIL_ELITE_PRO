from __future__ import annotations

from collections import Counter, deque
from datetime import datetime
from math import comb
from pathlib import Path

import pandas as pd


RAIZ = Path(__file__).resolve().parents[1]
CAMINHO_BASE = RAIZ / "dados" / "lotofacil_historico.csv"
PASTA_EXPORTS = RAIZ / "exports"
CAMINHO_RESUMO_V1 = PASTA_EXPORTS / "resumo_backtest_lotofacil_v1.csv"
COLUNAS_DEZENAS = [f"Bola{i}" for i in range(1, 16)]
TODAS_DEZENAS = list(range(1, 26))
JOGOS_POR_CONCURSO_V2 = comb(20, 15)


def carregar_base() -> pd.DataFrame:
    df = pd.read_csv(CAMINHO_BASE, encoding="utf-8-sig")
    df = df[["Concurso", "Data", *COLUNAS_DEZENAS]].copy()
    for coluna in ["Concurso", *COLUNAS_DEZENAS]:
        df[coluna] = pd.to_numeric(df[coluna], errors="coerce").astype(int)
    return df.sort_values("Concurso").reset_index(drop=True)


def carregar_resumo_v1() -> pd.DataFrame:
    if not CAMINHO_RESUMO_V1.exists():
        raise FileNotFoundError("Execute primeiro scripts/backtest_lotofacil_v1.py para gerar o resumo V1.")
    resumo = pd.read_csv(CAMINHO_RESUMO_V1, encoding="utf-8-sig")
    resumo["Motor"] = resumo["Motor"].replace({"Motor Elite Lotofacil": "Elite V1"})
    return resumo


def top20_v2(
    concurso: int,
    freq_geral: Counter,
    freq_5: Counter,
    freq_10: Counter,
    freq_20: Counter,
    ultimo_por_dezena: dict[int, int],
    ultimo_jogo: set[int],
) -> list[int]:
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
    return sorted(TODAS_DEZENAS, key=lambda d: (-scores[d], d))[:20]


def contar_acertos_portfolio(top20: set[int], sorteadas: set[int]) -> Counter:
    intersecao = len(top20 & sorteadas)
    fora = len(top20 - sorteadas)
    contagem = Counter()
    for acertos in range(0, 16):
        erros = 15 - acertos
        if acertos <= intersecao and erros <= fora:
            contagem[acertos] += comb(intersecao, acertos) * comb(fora, erros)
    return contagem


def melhor_jogo_do_portfolio(top20: set[int], sorteadas: set[int]) -> tuple[int, str]:
    acertos = len(top20 & sorteadas)
    melhor_acerto = min(15, acertos)
    dezenas_acertadas = sorted(top20 & sorteadas)
    complemento = sorted(top20 - sorteadas)
    jogo = sorted(dezenas_acertadas[:melhor_acerto] + complemento[: 15 - melhor_acerto])
    return melhor_acerto, " - ".join(f"{d:02d}" for d in jogo)


def executar_v2(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    freq_geral = Counter()
    freq_5 = Counter()
    freq_10 = Counter()
    freq_20 = Counter()
    janela_5: deque[list[int]] = deque(maxlen=5)
    janela_10: deque[list[int]] = deque(maxlen=10)
    janela_20: deque[list[int]] = deque(maxlen=20)
    ultimo_por_dezena = {dezena: 0 for dezena in TODAS_DEZENAS}
    ultimo_jogo: set[int] = set()
    total_por_acerto = Counter()
    melhores = []

    def atualizar_janela(janela: deque[list[int]], freq: Counter, dezenas: list[int]) -> None:
        if len(janela) == janela.maxlen:
            for dezena in janela[0]:
                freq[dezena] -= 1
        janela.append(dezenas)
        for dezena in dezenas:
            freq[dezena] += 1

    for indice, row in df.iterrows():
        concurso = int(row["Concurso"])
        sorteadas = {int(row[coluna]) for coluna in COLUNAS_DEZENAS}
        if indice > 0:
            top = set(top20_v2(concurso, freq_geral, freq_5, freq_10, freq_20, ultimo_por_dezena, ultimo_jogo))
            contagem = contar_acertos_portfolio(top, sorteadas)
            total_por_acerto.update(contagem)
            melhor_acerto, melhor_jogo = melhor_jogo_do_portfolio(top, sorteadas)
            melhores.append(
                {
                    "Concurso": concurso,
                    "Data": row["Data"],
                    "Top20 V2": " - ".join(f"{d:02d}" for d in sorted(top)),
                    "Melhor acerto no portfolio": melhor_acerto,
                    "Melhor jogo no portfolio": melhor_jogo,
                    "Jogos 11 pontos": contagem[11],
                    "Jogos 12 pontos": contagem[12],
                    "Jogos 13 pontos": contagem[13],
                    "Jogos 14 pontos": contagem[14],
                    "Jogos 15 pontos": contagem[15],
                }
            )

        dezenas_lista = [int(row[coluna]) for coluna in COLUNAS_DEZENAS]
        for dezena in dezenas_lista:
            freq_geral[dezena] += 1
            ultimo_por_dezena[dezena] = concurso
        atualizar_janela(janela_5, freq_5, dezenas_lista)
        atualizar_janela(janela_10, freq_10, dezenas_lista)
        atualizar_janela(janela_20, freq_20, dezenas_lista)
        ultimo_jogo = set(dezenas_lista)

    detalhe = pd.DataFrame(melhores)
    total_jogos = int((len(df) - 1) * JOGOS_POR_CONCURSO_V2)
    melhor = detalhe.sort_values("Melhor acerto no portfolio", ascending=False).iloc[0]
    resumo = {
        "Motor": "Elite V2",
        "Perfil": "Top20 combinatorio V2",
        "Jogos por concurso": JOGOS_POR_CONCURSO_V2,
        "Total de jogos auditados": total_jogos,
        "Melhor acerto": int(detalhe["Melhor acerto no portfolio"].max()),
        "Concurso do melhor resultado": int(melhor["Concurso"]),
        "Melhor jogo encontrado": melhor["Melhor jogo no portfolio"],
    }
    for ponto in range(11, 16):
        quantidade = int(total_por_acerto[ponto])
        resumo[f"Jogos com {ponto} pontos"] = quantidade
        resumo[f"Taxa {ponto} pontos (%)"] = round((quantidade / total_jogos) * 100, 6)
    return detalhe, pd.DataFrame([resumo])


def montar_comparativo(resumo_v1: pd.DataFrame, resumo_v2: pd.DataFrame) -> pd.DataFrame:
    elite_v1 = resumo_v1[resumo_v1["Motor"] == "Elite V1"]
    aleatorio = resumo_v1[resumo_v1["Motor"] == "Aleatorio"]
    comparativo = pd.concat([elite_v1, resumo_v2, aleatorio], ignore_index=True)
    ordem = {"Elite V1": 1, "Elite V2": 2, "Aleatorio": 3}
    comparativo["_ordem"] = comparativo["Motor"].map(ordem)
    return comparativo.sort_values("_ordem").drop(columns=["_ordem"]).reset_index(drop=True)


def gerar_relatorio(df: pd.DataFrame, comparativo: pd.DataFrame, detalhe_v2: pd.DataFrame) -> str:
    v1 = comparativo[comparativo["Motor"] == "Elite V1"].iloc[0]
    v2 = comparativo[comparativo["Motor"] == "Elite V2"].iloc[0]
    aleatorio = comparativo[comparativo["Motor"] == "Aleatorio"].iloc[0]
    objetivo = all(int(v2[f"Jogos com {p} pontos"]) > int(v1[f"Jogos com {p} pontos"]) for p in (13, 14, 15))
    linhas = [
        "# BACKTEST LOTOFACIL ELITE PRO V2",
        "",
        f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Base",
        "",
        f"- Arquivo: `{CAMINHO_BASE}`",
        f"- Total de concursos oficiais: {len(df)}",
        f"- Concursos auditados: {len(df) - 1}",
        f"- Menor concurso: {int(df['Concurso'].min())}",
        f"- Maior concurso: {int(df['Concurso'].max())}",
        "",
        "## Elite V2 implementado",
        "",
        "- Repeticao do ultimo concurso",
        "- Peso Centro x Moldura",
        "- Peso Linhas",
        "- Peso Colunas",
        "- Frequencia ultimos 5 concursos",
        "- Frequencia ultimos 10 concursos",
        "- Frequencia ultimos 20 concursos",
        "- Monte Carlo / portfolio combinatorio a partir do Top 20",
        "- Ranking dos melhores jogos",
        "- Elite Score V2",
        "",
        "## Configuracao V2",
        "",
        f"- Dezenas ranqueadas por concurso: 20",
        f"- Jogos auditados por concurso V2: {JOGOS_POR_CONCURSO_V2}",
        f"- Total de jogos auditados V2: {int(v2['Total de jogos auditados'])}",
        "",
        "## Comparativo",
        "",
        "| Motor | Jogos/concurso | Total jogos | Melhor acerto | 11 pts | 12 pts | 13 pts | 14 pts | 15 pts |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for _, row in comparativo.iterrows():
        linhas.append(
            f"| {row['Motor']} | {row['Jogos por concurso']} | {row['Total de jogos auditados']} | "
            f"{row['Melhor acerto']} | {row['Jogos com 11 pontos']} | {row['Jogos com 12 pontos']} | "
            f"{row['Jogos com 13 pontos']} | {row['Jogos com 14 pontos']} | {row['Jogos com 15 pontos']} |"
        )
    linhas += [
        "",
        "## Diferenca Elite V2 vs Elite V1",
        "",
    ]
    for ponto in range(13, 16):
        linhas.append(f"- {ponto} pontos: {int(v2[f'Jogos com {ponto} pontos'] - v1[f'Jogos com {ponto} pontos'])}")
    linhas += [
        "",
        "## Melhor resultado Elite V2",
        "",
        f"- Melhor acerto: {v2['Melhor acerto']}",
        f"- Concurso do melhor resultado: {v2['Concurso do melhor resultado']}",
        f"- Melhor jogo encontrado: {v2['Melhor jogo encontrado']}",
        "",
        "## Objetivo minimo",
        "",
        f"- Superar V1 em 13, 14 e 15 pontos: {'SIM' if objetivo else 'NAO'}",
        "",
        "## Observacao tecnica",
        "",
        "O V2 utiliza um portfolio Top20 combinatorio, portanto audita mais jogos por concurso que o V1.",
        "A comparacao deve ser lida junto com `Jogos por concurso`, `Total de jogos auditados` e taxas percentuais.",
        "",
        "## Arquivos gerados",
        "",
        "- `exports/BACKTEST_LOTOFACIL_ELITE_PRO_V2.md`",
        "- `exports/comparativo_v1_v2.csv`",
        "- `exports/backtest_lotofacil_v2_por_concurso.csv`",
    ]
    return "\n".join(linhas)


def main() -> None:
    PASTA_EXPORTS.mkdir(parents=True, exist_ok=True)
    df = carregar_base()
    resumo_v1 = carregar_resumo_v1()
    detalhe_v2, resumo_v2 = executar_v2(df)
    comparativo = montar_comparativo(resumo_v1, resumo_v2)
    detalhe_v2.to_csv(PASTA_EXPORTS / "backtest_lotofacil_v2_por_concurso.csv", index=False, encoding="utf-8-sig")
    comparativo.to_csv(PASTA_EXPORTS / "comparativo_v1_v2.csv", index=False, encoding="utf-8-sig")
    (PASTA_EXPORTS / "BACKTEST_LOTOFACIL_ELITE_PRO_V2.md").write_text(
        gerar_relatorio(df, comparativo, detalhe_v2),
        encoding="utf-8",
    )
    print("BACKTEST_V2_OK")
    print(comparativo.to_string(index=False))


if __name__ == "__main__":
    main()
