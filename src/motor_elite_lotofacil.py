from __future__ import annotations

from collections import Counter, deque
from itertools import combinations
import random

import pandas as pd

from .carregar_dados import COLUNAS_DEZENAS
from .estatisticas_lotofacil import (
    TODAS_DEZENAS,
    centro_moldura,
    dezenas_atrasadas,
    frequencia_dezenas,
    linhas_colunas,
    pares_impares,
)


def ranking_elite_lotofacil(df: pd.DataFrame) -> pd.DataFrame:
    freq_geral = frequencia_dezenas(df).set_index("Dezena")["Frequencia"]
    freq_20 = frequencia_dezenas(df, 20).set_index("Dezena")["Frequencia"]
    atraso = dezenas_atrasadas(df).set_index("Dezena")["Atraso"]
    registros = []
    for dezena in TODAS_DEZENAS:
        score = (freq_geral[dezena] * 0.45) + (freq_20[dezena] * 1.8) + (atraso[dezena] * 0.25)
        registros.append(
            {
                "Dezena": dezena,
                "Frequencia geral": int(freq_geral[dezena]),
                "Frequencia ultimos 20": int(freq_20[dezena]),
                "Atraso": int(atraso[dezena]),
                "Elite Score": round(float(score), 3),
            }
        )
    return pd.DataFrame(registros).sort_values(["Elite Score", "Dezena"], ascending=[False, True])


def score_jogo(dezenas: list[int], ranking: pd.DataFrame) -> float:
    scores = ranking.set_index("Dezena")["Elite Score"].to_dict()
    base = sum(float(scores.get(d, 0)) for d in dezenas)
    pi = pares_impares(dezenas)
    cm = centro_moldura(dezenas)
    lc = linhas_colunas(dezenas)
    penalidade = 0.0
    if not (6 <= pi["Pares"] <= 9):
        penalidade += 10
    if not (4 <= cm["Centro"] <= 7):
        penalidade += 8
    if max(lc["Linhas"].values()) > 5:
        penalidade += 6
    if max(lc["Colunas"].values()) > 5:
        penalidade += 6
    return round(base - penalidade, 3)


def gerar_jogo_inteligente(df: pd.DataFrame, dezenas_por_jogo: int = 15, semente: int | None = None) -> dict:
    rng = random.Random(semente)
    ranking = ranking_elite_lotofacil(df)
    top = ranking.head(20)["Dezena"].astype(int).tolist()
    candidatos = []
    for _ in range(240):
        jogo = sorted(rng.sample(top, min(dezenas_por_jogo, len(top))))
        while len(jogo) < dezenas_por_jogo:
            dezena = rng.choice(TODAS_DEZENAS)
            if dezena not in jogo:
                jogo.append(dezena)
                jogo.sort()
        candidatos.append({"Jogo": jogo, "Elite Score": score_jogo(jogo, ranking)})
    melhor = max(candidatos, key=lambda item: item["Elite Score"])
    return {
        "jogo": melhor["Jogo"],
        "score": melhor["Elite Score"],
        "ranking": ranking,
        "pares_impares": pares_impares(melhor["Jogo"]),
        "linhas_colunas": linhas_colunas(melhor["Jogo"]),
        "centro_moldura": centro_moldura(melhor["Jogo"]),
    }


def gerar_varios_jogos(df: pd.DataFrame, quantidade: int = 5) -> pd.DataFrame:
    linhas = []
    for i in range(quantidade):
        pacote = gerar_jogo_inteligente(df, semente=1000 + i)
        linha = {f"Bola{j}": dezena for j, dezena in enumerate(pacote["jogo"], start=1)}
        linha["Elite Score"] = pacote["score"]
        linhas.append(linha)
    return pd.DataFrame(linhas)


