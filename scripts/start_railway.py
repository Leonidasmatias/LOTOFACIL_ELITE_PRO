"""Inicializador deterministico do Streamlit para Railway e outros PaaS."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


PORTA_PADRAO = 8501


def obter_porta(ambiente: dict[str, str] | None = None) -> int:
    variaveis = os.environ if ambiente is None else ambiente
    valor = str(variaveis.get("PORT", PORTA_PADRAO)).strip()
    try:
        porta = int(valor)
    except ValueError as erro:
        raise SystemExit(f"PORT invalida: {valor!r}") from erro
    if not 1 <= porta <= 65535:
        raise SystemExit(f"PORT fora do intervalo TCP: {porta}")
    return porta


def comando_streamlit(porta: int) -> list[str]:
    return [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        "app.py",
        "--server.address=0.0.0.0",
        f"--server.port={porta}",
        "--server.headless=true",
        "--browser.gatherUsageStats=false",
    ]


def main() -> int:
    porta = obter_porta()
    raiz = Path(__file__).resolve().parents[1]
    os.chdir(raiz)
    comando = comando_streamlit(porta)
    print(f"[railway] raiz={raiz}", flush=True)
    print(f"[railway] PORT={porta}", flush=True)
    print("[railway] bind=0.0.0.0", flush=True)
    print(f"[railway] comando={' '.join(comando)}", flush=True)
    return subprocess.call(comando)


if __name__ == "__main__":
    raise SystemExit(main())
