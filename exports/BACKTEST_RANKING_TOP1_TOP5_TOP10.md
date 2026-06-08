# BACKTEST RANKING TOP1 TOP5 TOP10

Data: 2026-06-08 02:03:51

## Objetivo

Medir se o ranking do Motor Elite V2 coloca os melhores jogos no topo.

## Base

- Arquivo: `C:\Users\Leonidas\Documents\New project\LOTOFACIL_ELITE_PRO\dados\lotofacil_historico.csv`
- Total de concursos oficiais: 3596
- Concursos auditados: 3595
- Menor concurso: 1
- Maior concurso: 3596

## Metodologia

- Para cada concurso, o historico anterior foi usado para gerar o ranking.
- Foram auditados apenas Elite V2 Top 1, Elite V2 Top 5 e Elite V2 Top 10.
- Motor Elite V1 e Aleatorio usam o resumo do backtest V1 como referencia de 1 jogo por concurso.

## Comparativo

| Motor | Jogos/concurso | Total jogos | Melhor acerto | 11 pts | Taxa 11 | 12 pts | Taxa 12 | 13 pts | Taxa 13 | 14 pts | Taxa 14 | 15 pts | Taxa 15 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Motor Elite V1 | 1 | 3595 | 13 | 333 | 9.2629% | 63 | 1.7524% | 9 | 0.2503% | 0 | 0.0% | 0 | 0.0% |
| Elite V2 Top 1 | 1 | 3595 | 13 | 307 | 8.539638% | 65 | 1.808067% | 3 | 0.083449% | 0 | 0.0% | 0 | 0.0% |
| Elite V2 Top 5 | 5 | 17975 | 13 | 1635 | 9.095967% | 293 | 1.630042% | 25 | 0.139082% | 0 | 0.0% | 0 | 0.0% |
| Elite V2 Top 10 | 10 | 35950 | 13 | 3215 | 8.942976% | 601 | 1.671766% | 51 | 0.141864% | 0 | 0.0% | 0 | 0.0% |
| Aleatorio | 1 | 3595 | 13 | 320 | 8.9013% | 63 | 1.7524% | 8 | 0.2225% | 0 | 0.0% | 0 | 0.0% |

## Leitura do ranking

- Elite V2 Top 1 com 13 pontos: 3
- Elite V2 Top 5 com 13 pontos: 25
- Elite V2 Top 10 com 13 pontos: 51
- Elite V2 Top 10 com 14 pontos: 0
- Elite V2 Top 10 com 15 pontos: 0

## Conclusao

O ranking V2 ainda nao coloca os melhores jogos no topo. O portfolio amplo V2 encontrou 14 e 15 pontos, mas esses picos nao aparecem no Top 1, Top 5 ou Top 10. No Top 1, o V2 fez menos jogos de 13 pontos que o V1 e que o aleatorio; no Top 5/Top 10, a contagem bruta aumenta porque ha mais jogos, mas a taxa de 13 pontos fica abaixo do V1.

## Arquivos gerados

- `exports/BACKTEST_RANKING_TOP1_TOP5_TOP10.md`
- `exports/comparativo_ranking.csv`
- `exports/backtest_ranking_top1_top5_top10.csv`
