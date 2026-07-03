"""Testes de regressao: regras puras de pagamento (Core).

Fase 0 - Phoenix V1.
"""
from __future__ import annotations

import unittest

from src.core import pagamento_regras


class TestPagamentoRegras(unittest.TestCase):
    def test_email_valido_aceita_formato_correto(self) -> None:
        self.assertTrue(pagamento_regras.email_cliente_valido("cliente@dominio.com"))

    def test_email_valido_rejeita_formatos_incorretos(self) -> None:
        for email in ["", "sem-arroba.com", "sem-dominio@", "com espaco@dominio.com"]:
            self.assertFalse(pagamento_regras.email_cliente_valido(email))

    def test_calcular_valor_pagamento_quantidade_1(self) -> None:
        self.assertEqual(pagamento_regras.calcular_valor_pagamento(1), 1.0)

    def test_calcular_valor_pagamento_quantidade_multipla(self) -> None:
        self.assertEqual(pagamento_regras.calcular_valor_pagamento(3), 3.0)

    def test_calcular_valor_pagamento_minimo_e_1(self) -> None:
        self.assertEqual(pagamento_regras.calcular_valor_pagamento(0), 1.0)
        self.assertEqual(pagamento_regras.calcular_valor_pagamento(-5), 1.0)


if __name__ == "__main__":
    unittest.main()
