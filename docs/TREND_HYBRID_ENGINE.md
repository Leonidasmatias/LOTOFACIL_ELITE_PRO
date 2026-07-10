# Trend Hybrid Engine 9+6

Novo motor de geração de bilhetes: em vez de amostragem ponderada aleatória
(como o Motor Elite V2), o Trend Hybrid Engine calcula um **Trend Score**
determinístico para as 25 dezenas e monta o bilhete escolhendo sempre as de
maior score dentro de cada grupo — **nenhuma dezena é escolhida por sorteio
puro**, toda escolha tem uma métrica e uma justificativa associada.

> A Lotofácil é aleatória. O backtest completo (seção "Resultados do
> backtest", abaixo) mostra desempenho estatisticamente equivalente ao
> acaso. Este motor não garante prêmio nem retorno financeiro.

## Objetivo (recapitulando a especificação)

Gerar um bilhete de 15 dezenas combinando:

- **Grupo A**: as dezenas que saíram no último concurso (por padrão, 9 das
  15).
- **Grupo B**: as dezenas que não saíram no último concurso (por padrão, 6
  das 10).

Cada dezena de cada grupo é escolhida pelo maior Trend Score — nunca por
amostragem aleatória.

## Onde vive o código

Seguindo a arquitetura em camadas do projeto (`docs/ARCHITECTURE.md`):

| Camada | Arquivo | Responsabilidade |
|---|---|---|
| `models` | `src/models/trend_hybrid.py` | Dataclasses: `PesosTendencia`, `IndicadoresDezena`, `DezenaPontuada`, `BilheteTrendHybrid` |
| `core` | `src/core/trend_hybrid_engine.py` | Trend Score, grupos A/B, seleção do bilhete — puro, sem I/O |
| `core` | `src/core/trend_hybrid_backtest.py` | Backtest temporal e otimização de divisão — puro, sem I/O |
| `ai` | `src/ai/trend_hybrid_explainer.py` | Explicação textual por dezena, a partir de valores já calculados |
| `services` | `src/services/trend_hybrid_service.py` | Orquestra core + ai para a UI |
| `ui` | `app.py` (`render_trend_hybrid`) | Aba "Trend Hybrid 9+6" no Streamlit |
| `scripts` | `scripts/backtest_trend_hybrid.py` | Backtest completo offline, salva relatório em `exports/` |

Nenhum código do Motor Elite V2, do Elite Score ou de qualquer motor
existente foi alterado.

## Trend Score: indicadores e pesos

Para cada uma das 25 dezenas, calculamos 9 indicadores brutos usando
**somente concursos anteriores ao concurso-alvo** (nunca há vazamento
temporal — ver seção "Sem vazamento temporal"):

| Indicador | O que mede |
|---|---|
| Frequência últimos 10/20/50/100 | Quantas vezes a dezena saiu nas últimas N extrações |
| Frequência histórica | Quantas vezes a dezena já saiu em toda a base |
| Atraso | Concursos desde a última aparição |
| Regularidade | `1 / (1 + coeficiente de variação dos intervalos entre aparições)` — quanto mais regular o intervalo entre aparições, mais próximo de 1 |
| Momentum | `(frequência últimos 10 / 10) − (frequência últimos 50 / 50)` — tendência recente acima ou abaixo da tendência de médio prazo |
| Sequência consecutiva | Maior sequência de concursos consecutivos em que a dezena saiu |
| Persistência | Fração dos blocos de 50 concursos (já completados) em que a dezena apareceu ao menos uma vez |

Cada indicador é normalizado (min-max, 0 a 1) entre as 25 dezenas e
combinado com pesos (`PesosTendencia`, `src/models/trend_hybrid.py`):

| Peso | Valor padrão |
|---|---:|
| Últimos 10 | 30% |
| Últimos 20 | 20% |
| Últimos 50 | 15% |
| Últimos 100 | 10% |
| Histórico | 10% |
| Regularidade | 5% |
| Momentum | 5% |
| Persistência | 5% |
| **Atraso (adaptativo)** | 0% a 10%, padrão 5% |

O peso do atraso é o único "solto": pode variar de 0% a 10% (parâmetro
`peso_atraso` de `PesosTendencia`, exposto na UI como um slider). Os demais
pesos-base somam 1.0 entre si e são reescalados proporcionalmente por
`(1 − peso_atraso)`, de forma que a soma final dos pesos efetivos seja
**sempre exatamente 1.0**, qualquer que seja o valor escolhido para o
atraso — essa é a interpretação usada aqui para "0–10% (adaptativo, não
fixo)" da especificação. Recalibrar automaticamente os demais pesos por
evidência estatística (em vez de manter os valores sugeridos na
especificação) foi deliberadamente deixado fora desta fase: o histórico
disponível (~3.700 concursos) é pequeno demais para ajustar 8 pesos sem
risco real de overfitting, e o backtest (abaixo) já mostra que o sinal
estatístico disponível é muito fraco — otimizar pesos sobre um sinal fraco
tende a apenas memorizar ruído. Ver "Prontos para IA futura" para o caminho
recomendado quando houver base suficiente.

