"""Modelos de dominio (dataclasses).

Fase 4 - Phoenix V1: modelos adicionados de forma aditiva, sem substituir o uso
de ``pandas.DataFrame`` nos motores estatisticos e de geracao de jogos (Core).
Essa troca exigiria reescrever ranking/geracao linha-a-linha, o que aumenta
risco de regressao e piora performance sem necessidade real agora. Os modelos
abaixo servem para consumo futuro por API/mobile/dashboard, onde um contrato
tipado e mais valioso do que dentro do pipeline vetorizado do Core.
"""
