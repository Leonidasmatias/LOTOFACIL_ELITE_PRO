"""Fingerprint reprodutivel dos dados historicos usados por uma previsao
(LF-04, Fase 9 -- reprodutibilidade)."""
from __future__ import annotations

import hashlib
from typing import Sequence

from .contracts import ContestSnapshot


def data_fingerprint(history: Sequence[ContestSnapshot]) -> str:
    """Hash SHA256 determinístico do conteudo exato do historico recebido
    (numero, data e dezenas de cada concurso, na ordem dada). Duas
    execucoes com o mesmo historico sempre produzem o mesmo fingerprint;
    qualquer diferenca (um concurso extra, uma dezena diferente, ordem
    diferente) produz um fingerprint diferente."""
    linhas = [
        f"{concurso.number}|{concurso.date}|{'-'.join(f'{d:02d}' for d in concurso.numbers)}"
        for concurso in history
    ]
    conteudo = "\n".join(linhas).encode("utf-8")
    return hashlib.sha256(conteudo).hexdigest()
