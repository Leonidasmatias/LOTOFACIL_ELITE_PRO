"""Sensibilidade do resultado LF-05 a politica de seed do motor (LF-06,
Fase 13).

10 politicas de seed do motor, FIXAS e definidas algoritmicamente ANTES de
qualquer execucao -- nunca escolhidas depois de ver resultados. A politica
original do LF-05 (base=7_000_000) esta incluida, identificada e nunca
substituida.

Isto e replicacao diagnostica, nao busca de seed: nenhuma funcao aqui
recebe metrica de desempenho para decidir qual politica usar.
"""
from __future__ import annotations

SEED_POLICY_BASES: dict[str, int] = {
    "ORIGINAL_LF05": 7_000_000,
    **{f"ALT_{indice:02d}": 7_000_000 + indice * 100_000 for indice in range(1, 10)},
}


def seed_for_policy(policy_name: str, target_contest: int) -> int:
    """seed(politica, alvo) = base(politica) + alvo -- mesma forma
    funcional da politica original (``benchmark.motor_seed_policy``),
    variando apenas a base, de forma deterministica."""
    if policy_name not in SEED_POLICY_BASES:
        raise ValueError(f"Politica de seed desconhecida: {policy_name!r}.")
    return SEED_POLICY_BASES[policy_name] + target_contest
