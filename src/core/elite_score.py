"""Elite Score: indice estatistico de qualidade de um jogo ja gerado (Phoenix V2).

Regras obrigatorias desta camada:
  - NAO altera ``src/core/motor_elite.py`` nem nenhuma regra matematica dele;
  - NAO influencia a geracao de jogos: so classifica jogos ja produzidos;
  - usa apenas metricas ja existentes em ``src/core/estatisticas.py`` (ou
    derivacoes diretas delas: soma, repeticao com concurso anterior,
    diversidade entre jogos do mesmo lote).

Metodologia (identica para todos os componentes "de aderencia historica"):
para cada metrica, calculamos min/p10/p90/max observados na base de
concursos ja sorteados (``construir_referencias``). O sub-score (0-100) de um
jogo nessa metrica e:

  - 100 pontos se o valor do jogo esta dentro de [p10, p90] -- a faixa
    "tipica", onde caem ~80% dos concursos historicos;
  - decai linearmente ate um piso de 20 pontos ao se aproximar do extremo
    historicamente observado (min/max);
  - continua decaindo (podendo chegar a 0) caso o valor va alem do extremo
    ja observado na base.

Isso e 100% baseado em percentis empiricos da propria base de dados -- nenhuma
suposicao de distribuicao (ex.: normalidade) e nenhuma heuristica arbitraria.

A unica excecao e "diversidade entre jogos do lote", que nao compara contra a
base historica de concursos, e sim contra os outros jogos gerados junto (ver
``_sub_score_diversidade``).

Calculo puramente deterministico em toda a camada: a mesma entrada (jogo +
base + lote) sempre produz a mesma saida. Nao ha nenhum numero aleatorio
envolvido.
"""
from __future__ import annotations

import pandas as pd

from ..models.elite_score import (
    ComponenteEliteScore,
    EliteScoreResultado,
    FaixaHistorica,
    ReferenciasEliteScore,
)
from ..repository.base_repository import COLUNAS_DEZENAS
from .estatisticas import centro_moldura, dezenas_atrasadas, frequencia_dezenas, linhas_colunas, pares_impares

# Pesos calibrados pela variancia real observada na base historica: metricas
# com maior amplitude/discriminacao (pares/impares, soma, repeticao,
# linhas/colunas, centro/moldura) recebem peso maior; frequencia historica e
# atraso tem sinal estatistico fraco na Lotofacil (ver docs/ELITE_SCORE.md) e
# por isso recebem peso baixo, mesmo mantidos por serem metricas pedidas
# explicitamente. Soma exatamente 1.0.
PESOS: dict[str, float] = {
    "pares_impares": 0.20,
    "linhas_colunas": 0.15,
    "moldura_miolo": 0.15,
    "soma": 0.15,
    "repeticao": 0.15,
    "diversidade": 0.10,
    "frequencia_historica": 0.05,
    "atraso": 0.05,
}

PISO_SUB_SCORE = 20.0


def _faixa(serie: pd.Series) -> FaixaHistorica:
    return FaixaHistorica(
        minimo=float(serie.min()),
        p10=float(serie.quantile(0.10)),
        p90=float(serie.quantile(0.90)),
        maximo=float(serie.max()),
    )


def _max_linha_coluna(dezenas: list[int]) -> int:
    lc = linhas_colunas(dezenas)
    return max(max(lc["Linhas"].values()), max(lc["Colunas"].values()))


def construir_referencias(df: pd.DataFrame) -> ReferenciasEliteScore:
    """Calcula, a partir da base de concursos ja sorteados, as faixas
    historicas (min/p10/p90/max) usadas como referencia para pontuar
    qualquer jogo. Deve ser chamada uma unica vez por base/lote (nao depende
    do jogo avaliado).

    Nota de performance (Fase Hardening RC): converte cada concurso para uma
    lista/set de ``int`` uma unica vez (``dezenas_por_concurso``) e reaproveita
    essa mesma estrutura tanto para pares/centro/linhas-colunas quanto para a
    repeticao com o concurso anterior, em vez de percorrer o DataFrame 4 vezes
    separadas com ``DataFrame.apply(axis=1)``.

    Uma primeira tentativa desta otimizacao usou ``df.apply(..., axis=1)``
    devolvendo um ``pd.Series`` por linha (para calcular as 3 metricas numa
    unica passada); medicao real mostrou que essa abordagem e MAIS LENTA que
    o codigo original (o pandas paga um custo alto para montar/alinhar um
    ``Series`` por linha), entao foi descartada em favor deste loop Python
    puro sobre listas ja materializadas, que e o que efetivamente reduz o
    tempo de execucao (medido: de ~50ms para ~31ms nesta etapa, numa base com
    3596 concursos)."""
    dezenas_por_concurso = [[int(d) for d in linha] for linha in df[COLUNAS_DEZENAS].values.tolist()]

    pares_lista: list[float] = []
    centro_lista: list[float] = []
    max_lc_lista: list[float] = []
    for dezenas in dezenas_por_concurso:
        pares_lista.append(float(pares_impares(dezenas)["Pares"]))
        centro_lista.append(float(centro_moldura(dezenas)["Centro"]))
        max_lc_lista.append(float(_max_linha_coluna(dezenas)))

    pares_serie = pd.Series(pares_lista)
    centro_serie = pd.Series(centro_lista)
    max_lc_serie = pd.Series(max_lc_lista)
    soma_serie = df[COLUNAS_DEZENAS].sum(axis=1)

    conjuntos_por_concurso = [set(dezenas) for dezenas in dezenas_por_concurso]
    repeticao_serie = pd.Series(
        [
            len(conjuntos_por_concurso[i] & conjuntos_por_concurso[i - 1])
            for i in range(1, len(conjuntos_por_concurso))
        ],
        dtype=float,
    )

    freq_dezena = frequencia_dezenas(df).set_index("Dezena")["Frequencia"].astype(float)
    atraso_dezena = dezenas_atrasadas(df).set_index("Dezena")["Atraso"].astype(float)

    return ReferenciasEliteScore(
        pares=_faixa(pares_serie),
        centro=_faixa(centro_serie),
        max_linha_coluna=_faixa(max_lc_serie),
        soma=_faixa(soma_serie),
        repeticao=_faixa(repeticao_serie) if len(repeticao_serie) else FaixaHistorica(0.0, 0.0, 0.0, 0.0),
        frequencia_media=_faixa(freq_dezena),
        atraso_medio=_faixa(atraso_dezena),
        frequencia_por_dezena=freq_dezena.to_dict(),
        atraso_por_dezena=atraso_dezena.to_dict(),
    )


