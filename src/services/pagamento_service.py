"""Orquestra o fluxo de pagamento PIX (Mercado Pago) + registro de auditoria.

Extraido de ``app.py`` (Fase 3 - Phoenix V1). Chama ``core.pagamento_regras``
para as regras puras e ``repository`` para I/O (gateway HTTP + log CSV).
"""
from __future__ import annotations

from ..core.pagamento_regras import calcular_valor_pagamento, email_cliente_valido
from ..repository import mercado_pago_gateway
from ..repository.pagamento_repository import registrar_pagamento as _registrar_pagamento


def valor_padrao_analise(quantidade: int = 1) -> float:
    return calcular_valor_pagamento(quantidade)


def email_valido(email: str) -> bool:
    return email_cliente_valido(email)


def criar_pix(access_token: str, valor: float, descricao: str, email_cliente: str) -> dict:
    resposta = mercado_pago_gateway.criar_pagamento_pix(access_token, valor, descricao, email_cliente)
    return mercado_pago_gateway.extrair_dados_pix(resposta)


def consultar_pix(access_token: str, payment_id: str | int) -> dict:
    resposta = mercado_pago_gateway.consultar_pagamento_pix(access_token, payment_id)
    return mercado_pago_gateway.extrair_dados_pix(resposta)


def registrar_pagamento(
    funcao: str,
    concurso_alvo: int | str,
    valor_total: float,
    status_pagamento: str,
    payment_id: str | int | None,
    email_pagador: str,
    conteudo_liberado: str = "",
) -> None:
    _registrar_pagamento(
        funcao, concurso_alvo, valor_total, status_pagamento, payment_id, email_pagador, conteudo_liberado
    )
