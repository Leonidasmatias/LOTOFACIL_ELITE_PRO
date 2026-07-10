# Changelog

## Trend Hybrid Engine 9+6 — botão explícito + modo Sorteio Aleatório (auditável)

Duas melhorias de UX sobre o Trend Hybrid Engine, sem alterar nenhuma regra
de validação já existente (`ConfiguracaoMotor`/`validar_jogo`):

1. O bilhete deixou de ser montado automaticamente ao abrir a aba — agora
   depende de um clique explícito em "GERAR BILHETE TREND HYBRID" (mesmo
   padrão das outras abas do app).
2. Novo modo **"Sorteio aleatório (novo bilhete a cada clique)"**,
   selecionável por um `st.radio` ao lado do modo determinístico original
   ("Recomendação Trend Score"). Sorteia N dezenas aleatórias dentro do
   Grupo A (último concurso) + as demais dentro do Grupo B (não saíram),
   validado por `ConfiguracaoMotor`/`validar_jogo` a cada tentativa. Um
   painel de auditoria (nº do sorteio, semente e horário) confirma
   visualmente que cada clique gera um resultado novo.

### Adicionado

- `src/models/trend_hybrid.py`: `BilheteSorteioGrupos`.
- `src/core/trend_hybrid_engine.py`: `obter_grupo_a_grupo_b`,
  `sortear_bilhete_aleatorio_grupos` (sorteio validado dentro dos grupos,
  com semente opcional para reprodutibilidade).
- `src/services/trend_hybrid_service.py`: `sortear_bilhete_aleatorio`
  (wrapper de orquestração para a UI).
- `app.py`: seletor de modo (`st.radio`) e painel de auditoria (sorteio nº,
  semente, horário) na aba "Trend Hybrid 9+6".
- Testes cobrindo o modo aleatório em
  `tests/test_core_trend_hybrid_engine.py` e
  `tests/test_services_trend_hybrid_service.py`.

## Trend Hybrid Engine 9+6 — novo motor de geração determinístico

Nova funcionalidade aditiva: motor de geração de bilhete baseado em Trend
Score (9 dezenas do último concurso + 6 que não saíram, sempre pelas de
maior score, nunca por sorteio aleatório puro). Não altera nenhuma regra do
Motor Elite V2, do Elite Score ou de qualquer motor existente.

### Adicionado

- `src/models/trend_hybrid.py`: `PesosTendencia`, `IndicadoresDezena`,
  `DezenaPontuada`, `BilheteTrendHybrid`.
- `src/core/trend_hybrid_engine.py`: cálculo do Trend Score (estado
  incremental single-pass, sem vazamento temporal), separação Grupo A/Grupo
  B e seleção do bilhete com validação via `ConfiguracaoMotor`/`validar_jogo`
  já existentes.
- `src/core/trend_hybrid_backtest.py`: backtest temporal e otimização de
  divisão (8+7, 9+6, 10+5, 11+4).
- `src/ai/trend_hybrid_explainer.py`: explicação por dezena (selecionada e
  descartada), sem recalcular nenhum valor.
- `src/services/trend_hybrid_service.py`: orquestração para a UI.
- `app.py`: nova aba "Trend Hybrid 9+6" (`render_trend_hybrid`).
- `scripts/backtest_trend_hybrid.py`: backtest completo offline, salva
  relatório em `exports/`.
- `docs/TREND_HYBRID_ENGINE.md`: documentação completa do algoritmo, pesos,
  resultados do backtest e pontos de extensão para IA futura (não
  implementados nesta fase).
- Testes: `tests/test_core_trend_hybrid_engine.py`,
  `tests/test_core_trend_hybrid_backtest.py`,
  `tests/test_ai_trend_hybrid_explainer.py`,
  `tests/test_services_trend_hybrid_service.py`.

## UX Final Simplification — fluxo único da tela pública

Reestruturação de UI/UX pura na tela pública: nenhuma regra do Motor Elite,
do Elite Score (V2) ou do Elite Decision Engine (V1.5) foi alterada — só a
forma como os mesmos resultados já calculados são apresentados.

### Alterado

- `src/ui/pagina_publica.py`: novo ponto de entrada único
  `render_fluxo_publico(df, meta)`, que concentra botão "🎯 GERAR MEUS
  JOGOS" + gate de pagamento PIX + resultado completo (movido de `app.py`,
  mesmas chaves de `session_state`, mesmo comportamento de pagamento).
  `render_resultado` reorganizado num fluxo linear com 4 seções claras, sem
  abas nem cliques extras: 📊 Resultado → 🧠 Qualidade → 💬 Explicação →
  🎯 Estratégia — tudo na mesma página, revelado de uma vez após a
  aprovação do PIX.