def ranking_elite_lotofacil_v2(df: pd.DataFrame) -> pd.DataFrame:
    freq_geral = frequencia_dezenas(df).set_index("Dezena")["Frequencia"]
    freq_5 = frequencia_dezenas(df, 5).set_index("Dezena")["Frequencia"]
    freq_10 = frequencia_dezenas(df, 10).set_index("Dezena")["Frequencia"]
    freq_20 = frequencia_dezenas(df, 20).set_index("Dezena")["Frequencia"]
    atraso = dezenas_atrasadas(df).set_index("Dezena")["Atraso"]
    ultimo = set(df.tail(1)[COLUNAS_DEZENAS].iloc[0].astype(int).tolist()) if not df.empty else set()
    registros = []
    for dezena in TODAS_DEZENAS:
        score = (
            freq_geral[dezena] * 0.16
            + freq_5[dezena] * 3.40
            + freq_10[dezena] * 2.40
            + freq_20[dezena] * 1.30
            + atraso[dezena] * 0.10
            + (3.50 if dezena in ultimo else 0.0)
        )
        registros.append(
            {
                "Dezena": dezena,
                "Frequencia geral": int(freq_geral[dezena]),
                "Frequencia ultimos 5": int(freq_5[dezena]),
                "Frequencia ultimos 10": int(freq_10[dezena]),
                "Frequencia ultimos 20": int(freq_20[dezena]),
                "Atraso": int(atraso[dezena]),
                "Repetiu ultimo": int(dezena in ultimo),
                "Elite Score V2": round(float(score), 3),
            }
        )
    return pd.DataFrame(registros).sort_values(["Elite Score V2", "Dezena"], ascending=[False, True])


def score_jogo_v2(dezenas: list[int], ranking: pd.DataFrame) -> float:
    scores = ranking.set_index("Dezena")["Elite Score V2"].to_dict()
    base = sum(float(scores.get(d, 0.0)) for d in dezenas)
    pi = pares_impares(dezenas)
    cm = centro_moldura(dezenas)
    lc = linhas_colunas(dezenas)
    penalidade = 0.0
    if not (6 <= pi["Pares"] <= 9):
        penalidade += 12
    penalidade += abs(cm["Centro"] - 5) * 5
    penalidade += sum(max(0, qtd - 4) for qtd in lc["Linhas"].values()) * 3
    penalidade += sum(max(0, qtd - 4) for qtd in lc["Colunas"].values()) * 3
    return round(base - penalidade, 3)


def gerar_portfolio_elite_lotofacil_v2(df: pd.DataFrame, limite_jogos: int = 25) -> pd.DataFrame:
    ranking = ranking_elite_lotofacil_v2(df)
    top20 = ranking.head(20)["Dezena"].astype(int).tolist()
    linhas = []
    for jogo in combinations(top20, 15):
        dezenas = sorted(jogo)
        linha = {f"Bola{i}": dezena for i, dezena in enumerate(dezenas, start=1)}
        linha["Elite Score V2"] = score_jogo_v2(dezenas, ranking)
        linhas.append(linha)
    return (
        pd.DataFrame(linhas)
        .sort_values(["Elite Score V2", "Bola1"], ascending=[False, True])
        .head(max(1, int(limite_jogos)))
        .reset_index(drop=True)
    )


MOTOR_OFICIAL_PRODUCAO = "ELITE_SCORE_V35_TEMPORAL"
NOMES_JOGOS_PRODUCAO = ["Diamante", "Ouro", "Prata", "Agressivo", "Conservador"]
_CACHE_ESTADO_TEMPORAL: dict[tuple, tuple[dict, dict[int, float], set[int]]] = {}
_CACHE_CANDIDATOS_15: dict[tuple, list[tuple[float, tuple[int, ...], dict]]] = {}
ESTRATEGIAS_PERFIS = {
    "Diamante": "Maior força no ranking temporal e aderência ao DNA histórico.",
    "Ouro": "Equilíbrio entre score alto, regularidade e frequência recente.",
    "Prata": "Alternativa forte com menor dependência das dezenas mais óbvias.",
    "Agressivo": "Maior variação, presença de atrasadas e padrões menos explorados.",
    "Conservador": "Estabilidade, regularidade e padrões históricos consistentes.",
}


