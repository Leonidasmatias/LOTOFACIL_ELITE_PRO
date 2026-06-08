# BACKTEST LOTOFACIL ELITE PRO V2

Data: 2026-06-08 01:22:45

## Base

- Arquivo: `C:\Users\Leonidas\Documents\New project\LOTOFACIL_ELITE_PRO\dados\lotofacil_historico.csv`
- Total de concursos oficiais: 3596
- Concursos auditados: 3595
- Menor concurso: 1
- Maior concurso: 3596

## Elite V2 implementado

- Repeticao do ultimo concurso
- Peso Centro x Moldura
- Peso Linhas
- Peso Colunas
- Frequencia ultimos 5 concursos
- Frequencia ultimos 10 concursos
- Frequencia ultimos 20 concursos
- Monte Carlo / portfolio combinatorio a partir do Top 20
- Ranking dos melhores jogos
- Elite Score V2

## Configuracao V2

- Dezenas ranqueadas por concurso: 20
- Jogos auditados por concurso V2: 15504
- Total de jogos auditados V2: 55736880

## Comparativo

| Motor | Jogos/concurso | Total jogos | Melhor acerto | 11 pts | 12 pts | 13 pts | 14 pts | 15 pts |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Elite V1 | 1 | 3595 | 13 | 333 | 63 | 9 | 0 | 0 |
| Elite V2 | 15504 | 55736880 | 15 | 4838673 | 908201 | 76965 | 2367 | 15 |
| Aleatorio | 1 | 3595 | 13 | 320 | 63 | 8 | 0 | 0 |

## Diferenca Elite V2 vs Elite V1

- 13 pontos: 76956
- 14 pontos: 2367
- 15 pontos: 15

## Melhor resultado Elite V2

- Melhor acerto: 15
- Concurso do melhor resultado: 1639
- Melhor jogo encontrado: 01 - 03 - 05 - 06 - 07 - 08 - 09 - 10 - 11 - 14 - 15 - 19 - 20 - 22 - 25

## Objetivo minimo

- Superar V1 em 13, 14 e 15 pontos: SIM

## Observacao tecnica

O V2 utiliza um portfolio Top20 combinatorio, portanto audita mais jogos por concurso que o V1.
A comparacao deve ser lida junto com `Jogos por concurso`, `Total de jogos auditados` e taxas percentuais.

## Arquivos gerados

- `exports/BACKTEST_LOTOFACIL_ELITE_PRO_V2.md`
- `exports/comparativo_v1_v2.csv`
- `exports/backtest_lotofacil_v2_por_concurso.csv`