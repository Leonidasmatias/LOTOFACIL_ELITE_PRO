# Elite Score (Phoenix V2)

Modulo de analise que avalia a qualidade de um jogo ja gerado pelo Motor
Elite, numa escala de 0 a 100. **Nao altera o Motor Elite, nao influencia a
geracao de jogos e nao modifica nenhuma regra matematica existente** — apenas
le jogos ja produzidos e os classifica.

## Por que criar um score separado do Motor Elite?

O Motor Elite ja calcula scores internos (`Elite Score`, `Elite Score V2`,
`Elite Score Temporal`) para **decidir quais dezenas/jogos gerar**. O Elite
Score deste modulo tem outro papel: **avaliar, depois do jogo pronto**, o
quanto ele e estatisticamente tipico em relacao ao padrao historico real de
concursos sorteados — util tanto para o usuario entender por que um jogo
"parece bom" quanto para futuras funcionalidades (ranquear estrategias,
dashboard, IA explicativa).

## Metodologia

Para 7 dos 8 componentes, usamos o mesmo principio, 100% baseado em
percentis empiricos da base historica (`dados/lotofacil_historico.csv`),
sem nenhuma suposicao de distribuicao estatistica (ex.: normalidade) e sem
heuristica arbitraria:

1. Calculamos, a partir de todos os concursos ja sorteados, o **minimo**, o
   **percentil 10 (p10)**, o **percentil 90 (p90)** e o **maximo** observados
   daquela metrica.
2. O sub-score (0-100) do jogo avaliado e:
   - **100** se o valor do jogo cai dentro de `[p10, p90]` — a faixa "tipica",
     onde estao ~80% dos concursos historicos;
   - decai linearmente ate um **piso de 20 pontos** conforme o valor se
     aproxima do extremo ja observado (`min`/`max`);
   - continua decaindo (podendo chegar a **0**) se o valor for alem do
     extremo ja observado na base (algo nunca visto historicamente).

O oitavo componente (**diversidade entre jogos do lote**) tem natureza
diferente: nao compara contra a base historica, compara o jogo contra os
**outros jogos gerados na mesma leva** (ex.: os 5 perfis de producao).

O calculo e **puramente deterministico**: a mesma entrada (jogo + base +
lote) sempre produz a mesma saida. Nao ha nenhum numero aleatorio envolvido.

## Componentes, pesos e justificativa

Os pesos foram calibrados pela **variancia real observada na base historica**
(3.596 concursos, na data desta analise) — metricas com maior amplitude/poder
de discriminacao entre jogos recebem peso maior; metricas com sinal fraco
recebem peso baixo, mesmo mantidas por serem explicitamente solicitadas.

| Componente | Peso | Valor do jogo | Referencia historica | Por que esse peso |
|---|---|---|---|---|
| Pares/Impares | 20% | Qtde. de dezenas pares | media 7,20, p10=6, p90=9 (88,8% dos concursos tem entre 6 e 9 pares) | Padrao historico forte e ja usado como regra no proprio Motor Elite |
| Linhas/Colunas | 15% | Maior concentracao numa linha/coluna do volante 5x5 | media 4,48, p10=4, p90=5 (nunca observado acima de 5) | Padrao muito consistente; evita jogos com concentracao anormal |
| Moldura/Miolo | 15% | Qtde. de dezenas do miolo (centro) | media 5,37, p10=4, p90=7 | Padrao claro de equilibrio moldura/miolo |
| Soma das dezenas | 15% | Soma das 15 dezenas | media 195,16, desvio 17,84, p10=172, p90=218 | Boa variancia — discrimina bem entre jogos |
| Repeticao com concurso anterior | 15% | Qtde. de dezenas iguais ao ultimo concurso | media 8,97, desvio 1,22, p10=7, p90=11 (proximo do valor esperado por combinatoria pura: 15x15/25=9) | Padrao consistente; note-se que o valor esperado ja e alto por construcao do jogo (15 de 25 dezenas), entao isso mede conformidade estatistica, nao "sorte" |
| Diversidade entre jogos do lote | 10% | Media de dezenas diferentes em relacao aos outros jogos da leva | (nao usa base historica) | Incentiva portfolios complementares em vez de jogos redundantes |
| Frequencia historica | 5% | Media da frequencia historica das 15 dezenas do jogo | media por dezena 2157,6, desvio 45,3 (amplitude entre a melhor e a pior combinacao possivel de 15 dezenas: **so ~2,5%**) | **Peso baixo de proposito**: a Lotofacil e sorteada de forma muito uniforme ao longo de milhares de concursos, entao a frequencia historica por si so discrimina pouco entre jogos |
| Atraso | 5% | Media do atraso das 15 dezenas do jogo | media por dezena 0,76, desvio 1,13 (atraso maximo observado: 4 concursos) | **Peso baixo de proposito**, pelo mesmo motivo: atraso tem amplitude muito pequena nesta loteria, sinal estatistico fraco |

Soma dos pesos: **100%** (constante `PESOS` em `src/core/elite_score.py`,
validada por teste automatizado).

### Por que frequencia e atraso tem peso baixo (honestidade estatistica)

