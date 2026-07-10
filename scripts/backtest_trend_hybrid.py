"""Backtest completo (offline) do Trend Hybrid Engine 9+6.

Roda o backtest temporal sem vazamento sobre TODO o historico disponivel,
compara as quatro divisoes suportadas (8+7, 9+6, 10+5, 11+4 -- Passo 8 da
especificacao "Trend Hybrid Engine 9+6") e salva os relatorios em
``exports/``. Nao faz parte do app em execucao (mesmo papel de
``scripts/backtest_elite_score_v35.py``): e um script standalone,
reproduzivel, para auditoria e comparacao offline.

Uso:
    python scripts/backtest_trend_hybrid.py
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from src.core.trend_hybrid_backtest import otimizar_divisao
from src.repository.base_repository import CAMINHO_BASE_PADRAO, carregar_base

PASTA_EXPORTS = RAIZ / "exports"
CAMINHO_COMPARATIVO = PASTA_EXPORTS / "comparativo_trend_hybrid.csv"
CAMINHO_DETALHES = PASTA_EXPORTS / "backtest_trend_hybrid_detalhes.csv"
CAMINHO_RELATORIO = PASTA_EXPORTS / "BACKTEST_TREND_HYBRID.md"


def gerar_relatorio(comparativo, melhor_divisao: tuple[int, int]) -> str:
    linhas = [
        "# TREND HYBRID ENGINE 9+6 — BACKTEST COMPLETO",
        "",
        f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Objetivo",
        "",
        "Comparar as divisões Grupo A (saiu no último concurso) / Grupo B (não saiu) do "
        "Trend Hybrid Engine em todo o histórico disponível, sem vazamento temporal (cada "
        "concurso é previsto usando somente concursos anteriores a ele).",
        "",
        "## Divisões comparadas",
        "",
        "| Divisão | Concursos | Melhor | Média | Desvio | Taxa 11+ | Taxa 12+ | Taxa 13+ | Taxa 14+ | Taxa 15+ |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for _, row in comparativo.iterrows():
        linhas.append(
            f"| {row['Divisão']} | {row['Concursos avaliados']} | {row['Melhor acerto']} | "
            f"{row['Média de acertos']:.4f} | {row['Desvio padrão']:.4f} | {row['Taxa 11+ (%)']:.2f}% | "
            f"{row['Taxa 12+ (%)']:.2f}% | {row['Taxa 13+ (%)']:.2f}% | {row['Taxa 14+ (%)']:.2f}% | "
            f"{row['Taxa 15+ (%)']:.2f}% |"
        )
    linhas += [
        "",
        f"## Divisão recomendada: {melhor_divisao[0]}+{melhor_divisao[1]}",
        "",
        "Critério: maior Média de acertos no backtest completo; empates resolvidos por maior "
        "Taxa 13+ e, em seguida, maior Taxa 14+.",
        "",
        "## Aviso",
        "",
        "A Lotofácil é aleatória. Resultados históricos e taxas simuladas não representam garantia "
        "de prêmio ou retorno financeiro futuro. Jogue com responsabilidade.",
        "",
        "## Arquivos gerados",
        "",
        "- `exports/comparativo_trend_hybrid.csv`",
        "- `exports/backtest_trend_hybrid_detalhes.csv` (divisão recomendada, detalhado por concurso)",
        "- `exports/BACKTEST_TREND_HYBRID.md`",
    ]
    return "\n".join(linhas)


def main() -> None:
    PASTA_EXPORTS.mkdir(parents=True, exist_ok=True)
    df = carregar_base(CAMINHO_BASE_PADRAO)
    comparativo, melhor_divisao, resultados = otimizar_divisao(df, historico_minimo=100)
    comparativo.to_csv(CAMINHO_COMPARATIVO, index=False, encoding="utf-8-sig")
    resultados[melhor_divisao].detalhes.to_csv(CAMINHO_DETALHES, index=False, encoding="utf-8-sig")
    relatorio = gerar_relatorio(comparativo, melhor_divisao)
    CAMINHO_RELATORIO.write_text(relatorio, encoding="utf-8")
    print("BACKTEST_TREND_HYBRID_OK")
    print(f"Divisão recomendada: {melhor_divisao[0]}+{melhor_divisao[1]}")
    print(comparativo.to_string(index=False))


if __name__ == "__main__":
    main()