- Linguagem simplificada: removida a legenda "Motor oficial: ..." (nome
  interno do motor de geração) e o metric "Score temporal" (métrica interna
  do Motor Elite, redundante com o Elite Score já exibido na seção
  Qualidade) da tela pública. Textos técnicos como "sub-score" e
  "Penalidades" foram reescritos em linguagem mais direta ("Pontos de
  atenção", notas simples "X/100").
- `src/ui/componentes.py::render_qualidade_elite_simplificada` (nova
  função, só usada na tela pública): mostra uma tabela simples (Jogo, Nota,
  Classificação) reaproveitando `elite_explainer.classificar_score` sem
  recalcular nada; o detalhamento estatístico completo (sub-score, peso,
  faixa típica) continua disponível, mas escondido por padrão num expansor
  opcional "Ver detalhes técnicos". `render_elite_score_painel` (usado pelo
  painel admin) não foi alterado.
- Corrigido um problema de codificação pré-existente (emojis exibidos como
  "ðŸŽ¯"/"ðŸ”¥" em `app.py`, herdado do app original antes da Phoenix) ao
  mover e reescrever o texto do botão principal.

### Compatibilidade

Elite Score, Explainable AI (V1.4) e Elite Decision Engine (V1.5) continuam
funcionando exatamente como antes — os mesmos módulos, sem nenhuma linha
alterada (`git diff` vazio para `src/core/elite_score.py`,
`src/ai/elite_explainer.py`, `src/ai/elite_decision_engine.py` e
`src/core/motor_elite.py`). O painel admin (`pagina_admin.py`) também não
foi tocado nesta fase.

## V1.5 — Elite Decision Engine

Camada estrategica construida ACIMA do Elite Score (Phoenix V2) e da
Explainable AI (V1.4), na camada `src/ai/`. Nao altera
`src/core/motor_elite.py`, nenhuma formula do Elite Score
(`src/core/elite_score.py` permanece intocado) nem gera jogos novos — apenas
le e agrega os scores ja calculados.

### Adicionado

- `src/ai/elite_decision_engine.py`: `classificar_jogos(jogos)` (classifica
  cada jogo ja pontuado em `ELITE PREMIUM` ≥90, `ALTO POTENCIAL` 75–89,
  `NEUTRO` 50–74, `FRACO` <50), `montar_estrategia(jogos_classificados)`
  (define o perfil `CONSERVADOR` / `EQUILIBRADO` / `AGRESSIVO` a partir da
  media dos scores e da proporcao de jogos fortes/fracos do lote) e
  `gerar_relatorio_estrategico(jogos)` (relatorio completo: distribuicao,
  perfil recomendado, justificativa, nivel de risco e potencial teorico).
  100% local e deterministico — mesma lista de scores sempre produz o mesmo
  relatorio.
- A decisao de perfil reaproveita os mesmos limiares (50/75/90) usados na
  classificacao por jogo, evitando um segundo conjunto de numeros para a
  mesma escala; o nivel de risco e derivado diretamente do perfil (nao e um
  eixo independente) — ver justificativa completa na docstring do modulo.
- `src/ui/componentes.py::render_estrategia_recomendada`: secao "📊
  Estrategia recomendada para hoje", integrada em
  `pagina_publica.py::render_resultado` apos a secao de Elite Score/
  explicabilidade. `pagina_admin.py` nao foi alterado (`git diff` vazio).
- `tests/test_elite_decision_engine.py` (20 testes): classificacao nos
  limites exatos das faixas, estrategia correta para diferentes
  distribuicoes de lote (majoritariamente forte/fraco/misto), casos de
  borda (lote vazio), repetibilidade e integracao com o Elite Score real
  sem alterar nenhum score original.

## V1.4 — Elite Score Explainable AI

Nova camada de explicacao sobre o Elite Score (Phoenix V2), construida
inteiramente na camada `src/ai/`. Nao altera `src/core/motor_elite.py`,
nenhuma formula do Elite Score (`src/core/elite_score.py` permanece
intocado) nem a arquitetura existente.

### Adicionado

- `src/ai/elite_explainer.py`: `explicar_jogo(jogo, features, score)` e o
  atalho `explicar_resultado(jogo, resultado)`, mais as dataclasses
  `PontoDeAtencao` e `ExplicacaoElite`. Traduz os componentes ja calculados
  pelo Core (`ComponenteEliteScore`) em classificacao (`ELITE PREMIUM` /
  `ALTO` / `MÉDIO` / `BAIXO`), pontos fortes e penalidades — sem recalcular
  nenhum valor. 100% local e deterministico: mesma entrada sempre produz a
  mesma explicacao, sem chamadas de rede nem modelo de IA generativa.
- Limiares de classificacao (40/60/80) derivados diretamente de
  `core.elite_score.PISO_SUB_SCORE` (divisao do intervalo valido de
  sub-score `[20, 100]` em quartis), evitando numeros arbitrarios novos —
  ver justificativa completa na docstring do modulo.
- `src/ui/componentes.py::render_explicacao_elite`: secao "Por que esse jogo
  recebeu essa nota?", integrada em `pagina_publica.py::render_resultado`
  logo apos o painel de Elite Score existente.
  `render_elite_score_painel` passou a devolver `(dezenas, resultado)` do
  jogo selecionado (antes devolvia `None`), de forma aditiva e retro
  compativel — `pagina_admin.py` continua ignorando o retorno e permanece
  sem nenhuma alteracao (`git diff` vazio para esse arquivo).
- `tests/test_elite_explainer.py` (18 testes): classificacao nos limites
  exatos das faixas, selecao correta de pontos fortes/penalidades,
  repetibilidade e integracao com o Elite Score real sem alterar o
  resultado original do Core.

## Hardening RC — Release Candidate Phoenix v1.3.0

Missão de hardening (sem novas funcionalidades): auditoria completa de
código morto, arquitetura, performance, qualidade, testes, segurança e
documentação, seguida apenas das correções de problemas reais encontrados.
Motor Elite, regras matemáticas, pagamentos e arquitetura em camadas
permanecem inalterados.

### Corrigido

- **Acoplamento UI → Core** (`src/ui/pagina_publica.py`,
  `src/ui/pagina_admin.py`): a camada de apresentação importava
  `src.core.motor_elite` e `src.core.estatisticas` diretamente, contornando a
  camada `services`. Corrigido roteando pela camada de serviço: nova função
  `previsao_service.motor_oficial_nome()` e novos wrappers finos em
  `base_service` (`dezenas_quentes`, `dezenas_frias`, `dezenas_atrasadas`,
  `pares_impares`, `centro_moldura`, `linhas_colunas`), que apenas repassam
  para `core.estatisticas` sem alterar nenhum cálculo (equivalência coberta
  por teste).
- **Duplicação de código** (`src/ui/pagina_publica.py`): a lista de colunas
  de dezenas de um jogo (`Bola1..Bola15`) era reconstruída manualmente
  (`[f"Bola{i}" for i in range(1, 16)]`) em vez de reaproveitar a constante
  já importada `COLUNAS_DEZENAS`.
- **Imports não utilizados**: `from statistics import mean`
  (`scripts/auditoria_15_pontos.py`) e `import shutil`
  (`tests/test_services.py`), ambos sem nenhum uso no corpo do arquivo
  (confirmado por análise estática AST, já que `ruff`/`pyflakes` não puderam
  ser instalados neste ambiente por falta de acesso à rede).
- **Performance** (`src/core/elite_score.py::construir_referencias`): a
  função percorria o DataFrame histórico 4 vezes separadas
  (`DataFrame.apply(axis=1)` para pares, centro, linhas/colunas e novamente
  para montar os conjuntos de repetição). Corrigido convertendo cada
  concurso para lista/conjunto de `int` uma única vez e reaproveitando essa
  estrutura em todas as métricas. Medição real na base de 3.596 concursos:
  ~484ms → ~76ms (≈6,4x mais rápido), com equivalência numérica confirmada
  contra a versão anterior por teste dedicado. (Uma primeira tentativa desta
  otimização usando `DataFrame.apply` retornando `pd.Series` por linha
  mostrou-se mais lenta que o código original e foi descartada antes de
  chegar a este arquivo.)
- **Validação de entrada** (`src/core/elite_score.py::calcular_elite_score`):
  passou a levantar `ValueError` para jogos que não tenham exatamente 15
  dezenas distintas entre 1 e 25, alinhando o comportamento com as mesmas
  validações já existentes em `src/models/jogo.py` e
  `src/models/concurso.py`. Não altera o cálculo do score em si.

### Testes

- 9 novos testes adicionados (55 no total, antes 46): equivalência dos
  wrappers de `base_service`/`previsao_service` contra as chamadas diretas
  ao Core, cobertura da camada `services` (`base_service`,
  `previsao_service`, `elite_score_service`, `pagamento_service`) e 3 testes
  de validação de entrada em `calcular_elite_score` (número errado de
  dezenas, dezena repetida, dezena fora da faixa 1-25).

### Conhecido / não corrigido nesta fase

- `src/repository/mercado_pago_gateway.py` e o fluxo de pagamento PIX
  dependente de rede não têm testes automatizados dedicados (exigiria mock
  de chamadas HTTP), classificado como melhoria futura — fora do escopo
  desta missão de hardening.
- `ruff` e `mypy` não puderam ser executados neste ambiente por não haver
  acesso à rede para instalação; a análise estática equivalente foi feita
  manualmente via script AST próprio. Recomenda-se rodar
  `pip install -r requirements-dev.txt && ruff check . && mypy src` em um
  ambiente com acesso à internet antes do release final.

## Phoenix V2 — Modulo Elite Score

Primeira funcionalidade nova construida sobre a arquitetura Phoenix V1
(congelada). Nao altera o Motor Elite, nenhuma regra matematica, a
arquitetura ou a interface existente — apenas adiciona uma camada de
analise sobre jogos ja gerados.

### Adicionado

- `src/models/elite_score.py`: dataclasses `FaixaHistorica`,
  `ReferenciasEliteScore`, `ComponenteEliteScore`, `EliteScoreResultado`.
- `src/core/elite_score.py`: `construir_referencias(df)`,
  `calcular_elite_score(...)`, `calcular_elite_score_lote(...)`, constante
  `PESOS` (soma 100%). Metodologia por percentis historicos (p10/p90/min/max),
  sem heuristica arbitraria — detalhes em `docs/ELITE_SCORE.md`.
- `src/services/elite_score_service.py`: `anexar_elite_score(jogos_df,
  df_historico)` e `calcular_scores(...)`.
- `src/ui/componentes.py::render_elite_score_painel`: tabela + seletor de
  jogo + explicacao resumida + detalhamento, usado em
  `pagina_publica.py::render_resultado` e `pagina_admin.py::render_admin`.
- `tests/test_core_elite_score.py` (15 testes) e `TestEliteScoreService` em
  `tests/test_services.py` (4 testes): consistencia, repetibilidade,
  estabilidade e o caso de borda de diversidade com jogos duplicados.
- `docs/ELITE_SCORE.md`: metodologia completa, justificativa de cada peso
  (incluindo por que frequencia historica e atraso tem peso baixo, calibrado
  pela variancia real observada na base) e limitacoes conhecidas.

### Decisoes tecnicas registradas

- Coluna de exibicao mantida como **"Elite Score"** (conforme pedido), com
  legenda explicando que e diferente do "Elite Score Temporal"/"Elite Score
  V2" do Motor Elite (que geram os jogos). No painel admin, a coluna "Elite
  Score" ja existente (Motor Elite V1) foi renomeada apenas na exibicao para
  "Elite Score (Motor V1)" — sem tocar no Motor Elite.
- Pesos dos 8 componentes calibrados pela variancia real da base historica
  (3.596 concursos): pares/impares 20%, linhas/colunas 15%, moldura/miolo
  15%, soma 15%, repeticao 15%, diversidade do lote 10%, frequencia
  historica 5%, atraso 5%.
- Diversidade entre jogos do lote exclui o proprio jogo por POSICAO, nao por
  valor (bug encontrado e corrigido em desenvolvimento, com teste de
  regressao dedicado).

## Infraestrutura de desenvolvimento (pre-Phoenix V2)

Última etapa de infraestrutura antes da Phoenix V2. Somente ferramental de
desenvolvimento — nenhuma regra de negócio, o Motor Elite, a arquitetura
Phoenix V1 ou a interface foram alterados.

### Adicionado

- `.gitattributes`: normaliza fim de linha para LF em arquivos de texto,
  eliminando de forma definitiva o ruído de CRLF/LF identificado na auditoria
  da Phoenix V1 (comando de normalização único documentado em
  `docs/DESENVOLVIMENTO.md`, a ser executado e revisado pelo usuário).
- `.editorconfig`: padroniza UTF-8, LF, indentação e newline final entre
  editores.
- `.gitignore`: ampliado para cobrir caches de teste/lint/tipagem
  (`.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `.coverage`,
  `htmlcov/`), artefatos gerados em tempo de execução
  (`exports/lotofacil_previsao_*.csv`), pastas de build/empacotamento,
  arquivos de IDE e de sistema operacional.
- `requirements-dev.txt`: reescrito para conter **apenas** dependências de
  desenvolvimento (`pytest`, `pytest-cov`, `mypy`, `ruff`), sem incluir as
  dependências de produção.
- `.github/workflows/ci.yml`: estrutura de CI dormente e vendor-neutra —
  instala dependências e chama `dev_check.py`; inerte até o repositório ser
  hospedado no GitHub com Actions habilitado, sem exigir nenhum serviço
  externo adicional.
- `dev_check.py`: script único de desenvolvimento local, roda estrutura de
  pastas/arquivos → validação de imports → suite de testes, com resumo e
  código de saída para uso em CI.
- `docs/DESENVOLVIMENTO.md`: fluxo oficial de desenvolvimento (ambiente,
  padrões de arquivo, o que não é versionado, CI, lint/tipagem).
- `README.md`: link para o novo fluxo de desenvolvimento e instrução de uso
  do `dev_check.py`.

## Phoenix V1 — Refatoracao arquitetural (nao muda comportamento)

Refatoracao incremental do Lotofacil Elite Pro para uma arquitetura em
camadas (Core / Services / Repository / Models / UI / AI), preservando 100%
das funcionalidades, regras de negocio, formulas e comportamento visual
existentes. Nenhuma tela, rota ou regra matematica foi alterada.

### Adicionado

- `src/core/`: `estatisticas.py`, `motor_elite.py`, `pagamento_regras.py` —
  regras de negocio puras, sem I/O.
- `src/repository/`: `base_repository.py`, `pagamento_repository.py`,
  `mercado_pago_gateway.py`, `exportacoes_repository.py` — toda leitura e
  escrita de dados (CSV, HTTP).
- `src/services/`: `base_service.py`, `previsao_service.py`,
  `pagamento_service.py` — orquestracao entre core e repository.
- `src/models/`: `Concurso`, `MetaConcurso`, `Jogo`, `Pagamento` —
  dataclasses de dominio, uso aditivo (preparando API/mobile futuros).
- `src/ui/`: `estilos.py`, `componentes.py`, `pagina_publica.py`,
  `pagina_admin.py` — apresentacao Streamlit extraida de `app.py`.
- `src/ai/elite_explicativo.py`: camada explicativa (sem Machine Learning),
  le rankings/jogos ja calculados e produz texto. Nao altera o algoritmo.
- `src/utils/formatacao.py`, `src/utils/logging_config.py`: formatacao de
  moeda e logging centralizado (substitui `except Exception: pass` silenciosos
  por log auditavel, sem mudar o fallback).
- `config.py`: constantes de versao/status e acesso a `st.secrets`
  centralizados (antes espalhados em `app.py`).
- `tests/`: 27 testes unitarios/integracao cobrindo leitura de base,
  estatisticas, geracao de jogos (Motor Elite oficial V3.5 temporal), regras
  de pagamento e services.
- `requirements-dev.txt`: dependencia de teste (`pytest`) separada da
  producao.
- `docs/ARCHITECTURE.md`: documentacao da arquitetura e da decisao tecnica
  Streamlit vs. Flask.

### Removido (apos migracao 1:1 confirmada)

- `src/carregar_dados.py` → `src/repository/base_repository.py`
- `src/estatisticas_lotofacil.py` → `src/core/estatisticas.py`
- `src/motor_elite_lotofacil.py` → `src/core/motor_elite.py`
- `src/mercado_pago_pix.py` → `src/repository/mercado_pago_gateway.py`
- `src/pagamentos.py` → dividido em `src/core/pagamento_regras.py` (regras
  puras) e `src/repository/pagamento_repository.py` (log CSV).

Antes da remocao, a saida de todas as funcoes acima foi comparada
programaticamente (modulo antigo vs. novo) usando a base real do projeto
(`dados/lotofacil_historico.csv`, 3596 concursos): jogos de producao,
rankings V1/V2, dezenas quentes/frias/atrasadas, validacao de e-mail e calculo
de valor de pagamento retornaram **resultados identicos**.

### Decisao tecnica registrada

- **Streamlit mantido como camada de apresentacao** (em vez de migrar para
  Flask, conforme o plano generico original). Ver justificativa completa em
  `docs/ARCHITECTURE.md`.
- **DataFrame mantido no Core** (estatisticas e Motor Elite): nao foi
  convertido para dataclasses por linha, pois o pipeline e vetorizado com
  pandas; converter aumentaria risco de regressao e custo de performance sem
  ganho real. Os modelos de dominio (`src/models/`) foram adicionados de forma
  aditiva, para consumo futuro por API/mobile.
- `scripts/` (backtests standalone) e `exports/` (relatorios historicos) nao
  foram alterados: nao fazem parte do runtime do app e nao importam nada de
  `src/`.

### Compatibilidade

`app.py` continua sendo o ponto de entrada (`streamlit run app.py`), com
exatamente as mesmas telas, textos, chaves de `session_state`, CSS e fluxo de
pagamento PIX de antes. Nenhuma rota ou funcionalidade publica mudou.
