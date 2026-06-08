from __future__ import annotations

import base64
from io import BytesIO

import requests


API_PAGAMENTOS = "https://api.mercadopago.com/v1/payments"


def criar_pagamento_pix(access_token: str, valor: float, descricao: str, email_cliente: str) -> dict:
    payload = {
        "transaction_amount": float(valor),
        "description": descricao,
        "payment_method_id": "pix",
        "payer": {"email": email_cliente},
    }
    resposta = requests.post(
        API_PAGAMENTOS,
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
        json=payload,
        timeout=30,
    )
    resposta.raise_for_status()
    return resposta.json()


def consultar_pagamento_pix(access_token: str, payment_id: str | int) -> dict:
    resposta = requests.get(
        f"{API_PAGAMENTOS}/{payment_id}",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=30,
    )
    resposta.raise_for_status()
    return resposta.json()


def extrair_dados_pix(resposta: dict) -> dict:
    transacao = resposta.get("point_of_interaction", {}).get("transaction_data", {})
    qr_base64 = transacao.get("qr_code_base64") or ""
    return {
        "payment_id": resposta.get("id"),
        "status": resposta.get("status", "pending"),
        "qr_code": transacao.get("qr_code", ""),
        "qr_code_base64": qr_base64,
        "qr_code_bytes": base64.b64decode(qr_base64) if qr_base64 else b"",
    }
