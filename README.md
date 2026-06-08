# Lotofacil Elite Pro

Versao inicial: `LOTOFACIL_ELITE_PRO_V1`

Status: `DESENVOLVIMENTO`

Sistema independente inspirado na arquitetura do Mega-Sena Pro, adaptado para Lotofacil com interface publica simplificada, PIX Mercado Pago, modo admin e Motor Elite Lotofacil.

## Rodar localmente

```powershell
streamlit run app.py
```

## Configuracao PIX

Copie `.streamlit/secrets.toml.example` para `.streamlit/secrets.toml` e configure:

```toml
MERCADO_PAGO_ACCESS_TOKEN = "SEU_TOKEN"
MODO_ADMIN = false
```

## Aviso

A Lotofacil e aleatoria. Este sistema faz analise estatistica e nao garante acerto, premio ou resultado.
