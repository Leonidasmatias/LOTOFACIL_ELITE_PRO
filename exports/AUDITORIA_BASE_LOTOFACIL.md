# AUDITORIA BASE HISTORICA LOTOFACIL

Data: 2026-06-08

## Objetivo

Baixar e carregar o historico oficial completo da Lotofacil, substituindo a base local de desenvolvimento.

## Base atualizada

Arquivo:

- `dados/lotofacil_historico.csv`

## Fonte

Fonte oficial CAIXA:

- `https://servicebus2.caixa.gov.br/portaldeloterias/api/resultados/download?modalidade=LOTOFACIL`

Fallback implementado:

- API concurso a concurso: `https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil/{concurso}`

## Estrutura do CSV

Campos:

- Concurso
- Data
- Bola1
- Bola2
- Bola3
- Bola4
- Bola5
- Bola6
- Bola7
- Bola8
- Bola9
- Bola10
- Bola11
- Bola12
- Bola13
- Bola14
- Bola15

## Resultado da auditoria

- Total de concursos: 3596
- Menor concurso: 1
- Maior concurso: 3596
- Data do primeiro concurso: 29/09/2003
- Data do ultimo concurso: 24/01/2026

## Primeiro concurso carregado

- Concurso: 1
- Dezenas: 02 03 05 06 09 10 11 13 14 16 18 20 23 24 25

## Ultimo concurso carregado

- Concurso: 3596
- Dezenas: 01 02 03 04 05 06 07 08 14 15 16 18 20 21 22

## Arquivos alterados

- `dados/lotofacil_historico.csv`
- `src/carregar_dados.py`
- `src/motor_elite_lotofacil.py`
- `app.py`
- `exports/AUDITORIA_BASE_LOTOFACIL.md`

## Validacao

- Download oficial CAIXA: concluido.
- Base de desenvolvimento substituida.
- Leitura via `carregar_base()`: aprovada.
- Campos `Bola1..Bola15`: aprovados.
- Compilacao Python: aprovada.

## Observacao

O projeto Mega-Sena Pro nao foi alterado. A atualizacao foi restrita ao projeto independente `LOTOFACIL_ELITE_PRO`.
