"""Shim de compatibilidade — NAO adicionar logica nova aqui.

O modulo original ``src/estatisticas_lotofacil.py`` foi movido, sem
alteracao de logica, para ``src/core/estatisticas.py`` durante a Fase 2 do
Phoenix Architecture. Este arquivo faz este nome antigo apontar para o
mesmo objeto de modulo (mesmo ``sys.modules`` entry), e nao apenas
reexportar alguns nomes.

Qualquer alteracao de comportamento deve ser feita em
``src/core/estatisticas.py``, nunca aqui.
"""

from __future__ import annotations

import sys

from src.core import estatisticas as _impl

sys.modules[__name__] = _impl