Ao calibrar os pesos, medimos a amplitude real de cada metrica na base:
frequencia historica varia apenas ~2,5% entre a melhor e a pior combinacao
possivel de 15 dezenas, e o atraso maximo observado em 3.596 concursos e de
apenas 4 concursos. Isso e uma consequencia estrutural da Lotofacil sortear
15 de 25 dezenas a cada concurso (nao uma falha de calculo): com uma amostra
tao grande, a frequencia tende a se equalizar entre as dezenas. Dar peso alto
a essas duas metricas daria uma falsa impressao de precisao onde, na
pratica, ha pouco a discriminar. Por isso o peso delas e baixo — elas
continuam no calculo porque foram pedidas explicitamente, mas de forma
proporcional ao que realmente informam.

## Diversidade entre jogos do lote (detalhe tecnico)

Para cada jogo do lote, comparamos contra os **outros** jogos da mesma leva
(excluidos pela **posicao** no lote, nao pelo valor — assim, se dois jogos
por acaso tiverem as mesmas 15 dezenas, ainda sao comparados corretamente
entre si, com diversidade 0, em vez de serem ignorados por engano). O
sub-score e a media do numero de dezenas diferentes em relacao a cada outro
jogo, normalizada para 0-100 (100 = totalmente diferente de todos os
outros). Se o jogo for avaliado sozinho (sem lote), o componente fica neutro
(100).

## Arquitetura (camadas existentes, nenhuma pasta nova)

- `src/models/elite_score.py` — dataclasses `FaixaHistorica`,
  `ReferenciasEliteScore`, `ComponenteEliteScore`, `EliteScoreResultado`.
- `src/core/elite_score.py` — `construir_referencias(df)`,
  `calcular_elite_score(jogo, referencias, ...)`,
  `calcular_elite_score_lote(jogos, df, ...)`, constante `PESOS`. Nao importa
  Streamlit, nao faz I/O, nao toca em `motor_elite.py`.
- `src/services/elite_score_service.py` — `anexar_elite_score(jogos_df,
  df_historico)`: extrai as dezenas de um DataFrame de jogos (colunas
  Bola1..Bola15) e devolve o DataFrame com a coluna "Elite Score" mais o
  detalhamento por jogo.
- `src/ui/componentes.py::render_elite_score_painel` — tabela + seletor de
  jogo + explicacao resumida + tabela de detalhamento, reaproveitado em
  `src/ui/pagina_publica.py::render_resultado` e
  `src/ui/pagina_admin.py::render_admin` (aba "Motor Elite").
- `tests/test_core_elite_score.py` e `tests/test_services.py` — testes de
  consistencia, repetibilidade e estabilidade (ver secao Testes).

## Interface

Na tela de resultado (publica) e na aba "Motor Elite" do painel admin, a
tabela de jogos ganhou uma coluna **"Elite Score"**, com uma legenda deixando
claro que ela e diferente do "Elite Score Temporal"/"Elite Score V2" (scores
internos do Motor Elite, usados para **gerar** os jogos). No painel admin, a
coluna "Elite Score" que ja existia (Motor Elite V1) foi renomeada apenas na
**exibicao** para "Elite Score (Motor V1)", evitando colisao de nomes — o
Motor Elite em si nao foi alterado.

Abaixo da tabela, um seletor permite escolher um jogo e ver:
- uma frase resumindo as duas metricas que mais e as duas que menos
  contribuiram em **pontos** (peso x sub-score) para o total;
- uma tabela com todos os 8 componentes: valor do jogo, faixa tipica
  historica, sub-score, peso e contribuicao em pontos.

## Testes

`tests/test_core_elite_score.py` (15 testes) e a secao `TestEliteScoreService`
em `tests/test_services.py` (4 testes) cobrem:

- **Consistencia**: soma dos pesos = 100%; cada resultado tem os 8
  componentes; contribuicao = peso × sub-score; total = soma das
  contribuicoes; sub-score sempre entre 0 e 100.
- **Repetibilidade**: a mesma entrada (jogo + referencias + ultimo concurso)
  produz exatamente o mesmo resultado, inclusive repetindo o calculo 10 vezes
  seguidas.
- **Estabilidade**: valores no extremo/alem do historico saturam
  corretamente (nunca saem de 0-100); componentes de repeticao/diversidade
  ficam neutros (100) quando a informacao nao e fornecida.
- **Caso de borda que motivou uma correcao durante o desenvolvimento**: dois
  jogos identicos no mesmo lote agora sao corretamente penalizados na
  diversidade (o bug original excluia por VALOR em vez de por POSICAO,
  fazendo com que duplicatas "sumissem" da comparacao e recebessem
  diversidade neutra por engano).

## Limitacoes conhecidas / possiveis evolucoes futuras (sem mudar comportamento)

- A media de frequencia/atraso do jogo e comparada contra a distribuicao
  **por dezena individual** (25 valores), nao contra a distribuicao real de
  "media de uma amostra aleatoria de 15 dezenas" (que teria variancia menor).
  Dado o peso baixo (5% cada), essa simplificacao foi deliberada para manter
  o calculo simples (KISS) — pode ser refinada depois, se necessario, sem
  mudar a API publica do modulo.
- O modulo ainda nao esta conectado a `src/ai/elite_explicativo.py` (camada
  de IA explicativa da Phoenix V1); a explicacao hoje e gerada diretamente
  pelo `core`/`models`. Uma integracao futura poderia enriquecer o texto sem
  alterar o calculo do score.
