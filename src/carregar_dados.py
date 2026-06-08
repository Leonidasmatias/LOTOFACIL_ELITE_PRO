from __future__ import annotations

import csv
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pandas as pd


RAIZ_PROJETO = Path(__file__).resolve().parents[1]
CAMINHO_BASE_PADRAO = RAIZ_PROJETO / "dados" / "lotofacil_historico.csv"
API_CAIXA_LOTOFACIL_URL = "https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil"
DOWNLOAD_CAIXA_LOTOFACIL_URL = (
    "https://servicebus2.caixa.gov.br/portaldeloterias/api/resultados/download"
    "?modalidade=LOTOFACIL"
)
FONTE_CAIXA_URL = "https://loterias.caixa.gov.br/Paginas/Lotofacil.aspx"
COLUNAS_DEZENAS = [f"Bola{i}" for i in range(1, 16)]
COLUNAS_OBRIGATORIAS = ["Concurso", "Data", *COLUNAS_DEZENAS]
ERROS_REDE = (HTTPError, URLError, TimeoutError, OSError, ValueError)


def _abrir_url_json(url: str, timeout: int = 20) -> dict:
    import json

    req = Request(url, headers={"User-Agent": "Mozilla/5.0", "Referer": FONTE_CAIXA_URL})
    with urlopen(req, timeout=timeout) as resposta:
        return json.loads(resposta.read().decode("utf-8-sig"))


def _abrir_url_bytes(url: str, timeout: int = 30) -> bytes:
    req = Request(url, headers={"User-Agent": "Mozilla/5.0", "Referer": FONTE_CAIXA_URL})
    with urlopen(req, timeout=timeout) as resposta:
        return resposta.read()


def _normalizar_nome_coluna(coluna: object) -> str:
    import re
    from unicodedata import normalize

    texto = normalize("NFKD", str(coluna).strip().lower()).encode("ascii", "ignore").decode("ascii")
    texto = re.sub(r"[\s_.-]+", " ", texto).strip()
    compacto = texto.replace(" ", "")
    if compacto in {"concurso", "nconcurso", "numeroconcurso", "numerodoconcurso"}:
        return "Concurso"
    if compacto in {"data", "datasorteio", "datadosorteio", "dataapuracao"}:
        return "Data"
    for i in range(1, 16):
        candidatos = {
            f"bola{i}",
            f"bola {i}",
            f"dezena{i}",
            f"dezena {i}",
            f"d{i}",
            f"{i}dezena",
            f"{i}a dezena",
        }
        if compacto in {c.replace(" ", "") for c in candidatos} or texto in candidatos:
            return f"Bola{i}"
    return str(coluna).strip()


def _normalizar_base_oficial(df: pd.DataFrame) -> pd.DataFrame:
    dados = df.copy()
    dados.columns = [_normalizar_nome_coluna(coluna) for coluna in dados.columns]
    if not set(COLUNAS_OBRIGATORIAS).issubset(dados.columns):
        # Alguns downloads chegam com colunas extras antes das dezenas. Usa as primeiras
        # 15 colunas numericas depois de Concurso/Data como dezenas.
        colunas = list(dados.columns)
        concurso = next((c for c in colunas if c == "Concurso"), None)
        data = next((c for c in colunas if c == "Data"), None)
        outras = [c for c in colunas if c not in {"Concurso", "Data"}]
        if concurso and data and len(outras) >= 15:
            renomear = {outras[i]: f"Bola{i + 1}" for i in range(15)}
            dados = dados.rename(columns=renomear)
    return validar_base(dados)


def _ler_tabela_download_caixa(conteudo: bytes) -> pd.DataFrame:
    from io import BytesIO
    import zipfile

    if zipfile.is_zipfile(BytesIO(conteudo)):
        with zipfile.ZipFile(BytesIO(conteudo)) as arquivo_zip:
            nomes = arquivo_zip.namelist()
            if "xl/workbook.xml" in nomes:
                return pd.read_excel(BytesIO(conteudo))
            candidatos = [
                nome for nome in nomes if Path(nome).suffix.lower() in {".csv", ".xlsx", ".xls", ".htm", ".html"}
            ]
            if not candidatos:
                raise ValueError("Download oficial da CAIXA sem tabela reconhecida.")
            conteudo = arquivo_zip.read(candidatos[0])
    for leitor in (
        lambda b: pd.read_excel(BytesIO(b)),
        lambda b: pd.read_csv(BytesIO(b), sep=None, engine="python", encoding="utf-8-sig"),
        lambda b: pd.read_csv(BytesIO(b), sep=None, engine="python", encoding="latin1"),
    ):
        try:
            return leitor(conteudo)
        except Exception:
            pass
    tabelas = pd.read_html(BytesIO(conteudo))
    if not tabelas:
        raise ValueError("Nenhuma tabela encontrada no download oficial da CAIXA.")
    return max(tabelas, key=len)


