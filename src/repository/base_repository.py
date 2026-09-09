from __future__ import annotations

import csv
import json
import os
from pathlib import Path
import shutil
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import numpy as np
import pandas as pd

from ..core.lotofacil_contract import ContratoLotofacilError, validar_resultado


RAIZ_PROJETO = Path(__file__).resolve().parents[2]
CAMINHO_BASE_EMBUTIDA = RAIZ_PROJETO / "dados" / "lotofacil_historico.csv"
CAMINHO_METADADOS_OFICIAIS = RAIZ_PROJETO / "dados" / "metadados_oficiais_lotofacil.json"
DIRETORIO_DADOS = Path(os.getenv("LOTOFACIL_DATA_DIR", RAIZ_PROJETO / "dados"))
CAMINHO_BASE_PADRAO = Path(os.getenv("LOTOFACIL_BASE_PATH", DIRETORIO_DADOS / "lotofacil_historico.csv"))
API_CAIXA_LOTOFACIL_URL = "https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil"
DOWNLOAD_CAIXA_LOTOFACIL_URL = (
    "https://servicebus2.caixa.gov.br/portaldeloterias/api/resultados/download"
    "?modalidade=LOTOFACIL"
)
FONTE_CAIXA_URL = "https://loterias.caixa.gov.br/Paginas/Lotofacil.aspx"
COLUNAS_DEZENAS = [f"Bola{i}" for i in range(1, 16)]
COLUNAS_OBRIGATORIAS = ["Concurso", "Data", *COLUNAS_DEZENAS]
ERROS_REDE = (HTTPError, URLError, TimeoutError, OSError, ValueError)


def _log_update(mensagem: str) -> None:
    print(f"[UPDATE] {mensagem}", flush=True)


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


def _parse_inteiro_externo(valor: object, rotulo: str) -> int:
    """Parser EXPLICITO do formato de origem externa (API CAIXA), usado
    SOMENTE ao ler a resposta JSON crua -- ANTES de qualquer valor entrar no
    DataFrame candidato. A API da CAIXA documentadamente pode serializar
    numeros como texto decimal, com ou sem zeros a esquerda (ex.: "01",
    "3780"); este parser aceita especificamente esse formato.

    NAO deve ser usado para validar celulas de um DataFrame ja construido
    -- essa e a responsabilidade de ``_inteiro_canonico_estrito``, mais
    estrita, usada exclusivamente por ``validar_base_estrita``.

    Rejeita EXPLICITAMENTE bool/``numpy.bool_``, float/``numpy.floating``
    (mesmo com valor inteiro, ex.: 15.0 ou "1.0"), None, string vazia e
    qualquer string que nao seja puramente numerica. Nunca trunca."""
    if isinstance(valor, (bool, np.bool_)):
        raise ValueError(f"{rotulo}: valor booleano nao e um inteiro valido ({valor!r}).")
    if isinstance(valor, (int, np.integer)):
        return int(valor)
    if isinstance(valor, str) and valor.strip().isdigit():
        return int(valor.strip())
    raise ValueError(f"{rotulo}: valor {valor!r} ({type(valor).__name__}) nao e um inteiro valido.")


def _inteiro_canonico_estrito(valor: object, rotulo: str) -> int:
    """Checagem de TIPO CANONICO, usada exclusivamente dentro de
    ``validar_base_estrita`` sobre celulas de um DataFrame candidato que ja
    deveria ter passado pelo parser explicito de fonte externa
    (``_parse_inteiro_externo``). Ao contrario dele, esta funcao e mais
    estrita e NAO aceita representacao textual: exige ``int`` nativo ou
    ``numpy.integer`` real (o tipo que o pandas usa em colunas inteiras --
    NAO e subclasse de ``int`` do Python, por isso precisa de checagem
    explicita). Rejeita EXPLICITAMENTE bool/``numpy.bool_`` (idem: nao e
    subclasse de ``bool``), string (mesmo puramente numerica, ex.: "5" ou
    "05"), float/``numpy.floating`` (mesmo 5.0) e None -- se qualquer um
    desses chegar aqui, e um erro de canonicalizacao ANTES desta fronteira,
    nao algo para reparsear silenciosamente agora."""
    if isinstance(valor, (bool, np.bool_)):
        raise ValueError(f"{rotulo}: valor booleano nao e um inteiro canonico valido ({valor!r}).")
    if isinstance(valor, (int, np.integer)):
        return int(valor)
    raise ValueError(
        f"{rotulo}: valor {valor!r} ({type(valor).__name__}) nao e um inteiro canonico valido "
        "(strings/float/None nao sao aceitos nesta fronteira -- devem ser convertidos antes)."
    )


