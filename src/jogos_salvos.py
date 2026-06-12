from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re
from unicodedata import normalize

import pandas as pd

from .carregar_dados import COLUNAS_DEZENAS, RAIZ_PROJETO
from .motor_elite_lotofacil import validar_jogos_producao


CAMINHO_JOGOS_SALVOS = RAIZ_PROJETO / "exports" / "jogos_salvos_lotofacil.csv"
COLUNAS_JOGOS_SALVOS = [
    "DataHora",
    "Carteira",
    "Concurso Alvo",
    "Perfil",
    "Dezenas",
    "Score",
    "Soma",
    "Pares",
    "Impares",
    "Status",
    "Acertos",
]


def _formatar_dezenas(dezenas: list[int]) -> str:
    return "-".join(f"{dezena:02d}" for dezena in sorted(dezenas))


def _parsear_dezenas(valor: object) -> set[int]:
    return {int(item) for item in re.findall(r"\d+", str(valor or ""))}


def _chave_coluna(coluna: object) -> str:
    texto = normalize("NFKD", str(coluna)).encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]", "", texto)


def _coluna_canonica(coluna: object) -> str | None:
    chave = _chave_coluna(coluna)
    if chave.startswith("datahora"):
        return "DataHora"
    if "carteira" in chave:
        return "Carteira"
    if chave.startswith("concursoalvo"):
        return "Concurso Alvo"
    if chave == "perfil":
        return "Perfil"
    if chave.startswith("dezenas") and "sorteadas" not in chave:
        return "Dezenas"
    if chave == "score":
        return "Score"
    if chave == "soma":
        return "Soma"
    if chave == "pares":
        return "Pares"
    if chave.endswith("mpares"):
        return "Impares"
    if chave.startswith("status"):
        return "Status"
    if chave == "acertos":
        return "Acertos"
    return None


def normalizar_colunas_jogos_salvos(dados: pd.DataFrame | None) -> pd.DataFrame:
    if not isinstance(dados, pd.DataFrame):
        dados = pd.DataFrame()

    aliases_status = {
        "Status de Conferência": "Status",
        "Status Conferencia": "Status",
    }
    renomear = {
        coluna: aliases_status[coluna]
        for coluna in dados.columns
        if coluna in aliases_status and aliases_status[coluna] not in dados.columns
    }
    if renomear:
        dados = dados.rename(columns=renomear)

    normalizados = pd.DataFrame(index=dados.index)
    for coluna_origem in dados.columns:
        coluna_destino = _coluna_canonica(coluna_origem)
        if coluna_destino is None:
            continue
        valores = dados[coluna_origem].astype(str)
        if coluna_destino not in normalizados:
            normalizados[coluna_destino] = valores
        else:
            vazios = normalizados[coluna_destino].str.strip().eq("")
            normalizados.loc[vazios, coluna_destino] = valores.loc[vazios]

    for coluna in COLUNAS_JOGOS_SALVOS:
        if coluna not in normalizados.columns:
            if coluna == "Status":
                normalizados[coluna] = "PENDENTE"
            elif coluna == "Acertos":
                normalizados[coluna] = "0"
            else:
                normalizados[coluna] = ""
    normalizados["Status"] = normalizados["Status"].str.strip().replace("", "PENDENTE")
    normalizados["Acertos"] = normalizados["Acertos"].fillna("0").astype(str).str.strip().replace("", "0")
    normalizados["Dezenas"] = normalizados["Dezenas"].map(
        lambda valor: _formatar_dezenas(sorted(_parsear_dezenas(valor))) if _parsear_dezenas(valor) else ""
    )
    return normalizados[COLUNAS_JOGOS_SALVOS].copy()


def ler_jogos_salvos(caminho: Path = CAMINHO_JOGOS_SALVOS) -> pd.DataFrame:
    if not caminho.exists() or caminho.stat().st_size == 0:
        return normalizar_colunas_jogos_salvos(pd.DataFrame())
    dados = pd.read_csv(caminho, encoding="utf-8-sig", dtype=str, keep_default_na=False)
    return normalizar_colunas_jogos_salvos(dados)


def salvar_carteira(
    jogos: pd.DataFrame,
    numero_carteira: int,
    concurso_alvo: int,
    caminho: Path = CAMINHO_JOGOS_SALVOS,
    data_hora: datetime | None = None,
) -> pd.DataFrame:
    validar_jogos_producao(jogos)
    instante = data_hora or datetime.now().astimezone()
    linhas = []
    for _, row in jogos.iterrows():
        dezenas = [int(row[f"Bola{i}"]) for i in range(1, 16)]
        linhas.append(
            {
                "DataHora": instante.isoformat(timespec="seconds"),
                "Carteira": int(numero_carteira),
                "Concurso Alvo": int(concurso_alvo),
                "Perfil": str(row["Perfil"]),
                "Dezenas": _formatar_dezenas(dezenas),
                "Score": f'{float(row["Elite Score Temporal"]):.6f}',
                "Soma": int(row["Soma"]),
                "Pares": int(row["Pares"]),
                "Impares": int(row["Impares"]),
                "Status": "PENDENTE",
                "Acertos": "0",
            }
        )

    anteriores = ler_jogos_salvos(caminho)
    atualizados = pd.concat([anteriores, pd.DataFrame(linhas)], ignore_index=True)
    atualizados = normalizar_colunas_jogos_salvos(atualizados)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    atualizados = normalizar_colunas_jogos_salvos(atualizados)
    atualizados.to_csv(caminho, index=False, encoding="utf-8-sig")
    return atualizados


def conferir_jogos_salvos(
    base_historica: pd.DataFrame,
    caminho: Path = CAMINHO_JOGOS_SALVOS,
) -> pd.DataFrame:
    salvos = normalizar_colunas_jogos_salvos(ler_jogos_salvos(caminho))
    if salvos.empty:
        return salvos

    resultados = {
        int(row["Concurso"]): {int(row[coluna]) for coluna in COLUNAS_DEZENAS}
        for _, row in base_historica.iterrows()
    }
    for indice, row in salvos.iterrows():
        try:
            concurso = int(row["Concurso Alvo"])
        except (TypeError, ValueError):
            salvos.at[indice, "Status"] = "PENDENTE"
            salvos.at[indice, "Acertos"] = "0"
            continue
        sorteadas = resultados.get(concurso)
        if sorteadas is None:
            salvos.at[indice, "Status"] = "PENDENTE"
            salvos.at[indice, "Acertos"] = "0"
            continue
        geradas = _parsear_dezenas(row["Dezenas"])
        salvos.at[indice, "Status"] = "CONFERIDO"
        salvos.at[indice, "Acertos"] = str(len(geradas & sorteadas))

    salvos = normalizar_colunas_jogos_salvos(salvos)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    salvos = normalizar_colunas_jogos_salvos(salvos)
    salvos.to_csv(caminho, index=False, encoding="utf-8-sig")
    return salvos