def _sub_score_percentil(valor: float, faixa: FaixaHistorica, piso: float = PISO_SUB_SCORE) -> float:
    """Sub-score 0-100 por aderencia a faixa tipica historica (ver docstring
    do modulo para a explicacao completa da metodologia)."""
    minimo, p10, p90, maximo = faixa.minimo, faixa.p10, faixa.p90, faixa.maximo

    if p10 <= valor <= p90:
        return 100.0

    if valor > p90:
        extensao = maximo - p90
        if extensao <= 0:
            return 100.0
        score = piso + (100.0 - piso) * (maximo - valor) / extensao
        return max(0.0, min(100.0, score))

    # valor < p10
    extensao = p10 - minimo
    if extensao <= 0:
        return 100.0
    score = piso + (100.0 - piso) * (valor - minimo) / extensao
    return max(0.0, min(100.0, score))


def _sub_score_diversidade(jogo: list[int], outros_jogos: list[list[int]] | None) -> float:
    """Mede o quanto um jogo difere dos demais jogos do mesmo lote gerado.

    Nao compara contra a base historica: compara o jogo apenas contra os
    OUTROS jogos produzidos na mesma leva (ex.: os 5 perfis de producao).
    ``outros_jogos`` NAO deve incluir o proprio jogo avaliado -- a exclusao e
    responsabilidade de quem monta a lista (ver ``calcular_elite_score_lote``,
    que exclui a propria posicao do lote, e nao por valor -- assim, dois
    jogos que por acaso tenham as mesmas 15 dezenas continuam sendo
    comparados corretamente entre si, com diversidade 0).

    Se nao houver outros jogos para comparar, o componente e neutro (100)."""
    if not outros_jogos:
        return 100.0
    conjunto_jogo = set(jogo)
    diferencas = [15 - len(conjunto_jogo & set(outro)) for outro in outros_jogos]
    media_diferenca = sum(diferencas) / len(diferencas)
    return max(0.0, min(100.0, (media_diferenca / 15.0) * 100.0))


def _media_por_dezena(jogo: list[int], valores_por_dezena: dict[int, float]) -> float:
    valores = [valores_por_dezena[d] for d in jogo if d in valores_por_dezena]
    if not valores:
        return 0.0
    return sum(valores) / len(valores)


