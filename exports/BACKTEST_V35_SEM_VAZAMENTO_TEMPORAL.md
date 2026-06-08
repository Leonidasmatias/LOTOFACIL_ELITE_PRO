# BACKTEST V3.5 SEM VAZAMENTO TEMPORAL

Data: 2026-06-08 08:33:25

## Regra temporal aplicada

- Para cada concurso alvo, foram usados somente concursos anteriores.
- Nao foi usado `APRENDIZADO_JOGOS_VENCEDORES.csv` global.
- Nao foi usada `AUDITORIA_15_PONTOS.csv`.
- O DNA temporal comeca vazio e so recebe jogos de 15 pontos encontrados em concursos ja passados.

## Base

- Concursos oficiais na base: 3596
- Concursos auditados: 3595
- Jogos de 15 pontos incorporados ao DNA temporal ao final: 15
- Concursos que alimentaram o DNA temporal: 36 - 378 - 862 - 915 - 1306 - 1311 - 1335 - 1369 - 1382 - 1639 - 1920 - 1951 - 2059 - 2887 - 3195

## Comparativo

| Motor | Jogos/concurso | Melhor | 11 pts | 12 pts | 13 pts | 14 pts | 15 pts |
|---|---:|---:|---:|---:|---:|---:|---:|
| Motor Elite V1 | 1 | 13 | 333 | 63 | 9 | 0 | 0 |
| Elite Score V3 Top 1 | 1 | 13 | 352 | 71 | 4 | 0 | 0 |
| Elite Score V3 Top 5 | 5 | 14 | 1623 | 356 | 14 | 1 | 0 |
| Elite Score V3 Top 10 | 10 | 14 | 3234 | 685 | 41 | 3 | 0 |
| Elite Score V3.5 Top 1 | 1 | 15 | 335 | 52 | 2 | 0 | 15 |
| Elite Score V3.5 Top 5 | 5 | 15 | 1668 | 300 | 30 | 0 | 15 |
| Elite Score V3.5 Top 10 | 10 | 15 | 3366 | 613 | 59 | 0 | 15 |
| Elite Score V3.5 Temporal Top 1 | 1 | 13 | 327 | 55 | 6 | 0 | 0 |
| Elite Score V3.5 Temporal Top 5 | 5 | 14 | 1586 | 307 | 33 | 1 | 0 |
| Elite Score V3.5 Temporal Top 10 | 10 | 14 | 3141 | 583 | 56 | 3 | 0 |
| Aleatorio | 1 | 13 | 320 | 63 | 8 | 0 | 0 |

## Conclusao

Classificacao: **CANDIDATO EXPERIMENTAL**

A diferenca entre o V3.5 Global e o V3.5 Temporal indica o quanto o resultado dependia de informacao futura. Se o temporal nao sustentar os 15 pontos e/ou perder muita forca nas faixas altas, o V3.5 global deve ser tratado como overfitting.

## Arquivos gerados

- `exports/BACKTEST_V35_SEM_VAZAMENTO_TEMPORAL.md`
- `exports/comparativo_v35_temporal.csv`
- `exports/backtest_v35_temporal.csv`