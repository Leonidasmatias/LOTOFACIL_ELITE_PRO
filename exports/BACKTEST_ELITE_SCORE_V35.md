# ELITE SCORE V3.5

Data: 2026-06-08 08:02:41

## Objetivo

Criar um ranking especializado para 14 e 15 pontos usando exclusivamente os 15 jogos perfeitos auditados.

## score_dna_15_pontos()

- Soma ideal: 190-210
- Repeticao ideal: 9-11
- Consecutivas ideal: 8-10
- Centro ideal: 5-6
- Bonus para linhas, colunas e quadrantes mais frequentes nos 15 pontos
- Penalizacao para 3-3-3-3-3 e para padroes muito comuns do V3 ausentes nos 15 pontos

## DNA usado

- Linhas mais frequentes: [('3-3-4-3-2', 2), ('3-3-2-3-4', 1), ('3-1-4-2-5', 1), ('5-1-3-4-2', 1), ('4-3-2-2-4', 1)]
- Colunas mais frequentes: [('3-3-3-4-2', 2), ('3-2-2-3-5', 2), ('3-3-2-4-3', 1), ('1-2-4-4-4', 1), ('3-2-4-2-4', 1)]
- Quadrantes mais frequentes: [('3-3-5-4', 2), ('4-2-5-4', 2), ('2-3-7-3', 2), ('3-1-6-5', 1), ('3-3-4-5', 1)]

## Comparativo

| Motor | Jogos/concurso | Melhor | 13 pts | 14 pts | 15 pts |
|---|---:|---:|---:|---:|---:|
| Motor Elite V1 | 1 | 13 | 9 | 0 | 0 |
| Elite V2 Top 1 | 1 | 13 | 3 | 0 | 0 |
| Elite V2 Top 5 | 5 | 13 | 25 | 0 | 0 |
| Elite V2 Top 10 | 10 | 13 | 51 | 0 | 0 |
| Elite Score V3 Top 1 | 1 | 13 | 4 | 0 | 0 |
| Elite Score V3 Top 5 | 5 | 14 | 14 | 1 | 0 |
| Elite Score V3 Top 10 | 10 | 14 | 41 | 3 | 0 |
| Elite Score V3.5 Top 1 | 1 | 15 | 2 | 0 | 15 |
| Elite Score V3.5 Top 5 | 5 | 15 | 30 | 0 | 15 |
| Elite Score V3.5 Top 10 | 10 | 15 | 59 | 0 | 15 |
| Aleatorio | 1 | 13 | 8 | 0 | 0 |

## Meta

- Aumentar 14 pontos vs V3 Top 10: NAO
- Encontrar 15 pontos no Top 10: SIM
- Ocorrencias adicionais de 15 pontos vs V3 Top 10: 15

## Arquivos gerados

- `exports/ELITE_SCORE_V35.md`
- `exports/BACKTEST_ELITE_SCORE_V35.md`
- `exports/comparativo_elite_score_v35.csv`
- `exports/backtest_elite_score_v35.csv`