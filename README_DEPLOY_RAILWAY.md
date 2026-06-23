# Deploy Railway — Lotofácil Elite Pro V5

## Pré-requisitos

- Repositório Git com este diretório como raiz do serviço.
- Conta Railway.
- Volume persistente para o CSV atualizado e o SQLite.

## Configuração

1. Crie um projeto no Railway e selecione **Deploy from GitHub repo**.
2. Se o repositório for monorepo, defina **Root Directory** como `LOTOFACIL_ELITE_PRO`.
3. Crie um volume e monte-o em `/app/data`.
4. Cadastre as variáveis:

```text
LOTOFACIL_DATA_DIR=/app/data
PYTHONUNBUFFERED=1
TZ=America/Sao_Paulo
```

5. O primeiro start copia a base histórica embarcada para o volume quando ele estiver vazio.
6. O `railway.json` usa `/_stcore/health` como health check e executa `python scripts/start_railway.py`.
7. O inicializador lê e valida `PORT`, faz bind em `0.0.0.0` e repassa a porta ao Streamlit sem depender de expansão de variável pelo shell.

## Comando de início

```text
python scripts/start_railway.py
```

Não configure uma porta fixa no painel. O Railway fornece `PORT` dinamicamente.

## Persistência

O volume guarda:

```text
/app/data/lotofacil_historico.csv
/app/data/lotofacil_v5.sqlite3
```

Sem volume, alterações no CSV e no SQLite podem ser perdidas a cada novo deployment.

## Domínio

Após o serviço ficar saudável:

1. Acesse **Settings → Networking → Custom Domain**.
2. Adicione `lotofacil.leonidastech.com.br`.
3. Copie o registro CNAME fornecido pelo Railway para a zona DNS do Registro.br.
4. Aguarde a emissão do certificado HTTPS.

## Validação

```powershell
python -m pytest -q
$env:PORT="18234"
python scripts/start_railway.py
```

Verifique também:

- `https://SEU-DOMINIO/_stcore/health` retorna `ok`.
- A base oficial permanece após redeploy.
- O histórico SQLite permanece após redeploy.
- A atualização da CAIXA não substitui a base se ocorrer falha.

## Observação responsável

A Lotofácil é aleatória. A aplicação realiza análise histórica e busca estatística pelos 15 acertos, sem garantia de acerto, prêmio ou retorno financeiro.