def validar_base_estrita(
    df: pd.DataFrame,
    exigir_sequencia_continua: bool = True,
) -> pd.DataFrame:
    """Validacao estrita (fail-closed) da fronteira de ingestao externa.

    Ao contrario de ``validar_base`` (tolerante -- usada na leitura de
    rotina do arquivo local ja confiavel, ex.: ``carregar_base``, chamada a
    cada carregamento de pagina), esta funcao e a UNICA autoridade usada
    antes de persistir dados vindos de fonte externa (CAIXA) no CSV
    historico oficial (ver ``baixar_base_oficial_completa``). Nunca corrige
    silenciosamente: nenhuma linha e descartada, nenhuma coercao silenciosa
    de tipo, nenhum concurso duplicado e resolvido automaticamente -- tudo
    isso levanta ``ValueError`` com uma mensagem explicita e rastreavel
    (linha e motivo). Reutiliza ``validar_resultado`` (contrato LF-02) como
    autoridade para quantidade/tipo/unicidade/faixa das dezenas -- nao
    duplica esses invariantes manualmente.

    ``exigir_sequencia_continua`` (padrao ``True``): a unica chamadora real
    hoje (``baixar_base_oficial_completa``) monta a serie HISTORICA
    COMPLETA da Lotofacil, e uma lacuna interna na sequencia de concursos
    ali invalida o dataset candidato inteiro. Um eventual caller futuro que
    precise validar apenas um FRAGMENTO/janela parcial da serie (nao a base
    completa) deve passar ``False`` explicitamente para essa checagem
    especifica de continuidade -- as demais checagens (tipo, unicidade,
    faixa, duplicidade de concurso) continuam valendo sempre,
    incondicionalmente.
    """
    if df is None:
        raise ValueError("Base candidata a persistencia nao pode ser None.")
    faltantes = [col for col in COLUNAS_OBRIGATORIAS if col not in df.columns]
    if faltantes:
        raise ValueError(f"Base candidata sem colunas obrigatorias: {faltantes}")

    dados = df[COLUNAS_OBRIGATORIAS].reset_index(drop=True)
    if dados.empty:
        raise ValueError("Base candidata a persistencia esta vazia.")

    concursos_vistos: dict[int, int] = {}
    linhas_normalizadas: list[dict[str, object]] = []
    # itertuples() -- NUNCA iterrows(): iterrows() materializa cada linha
    # como uma pandas Series, que exige um dtype comum unico para a linha
    # inteira. Isso faz o pandas fazer upcast SILENCIOSO de valores int64
    # para float64 sempre que qualquer OUTRA coluna daquela mesma linha for
    # float/NaN (ex.: uma "Data" invalida faria o "Concurso" da mesma linha
    # parecer um float, mascarando a causa raiz real). itertuples() preserva
    # o tipo nativo de cada celula, por coluna, sem essa contaminacao.
    for linha in dados.itertuples(index=True):
        indice = linha.Index
        numero_concurso = _inteiro_canonico_estrito(linha.Concurso, f"Linha {indice}: Concurso")
        if numero_concurso <= 0:
            raise ValueError(f"Linha {indice}: Concurso deve ser positivo; recebeu {numero_concurso}.")
        if numero_concurso in concursos_vistos:
            raise ValueError(
                f"Concurso {numero_concurso} duplicado (linhas {concursos_vistos[numero_concurso]} e {indice})."
            )
        concursos_vistos[numero_concurso] = indice

        data_concurso = linha.Data
        if data_concurso is None or (isinstance(data_concurso, float) and pd.isna(data_concurso)):
            raise ValueError(f"Concurso {numero_concurso}: Data ausente.")
        data_texto = str(data_concurso).strip()
        if data_texto == "" or data_texto.lower() == "nan":
            raise ValueError(f"Concurso {numero_concurso}: Data ausente/invalida ({data_concurso!r}).")

        try:
            dezenas_brutas = [getattr(linha, coluna) for coluna in COLUNAS_DEZENAS]
            dezenas_inteiras = [
                _inteiro_canonico_estrito(valor, f"Concurso {numero_concurso}: dezena")
                for valor in dezenas_brutas
            ]
            dezenas_validadas = validar_resultado(dezenas_inteiras)
        except (ContratoLotofacilError, ValueError) as erro:
            raise ValueError(f"Concurso {numero_concurso}: resultado invalido -- {erro}") from erro

        registro: dict[str, object] = {"Concurso": numero_concurso, "Data": data_texto}
        for posicao, dezena in enumerate(dezenas_validadas, start=1):
            registro[f"Bola{posicao}"] = dezena
        linhas_normalizadas.append(registro)

    normalizados = pd.DataFrame(linhas_normalizadas, columns=COLUNAS_OBRIGATORIAS)
    normalizados = normalizados.sort_values("Concurso").reset_index(drop=True)

    if exigir_sequencia_continua:
        concursos_ordenados = normalizados["Concurso"].tolist()
        esperado = list(range(concursos_ordenados[0], concursos_ordenados[-1] + 1))
        if concursos_ordenados != esperado:
            faltando = sorted(set(esperado) - set(concursos_ordenados))
            raise ValueError(
                "Base candidata tem lacuna(s) na sequencia de concursos: "
                f"{faltando[:10]}{'...' if len(faltando) > 10 else ''}."
            )

    for coluna in COLUNAS_DEZENAS:
        normalizados[coluna] = normalizados[coluna].astype(int)
    normalizados["Concurso"] = normalizados["Concurso"].astype(int)
    return normalizados


