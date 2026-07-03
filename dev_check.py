#!/usr/bin/env python3
"""Script unico de verificacao para desenvolvimento local (Phoenix V1).

Roda tres checagens e imprime um resumo no final:

    1) estrutura de pastas/arquivos esperada pela arquitetura Phoenix;
    2) import de todos os modulos do projeto;
    3) suite de testes automatizados (tests/).

Uso:

    python dev_check.py

Codigo de saida 0 = tudo passou. Codigo != 0 = alguma checagem falhou.

Nao depende de nenhum servico externo — roda 100% localmente, com apenas a
biblioteca padrao do Python mais o que ja estiver instalado do
``requirements.txt``/``requirements-dev.txt``. E o mesmo comando usado pelo
workflow de CI em ``.github/workflows/ci.yml``.
"""
from __future__ import annotations

import importlib
import importlib.util
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent

# Arquivos/pastas que a arquitetura Phoenix V1 espera encontrar. Serve para
# detectar cedo se algo foi movido, renomeado ou apagado por engano.
ESTRUTURA_ESPERADA: list[str] = [
    "app.py",
    "config.py",
    "requirements.txt",
    "requirements-dev.txt",
    "src/__init__.py",
    "src/core/estatisticas.py",
    "src/core/motor_elite.py",
    "src/core/pagamento_regras.py",
    "src/core/elite_score.py",
    "src/repository/base_repository.py",
    "src/repository/mercado_pago_gateway.py",
    "src/repository/pagamento_repository.py",
    "src/repository/exportacoes_repository.py",
    "src/services/base_service.py",
    "src/services/previsao_service.py",
    "src/services/pagamento_service.py",
    "src/services/elite_score_service.py",
    "src/models/concurso.py",
    "src/models/jogo.py",
    "src/models/pagamento.py",
    "src/models/elite_score.py",
    "src/ui/estilos.py",
    "src/ui/componentes.py",
    "src/ui/pagina_publica.py",
    "src/ui/pagina_admin.py",
    "src/ai/elite_explicativo.py",
    "src/ai/elite_explainer.py",
    "src/ai/elite_decision_engine.py",
    "src/utils/formatacao.py",
    "src/utils/logging_config.py",
    "tests",
    "docs/ARCHITECTURE.md",
]

# Modulos que NAO dependem de Streamlit: sempre podem (e devem) ser
# importados, em qualquer ambiente.
MODULOS_PUROS: list[str] = [
    "src.core.estatisticas",
    "src.core.motor_elite",
    "src.core.pagamento_regras",
    "src.core.elite_score",
    "src.repository.base_repository",
    "src.repository.mercado_pago_gateway",
    "src.repository.pagamento_repository",
    "src.repository.exportacoes_repository",
    "src.services.base_service",
    "src.services.previsao_service",
    "src.services.pagamento_service",
    "src.services.elite_score_service",
    "src.models.concurso",
    "src.models.jogo",
    "src.models.pagamento",
    "src.models.elite_score",
    "src.ai.elite_explicativo",
    "src.ai.elite_explainer",
    "src.ai.elite_decision_engine",
    "src.utils.formatacao",
    "src.utils.logging_config",
]

# Modulos que dependem de Streamlit (camada UI + config + bootstrap). So sao
# checados se o pacote ``streamlit`` estiver instalado no ambiente atual.
MODULOS_STREAMLIT: list[str] = [
    "config",
    "src.ui.estilos",
    "src.ui.componentes",
    "src.ui.pagina_publica",
    "src.ui.pagina_admin",
    "app",
]


def _titulo(texto: str) -> None:
    print(f"\n=== {texto} ===")


def _modulo_disponivel(nome: str) -> bool:
    """Checa se um pacote esta instalado, sem quebrar em casos raros onde
    ``importlib.util.find_spec`` levanta excecao (ex.: modulo ja presente em
    ``sys.modules`` sem ``__spec__`` valido)."""
    try:
        return importlib.util.find_spec(nome) is not None
    except (ImportError, ValueError):
        return nome in sys.modules


def verificar_estrutura() -> bool:
    _titulo("1/3 - Verificacao da estrutura de pastas/arquivos")
    faltando = [item for item in ESTRUTURA_ESPERADA if not (RAIZ / item).exists()]
    if faltando:
        print("Itens esperados que NAO foram encontrados:")
        for item in faltando:
            print(f"  - {item}")
        return False
    print(f"OK: {len(ESTRUTURA_ESPERADA)} itens esperados estao presentes.")
    return True


def verificar_imports() -> bool:
    _titulo("2/3 - Validacao de imports")
    if str(RAIZ) not in sys.path:
        sys.path.insert(0, str(RAIZ))

    ok = True
    for nome in MODULOS_PUROS:
        try:
            importlib.import_module(nome)
        except Exception as erro:  # noqa: BLE001 - queremos capturar e reportar qualquer falha de import
            print(f"  FALHOU: {nome} -> {erro!r}")
            ok = False
    print(f"Modulos sem dependencia de Streamlit verificados: {len(MODULOS_PUROS)}")

    if not _modulo_disponivel("streamlit"):
        print(
            "AVISO: pacote 'streamlit' nao instalado neste ambiente — "
            f"pulando a validacao de {len(MODULOS_STREAMLIT)} modulo(s) de UI/bootstrap "
            "(config.py, src/ui/*, app.py). Rode 'pip install -r requirements.txt' "
            "para valida-los tambem."
        )
    else:
        for nome in MODULOS_STREAMLIT:
            try:
                importlib.import_module(nome)
            except Exception as erro:  # noqa: BLE001
                print(f"  FALHOU: {nome} -> {erro!r}")
                ok = False
        print(f"Modulos dependentes de Streamlit verificados: {len(MODULOS_STREAMLIT)}")

    if ok:
        print("OK: todos os modulos verificados importaram sem erro.")
    return ok


def rodar_testes() -> bool:
    _titulo("3/3 - Suite de testes automatizados")
    usar_pytest = _modulo_disponivel("pytest")
    if usar_pytest:
        comando = [sys.executable, "-m", "pytest", "tests", "-q"]
    else:
        print("AVISO: 'pytest' nao instalado, usando 'unittest' (stdlib) como alternativa.")
        comando = [sys.executable, "-m", "unittest", "discover", "-s", "tests"]

    resultado = subprocess.run(comando, cwd=RAIZ)
    return resultado.returncode == 0


def main() -> int:
    resultados = {
        "Estrutura": verificar_estrutura(),
        "Imports": verificar_imports(),
        "Testes": rodar_testes(),
    }

    _titulo("Resumo")
    for etapa, sucesso in resultados.items():
        status = "OK" if sucesso else "FALHOU"
        print(f"  {etapa}: {status}")

    if all(resultados.values()):
        print("\nTudo certo. Ambiente pronto para desenvolvimento.")
        return 0

    print("\nExistem checagens que falharam. Corrija antes de commitar/abrir PR.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
