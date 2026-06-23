# Auditoria Railway — Lotofácil Elite Pro

## Diagnóstico

- Entrada Streamlit: `app.py`.
- Entrada Railway: `python scripts/start_railway.py`.
- Bind: `0.0.0.0`.
- Porta: variável `PORT` fornecida pelo Railway; `8501` somente como padrão local.
- Health check: `/_stcore/health`.
- Não há `localhost`, `127.0.0.1`, porta fixa de produção ou caminho absoluto Windows no código Python de runtime.

## Causa do 502

O branch remoto `main`, confirmado por `git ls-remote`, aponta para `be3af48` e contém somente `app.py` e
`requirements.txt` entre os arquivos de implantação. Ele não contém `Procfile`, `railway.json`
nem `.python-version`. Assim, o deploy a partir desse branch não recebe o comando web e o health
check preparados localmente. Além disso, a configuração local anterior dependia da expansão de
`$PORT` dentro da string de start.

## Correção

O `Procfile` e o `railway.json` agora chamam um inicializador único. Esse inicializador lê `PORT`
diretamente do ambiente, valida o intervalo TCP e inicia o Streamlit com endereço `0.0.0.0`.
Os arquivos precisam ser commitados e enviados ao branch que o serviço Railway acompanha; só
existirem no diretório local não altera o deployment.

## Persistência

Com `LOTOFACIL_DATA_DIR=/app/data` e um volume montado nesse caminho, a base e o SQLite são
gravados em local persistente. A criação do diretório, a cópia inicial da base e a criação do banco
foram validadas com um diretório vazio. Sem volume, o serviço continua funcionando, mas os dados
gravados no filesystem efêmero podem desaparecer após um novo deploy.

## Validação local Railway

Ambiente usado: `PORT=18234` e `LOTOFACIL_DATA_DIR` apontando para diretório temporário vazio.

- `/`: HTTP 200.
- `/_stcore/health`: HTTP 200, corpo `ok`.
- Listener informado pelo Streamlit: `0.0.0.0:18234`.