def carregar_base(caminho: Path = CAMINHO_BASE_PADRAO) -> pd.DataFrame:
    if not caminho.exists():
        caminho.parent.mkdir(parents=True, exist_ok=True)
        if CAMINHO_BASE_EMBUTIDA.exists() and caminho.resolve() != CAMINHO_BASE_EMBUTIDA.resolve():
            shutil.copy2(CAMINHO_BASE_EMBUTIDA, caminho)
        else:
            criar_base_inicial_desenvolvimento(caminho)
    elif CAMINHO_BASE_EMBUTIDA.exists() and caminho.resolve() != CAMINHO_BASE_EMBUTIDA.resolve():
        temporario = caminho.with_suffix(caminho.suffix + ".embedded.tmp")
        try:
            base_volume = validar_base(pd.read_csv(caminho, encoding="utf-8-sig"))
            base_embutida = validar_base(pd.read_csv(CAMINHO_BASE_EMBUTIDA, encoding="utf-8-sig"))
            ultimo_volume = int(base_volume["Concurso"].max()) if not base_volume.empty else 0
            ultimo_embutido = int(base_embutida["Concurso"].max()) if not base_embutida.empty else 0
            if ultimo_embutido > ultimo_volume:
                shutil.copy2(CAMINHO_BASE_EMBUTIDA, temporario)
                validar_base(pd.read_csv(temporario, encoding="utf-8-sig"))
                temporario.replace(caminho)
                _log_update(f"Volume promovido de {ultimo_volume} para {ultimo_embutido} usando a base publicada")
        except Exception as erro:
            temporario.unlink(missing_ok=True)
            _log_update(f"ERRO ao sincronizar base publicada com volume: {type(erro).__name__}: {erro}")
    return validar_base(pd.read_csv(caminho, encoding="utf-8-sig"))


