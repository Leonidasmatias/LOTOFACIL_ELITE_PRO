# Fluxo de Desenvolvimento

Este documento descreve o fluxo oficial para trabalhar no Lotofacil Elite Pro
a partir da infraestrutura criada nesta etapa (preparação para a Phoenix V2).
Nenhuma regra de negócio, o Motor Elite, a arquitetura Phoenix ou a interface
foram alterados por esta etapa — é só ferramental de desenvolvimento.

## 1. Configurar o ambiente

```powershell
python -m venv .venv
.venv\Scripts\activate

pip install -r requirements.txt
pip install -r requirements-dev.txt
```

`requirements.txt` tem as dependências de produção (Streamlit, pandas etc.).
`requirements-dev.txt` tem **apenas** as de desenvolvimento (`pytest`,
`pytest-cov`, `mypy`, `ruff`) — instale as duas, em separado, no seu ambiente
local.

## 2. Rodar a aplicação

```powershell
streamlit run app.py
```

## 3. Antes de commitar: rodar a verificação única

```powershell
python dev_check.py
```

Esse script roda, nesta ordem, e mostra um resumo no final:

1. **Estrutura** — confere se os arquivos/pastas esperados pela arquitetura
   Phoenix (`src/core`, `src/repository`, `src/services`, `src/models`,
   `src/ui`, `src/ai`, `src/utils`, `tests`, `docs`) continuam no lugar.
2. **Imports** — importa todos os módulos do projeto. Módulos que não
   dependem de Streamlit (`core`, `repository`, `services`, `models`, `ai`,
   `utils`) são sempre checados; os que dependem (`config.py`, `src/ui/*`,
   `app.py`) só são checados se o Streamlit estiver instalado no ambiente.
3. **Testes** — roda `pytest tests/ -q` (ou `unittest` como alternativa, caso
   `pytest` não esteja instalado).

Código de saída `0` = tudo certo. Qualquer coisa diferente de `0` = alguma
checagem falhou (o próprio script imprime o que falhou e por quê).

Esse é o mesmo comando que o CI roda — rodá-lo localmente antes de abrir um
PR evita surpresas.

## 4. Padrões de arquivo (automáticos no editor)

- **`.editorconfig`**: UTF-8, fim de linha LF, indentação de 4 espaços em
  Python (2 em YAML/JSON/TOML), newline final — a maioria dos editores
  (VS Code, PyCharm, Sublime etc.) já lê esse arquivo automaticamente, sem
  configuração adicional.
- **`.gitattributes`**: força fim de linha LF no repositório para arquivos de
  texto (`.py`, `.md`, `.csv`, `.toml` etc.), eliminando o problema de
  CRLF/LF identificado na auditoria da Phoenix V1. Isso vale para novos
  arquivos e para o próximo `git add` de arquivos já existentes. Para
  normalizar de uma vez os arquivos que já estão no repositório, rode (uma
  única vez, e revise o diff antes de commitar):

  ```powershell
  git add --renormalize .
  git commit -m "chore: normaliza fim-de-linha para LF"
  ```

  Isso só reescreve a codificação da quebra de linha — nenhum conteúdo ou
  regra de negócio é alterado.

## 5. O que não é versionado

`.gitignore` cobre, além do já existente (`.venv`, `__pycache__`, segredos do
Streamlit, backups locais): caches de teste/lint/tipagem (`.pytest_cache/`,
`.mypy_cache/`, `.ruff_cache/`, `.coverage`, `htmlcov/`), arquivos gerados em
tempo de execução (`exports/lotofacil_previsao_*.csv`, `exports/pagamentos.csv`,
`exports/*.log`), pastas de build/empacotamento, arquivos de IDE
(`.vscode/`, `.idea/`) e arquivos de sistema operacional
(`.DS_Store`, `Thumbs.db`, `Desktop.ini`).

`dados/lotofacil_historico.csv` e o conteúdo de `exports/*.md` /
`exports/backtest_*.csv` **continuam versionados de propósito**: são dado
histórico e relatórios de auditoria, não artefatos descartáveis.

## 6. Integração contínua (CI)

`.github/workflows/ci.yml` fica pronto (mas inerte) para quando o repositório
estiver hospedado no GitHub com Actions habilitado — não exige nenhuma conta
ou serviço externo além do próprio GitHub. Ele só instala as dependências e
chama `python dev_check.py`, então qualquer outro provedor de CI (GitLab CI,
Azure Pipelines etc.) pode ser configurado copiando os mesmos dois passos,
sem duplicar lógica de verificação.

## 7. Lint e tipagem (ferramental disponível, uso opcional por enquanto)

`requirements-dev.txt` já inclui `ruff` (lint/formatação) e `mypy` (checagem
estática de tipos). Ainda não há um arquivo de configuração dedicado
(`pyproject.toml`/`ruff.toml`/`mypy.ini`) nem integração no `dev_check.py` —
isso fica para uma próxima etapa de infraestrutura, para não misturar
introdução de lint estrito com a normalização de ambiente feita agora.
