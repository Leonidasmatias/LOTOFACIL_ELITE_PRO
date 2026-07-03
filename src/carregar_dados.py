"""Shim de compatibilidade — NAO adicionar logica nova aqui.

O modulo original ``src/carregar_dados.py`` foi movido, sem alteracao de
logica, para ``src/repository/base_repository.py`` durante a Fase 1 do
Phoenix Architecture. Este arquivo faz este nome antigo apontar para o
mesmo objeto de modulo (mesmo ``sys.modules`` entry), e nao apenas
reexportar alguns nomes. Isso garante que testes e codigo legado que usam
``monkeypatch.setattr(carregar_dados, "algo", ...)`` continuem funcionando,
porque o "algo" corrigido é o mesmo atributo lido pelas funcoes internas de
``base_repository.py`` (mesmo modulo, mesmo __dict__).

Qualquer alteracao de comportamento deve ser feita em
``src/repository/base_repository.py``, nunca aqui.
"""

from __future__ import annotations

import sys

from src.repository import base_repository as _impl

sys.modules[__name__] = _impl