def validar_base(df: pd.DataFrame) -> pd.DataFrame:
    dados = df.copy()
    faltantes = [col for col in COLUNAS_OBRIGATORIAS if col not in dados.columns]
    if faltantes:
        raise ValueError(f"Base Lotofacil sem colunas obrigatorias: {faltantes}")

    dados = dados[COLUNAS_OBRIGATORIAS].copy()
    dados["Concurso"] = pd.to_numeric(dados["Concurso"], errors="coerce").astype("Int64")
    dados["Data"] = dados["Data"].astype(str)
    for coluna in COLUNAS_DEZENAS:
        dados[coluna] = pd.to_numeric(dados[coluna], errors="coerce").astype("Int64")

    dados = dados.dropna(subset=["Concurso", *COLUNAS_DEZENAS]).copy()
    for coluna in ["Concurso", *COLUNAS_DEZENAS]:
        dados[coluna] = dados[coluna].astype(int)
    dados = dados.sort_values("Concurso").drop_duplicates("Concurso", keep="last")
    return dados.reset_index(drop=True)


def carregar_base(caminho: Path = CAMINHO_BASE_PADRAO) -> pd.DataFrame:
    if not caminho.exists():
        criar_base_inicial_desenvolvimento(caminho)
    return validar_base(pd.read_csv(caminho, encoding="utf-8-sig"))


def buscar_info_concurso_atual() -> dict:
    fallback = {
        "fonte": "fallback_local",
        "concurso_atual": None,
        "proximo_concurso": None,
        "data_proximo_concurso": None,
        "premio_estimado": "Consultar CAIXA",
        "acumulou": None,
    }
    try:
        dados = _abrir_url_json(API_CAIXA_LOTOFACIL_URL)
    except ERROS_REDE:
        return fallback

    proximo = dados.get("numeroConcursoProximo") or dados.get("numero")
    try:
        proximo = int(proximo) + (0 if dados.get("numeroConcursoProximo") else 1)
    except (TypeError, ValueError):
        proximo = None
    return {
        **fallback,
        "fonte": "CAIXA",
        "concurso_atual": dados.get("numero"),
        "proximo_concurso": proximo,
        "data_proximo_concurso": dados.get("dataProximoConcurso"),
        "premio_estimado": dados.get("valorEstimadoProximoConcurso") or "Consultar CAIXA",
        "acumulou": bool(dados.get("acumulado")),
    }


def baixar_base_oficial_completa() -> pd.DataFrame:
    try:
        conteudo = _abrir_url_bytes(DOWNLOAD_CAIXA_LOTOFACIL_URL)
        return _normalizar_base_oficial(_ler_tabela_download_caixa(conteudo))
    except Exception:
        ultimo = _abrir_url_json(API_CAIXA_LOTOFACIL_URL)
        ultimo_concurso = int(ultimo["numero"])
        registros = []
        for concurso in range(1, ultimo_concurso + 1):
            resultado = _abrir_url_json(f"{API_CAIXA_LOTOFACIL_URL}/{concurso}", timeout=12)
            dezenas = resultado.get("listaDezenas") or resultado.get("dezenasSorteadasOrdemSorteio")
            if not dezenas or len(dezenas) < 15:
                continue
            linha = {"Concurso": resultado["numero"], "Data": resultado.get("dataApuracao", "")}
            for i, dezena in enumerate(dezenas[:15], start=1):
                linha[f"Bola{i}"] = int(dezena)
            registros.append(linha)
        if not registros:
            raise ValueError("Nenhum concurso oficial retornado pela CAIXA.")
        return validar_base(pd.DataFrame(registros))


def atualizar_base_local() -> bool:
    try:
        dados = baixar_base_oficial_completa()
    except ERROS_REDE:
        return False
    except Exception:
        return False
    CAMINHO_BASE_PADRAO.parent.mkdir(parents=True, exist_ok=True)
    dados.to_csv(CAMINHO_BASE_PADRAO, index=False, encoding="utf-8-sig")
    return True


def resumo_base(df: pd.DataFrame) -> dict:
    return {
        "total_concursos": int(len(df)),
        "primeiro_concurso": int(df["Concurso"].min()) if not df.empty else 0,
        "ultimo_concurso": int(df["Concurso"].max()) if not df.empty else 0,
    }


def criar_base_inicial_desenvolvimento(caminho: Path = CAMINHO_BASE_PADRAO) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    linhas = []
    for concurso in range(1, 61):
        dezenas = sorted((((concurso * 7 + i * 3) % 25) + 1 for i in range(15)))
        # Resolve repeticoes mantendo 15 dezenas distintas.
        usadas = []
        cursor = 1
        for dezena in dezenas:
            while dezena in usadas:
                dezena = cursor
                cursor += 1
                if cursor > 25:
                    cursor = 1
            usadas.append(dezena)
        linha = {"Concurso": concurso, "Data": f"{(concurso % 28) + 1:02d}/01/2026"}
        for i, dezena in enumerate(sorted(usadas), start=1):
            linha[f"Bola{i}"] = dezena
        linhas.append(linha)
    with caminho.open("w", newline="", encoding="utf-8-sig") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=COLUNAS_OBRIGATORIAS)
        escritor.writeheader()
        escritor.writerows(linhas)
