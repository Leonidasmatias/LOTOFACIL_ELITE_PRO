# Lotofácil Elite Pro — V3 Inteligente

Aplicação Streamlit para análise histórica e **busca estatística pelos 15 acertos** da Lotofácil.

> A Lotofácil é aleatória. A aplicação não garante acertos, prêmio ou retorno financeiro. Use os indicadores como apoio estatístico e jogue com responsabilidade.

## Novidades da V3

- Estratégia Inteligente com recomendação operacional diária.
- Ranking dos perfis Conservador, Equilibrado, Agressivo, Elite e Experimental.
- Comparação histórica entre Motor Elite e carteiras aleatórias equivalentes.
- Carteiras configuráveis de 5, 10, 20 ou 30 jogos.
- Custo estimado da carteira com valor unitário configurável.
- Histórico agregado de desempenho das carteiras salvas.
- Relatório “Melhor Estratégia do Dia” em CSV e TXT.
- Backtest configurável por quantidade de jogos, perfil e comparação aleatória.

## Motor estatístico

O motor considera:

- Frequência histórica e janelas recentes de 10, 25, 50 e 100 concursos.
- Atraso e presença no último concurso.
- Soma, pares/ímpares e repetição.
- Linhas e colunas da cartela 5×5.
- Moldura, miolo e sequência máxima.
- Penalidade de similaridade e diversidade mínima entre jogos.
- Score final por jogo e ranking das 25 dezenas.

## Estratégia Inteligente

A nova aba combina dados históricos e backtest temporal para apresentar:

- Perfil recomendado e ranking dos cinco estilos V3.
- Nível de risco e quantidade sugerida de jogos.
- Dezenas mais fortes e dezenas em alerta.
- Faixa ideal de soma, paridade e repetição sugerida.
- Justificativa operacional auditável.

A recomendação é estatística e não representa previsão garantida.

## Comparador contra aleatório

O backtest cria, para cada concurso simulado:

1. Uma carteira do Motor Elite.
2. Uma carteira aleatória válida com a mesma quantidade de jogos.
3. A comparação das taxas de 11+, 12+, 13+, 14+ e 15.

A vantagem apresentada é a diferença em pontos percentuais entre as taxas observadas. Resultados históricos não garantem desempenho futuro.

## Carteira configurável

Na aba **Gerar Jogos**, escolha 5, 10, 20 ou 30 jogos. Todos devem:

- Conter exatamente 15 dezenas únicas entre 1 e 25.
- Respeitar soma, paridade, repetição e sequência configuradas.
- Ser diferentes e manter diversidade mínima.

O custo mostrado é uma estimativa calculada pelo valor unitário informado em **Configurações**. Confirme o preço oficial antes de apostar.

## Histórico de desempenho

A aba **Conferir Jogos** agrupa as carteiras por geração e apresenta:

- Data, perfis e quantidade de jogos.
- Concurso-alvo e confirmação do resultado.
- Melhor acerto e média da carteira.
- Situação: aguardando resultado, premiado ou sem prêmio.

## Backtest sem vazamento temporal

Cada concurso é simulado usando exclusivamente os concursos anteriores. O resultado avaliado nunca é fornecido ao motor nem ao gerador aleatório.

É possível selecionar:

- Número de concursos simulados.
- Carteiras de 5, 10, 20 ou 30 jogos.
- Comparativo Motor Elite × aleatório.
- Resultado por perfil e melhor carteira simulada.

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

Acesso local padrão: `http://localhost:8501`.

## Atualizar a base

Use **ATUALIZAR BASE OFICIAL** na aba Configurações. Se a consulta falhar, o arquivo local é preservado.

Base: `dados/lotofacil_historico.csv`

## Testes

```powershell
python -m pytest -q
```

Os testes cobrem motor, carteiras 5/10/20/30, validação, comparação aleatória, estratégia diária, histórico, backtest temporal, jogos salvos e interface.

## Jogo responsável

Não comprometa despesas essenciais e não aumente apostas para recuperar perdas. A V3 melhora a análise e a disciplina da decisão; não altera a natureza aleatória do sorteio e não oferece garantia de prêmio.
