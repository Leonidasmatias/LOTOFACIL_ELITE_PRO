# ELITE SCORE V3

Data: 2026-06-08 06:57:47

## Objetivo

Recriar o ranking usando aprendizado historico dos jogos de 13, 14 e 15 pontos encontrados no portfolio V2.

## Jogos vencedores minerados

- Total de jogos 13+: 79347
- Jogos com 13 pontos: 76965
- Jogos com 14 pontos: 2367
- Jogos com 15 pontos: 15

## Variaveis analisadas

- Soma total
- Pares e impares
- Centro x moldura
- Linhas
- Colunas
- Repeticao do concurso anterior
- Frequencia curta
- Frequencia longa
- Dezenas consecutivas
- Distribuicao por quadrantes

## Score

`score_aprendizado_historico()` soma evidencias historicas ponderadas por resultado: 13 pontos, 14 pontos e 15 pontos.
O score final combina aprendizado historico com uma pequena parcela do score geometrico/frequencial V2.

## Principais padroes minerados

- soma_bin: 190-199 (21768.5), 200-209 (19622.0), 180-189 (17625.0), 210-219 (12586.0), 170-179 (9917.5)
- pares: 7 (30698.0), 8 (24514.5), 6 (19867.5), 9 (10202.0), 5 (6910.5)
- centro: 5 (31798.0), 6 (25553.0), 4 (19864.0), 7 (9119.5), 3 (6579.5)
- repeticao_anterior: 10 (30311.0), 11 (26007.5), 9 (19111.5), 12 (10020.5), 8 (7269.5)
- linhas: 3-3-3-3-3 (2905.0), 3-2-4-3-3 (2210.5), 4-2-3-3-3 (2125.0), 3-2-3-3-4 (1933.5), 3-3-4-2-3 (1800.0)
- colunas: 3-3-3-3-3 (3171.5), 3-3-2-3-4 (2190.5), 3-3-2-4-3 (2190.0), 2-3-3-4-3 (2021.5), 3-2-3-3-4 (1977.0)
- quadrantes: 3-3-5-4 (5930.5), 4-2-5-4 (4880.5), 3-2-6-4 (4478.0), 4-3-5-3 (4415.0), 3-3-6-3 (4012.5)
- consecutivas: 8 (29378.5), 9 (27403.5), 7 (16348.5), 10 (13526.0), 6 (4651.0)

## Arquivo de aprendizado

- `exports/APRENDIZADO_JOGOS_VENCEDORES.csv`