O Trend Score final de cada dezena é a soma ponderada dos indicadores
normalizados, escalada para 0–100.

## Seleção do bilhete (Grupo A / Grupo B)

1. Grupo A = as 15 dezenas do último concurso; Grupo B = as 10 restantes.
2. Cada grupo é ordenado pelo Trend Score, do maior para o menor.
3. São escolhidas as `N` melhores do Grupo A e as `15-N` melhores do Grupo B
   (divisão padrão 9+6; também suportadas: 8+7, 10+5, 11+4).
4. O bilhete resultante é validado com as mesmas regras já existentes do
   Motor Elite (`ConfiguracaoMotor`/`validar_jogo` — soma, pares/ímpares,
   sequência máxima, repetição do concurso anterior). Como o Grupo A sempre
   contribui exatamente `N` dezenas por construção, a regra de repetição já
   é satisfeita automaticamente para qualquer divisão suportada.
5. Se a combinação pura top-N/top-(15-N) não satisfizer as demais regras
   (soma, pares, sequência), a busca é ampliada em margens crescentes
   (top-(N+1), top-(N+2), ...) dentro de cada grupo, escolhendo — entre as
   combinações válidas encontradas — a de **maior Trend Score total**. Nunca
   há sorteio aleatório nessa etapa; no histórico completo (3.625 concursos
   avaliados), a margem de busca média ficou entre 0,23 e 0,24 para todas as
   divisões, ou seja, a combinação pura já é válida na grande maioria dos
   casos.

## Modo Sorteio Aleatório (novo bilhete a cada clique)

A seleção pelo Trend Score descrita acima é **determinística**: para o
mesmo histórico, divisão e pesos, `gerar_bilhete_trend_hybrid` sempre
devolve exatamente o mesmo bilhete. Isso é o comportamento correto para a
*recomendação* do motor, mas gerava a impressão de que o botão "GERAR
BILHETE TREND HYBRID" não estava fazendo nada ao ser clicado várias vezes
seguidas.

Por isso a UI (aba "Trend Hybrid 9+6") oferece um segundo modo, opcional,
selecionável por um `st.radio` acima do botão:

- **Sorteio aleatório (novo bilhete a cada clique)** — modo padrão.
  `sortear_bilhete_aleatorio_grupos` (`src/core/trend_hybrid_engine.py`) e o
  wrapper `sortear_bilhete_aleatorio` (`src/services/trend_hybrid_service.py`)
  sorteiam, **sem usar Trend Score**, `N` dezenas aleatórias dentro do Grupo A
  (as 15 do último concurso) e `15-N` dezenas aleatórias dentro do Grupo B
  (as que não saíram), com `random.Random(semente)`. Cada combinação
  candidata é validada com `ConfiguracaoMotor`/`validar_jogo` (soma,
  pares/ímpares, sequência máxima) antes de ser aceita, com nova tentativa
  em caso de falha (até `tentativas_maximas`, padrão 5000) — o mesmo padrão
  de retry-até-válido usado em `motor_elite_v2.gerar_jogos_v2`.