def _linha_coluna(dezena: int) -> tuple[int, int]:
    return ((dezena - 1) // 5) + 1, ((dezena - 1) % 5) + 1


def _quadrante(dezena: int) -> int:
    linha, coluna = _linha_coluna(dezena)
    if linha <= 2 and coluna <= 3:
        return 1
    if linha <= 2 and coluna >= 4:
        return 2
    if linha >= 3 and coluna <= 3:
        return 3
    return 4


def _binar_soma(soma: int) -> str:
    inicio = (soma // 10) * 10
    return f"{inicio}-{inicio + 9}"


def _atualizar_janela(janela: deque[list[int]], freq: Counter, dezenas: list[int]) -> None:
    if len(janela) == janela.maxlen:
        for dezena in janela[0]:
            freq[dezena] -= 1
    janela.append(dezenas)
    for dezena in dezenas:
        freq[dezena] += 1


def _scores_v35_temporal(
    concurso: int,
    freq_geral: Counter,
    freq_5: Counter,
    freq_10: Counter,
    freq_20: Counter,
    ultimo_por_dezena: dict[int, int],
    ultimo_jogo: set[int],
) -> dict[int, float]:
    scores = {}
    for dezena in TODAS_DEZENAS:
        atraso = concurso - ultimo_por_dezena.get(dezena, 0)
        scores[dezena] = (
            freq_geral[dezena] * 0.16
            + freq_5[dezena] * 3.40
            + freq_10[dezena] * 2.40
            + freq_20[dezena] * 1.30
            + atraso * 0.10
            + (3.50 if dezena in ultimo_jogo else 0.0)
        )
    return scores


def _features_temporais(dezenas: tuple[int, ...], ultimo_jogo: set[int]) -> dict:
    soma = sum(dezenas)
    pares = sum(1 for d in dezenas if d % 2 == 0)
    centro = sum(1 for d in dezenas if d in set(TODAS_DEZENAS) - {1, 2, 3, 4, 5, 6, 10, 11, 15, 16, 20, 21, 22, 23, 24, 25})
    linhas = [0, 0, 0, 0, 0]
    colunas = [0, 0, 0, 0, 0]
    quadrantes = [0, 0, 0, 0]
    faixas = [0, 0, 0, 0, 0]
    for dezena in dezenas:
        linha, coluna = _linha_coluna(dezena)
        linhas[linha - 1] += 1
        colunas[coluna - 1] += 1
        quadrantes[_quadrante(dezena) - 1] += 1
        faixas[(dezena - 1) // 5] += 1
    return {
        "soma_total": soma,
        "soma_bin": _binar_soma(soma),
        "pares": pares,
        "centro": centro,
        "repeticao": len(set(dezenas) & ultimo_jogo),
        "consecutivas": sum(1 for a, b in zip(dezenas, dezenas[1:]) if b == a + 1),
        "linhas": "-".join(map(str, linhas)),
        "colunas": "-".join(map(str, colunas)),
        "quadrantes": "-".join(map(str, quadrantes)),
        "faixas": "-".join(map(str, faixas)),
    }


def _registrar_dna_temporal(dna: dict, concurso: int, sorteadas: set[int], top20: set[int], ultimo_jogo: set[int]) -> None:
    if len(sorteadas & top20) < 15:
        return
    dezenas = tuple(sorted(sorteadas))
    features = _features_temporais(dezenas, ultimo_jogo)
    dna["total_15"] += 1
    dna["concursos"].append(concurso)
    dna["somas"].append(features["soma_total"])
    for chave, valor in (
        ("soma_bin", features["soma_bin"]),
        ("pares", str(features["pares"])),
        ("centro", str(features["centro"])),
        ("repeticao", str(features["repeticao"])),
        ("consecutivas", str(features["consecutivas"])),
        ("linhas", features["linhas"]),
        ("colunas", features["colunas"]),
        ("quadrantes", features["quadrantes"]),
        ("faixas", features["faixas"]),
    ):
        dna[chave][valor] += 1
    for dezena in dezenas:
        dna["dezenas"][dezena] += 1


def _score_faixa_temporal(valor: int, valores: list[int], peso: float, queda: float) -> float:
    if not valores:
        return 0.0
    distancia = abs(valor - (sum(valores) / len(valores)))
    return max(0.0, peso - (distancia * queda))


def _score_dna_temporal(features: dict, jogo: tuple[int, ...], dna: dict) -> float:
    score = 0.0
    if dna["total_15"] > 0:
        score += _score_faixa_temporal(features["soma_total"], dna["somas"], 18.0, 0.45)
        score += dna["soma_bin"][features["soma_bin"]] * 5.0
        score += dna["pares"][str(features["pares"])] * 6.0
        score += dna["centro"][str(features["centro"])] * 7.0
        score += dna["repeticao"][str(features["repeticao"])] * 8.0
        score += dna["consecutivas"][str(features["consecutivas"])] * 6.0
        score += dna["linhas"][features["linhas"]] * 11.0
        score += dna["colunas"][features["colunas"]] * 11.0
        score += dna["quadrantes"][features["quadrantes"]] * 9.0
        score += dna["faixas"][features["faixas"]] * 10.0
        score += sum(dna["dezenas"][d] for d in jogo) * 1.4
    if features["linhas"] == "3-3-3-3-3":
        score -= 25.0
    if features["colunas"] == "3-3-3-3-3":
        score -= 25.0
    return round(score, 6)


def _candidatos_v35_temporal(
    scores: dict[int, float], dna: dict, ultimo_jogo: set[int]
) -> list[tuple[float, tuple[int, ...], dict]]:
    top20 = sorted(TODAS_DEZENAS, key=lambda d: (-scores[d], d))[:20]
    top20_set = set(top20)
    candidatos = []
    for excluidas in combinations(top20, 5):
        jogo = tuple(sorted(top20_set - set(excluidas)))
        features = _features_temporais(jogo, ultimo_jogo)
        score = _score_dna_temporal(features, jogo, dna) + (sum(scores[d] for d in jogo) * 0.015)
        candidatos.append((round(score, 6), jogo, features))
    candidatos.sort(key=lambda item: (-item[0], item[1]))
    return candidatos


def _top_jogos_v35_temporal(scores: dict[int, float], dna: dict, ultimo_jogo: set[int], limite: int = 5) -> list[tuple[float, tuple[int, ...]]]:
    candidatos = _candidatos_v35_temporal(scores, dna, ultimo_jogo)
    return [(score, jogo) for score, jogo, _ in candidatos[:limite]]


def _estado_temporal_atual(df: pd.DataFrame) -> tuple[dict, dict[int, float], set[int]]:
    if df.empty:
        chave_cache = (0,)
    else:
        ultima = df.sort_values("Concurso").iloc[-1]
        chave_cache = (
            len(df),
            int(df["Concurso"].min()),
            int(df["Concurso"].max()),
            tuple(int(ultima[coluna]) for coluna in COLUNAS_DEZENAS),
        )
    if chave_cache in _CACHE_ESTADO_TEMPORAL:
        return _CACHE_ESTADO_TEMPORAL[chave_cache]

    freq_geral = Counter()
    freq_5 = Counter()
    freq_10 = Counter()
    freq_20 = Counter()
    janela_5: deque[list[int]] = deque(maxlen=5)
    janela_10: deque[list[int]] = deque(maxlen=10)
    janela_20: deque[list[int]] = deque(maxlen=20)
    ultimo_por_dezena = {dezena: 0 for dezena in TODAS_DEZENAS}
    ultimo_jogo: set[int] = set()
    dna = {
        "total_15": 0,
        "concursos": [],
        "somas": [],
        "soma_bin": Counter(),
        "pares": Counter(),
        "centro": Counter(),
        "repeticao": Counter(),
        "consecutivas": Counter(),
        "linhas": Counter(),
        "colunas": Counter(),
        "quadrantes": Counter(),
        "faixas": Counter(),
        "dezenas": Counter(),
    }

    for indice, row in df.sort_values("Concurso").reset_index(drop=True).iterrows():
        concurso = int(row["Concurso"])
        sorteadas = {int(row[col]) for col in COLUNAS_DEZENAS}
        if indice > 0:
            scores_passados = _scores_v35_temporal(concurso, freq_geral, freq_5, freq_10, freq_20, ultimo_por_dezena, ultimo_jogo)
            top20 = set(sorted(TODAS_DEZENAS, key=lambda d: (-scores_passados[d], d))[:20])
            _registrar_dna_temporal(dna, concurso, sorteadas, top20, ultimo_jogo)

        dezenas = [int(row[col]) for col in COLUNAS_DEZENAS]
        for dezena in dezenas:
            freq_geral[dezena] += 1
            ultimo_por_dezena[dezena] = concurso
        _atualizar_janela(janela_5, freq_5, dezenas)
        _atualizar_janela(janela_10, freq_10, dezenas)
        _atualizar_janela(janela_20, freq_20, dezenas)
        ultimo_jogo = set(dezenas)

    proximo_concurso = int(df["Concurso"].max()) + 1 if not df.empty else 1
    scores_atuais = _scores_v35_temporal(proximo_concurso, freq_geral, freq_5, freq_10, freq_20, ultimo_por_dezena, ultimo_jogo)
    estado = (dna, scores_atuais, ultimo_jogo)
    _CACHE_ESTADO_TEMPORAL.clear()
    _CACHE_ESTADO_TEMPORAL[chave_cache] = estado
    return estado


def assinatura_portfolio(jogos: pd.DataFrame) -> tuple[tuple[int, ...], ...]:
    """Cria uma assinatura imutavel dos cinco jogos para uso no session_state."""
    colunas = [f"Bola{i}" for i in range(1, 16)]
    faltantes = [coluna for coluna in colunas if coluna not in jogos.columns]
    if faltantes:
        raise ValueError(f"Carteira sem colunas para assinatura: {faltantes}")
    return tuple(tuple(sorted(int(row[coluna]) for coluna in colunas)) for _, row in jogos.iterrows())


def _selecionar_carteira_com_diversidade(
    df: pd.DataFrame,
    scores: dict[int, float],
    dna: dict,
    ultimo_jogo: set[int],
    semente: int,
) -> list[tuple[float, tuple[int, ...]]]:
    rng = random.Random(semente)
    chave_candidatos = (id(scores), len(df), int(df["Concurso"].max()) if not df.empty else 0)
    candidatos = _CACHE_CANDIDATOS_15.get(chave_candidatos)
    if candidatos is None:
        historico = {
            tuple(sorted(int(row[coluna]) for coluna in COLUNAS_DEZENAS))
            for _, row in df.iterrows()
        }
        candidatos = [
            (score, jogo, features)
            for score, jogo, features in _candidatos_v35_temporal(scores, dna, ultimo_jogo)
            if jogo not in historico
            and 165 <= features["soma_total"] <= 225
            and 6 <= features["pares"] <= 9
        ][:600]
        _CACHE_CANDIDATOS_15.clear()
        _CACHE_CANDIDATOS_15[chave_candidatos] = candidatos
    if len(candidatos) < len(NOMES_JOGOS_PRODUCAO):
        raise ValueError("Quantidade insuficiente de candidatos qualificados para a carteira Elite.")

    amplitude = max(1.0, candidatos[0][0] - candidatos[-1][0])
    avaliados = []
    for indice, (score_base, jogo, features) in enumerate(candidatos):
        ruido = rng.uniform(-0.035, 0.035) * amplitude
        bonus_diversidade = rng.random() * (amplitude * 0.012)
        score_final = score_base + ruido + bonus_diversidade
        avaliados.append((score_final, score_base, jogo, features, indice))

    top_scores = sorted(scores, key=lambda dezena: (-scores[dezena], dezena))
    atrasadas = set(top_scores[15:25])

    def ajuste_perfil(nome: str, item: tuple) -> float:
        _, score_base, jogo, features, indice = item
        score_dezenas = sum(scores[d] for d in jogo)
        distribuicao = [int(valor) for valor in features["faixas"].split("-")]
        equilibrio_faixas = 10.0 - (sum(abs(valor - 3) for valor in distribuicao) * 1.5)
        equilibrio = max(0.0, 12.0 - abs(features["soma_total"] - 195) * 0.18)
        equilibrio += max(0.0, 8.0 - abs(features["pares"] - 7.5) * 3.0)
        regularidade = max(0.0, 8.0 - abs(features["repeticao"] - 9) * 2.0)
        variacao = len(set(jogo) & atrasadas) * 2.2 + min(indice, 300) * 0.01
        if nome == "Diamante":
            return score_base * 1.12 + score_dezenas * 0.02 + equilibrio_faixas
        if nome == "Ouro":
            return score_base * 1.02 + equilibrio + equilibrio_faixas + regularidade
        if nome == "Prata":
            return score_base * 0.98 + equilibrio + variacao * 0.75 + equilibrio_faixas
        if nome == "Agressivo":
            return score_base * 0.90 + variacao * 2.0 + equilibrio_faixas * 0.6
        return score_base + regularidade * 1.5 + equilibrio * 1.2 + equilibrio_faixas

    escolhidos: list[tuple[float, tuple[int, ...]]] = []
    usados: set[tuple[int, ...]] = set()
    for nome in NOMES_JOGOS_PRODUCAO:
        disponiveis = [
            item for item in avaliados
            if item[2] not in usados
            and all(len(set(item[2]) - set(escolhido)) >= 3 for _, escolhido in escolhidos)
        ]
        if not disponiveis:
            disponiveis = [item for item in avaliados if item[2] not in usados]
        elite_perfil = sorted(
            disponiveis,
            key=lambda item: (-(ajuste_perfil(nome, item) + item[0] * 0.10), item[4]),
        )[:20]
        indice_elite = min(len(elite_perfil) - 1, int((rng.random() ** 2.4) * len(elite_perfil)))
        _, score_base, jogo, _, _ = elite_perfil[indice_elite]
        usados.add(jogo)
        escolhidos.append((score_base, jogo))
    return escolhidos


def _potencial_15(
    jogo: tuple[int, ...],
    score: float,
    features: dict,
    scores: dict[int, float],
    dna: dict,
) -> float:
    valores = list(scores.values())
    minimo, maximo = min(valores), max(valores)
    temporal = sum((scores[d] - minimo) / max(maximo - minimo, 1.0) for d in jogo) / 15
    soma = max(0.0, 1.0 - abs(features["soma_total"] - 195) / 45)
    paridade = max(0.0, 1.0 - abs(features["pares"] - 7.5) / 3.5)
    repeticao = max(0.0, 1.0 - abs(features["repeticao"] - 9) / 6)
    faixas = [int(valor) for valor in features["faixas"].split("-")]
    distribuicao = max(0.0, 1.0 - sum(abs(valor - 3) for valor in faixas) / 12)
    aderencia = max(0.0, min(1.0, score / max(score + 80.0, 1.0)))
    if dna["total_15"] <= 0:
        aderencia = 0.5
    potencial = (
        temporal * 32
        + aderencia * 23
        + soma * 12
        + paridade * 10
        + distribuicao * 12
        + repeticao * 8
        + 3
    )
    return round(max(0.0, min(100.0, potencial)), 2)


def gerar_jogos_producao_v1(
    df: pd.DataFrame,
    semente: int | None = None,
    assinatura_anterior: tuple[tuple[int, ...], ...] | None = None,
) -> pd.DataFrame:
    dna, scores, ultimo_jogo = _estado_temporal_atual(df)
    jogos = _selecionar_carteira_com_diversidade(df, scores, dna, ultimo_jogo, int(semente or 0))
    linhas = []
    for nome, (score, jogo) in zip(NOMES_JOGOS_PRODUCAO, jogos):
        features = _features_temporais(jogo, ultimo_jogo)
        linha = {"Perfil": nome, "Motor": MOTOR_OFICIAL_PRODUCAO}
        for indice, dezena in enumerate(jogo, start=1):
            linha[f"Bola{indice}"] = dezena
        linha["Dezenas"] = list(jogo)
        linha["Elite Score Temporal"] = score
        linha["Score"] = score
        linha["Soma"] = features["soma_total"]
        linha["Pares"] = features["pares"]
        linha["Impares"] = 15 - features["pares"]
        linha["Ímpares"] = 15 - features["pares"]
        linha["Centro"] = features["centro"]
        linha["Moldura"] = 15 - features["centro"]
        linha["Repeticao anterior"] = features["repeticao"]
        linha["Consecutivas"] = features["consecutivas"]
        linha["Linhas"] = features["linhas"]
        linha["Colunas"] = features["colunas"]
        linha["Quadrantes"] = features["quadrantes"]
        linha["Faixas"] = features["faixas"]
        linha["DNA temporal 15 pontos"] = dna["total_15"]
        linha["Potencial 15"] = _potencial_15(jogo, score, features, scores, dna)
        linha["Estrategia"] = ESTRATEGIAS_PERFIS[nome]
        linhas.append(linha)
    resultado = pd.DataFrame(linhas)
    validar_jogos_producao(resultado)
    if assinatura_anterior is not None and assinatura_portfolio(resultado) == assinatura_anterior:
        return gerar_jogos_producao_v1(df, int(semente or 0) + 1, assinatura_anterior)
    return resultado


def validar_jogos_producao(jogos: pd.DataFrame) -> None:
    """Garante o contrato visual e operacional dos cinco jogos oficiais."""
    colunas_bolas = [f"Bola{i}" for i in range(1, 16)]
    colunas_contrato = ["Perfil", "Dezenas", "Score", "Potencial 15", "Soma", "Pares", "Ímpares"]
    faltantes = [coluna for coluna in ["Motor", *colunas_contrato, *colunas_bolas] if coluna not in jogos.columns]
    if faltantes:
        raise ValueError(f"Jogos oficiais sem colunas obrigatorias: {faltantes}")
    if len(jogos) != len(NOMES_JOGOS_PRODUCAO):
        raise ValueError(f"O motor oficial deve gerar {len(NOMES_JOGOS_PRODUCAO)} jogos.")
    if jogos["Perfil"].tolist() != NOMES_JOGOS_PRODUCAO:
        raise ValueError("Os perfis oficiais foram gerados fora da ordem esperada.")
    if set(jogos["Motor"].astype(str)) != {MOTOR_OFICIAL_PRODUCAO}:
        raise ValueError(f"Motor divergente do oficial: {MOTOR_OFICIAL_PRODUCAO}.")

    combinacoes: set[tuple[int, ...]] = set()
    for _, row in jogos.iterrows():
        dezenas = tuple(sorted(int(row[coluna]) for coluna in colunas_bolas))
        if len(dezenas) != 15 or len(set(dezenas)) != 15:
            raise ValueError(f"O jogo {row['Perfil']} deve conter 15 dezenas unicas.")
        if any(dezena < 1 or dezena > 25 for dezena in dezenas):
            raise ValueError(f"O jogo {row['Perfil']} possui dezena fora do intervalo 01-25.")
        if dezenas in combinacoes:
            raise ValueError(f"O jogo {row['Perfil']} repete uma combinacao ja gerada.")
        dezenas_contrato = tuple(sorted(int(dezena) for dezena in row["Dezenas"]))
        if dezenas_contrato != dezenas:
            raise ValueError(f"O campo Dezenas do jogo {row['Perfil']} diverge das colunas Bola1-Bola15.")
        for existente in combinacoes:
            if len(set(dezenas) - set(existente)) < 3:
                raise ValueError("Cada par de jogos deve possuir pelo menos 3 dezenas diferentes.")
        combinacoes.add(dezenas)
