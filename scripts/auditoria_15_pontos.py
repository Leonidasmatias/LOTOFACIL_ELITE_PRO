from __future__ import annotations

from collections import Counter
from datetime import datetime
from pathlib import Path
from statistics import mean

import pandas as pd


RAIZ = Path(__file__).resolve().parents[1]
PASTA_EXPORTS = RAIZ / "exports"
CAMINHO_APRENDIZADO = PASTA_EXPORTS / "APRENDIZADO_JOGOS_VENCEDORES.csv"
CAMINHO_CSV = PASTA_EXPORTS / "AUDITORIA_15_PONTOS.csv"
CAMINHO_MD = PASTA_EXPORTS / "AUDITORIA_15_PONTOS.md"

NUMERICAS_BASE = [
    "soma_total",
    "pares",
    "impares",
    "centro",
    "moldura",
    "repeticao_anterior",
    "consecutivas",
]


def expandir_distribuicao(df: pd.DataFrame, coluna: str, prefixo: str, tamanho: int) -> pd.DataFrame:
    partes = df[coluna].astype(str).str.split("-", expand=True).iloc[:, :tamanho]
    partes = partes.apply(pd.to_numeric, errors="coerce").fillna(0).astype(int)
    partes.columns = [f"{prefixo}_{i}" for i in range(1, tamanho + 1)]
    return partes


def preparar_features(df: pd.DataFrame) -> pd.DataFrame:
    base = df.copy()
    for coluna in NUMERICAS_BASE:
        base[coluna] = pd.to_numeric(base[coluna], errors="coerce")
    partes = [
        expandir_distribuicao(base, "linhas", "linha", 5),
        expandir_distribuicao(base, "colunas", "coluna", 5),
        expandir_distribuicao(base, "quadrantes", "quadrante", 4),
    ]
    return pd.concat([base, *partes], axis=1)


def dezenas_do_jogo(jogo: str) -> list[int]:
    return [int(parte.strip()) for parte in str(jogo).split("-") if parte.strip()]


def perfil_medio(df: pd.DataFrame, colunas: list[str]) -> tuple[pd.Series, pd.Series]:
    media = df[colunas].mean(numeric_only=True)
    desvio = df[colunas].std(numeric_only=True).replace(0, 1)
    return media, desvio


def distancia_linha(row: pd.Series, media: pd.Series, desvio: pd.Series, colunas: list[str]) -> float:
    z = ((row[colunas] - media) / desvio).astype(float)
    return round(float((z.pow(2).sum()) ** 0.5), 4)


def maiores_desvios(row: pd.Series, media: pd.Series, desvio: pd.Series, colunas: list[str], limite: int = 5) -> str:
    itens = []
    for coluna in colunas:
        z = float((row[coluna] - media[coluna]) / desvio[coluna])
        direcao = "acima" if z > 0 else "abaixo"
        itens.append((abs(z), f"{coluna}: {row[coluna]} ({direcao} da media {media[coluna]:.2f}, z={z:.2f})"))
    return " | ".join(texto for _, texto in sorted(itens, reverse=True)[:limite])


def moda_textual(df: pd.DataFrame, coluna: str, limite: int = 5) -> list[tuple[str, int]]:
    contagem = Counter(df[coluna].astype(str))
    return contagem.most_common(limite)


def categorias_ausentes(df_total: pd.DataFrame, df_15: pd.DataFrame, coluna: str, limite: int = 8) -> list[tuple[str, int]]:
    valores_15 = set(df_15[coluna].astype(str))
    contagem_total = Counter(df_total[coluna].astype(str))
    return [(valor, qtd) for valor, qtd in contagem_total.most_common() if valor not in valores_15][:limite]


def formatar_lista_pares(pares: list[tuple[str, int]]) -> str:
    return ", ".join(f"{valor} ({qtd})" for valor, qtd in pares) if pares else "Nenhuma"


