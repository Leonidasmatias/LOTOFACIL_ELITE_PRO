# Lotofácil Elite Pro — V4 Laboratório Estatístico

Aplicação Streamlit para medir estratégias e apoiar a **busca estatística pelos 15 acertos** da Lotofácil.

> A Lotofácil é aleatória. O sistema não garante acertos, prêmio ou retorno financeiro. Resultados históricos e valores simulados não representam promessa de desempenho futuro. Jogue com responsabilidade.

## V4 Laboratório Estatístico

A nova aba **Laboratório Estatístico** executa cinco estratégias sob as mesmas condições:

- Motor Elite.
- Aleatório puro.
- Dezenas quentes.
- Dezenas frias.
- Híbrido quente/frio.

Cada concurso avaliado utiliza exclusivamente os concursos anteriores. Todas as estratégias recebem a mesma quantidade de jogos e são comparadas pelas taxas de 11+, 12+, 13+, 14+ e 15 acertos.

O painel mostra a melhor estratégia em cada métrica. Isso permite identificar vantagem ou desvantagem histórica sem transformar correlação em garantia.

## ROI simulado

O laboratório calcula:

- Valor unitário configurável.
- Total apostado na simulação.
- Retorno estimado por faixa de premiação.
- Saldo simulado.
- ROI percentual.

Todos os prêmios são valores editáveis usados somente para simulação. Confirme os valores oficiais antes de qualquer decisão. O ROI exibido não é garantido.

## Heatmap 5×5

A cartela visual das 25 dezenas pode exibir:

- Frequência histórica.
- Frequência recente.
- Atraso.
- Score V3.

O heatmap mantém a posição real de cada dezena na grade 5×5 da Lotofácil.

## Descoberta automática de padrões

Cada jogo simulado é classificado por:

- Faixa de soma.
- Pares/ímpares.
- Repetição do concurso anterior.
- Moldura/miolo.
- Sequência máxima.
- Distribuição por linhas e colunas.

O laboratório mede média de acertos e taxas de 13+ e 14+ por padrão. Grupos abaixo da amostra mínima são descartados para reduzir conclusões frágeis.

## Banco histórico de estratégias

Cada execução concluída registra em CSV:

- Data e estratégia.
- Concursos avaliados.
- Quantidade de jogos.
- Melhor acerto e média.
- ROI simulado e status.

Arquivo local: `exports/historico_laboratorio_v4.csv`.

## Recursos anteriores preservados

- Estratégia Inteligente e relatório diário CSV/TXT.
- Carteiras configuráveis de 5, 10, 20 ou 30 jogos.
- Comparador Motor Elite × aleatório.
- Ranking das dezenas.
- Histórico e conferência de carteiras.
- Backtest temporal sem vazamento futuro.
- Atualização defensiva da base oficial.

## Instalação

Requer Python 3.11 ou superior.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Executar

```powershell
python -m streamlit run app.py
```

Acesso padrão: `http://localhost:8501`.

## Atualizar dados

Use **ATUALIZAR BASE OFICIAL** em Configurações. Se a consulta falhar, a base local é preservada.

Base histórica: `dados/lotofacil_historico.csv`.

## Testes

```powershell
python -m pytest -q
```

Os testes cobrem as cinco estratégias, ROI, heatmap, padrões, banco histórico, carteiras válidas, exports, interface e ausência de vazamento temporal.

## Jogo responsável

Não comprometa despesas essenciais nem aumente apostas para recuperar perdas. A V4 é um laboratório de medição estatística; ela não altera a natureza aleatória do sorteio e não oferece garantia de prêmio.
