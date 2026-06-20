from __future__ import annotations

from dataclasses import dataclass
import pandas as pd

from .backtest_lotofacil import executar_backtest
from .carregar_dados import COLUNAS_DEZENAS
from .motor_elite_v2 import ranking_dezenas_v2
from .validacao_jogos import ConfiguracaoMotor


MAPA_PERFIS = {
    "Conservador": "Conservador",
    "Equilibrado": "Diamante",
    "Agressivo": "Agressivo",
    "Elite": "Ouro",
    "Experimental": "Prata",
}
RISCO_PERFIS = {
    "Conservador": "Baixo",
    "Equilibrado": "Moderado",
    "Agressivo": "Alto",
    "Elite": "Moderado-alto",
    "Experimental": "Alto",
}
JOGOS_RECOMENDADOS = {"Conservador": 5, "Equilibrado": 10, "Agressivo": 20, "Elite": 30, "Experimental": 10}


@dataclass
class EstrategiaDoDia:
    perfil_recomendado: str
    nivel_risco: str
    quantidade_jogos: int
    justificativa: str
    dezenas_fortes: list[int]
    dezenas_alerta: list[int]
    soma_ideal: tuple[int, int]
    pares_recomendados: int
    repeticao_sugerida: int
    ranking_perfis: pd.DataFrame

    def texto(self) -> str:
        fortes = ", ".join(f"{d:02d}" for d in self.dezenas_fortes)
        alertas = ", ".join(f"{d:02d}" for d in self.dezenas_alerta)
        return (
            "MELHOR ESTRATÉGIA DO DIA — LOTOFÁCIL ELITE PRO V3\n\n"
            f"Perfil recomendado: {self.perfil_recomendado}\n"
            f"Nível de risco: {self.nivel_risco}\n"
            f"Quantidade recomendada de jogos: {self.quantidade_jogos}\n"
            f"Dezenas mais fortes: {fortes}\n"
            f"Dezenas em alerta: {alertas}\n"
            f"Faixa ideal de soma: {self.soma_ideal[0]} a {self.soma_ideal[1]}\n"
            f"Pares/ímpares recomendado: {self.pares_recomendados}/{15 - self.pares_recomendados}\n"
            f"Repetição sugerida do último concurso: {self.repeticao_sugerida}\n"
            f"Justificativa: {self.justificativa}\n\n"
            "Busca estatística pelos 15 acertos, sem garantia de prêmio. Jogue com responsabilidade."
        )

    def csv_bytes(self) -> bytes:
        dados = pd.DataFrame([{
            "Perfil recomendado": self.perfil_recomendado,
            "Nível de risco": self.nivel_risco,
            "Quantidade de jogos": self.quantidade_jogos,
            "Dezenas fortes": "-".join(f"{d:02d}" for d in self.dezenas_fortes),
            "Dezenas em alerta": "-".join(f"{d:02d}" for d in self.dezenas_alerta),
            "Soma mínima": self.soma_ideal[0],
            "Soma máxima": self.soma_ideal[1],
            "Pares": self.pares_recomendados,
            "Ímpares": 15 - self.pares_recomendados,
            "Repetição sugerida": self.repeticao_sugerida,
            "Justificativa": self.justificativa,
        }])
        return dados.to_csv(index=False).encode("utf-8-sig")


def _moda(serie: pd.Series, padrao: int) -> int:
    moda = serie.mode()
    return int(moda.iloc[0]) if not moda.empty else padrao


def gerar_estrategia_do_dia(
    df: pd.DataFrame,
    resumo_backtest: pd.DataFrame | None = None,
    configuracao: ConfiguracaoMotor | None = None,
) -> EstrategiaDoDia:
    dados = df.sort_values("Concurso").reset_index(drop=True)
    if dados.empty:
        raise ValueError("Base histórica vazia.")
    if resumo_backtest is None:
        resumo_backtest = executar_backtest(
            dados,
            quantidade_concursos=min(12, max(1, len(dados) - 100)),
            historico_minimo=min(100, max(1, len(dados) - 1)),
            configuracao=configuracao,
            candidatos_por_perfil=100,
        ).resumo_perfis
    por_perfil = resumo_backtest.set_index("Perfil") if not resumo_backtest.empty else pd.DataFrame()
    linhas = []
    for perfil_v3, perfil_motor in MAPA_PERFIS.items():
        if not por_perfil.empty and perfil_motor in por_perfil.index:
            registro = por_perfil.loc[perfil_motor]
            media = float(registro.get("Média", 0.0))
            taxa_11 = float(registro.get("11+", 0.0))
            taxa_13 = float(registro.get("13+", 0.0))
            melhor = int(registro.get("Melhor", 0))
        else:
            media = taxa_11 = taxa_13 = 0.0
            melhor = 0
        score = media * 7 + taxa_11 * 0.20 + taxa_13 * 0.35 + melhor * 1.5
        linhas.append({"Perfil": perfil_v3, "Perfil do motor": perfil_motor, "Média histórica": round(media, 4), "Taxa 11+": round(taxa_11, 4), "Taxa 13+": round(taxa_13, 4), "Melhor acerto": melhor, "Score estratégico": round(score, 4), "Risco": RISCO_PERFIS[perfil_v3]})
    ranking_perfis = pd.DataFrame(linhas).sort_values(["Score estratégico", "Média histórica"], ascending=[False, False]).reset_index(drop=True)
    ranking_perfis.insert(0, "Posição", range(1, len(ranking_perfis) + 1))
    perfil = str(ranking_perfis.iloc[0]["Perfil"])
    perfil_motor = MAPA_PERFIS[perfil]
    ranking_dezenas = ranking_dezenas_v2(dados, perfil_motor)
    fortes = ranking_dezenas.head(8)["Dezena"].astype(int).tolist()
    alertas = ranking_dezenas.sort_values(["Score da dezena", "Atraso"], ascending=[True, False]).head(5)["Dezena"].astype(int).tolist()
    historico = dados.tail(min(100, len(dados)))
    somas = historico[COLUNAS_DEZENAS].sum(axis=1)
    soma_ideal = (int(somas.quantile(0.25)), int(somas.quantile(0.75)))
    pares = historico[COLUNAS_DEZENAS].apply(lambda row: sum(int(d) % 2 == 0 for d in row), axis=1)
    repeticoes = []
    for indice in range(1, len(historico)):
        atual = {int(d) for d in historico.iloc[indice][COLUNAS_DEZENAS]}
        anterior = {int(d) for d in historico.iloc[indice - 1][COLUNAS_DEZENAS]}
        repeticoes.append(len(atual & anterior))
    repeticao = _moda(pd.Series(repeticoes, dtype=int), 9)
    quantidade = JOGOS_RECOMENDADOS[perfil]
    justificativa = (
        f"O perfil {perfil} liderou o score combinado de média, taxa 11+, taxa 13+ e melhor acerto "
        f"no backtest temporal, usando apenas concursos anteriores a cada resultado."
    )
    return EstrategiaDoDia(
        perfil_recomendado=perfil,
        nivel_risco=RISCO_PERFIS[perfil],
        quantidade_jogos=quantidade,
        justificativa=justificativa,
        dezenas_fortes=fortes,
        dezenas_alerta=alertas,
        soma_ideal=soma_ideal,
        pares_recomendados=_moda(pares, 7),
        repeticao_sugerida=repeticao,
        ranking_perfis=ranking_perfis,
    )
