"""Shim de compatibilidade — NAO adicionar logica nova aqui.

O modulo original ``src/motor_elite_lotofacil.py`` foi movido, sem alteracao
de nenhuma regra ou formula, para ``src/core/motor_elite.py`` durante a
Fase 2 do Phoenix Architecture. Este arquivo faz este nome antigo apontar
para o mesmo objeto de modulo (mesmo ``sys.modules`` entry), e nao apenas
reexportar alguns nomes, para que testes com ``monkeypatch`` continuem
funcionando corretamente.

Qualquer alteracao de comportamento deve ser feita em
``src/core/motor_elite.py``, nunca aqui.
"""

from __future__ import annotations

import sys

from src.core import motor_elite as _impl

sys.modules[__name__] = _impl
