# LOTOFACIL PRODUCAO V1

Data: 2026-06-08

## Status

- Versao promovida: `LOTOFACIL_PRODUCAO_V1`
- Status: `PRODUCAO`
- Motor oficial: `ELITE_SCORE_V35_TEMPORAL`
- Base historica: `dados/lotofacil_historico.csv`
- Concursos oficiais na base: 3596

## Decisao tecnica

O motor promovido para producao e o Elite Score V3.5 Temporal, validado sem vazamento temporal.

O V3.5 Global nao foi promovido porque dependia do aprendizado global dos 15 jogos perfeitos historicos e perdeu os 15 pontos quando submetido a validacao temporal.

## Removido da entrega publica

- V3.5 Global
- Modo overfitting
- Testes experimentais
- Uso de `APRENDIZADO_JOGOS_VENCEDORES.csv` na previsao publica
- Uso de `AUDITORIA_15_PONTOS.csv` na previsao publica

## Mantido em producao

- Aprendizado temporal
- Ranking temporal
- DNA temporal
- Uso exclusivo de concursos anteriores ao estado atual da base

## Entrega ao usuario

A interface publica entrega 5 jogos inteligentes:

1. Diamante
2. Ouro
3. Prata
4. Agressivo
5. Conservador

Todos os jogos sao gerados pelo motor oficial:

`ELITE_SCORE_V35_TEMPORAL`

## Arquivos alterados

- `app.py`
- `src/motor_elite_lotofacil.py`
- `exports/LOTOFACIL_PRODUCAO_V1.md`

## Validacao executada

- `python -m py_compile app.py src\motor_elite_lotofacil.py scripts\backtest_v35_temporal.py`
- Smoke test de `gerar_jogos_producao_v1(df)`
- Importacao do app validada: `LOTOFACIL_PRODUCAO_V1 | PRODUCAO | ELITE_SCORE_V35_TEMPORAL | 5 jogos`
- Streamlit instalado: `1.58.0`
- Observacao: a tentativa de iniciar Streamlit em background nesta sessao falhou por duplicidade de variavel de ambiente `Path/PATH` no `Start-Process`, sem erro de codigo do app.

## Tag

- Tag solicitada: `LOTOFACIL_PRODUCAO_V1`
- Status: pendente
- Motivo: a pasta `LOTOFACIL_ELITE_PRO` nao possui repositorio Git (`.git`). Para criar uma tag Git e necessario inicializar ou vincular este projeto a um repositorio.

## Observacao obrigatoria

A Lotofacil e aleatoria. O sistema entrega analise estatistica e jogos inteligentes, sem garantia de acerto, premio ou resultado.
