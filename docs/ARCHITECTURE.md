# Arquitetura Phoenix V1

Este documento descreve a arquitetura em camadas adotada a partir da
refatoracao Phoenix V1. O objetivo foi eliminar duplicacao, separar
responsabilidades e preparar o projeto para IA explicativa, API publica,
aplicativos mobile e Dashboard Premium, **sem alterar nenhuma regra de
negocio, algoritmo ou comportamento visual existente**.

## Decisao tecnica: Streamlit em vez de Flask

A arquitetura originalmente planejada previa uma camada `api/` com rotas
Flask. O projeto real, porem, sempre foi construido sobre **Streamlit**
(`app.py` + `st.*`) — nao ha, e nunca houve, nenhuma rota Flask no codigo.

Migrar para Flask exigiria reescrever toda a interface (paginas, CSS,
`session_state`, componentes reativos, cache), o que contraria diretamente o
principio "evolucao incremental, sem reescrita, com a aplicacao sempre
funcional". Por isso, a camada de apresentacao foi mantida em Streamlit e
reorganizada em `src/ui/`, cumprindo o mesmo papel que a camada `api/`
cumpriria em uma stack Flask: recebe interacao do usuario e chama `services`,
sem conter regra de negocio.

Se no futuro for necessaria uma API HTTP publica (para mobile, por exemplo),
o caminho recomendado e criar uma camada Flask/FastAPI nova, em paralelo,
reaproveitando integralmente `core`, `services` e `repository` — nenhuma
dessas camadas depende de Streamlit.

## Camadas

```
lotofacil_elite/
  app.py            Bootstrap Streamlit (fino: so monta a pagina)
  config.py         Configuracao/segredos centralizados (versao, MODO_ADMIN, token PIX)
  requirements.txt
  requirements-dev.txt
  src/
    core/           Regras de negocio puras (sem I/O, sem Streamlit)
      estatisticas.py
      motor_elite.py
      pagamento_regras.py
    services/       Orquestracao: chama core + repository
      base_service.py
      previsao_service.py
      pagamento_service.py
    repository/     Toda leitura/escrita de dados (CSV, HTTP, disco)
      base_repository.py
      pagamento_repository.py
      mercado_pago_gateway.py
      exportacoes_repository.py
    models/         Dataclasses de dominio (uso aditivo, futuro)
      concurso.py
      jogo.py
      pagamento.py
    ui/             Apresentacao Streamlit (equivalente ao "api/" do plano original)
      estilos.py
      componentes.py
      pagina_publica.py
      pagina_admin.py
    ai/             Camada explicativa (sem Machine Learning ainda)
      elite_explicativo.py
    utils/          Helpers genericos (formatacao, logging)
  tests/            Testes unitarios e de integracao leve
  scripts/          Backtests standalone (nao fazem parte do app em execucao)
  docs/             Esta documentacao
```

### Regras entre camadas

- `core` nunca importa `streamlit`, `requests` ou faz I/O de arquivo/rede.
- `services` nunca contem formula matematica ou peso de algoritmo; apenas
  chama `core` e `repository` na ordem certa.
- `repository` e o unico lugar que le/escreve CSV, chama a API da CAIXA ou o
  gateway do Mercado Pago.
- `ui` nunca calcula score, ranking ou valida regra de negocio; apenas chama
  `services` e renderiza.
- `ai` apenas le rankings/jogos ja calculados pelo `core.motor_elite` e produz
  texto explicativo. Nao pode, em hipotese alguma, alterar score, ranking ou
  jogo gerado.

## O que NAO mudou (garantia de compatibilidade)

Todas as formulas do Motor Elite (`ranking_elite_lotofacil`,
`ranking_elite_lotofacil_v2`, `gerar_jogos_producao_v1` / DNA temporal V3.5),
os pesos, penalidades, e as regras de pagamento (valor de R$ 1,00 por analise,
regex de validacao de e-mail) foram movidos **byte a byte**, sem nenhuma
alteracao de logica. Isso foi validado automaticamente comparando a saida dos
modulos antigos com os novos usando a base real do projeto antes de remover o
codigo antigo (ver `docs/CHANGELOG.md`).

## Testes

`tests/` cobre: leitura/validacao da base historica, estatisticas
(quentes/frias/atrasadas/pares-impares/centro-moldura/linhas-colunas), geracao
de jogos do Motor Elite oficial (V3.5 temporal), regras de pagamento e os
services de orquestracao. Rodar com:

```powershell
pip install -r requirements-dev.txt
python -m pytest tests/ -v
```

(Os testes tambem rodam com `python -m unittest discover -s tests` caso o
`pytest` nao esteja instalado.)