def _info_fallback() -> dict:
    return {
        "fonte": "fallback_local",
        "concurso_atual": None,
        "data_concurso_atual": None,
        "proximo_concurso": None,
        "data_proximo_concurso": None,
        "premio_estimado": "Consultar CAIXA",
        "premiacao_resultado": {},
        "acumulou": None,
    }


def _normalizar_info_api(dados: dict) -> dict:
    fallback = _info_fallback()
    proximo = dados.get("numeroConcursoProximo") or dados.get("numero")
    try:
        proximo = int(proximo) + (0 if dados.get("numeroConcursoProximo") else 1)
    except (TypeError, ValueError):
        proximo = None
    premiacao = {}
    for faixa in dados.get("listaRateioPremio") or []:
        try:
            numero_faixa = int(faixa.get("faixa"))
        except (TypeError, ValueError, AttributeError):
            continue
        if numero_faixa not in {1, 2, 3, 4, 5}:
            continue
        premiacao[16 - numero_faixa] = {
            "valor": faixa.get("valorPremio"),
            "ganhadores": faixa.get("numeroDeGanhadores"),
        }
    return {
        **fallback,
        "fonte": "CAIXA",
        "concurso_atual": dados.get("numero"),
        "data_concurso_atual": dados.get("dataApuracao"),
        "proximo_concurso": proximo,
        "data_proximo_concurso": dados.get("dataProximoConcurso"),
        "premio_estimado": dados.get("valorEstimadoProximoConcurso") or "Consultar CAIXA",
        "premiacao_resultado": premiacao,
        "acumulou": bool(dados.get("acumulado")),
    }


def _buscar_metadado_publicado(concurso: int) -> dict:
    try:
        registros = json.loads(CAMINHO_METADADOS_OFICIAIS.read_text(encoding="utf-8"))
        dados = registros.get(str(int(concurso)), {})
        if not dados:
            return _info_fallback()
        info = _normalizar_info_api(dados)
        info["fonte"] = "CAIXA_CACHE_PUBLICADO"
        return info
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return _info_fallback()


def buscar_info_concurso(concurso: int) -> dict:
    try:
        dados = _abrir_url_json(f"{API_CAIXA_LOTOFACIL_URL}/{int(concurso)}")
        return _normalizar_info_api(dados)
    except ERROS_REDE:
        return _buscar_metadado_publicado(concurso)


def buscar_info_concurso_atual() -> dict:
    try:
        dados = _abrir_url_json(API_CAIXA_LOTOFACIL_URL)
    except ERROS_REDE:
        return _info_fallback()
    return _normalizar_info_api(dados)


