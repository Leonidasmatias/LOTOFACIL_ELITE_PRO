"""Harness de backtest walk-forward, a prova de vazamento temporal (LF-04).

Infraestrutura nova e isolada, independente de qualquer motor/score/Trend
Hybrid existente: mede o desempenho histórico de um motor de geracao de
jogos da Lotofacil sem nunca deixar informacao do concurso-alvo influenciar
a previsao daquele mesmo concurso.

Nao altera nenhum motor, algoritmo, score ou peso existente. Ver
`src/backtest/harness.py` para o ponto de entrada principal
(`run_walk_forward`) e `src/backtest/engine_adapter.py` para os adaptadores
dos motores existentes.
"""