- **Recomendação Trend Score (fixa)** — o comportamento original: sempre a
  combinação de maior Trend Score dentro da divisão escolhida.

A cada clique em "GERAR BILHETE TREND HYBRID" no modo aleatório, a UI gera
uma nova semente (`random.randint(1, 2_000_000_000)`), incrementa um
contador de sorteios (`numero_sorteio`) guardado em
`st.session_state.trend_aleatorio_contador` e registra o horário da geração
— esses três valores (nº do sorteio, semente e horário) aparecem em um
painel de auditoria na tela, permitindo confirmar visualmente que cada
clique produz um resultado novo. `BilheteSorteioGrupos`
(`src/models/trend_hybrid.py`) é o dataclass usado para esse modo — mesma
validação estrutural de 15 dezenas únicas de `BilheteTrendHybrid`, mas sem
os campos de pontuação (não faz sentido "explicar por Trend Score" uma
dezena que foi sorteada, não pontuada).

Com a mesma semente, o sorteio é reprodutível (útil para testes); sem
semente (`semente=None`), usa a entropia padrão do processo.

## Sem vazamento temporal

Tanto a geração "de hoje" quanto o backtest usam a mesma classe de estado
incremental (`_EstadoTendencia`, interna a `trend_hybrid_engine.py`),
processada em **uma única passada O(n)** sobre o histórico. Os indicadores
usados para prever o concurso em qualquer posição `i` são calculados
usando somente os concursos `0..i-1` — o próprio concurso-alvo nunca entra
no cálculo dos indicadores usados para prevê-lo. Isso é verificado
explicitamente em `tests/test_core_trend_hybrid_backtest.py`.

## Backtest e otimização de divisão

`scripts/backtest_trend_hybrid.py` roda o backtest completo (histórico
inteiro, 3.625 concursos avaliados após um período mínimo de aquecimento de
100 concursos) e compara as 4 divisões suportadas. Resultado da última
execução (ver `exports/BACKTEST_TREND_HYBRID.md` para a versão mais
recente):

| Divisão | Melhor | Média | Taxa 11+ | Taxa 12+ | Taxa 13+ | Taxa 14+ |
|---|---:|---:|---:|---:|---:|---:|
| 9+6 | 13 | 9,0223 | 11,17% | 1,79% | 0,28% | 0,00% |
| 8+7 | 14 | 9,0188 | 10,10% | 2,01% | 0,22% | 0,03% |
| 10+5 | 13 | 9,0086 | 10,81% | 1,52% | 0,11% | 0,00% |
| 11+4 | 13 | 9,0014 | 10,65% | 1,49% | 0,14% | 0,00% |

**Leitura honesta destes números**: o valor esperado de acertos de um
bilhete de 15 dezenas escolhido *sem nenhum critério* (puramente ao acaso,
por combinatória) contra um sorteio de 15 entre 25 já é `15 × 15/25 = 9,0`.
As quatro divisões do Trend Hybrid Engine ficaram entre 9,00 e 9,02 de
média — ou seja, dentro do que se espera pelo acaso, sem uma vantagem
estatisticamente clara de nenhuma divisão sobre as outras nem sobre uma
escolha aleatória. A divisão 9+6 (a pedida na especificação) teve a maior
média e a maior taxa de 11+ nesta execução, por isso é a recomendada por
`otimizar_divisao`/`scripts/backtest_trend_hybrid.py` — mas a diferença
entre divisões é pequena o suficiente para ser explicada por variação
amostral. Isso é consistente com o restante do projeto (ver
`docs/ELITE_SCORE.md`: "a Lotofácil é sorteada de forma muito uniforme") e
com os avisos responsáveis já presentes em toda a aplicação.

Para reproduzir: `python scripts/backtest_trend_hybrid.py` (gera
`exports/comparativo_trend_hybrid.csv`, `exports/backtest_trend_hybrid_detalhes.csv`
e `exports/BACKTEST_TREND_HYBRID.md`).