def baixar_base_oficial_completa() -> pd.DataFrame:
    ultimo = _abrir_url_json(API_CAIXA_LOTOFACIL_URL)
    ultimo_concurso = int(ultimo["numero"])
    base_local = carregar_base(CAMINHO_BASE_PADRAO) if CAMINHO_BASE_PADRAO.exists() else pd.DataFrame(columns=COLUNAS_OBRIGATORIAS)
    ultimo_local = int(base_local["Concurso"].max()) if not base_local.empty else 0
    _log_update(f"CSV={ultimo_local}")
    _log_update(f"API={ultimo_concurso}")
    try:
        conteudo = _abrir_url_bytes(DOWNLOAD_CAIXA_LOTOFACIL_URL)
        base = _normalizar_base_oficial(_ler_tabela_download_caixa(conteudo))
    except Exception as erro:
        _log_update(f"Download completo indisponível; usando CSV local: {type(erro).__name__}: {erro}")
        base = base_local

    ultimo_na_base = int(base["Concurso"].max()) if not base.empty else 0
    if ultimo_na_base > ultimo_concurso:
        raise ValueError("Base oficial retornou concurso anterior ao arquivo local.")

    registros = []
    for concurso in range(ultimo_na_base + 1, ultimo_concurso + 1):
        resultado = _abrir_url_json(f"{API_CAIXA_LOTOFACIL_URL}/{concurso}", timeout=12)
        dezenas_brutas = resultado.get("listaDezenas") or resultado.get("dezenasSorteadasOrdemSorteio")
        if not dezenas_brutas:
            raise ValueError(f"Concurso oficial {concurso} sem dezenas na resposta da API.")
        # Nunca truncar: uma resposta com 16+ dezenas e invalida, nao "15
        # dezenas com ruido extra". validar_resultado (contrato LF-02) exige
        # exatamente 15 e rejeita explicitamente float/bool/string/duplicata/
        # fora de 1..25. _parse_inteiro_externo converte o formato textual
        # documentado da API (ex.: "01") para inteiro canonico AQUI -- antes
        # de qualquer valor entrar no DataFrame candidato; validar_base_estrita
        # (mais abaixo) nao aceita mais strings, apenas o tipo ja canonico.
        try:
            numero_concurso = _parse_inteiro_externo(resultado.get("numero"), f"Concurso {concurso}: numero")
            dezenas_inteiras = [
                _parse_inteiro_externo(valor, f"Concurso {concurso}: dezena")
                for valor in dezenas_brutas
            ]
            dezenas_validadas = validar_resultado(dezenas_inteiras)
        except (ContratoLotofacilError, ValueError) as erro:
            raise ValueError(f"Concurso oficial {concurso}: resultado invalido -- {erro}") from erro
        linha = {"Concurso": numero_concurso, "Data": resultado.get("dataApuracao", "")}
        for i, dezena in enumerate(dezenas_validadas, start=1):
            linha[f"Bola{i}"] = dezena
        registros.append(linha)

    if registros:
        base = pd.concat([base, pd.DataFrame(registros)], ignore_index=True)
    # Boundary canonica: unica autoridade estrita antes de a base candidata
    # ser devolvida a atualizar_base_local() para persistencia. Validar
    # aqui -- e nao so depois de escrever um arquivo temporario -- garante
    # que nenhum dado externo invalido chegue perto de uma escrita real.
    base = validar_base_estrita(base)
    if base.empty or int(base.iloc[-1]["Concurso"]) != ultimo_concurso:
        raise ValueError("Base oficial incompleta; arquivo local preservado.")
    return base


def atualizar_base_local() -> bool:
    """Atualiza o CSV historico oficial a partir da fonte externa (CAIXA).

    Ordem estrita (a base candidata e validada ANTES de qualquer escrita,
    nao apos escrever e reler -- reler-e-validar por si so nao e proteção
    suficiente, pois o arquivo oficial so deve ser tocado depois que o
    candidato inteiro ja e conhecido como 100% valido):

        baixar_base_oficial_completa()  -- ja aplica validar_base_estrita()
        internamente, como ultimo passo, antes de devolver o candidato
        → validar_base_estrita() de novo, aqui -- DELIBERADAMENTE
        redundante: o writer e a ultima barreira antes do arquivo oficial e
        nunca deve depender apenas da validacao feita por quem produziu o
        candidato (se um caller futuro mudar/quebrar essa validacao, o
        writer ainda assim rejeita dado invalido)
        → escreve em arquivo temporario no mesmo diretorio
        → flush + fsync
        → close
        → replace atomico (os.replace via Path.replace)

    Qualquer excecao em qualquer etapa preserva o arquivo oficial anterior
    intacto e remove o temporario (nenhuma escrita parcial sobrevive).
    """
    temporario = CAMINHO_BASE_PADRAO.with_suffix(CAMINHO_BASE_PADRAO.suffix + ".tmp")
    try:
        dados = baixar_base_oficial_completa()
        dados = validar_base_estrita(dados)
        CAMINHO_BASE_PADRAO.parent.mkdir(parents=True, exist_ok=True)
        with open(temporario, "w", newline="", encoding="utf-8-sig") as arquivo:
            dados.to_csv(arquivo, index=False)
            arquivo.flush()
            os.fsync(arquivo.fileno())
        temporario.replace(CAMINHO_BASE_PADRAO)
        _log_update(f"Atualização executada com sucesso; CSV={int(dados['Concurso'].max())}")
    except Exception as erro:
        temporario.unlink(missing_ok=True)
        _log_update(f"ERRO: {type(erro).__name__}: {erro}")
        return False
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
