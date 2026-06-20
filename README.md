# Lotofácil Elite Pro — V2 Funcional

Aplicação Streamlit para análise histórica e **busca estatística pelos 15 acertos** da Lotofácil.

> A Lotofácil é um jogo aleatório. Este projeto não garante acertos, prêmio ou retorno financeiro. Use as análises como apoio estatístico e jogue com responsabilidade.

## Recursos da V2

- Frequência histórica e janelas recentes de 10, 25, 50 e 100 concursos.
- Atraso e presença das dezenas no último concurso.
- Avaliação de soma, pares/ímpares, repetição, linhas e colunas 5x5.
- Moldura, miolo e sequência máxima.
- Penalidade para jogos muito parecidos e diversidade mínima da carteira.
- Cinco perfis estatísticos com score final por jogo.
- Ranking completo das 25 dezenas.
- Backtest temporal por perfil, sem usar o resultado futuro na geração.
- Taxas de 11+, 12+, 13+, 14+ e 15 acertos.
- Salvamento, conferência e exportação CSV.

## Instalação

Requer Python 3.11 ou superior.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Executar localmente

```powershell
python -m streamlit run app.py
```

O navegador abrirá normalmente em `http://localhost:8501`.

## Abas

### Gerar Jogos

Gera cinco jogos válidos e distintos, permite salvar a carteira e exportar os jogos em CSV.

### Backtest

Selecione a quantidade de concursos e execute a simulação. Para cada concurso, o motor recebe somente os concursos anteriores. O resumo apresenta média, melhor resultado e taxas por faixa e perfil. O relatório detalhado pode ser exportado em CSV.

### Conferir Jogos

Compara as carteiras salvas com os resultados existentes na base e atualiza a quantidade de acertos.

### Ranking das Dezenas

Mostra frequência histórica, frequência recente, atraso e score por perfil.

### Configurações

Permite ajustar soma, pares, repetição, sequência, diversidade e tamanho da busca de candidatos.

## Atualizar dados

Use o botão **ATUALIZAR BASE OFICIAL** na aba Configurações. Se a CAIXA estiver indisponível, o arquivo local é preservado.

Base local:

`dados/lotofacil_historico.csv`

## Testes

```powershell
python -m pytest -q
```

Os testes cobrem motor, validade das dezenas, diversidade, ranking, backtest, jogos salvos e interface Streamlit.

## Jogo responsável

Não aumente apostas para recuperar perdas e não comprometa despesas essenciais. A V2 melhora o processo de análise; não altera a natureza aleatória do sorteio e não oferece garantia de prêmio.