def gerar_relatorio(
    aprendizado: pd.DataFrame,
    jogos_15: pd.DataFrame,
    auditoria: pd.DataFrame,
    colunas_distancia: list[str],
) -> str:
    media_total = aprendizado[colunas_distancia].mean(numeric_only=True)
    media_15 = jogos_15[colunas_distancia].mean(numeric_only=True)
    diffs = []
    for coluna in colunas_distancia:
        diffs.append((abs(float(media_15[coluna] - media_total[coluna])), coluna, media_15[coluna], media_total[coluna]))
    principais = sorted(diffs, reverse=True)[:12]

    linhas = [
        "# AUDITORIA DOS 15 PONTOS ENCONTRADOS",
        "",
        f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Fonte",
        "",
        f"- Arquivo: `{CAMINHO_APRENDIZADO}`",
        f"- Total do aprendizado V3: {len(aprendizado)} jogos 13+",
        f"- Jogos com 15 pontos localizados: {len(jogos_15)}",
        "",
        "## DNA medio dos 15 pontos",
        "",
        f"- Soma media: {media_15['soma_total']:.2f}",
        f"- Pares/impares medio: {media_15['pares']:.2f}/{media_15['impares']:.2f}",
        f"- Centro/moldura medio: {media_15['centro']:.2f}/{media_15['moldura']:.2f}",
        f"- Repeticao media do concurso anterior: {media_15['repeticao_anterior']:.2f}",
        f"- Dezenas consecutivas media: {media_15['consecutivas']:.2f}",
        f"- Distancia media para perfil V3: {auditoria['distancia_perfil_medio_v3'].mean():.4f}",
        f"- Menor distancia: {auditoria['distancia_perfil_medio_v3'].min():.4f}",
        f"- Maior distancia: {auditoria['distancia_perfil_medio_v3'].max():.4f}",
        "",
        "## Variaveis mais presentes nos 15 pontos",
        "",
        f"- Soma bin: {formatar_lista_pares(moda_textual(jogos_15, 'soma_bin'))}",
        f"- Pares: {formatar_lista_pares(moda_textual(jogos_15, 'pares'))}",
        f"- Centro: {formatar_lista_pares(moda_textual(jogos_15, 'centro'))}",
        f"- Repeticao anterior: {formatar_lista_pares(moda_textual(jogos_15, 'repeticao_anterior'))}",
        f"- Linhas: {formatar_lista_pares(moda_textual(jogos_15, 'linhas'))}",
        f"- Colunas: {formatar_lista_pares(moda_textual(jogos_15, 'colunas'))}",
        f"- Quadrantes: {formatar_lista_pares(moda_textual(jogos_15, 'quadrantes'))}",
        f"- Consecutivas: {formatar_lista_pares(moda_textual(jogos_15, 'consecutivas'))}",
        "",
        "## Variaveis mais diferentes do perfil medio V3",
        "",
    ]
    for _, coluna, media15, mediatotal in principais:
        linhas.append(f"- {coluna}: 15 pontos = {media15:.2f}; perfil V3 = {mediatotal:.2f}")

    linhas += [
        "",
        "## Variaveis ausentes nos 15 pontos",
        "",
        "Categorias frequentes no aprendizado V3 que nao apareceram entre os 15 pontos:",
        "",
    ]
    for coluna in ["soma_bin", "pares", "centro", "repeticao_anterior", "linhas", "colunas", "quadrantes", "consecutivas"]:
        linhas.append(f"- {coluna}: {formatar_lista_pares(categorias_ausentes(aprendizado, jogos_15, coluna, 5))}")

    linhas += [
        "",
        "## Jogos de 15 pontos",
        "",
        "| Concurso | Data | Jogo vencedor | Soma | Pares/Impares | Centro/Moldura | Linhas | Colunas | Quadrantes | Repeticao | Consecutivas | Distancia |",
        "|---:|---|---|---:|---|---|---|---|---|---:|---:|---:|",
    ]
    for _, row in auditoria.sort_values(["Concurso", "Jogo vencedor"]).iterrows():
        linhas.append(
            f"| {int(row['Concurso'])} | {row['Data']} | {row['Jogo vencedor']} | {int(row['soma_total'])} | "
            f"{int(row['pares'])}/{int(row['impares'])} | {int(row['centro'])}/{int(row['moldura'])} | "
            f"{row['linhas']} | {row['colunas']} | {row['quadrantes']} | {int(row['repeticao_anterior'])} | "
            f"{int(row['consecutivas'])} | {row['distancia_perfil_medio_v3']} |"
        )

    linhas += [
        "",
        "## Conclusao",
        "",
        "Os 15 pontos encontrados tendem a seguir um perfil muito equilibrado de linhas/colunas, forte repeticao do concurso anterior e concentracao em faixas especificas de soma, paridade, centro/moldura e consecutivas. O CSV detalha a distancia individual de cada jogo para o perfil medio do aprendizado V3 e os maiores desvios por jogo.",
        "",
        "## Arquivos gerados",
        "",
        "- `exports/AUDITORIA_15_PONTOS.csv`",
        "- `exports/AUDITORIA_15_PONTOS.md`",
    ]
    return "\n".join(linhas)