def calcular_elite_score(
    jogo: list[int],
    referencias: ReferenciasEliteScore,
    ultimo_concurso: list[int] | None = None,
    lote: list[list[int]] | None = None,
) -> EliteScoreResultado:
    """Calcula o Elite Score (0-100) de um jogo ja gerado.

    ``jogo``: as 15 dezenas do jogo avaliado.
    ``referencias``: faixas historicas (``construir_referencias``).
    ``ultimo_concurso``: dezenas do ultimo concurso sorteado (para o
    componente de repeticao). Se omitido, o componente de repeticao fica
    neutro (sub-score 100).
    ``lote``: os OUTROS jogos gerados junto, sem incluir o proprio ``jogo``
    (para o componente de diversidade). Se omitido/vazio, o componente fica
    neutro (sub-score 100).

    Calculo puramente deterministico: a mesma entrada sempre produz a mesma
    saida (sem numeros aleatorios envolvidos).

    Levanta ``ValueError`` se ``jogo`` nao tiver exatamente 15 dezenas
    distintas entre 1 e 25 (validacao defensiva adicionada na Fase Hardening
    RC, consistente com a mesma regra ja aplicada em ``src/models/jogo.py``
    e ``src/models/concurso.py``; nao altera o calculo do score em si).
    """
    if len(jogo) != 15:
        raise ValueError(f"Um jogo da Lotofacil precisa ter exatamente 15 dezenas (recebido: {len(jogo)}).")
    if len(set(jogo)) != 15:
        raise ValueError("Um jogo da Lotofacil nao pode ter dezenas repetidas.")
    if any(not (1 <= dezena <= 25) for dezena in jogo):
        raise ValueError("Todas as dezenas de um jogo da Lotofacil devem estar entre 1 e 25.")

    componentes: list[ComponenteEliteScore] = []

    def _add(nome: str, descricao: str, valor: float, faixa: FaixaHistorica, peso_chave: str) -> None:
        sub = _sub_score_percentil(valor, faixa)
        peso = PESOS[peso_chave]
        componentes.append(
            ComponenteEliteScore(
                nome=nome,
                descricao=descricao,
                valor_jogo=valor,
                faixa_tipica=(faixa.p10, faixa.p90),
                sub_score=sub,
                peso=peso,
                contribuicao=peso * sub,
            )
        )

    _add(
        "Pares/Impares",
        "Quantidade de dezenas pares no jogo, comparada a faixa tipica dos concursos ja sorteados.",
        float(pares_impares(jogo)["Pares"]),
        referencias.pares,
        "pares_impares",
    )
    _add(
        "Linhas/Colunas",
        "Maior concentracao de dezenas numa mesma linha ou coluna do volante (5x5).",
        float(_max_linha_coluna(jogo)),
        referencias.max_linha_coluna,
        "linhas_colunas",
    )
    _add(
        "Moldura/Miolo",
        "Quantidade de dezenas do miolo (centro do volante) presentes no jogo.",
        float(centro_moldura(jogo)["Centro"]),
        referencias.centro,
        "moldura_miolo",
    )
    _add(
        "Soma das dezenas",
        "Soma total das 15 dezenas do jogo.",
        float(sum(jogo)),
        referencias.soma,
        "soma",
    )

    if ultimo_concurso:
        _add(
            "Repeticao com concurso anterior",
            "Quantidade de dezenas do jogo que tambem saíram no ultimo concurso sorteado.",
            float(len(set(jogo) & set(ultimo_concurso))),
            referencias.repeticao,
            "repeticao",
        )
    else:
        peso = PESOS["repeticao"]
        componentes.append(
            ComponenteEliteScore(
                nome="Repeticao com concurso anterior",
                descricao="Nao informado (ultimo concurso nao fornecido); componente neutro.",
                valor_jogo=float("nan"),
                faixa_tipica=(referencias.repeticao.p10, referencias.repeticao.p90),
                sub_score=100.0,
                peso=peso,
                contribuicao=peso * 100.0,
            )
        )

    _add(
        "Frequencia historica",
        "Media da frequencia historica (numero de vezes sorteada) das 15 dezenas do jogo.",
        _media_por_dezena(jogo, referencias.frequencia_por_dezena),
        referencias.frequencia_media,
        "frequencia_historica",
    )
    _add(
        "Atraso",
        "Media do atraso (concursos desde a ultima vez que saiu) das 15 dezenas do jogo.",
        _media_por_dezena(jogo, referencias.atraso_por_dezena),
        referencias.atraso_medio,
        "atraso",
    )

    diversidade = _sub_score_diversidade(jogo, lote)
    peso_diversidade = PESOS["diversidade"]
    componentes.append(
        ComponenteEliteScore(
            nome="Diversidade entre jogos do lote",
            descricao="Quao diferente este jogo e dos demais jogos gerados junto (nao usa a base historica).",
            valor_jogo=diversidade,
            faixa_tipica=(0.0, 100.0),
            sub_score=diversidade,
            peso=peso_diversidade,
            contribuicao=peso_diversidade * diversidade,
        )
    )

    total = sum(c.contribuicao for c in componentes)
    return EliteScoreResultado(total=round(total, 2), componentes=tuple(componentes))


def calcular_elite_score_lote(
    jogos: list[list[int]], df: pd.DataFrame, ultimo_concurso: list[int] | None = None
) -> list[EliteScoreResultado]:
    """Calcula o Elite Score de todos os jogos de um mesmo lote, reaproveitando
    as mesmas referencias historicas (calculadas uma unica vez). Para o
    componente de diversidade, cada jogo e comparado contra os OUTROS jogos
    do lote, excluidos pela POSICAO (nao pelo valor) -- assim, dois jogos que
    por acaso coincidam nas mesmas 15 dezenas continuam sendo comparados
    entre si corretamente (diversidade 0), em vez de serem descartados."""
    referencias = construir_referencias(df)
    if ultimo_concurso is None and not df.empty:
        ultimo_concurso = df.iloc[-1][COLUNAS_DEZENAS].astype(int).tolist()
    resultados = []
    for indice, jogo in enumerate(jogos):
        outros_jogos = jogos[:indice] + jogos[indice + 1 :]
        resultados.append(
            calcular_elite_score(jogo, referencias, ultimo_concurso=ultimo_concurso, lote=outros_jogos)
        )
    return resultados
