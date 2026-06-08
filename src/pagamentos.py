from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re

import pandas as pd


VALOR_POR_ANALISE = 1.0
CAMINHO_LOG_PAGAMENTOS = Path("exports") / "pagamentos.csv"
EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def email_cliente_valido(email: str) -> bool:
    return bool(EMAIL_REGEX.match(str(email).strip()))


def calcular_valor_pagamento(quantidade: int = 1) -> float:
    return round(max(1, int(quantidade)) * VALOR_POR_ANALISE, 2)


def registrar_pagamento(
    funcao: str,
    concurso_alvo: int | str,
    valor_total: float,
    status_pagamento: str,
    payment_id: str | int | None,
    email_pagador: str,
    conteudo_liberado: str = "",
) -> None:
    CAMINHO_LOG_PAGAMENTOS.parent.mkdir(parents=True, exist_ok=True)
    linha = {
        "data_hora": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "funcao": funcao,
        "concurso_alvo": concurso_alvo,
        "valor_total": valor_total,
        "status_pagamento": status_pagamento,
        "payment_id": payment_id or "",
        "email_pagador": email_pagador,
        "conteudo_liberado": conteudo_liberado,
    }
    novo = pd.DataFrame([linha])
    if CAMINHO_LOG_PAGAMENTOS.exists():
        atual = pd.read_csv(CAMINHO_LOG_PAGAMENTOS, encoding="utf-8-sig")
        novo = pd.concat([atual, novo], ignore_index=True)
    novo.to_csv(CAMINHO_LOG_PAGAMENTOS, index=False, encoding="utf-8-sig")