Na UI (aba "Trend Hybrid 9+6"), o backtest rápido roda sobre uma janela
configurável (20 a 200 concursos) para manter a resposta interativa; o
backtest completo (~11s neste ambiente) é reservado ao script standalone.

## Explicabilidade

`src/ai/trend_hybrid_explainer.py` traduz um `BilheteTrendHybrid` já gerado
em uma explicação por dezena, sem recalcular nada:

- **Selecionadas**: Trend Score, frequência nos últimos 10 concursos,
  atraso, momentum, regularidade e um motivo textual (posição no ranking do
  grupo, se veio do Grupo A ou B).
- **Descartadas**: Trend Score e o motivo (posição no ranking do grupo,
  abaixo do corte da divisão escolhida).

## Prontos para IA futura (não implementado nesta fase)

A especificação pede que a arquitetura fique pronta para Machine Learning
sem implementá-lo ainda. Os pontos de extensão pensados para isso:

- **`IndicadoresDezena`** (`src/models/trend_hybrid.py`) já é a superfície
  de *features* por dezena — um modelo supervisionado (Random Forest,
  XGBoost, LightGBM, rede neural) poderia consumir exatamente esses campos
  como vetor de entrada, sem precisar recalcular nada do `core`.
- **`calcular_trend_scores`** (`src/core/trend_hybrid_engine.py`) é hoje uma
  combinação linear com pesos fixos (`PesosTendencia`). Essa função pode ser
  substituída por um modelo treinado (ex.: prever probabilidade de a dezena
  sair no próximo concurso) mantendo a mesma assinatura
  (`dict[int, IndicadoresDezena] -> dict[int, DezenaPontuada]`), sem alterar
  `selecionar_bilhete`, o `ai` ou os `services`.
- **`otimizar_divisao`** (`src/core/trend_hybrid_backtest.py`) já testa um
  espaço pequeno e discreto de configurações (as 4 divisões); o mesmo
  arcabouço de backtest sem vazamento temporal serve de função objetivo para
  **otimização bayesiana** ou **algoritmos genéticos** sobre os pesos de
  `PesosTendencia`, ou para buscar hiperparâmetros de um modelo de ML.
- **`iterar_estados_trend_hybrid`** já percorre o histórico em uma única
  passada sem vazamento — é a fonte natural de um dataset de treino
  (`indicadores` como features, "a dezena saiu no próximo concurso?" como
  rótulo) para qualquer modelo supervisionado.
- **Monte Carlo / simulação**: o mesmo backtest, rodado sobre bilhetes
  gerados com pesos aleatoriamente perturbados, serve de base para uma
  análise de sensibilidade Monte Carlo dos pesos.
- **Reinforcement Learning**: o loop concurso-a-concurso do backtest
  (estado → ação (bilhete) → recompensa (acertos)) já tem o formato de um
  ambiente de RL; não foi encapsulado como tal nesta fase para não introduzir
  complexidade sem um agente real para consumi-lo.

Nada disso está implementado nesta fase — são os pontos de extensão
recomendados, para quando houver decisão de investir em ML de fato (e,
idealmente, mais concursos históricos para reduzir o risco de overfitting).

## Testes

- `tests/test_core_trend_hybrid_engine.py` — Trend Score, validade e
  determinismo do bilhete, tratamento de divisões/configurações inválidas,
  e (modo aleatório) reprodutibilidade com a mesma semente, variação entre
  sementes diferentes, tamanhos de Grupo A/B e validação para todas as
  divisões suportadas, e erros para divisões inválidas.
- `tests/test_core_trend_hybrid_backtest.py` — ausência de vazamento
  temporal, forma do resultado do backtest, determinismo, otimização de
  divisão.
- `tests/test_ai_trend_hybrid_explainer.py` — cobertura completa das 25
  dezenas, coerência da explicação com o bilhete original.
- `tests/test_services_trend_hybrid_service.py` — orquestração do service.
