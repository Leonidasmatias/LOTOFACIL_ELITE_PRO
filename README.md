# Lotofácil Elite Pro

Versão oficial candidata: `LOTOFACIL_ELITE_PRO_V1.1_GRATUITA`

Status: `PRODUÇÃO CANDIDATA`

Sistema independente inspirado na arquitetura do Mega-Sena Pro, adaptado para Lotofácil com interface pública simplificada e Motor Elite Lotofácil.

Versão gratuita do Motor Elite, sem cobrança, e-mail, PIX, secrets obrigatórios ou bloqueio de acesso aos jogos.

## Recursos congelados nesta versão

- Motor Elite `ELITE_SCORE_V35_TEMPORAL`.
- Cinco jogos inteligentes: Diamante, Ouro, Prata, Agressivo e Conservador.
- Indicador `Potencial 15` em todos os jogos.
- Salvamento e conferência de jogos.
- Download CSV.
- Acesso gratuito, sem PIX, e-mail ou cobrança.

## Rodar localmente

```powershell
streamlit run app.py
```

Na página inicial, o Motor Elite oficial gera e exibe diretamente os cinco jogos. Cada card apresenta 15 dezenas e pode ser atualizado pelo botão `GERAR / ATUALIZAR OS 5 JOGOS`.

Os jogos são apresentados como previsão estatística para o próximo sorteio, sem garantia de prêmio. A interface também exibe informações do motor, resumo estatístico da carteira e download da previsão atual.

## Salvar e conferir jogos

O botão `SALVAR JOGOS PARA CONFERÊNCIA` registra os cinco jogos atuais em:

`exports/jogos_salvos_lotofacil.csv`

Cada registro guarda data e hora, carteira, concurso alvo, perfil, dezenas, score, soma, pares, ímpares, status e acertos. O botão `CONFERIR JOGOS SALVOS` compara os registros com a base histórica: concursos ainda ausentes permanecem `PENDENTE`; concursos disponíveis passam para `CONFERIDO` com a quantidade de acertos.

## Validação

```powershell
python -m unittest discover -s tests -v
```

Motor oficial: `ELITE_SCORE_V35_TEMPORAL`
Base histórica: `dados/lotofacil_historico.csv`

O aplicativo inicia diretamente por `app.py` na raiz. Nenhum secret ou variável de ambiente é obrigatório para o deploy.

## Aviso

A Lotofácil é aleatória. Este sistema faz análise estatística e não garante acerto, prêmio ou resultado.
