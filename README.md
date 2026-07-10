# Lotofácil Elite Pro — V5 Inteligência de Dezenas

Aplicação Streamlit para medir estratégias estatísticas da Lotofácil e apoiar estudos históricos sobre combinações de 15 dezenas.

> A Lotofácil é aleatória. O sistema não garante acertos, prêmio ou retorno financeiro. Resultados históricos e valores simulados não representam promessa de desempenho futuro. Jogue com responsabilidade.

## Trend Hybrid Engine 9+6

Aba **Trend Hybrid 9+6**: motor de geração determinístico (sem sorteio
aleatório) que combina 9 dezenas do último concurso (Grupo A) com 6 dezenas
que não saíram (Grupo B), sempre escolhendo pelo maior **Trend Score**
(frequência em várias janelas, atraso, regularidade, momentum, sequência
consecutiva e persistência). Inclui explicação por dezena (selecionada e
descartada), backtest sem vazamento temporal e comparação entre as divisões
8+7, 9+6, 10+5 e 11+4. Detalhes completos do algoritmo, pesos e resultados do
backtest: `docs/TREND_HYBRID_ENGINE.md`. Backtest completo offline:
`python scripts/backtest_trend_hybrid.py`.

## V5 — Inteligência de Dezenas

- Ranking das dezenas nos últimos 20, 50, 100 e 200 concursos.
- Painéis de dezenas quentes, frias, atrasadas e repetidas.
- Histórico automático de todas as carteiras geradas em SQLite.
- Migração idempotente do histórico CSV existente.
- Atualização automática e defensiva da base oficial ao abrir o sistema.
- Alerta visual persistente quando um novo concurso é detectado.
- Rodapé institucional Leonidas Tech — Conectando o Futuro.
- Configuração completa para Railway com volume persistente.

Deploy externo: consulte `README_DEPLOY_RAILWAY.md`.

## V4 — Laboratório Estatístico

A aba **Laboratório Estatístico** executa cinco estratégias sob as mesmas condições:

1. Motor Elite
2. Aleatório puro
3. Dezenas quentes
4. Dezenas frias
5. Híbrido quente/frio

Cada concurso avaliado usa exclusivamente concursos anteriores, evitando qualquer vazamento de dados futuros.

Todas as estratégias recebem:

- A mesma quantidade de concursos avaliados
- A mesma quantidade de jogos por concurso
- Comparação pelas taxas de 11+, 12+, 13+, 14+ e 15 acertos

O painel exibe:

- Melhor estratégia por métrica
- Melhor acerto
- Média de acertos
- Taxas de 11+, 12+, 13+, 14+ e 15 acertos

## ROI simulado

O laboratório calcula:

- Valor unitário configurável
- Total apostado
- Retorno estimado por faixa de premiação
- Saldo simulado
- ROI percentual

Os valores de premiação são editáveis na interface e usados apenas para simulação.

> Confirme sempre os valores oficiais antes de qualquer decisão. O ROI exibido não é garantido.

## Heatmap 5×5

A visualização mantém a posição real das dezenas de 1 a 25 na cartela da Lotofácil e permite consultar:

- Frequência histórica
- Frequência recente
- Atraso
- Score V3

## Descoberta automática de padrões

Cada jogo simulado é classificado por:

- Faixa de soma
- Pares/ímpares
- Repetição do concurso anterior
- Moldura/miolo
- Sequência máxima
- Distribuição por linhas
- Distribuição por colunas

O laboratório mede por padrão:

- Média de acertos
- Taxa de 13+
- Taxa de 14+

A amostra mínima é configurável na interface. Grupos abaixo dela são descartados para reduzir conclusões frágeis.

## Banco histórico de estratégias

Cada execução concluída registra os resultados em:

```text
exports/historico_laboratorio_v4.csv
```

Campos registrados:

- Data/hora da execução
- Estratégia
- Concursos avaliados
- Quantidade de jogos
- Melhor acerto
- Média de acertos
- ROI simulado
- Status

## Recursos anteriores preservados

- Estratégia Inteligente
- Relatório diário CSV/TXT
- Carteiras configuráveis de 5, 10, 20 ou 30 jogos
- Comparador Motor Elite × Aleatório
- Ranking das dezenas
- Histórico e conferência de carteiras
- Backtest temporal sem vazamento futuro
- Atualização defensiva da base oficial

## Base histórica

```text
dados/lotofacil_historico.csv
```

Use **ATUALIZAR BASE OFICIAL** na aba Configurações. A atualização é atômica: se a consulta, gravação ou validação falhar, a base local é preservada.

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

Acesso padrão: [http://localhost:8501](http://localhost:8501).

## Testes

```powershell
python -m pytest -q
```

Os testes cobrem:

- Cinco estratégias
- ROI simulado
- Heatmap 5×5
- Descoberta de padrões
- Banco histórico CSV
- Carteiras válidas
- Exports
- Interface Streamlit
- Ausência de vazamento temporal
- Preservação da base local em caso de falha

## Jogo responsável

Não comprometa despesas essenciais nem aumente apostas para recuperar perdas.

A V4 é um laboratório de medição estatística. Ela não altera a natureza aleatória do sorteio e não oferece garantia de prêmio.