def main() -> None:
    PASTA_EXPORTS.mkdir(parents=True, exist_ok=True)
    aprendizado_original = pd.read_csv(CAMINHO_APRENDIZADO, encoding="utf-8-sig")
    aprendizado = preparar_features(aprendizado_original)
    jogos_15 = aprendizado[aprendizado["Acertos"] == 15].copy()
    if jogos_15.empty:
        raise RuntimeError("Nenhum jogo com 15 pontos encontrado no aprendizado.")

    colunas_distancia = [
        *NUMERICAS_BASE,
        *[f"linha_{i}" for i in range(1, 6)],
        *[f"coluna_{i}" for i in range(1, 6)],
        *[f"quadrante_{i}" for i in range(1, 5)],
    ]
    media, desvio = perfil_medio(aprendizado, colunas_distancia)

    auditoria = jogos_15.copy()
    auditoria["distancia_perfil_medio_v3"] = auditoria.apply(lambda row: distancia_linha(row, media, desvio, colunas_distancia), axis=1)
    auditoria["maiores_desvios_vs_perfil_medio"] = auditoria.apply(
        lambda row: maiores_desvios(row, media, desvio, colunas_distancia),
        axis=1,
    )
    auditoria["dezenas"] = auditoria["Jogo"].apply(lambda jogo: " ".join(f"{d:02d}" for d in dezenas_do_jogo(jogo)))
    auditoria = auditoria.rename(columns={"Jogo": "Jogo vencedor"})

    colunas_saida = [
        "Concurso",
        "Data",
        "Jogo vencedor",
        "dezenas",
        "soma_total",
        "pares",
        "impares",
        "centro",
        "moldura",
        "linhas",
        "colunas",
        "quadrantes",
        "repeticao_anterior",
        "consecutivas",
        "distancia_perfil_medio_v3",
        "maiores_desvios_vs_perfil_medio",
        *[f"linha_{i}" for i in range(1, 6)],
        *[f"coluna_{i}" for i in range(1, 6)],
        *[f"quadrante_{i}" for i in range(1, 5)],
        "soma_bin",
        "freq_curta_bin",
        "freq_20_bin",
        "freq_longa_bin",
    ]
    auditoria[colunas_saida].sort_values(["Concurso", "Jogo vencedor"]).to_csv(CAMINHO_CSV, index=False, encoding="utf-8-sig")
    CAMINHO_MD.write_text(gerar_relatorio(aprendizado, jogos_15, auditoria, colunas_distancia), encoding="utf-8")
    print("AUDITORIA_15_PONTOS_OK")
    print(auditoria[colunas_saida].sort_values(["Concurso", "Jogo vencedor"]).to_string(index=False))


if __name__ == "__main__":
    main()
