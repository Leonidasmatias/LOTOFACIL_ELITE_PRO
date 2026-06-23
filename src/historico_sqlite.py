from __future__ import annotations

from datetime import datetime
from hashlib import sha256
from pathlib import Path
import os
import sqlite3

import pandas as pd

from .carregar_dados import COLUNAS_DEZENAS, RAIZ_PROJETO
from .validacao_jogos import validar_carteira


DIRETORIO_DADOS = Path(os.getenv("LOTOFACIL_DATA_DIR", RAIZ_PROJETO / "dados"))
CAMINHO_BANCO_V5 = Path(os.getenv("LOTOFACIL_DB_PATH", DIRETORIO_DADOS / "lotofacil_v5.sqlite3"))


def _conectar(caminho: Path = CAMINHO_BANCO_V5) -> sqlite3.Connection:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    conexao = sqlite3.connect(caminho, timeout=30)
    conexao.row_factory = sqlite3.Row
    conexao.execute("PRAGMA foreign_keys = ON")
    conexao.execute("PRAGMA journal_mode = WAL")
    return conexao


def inicializar_banco(caminho: Path = CAMINHO_BANCO_V5) -> None:
    with _conectar(caminho) as conexao:
        conexao.executescript(
            """
            CREATE TABLE IF NOT EXISTS carteiras (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                assinatura TEXT NOT NULL UNIQUE,
                data_hora TEXT NOT NULL,
                numero_carteira INTEGER NOT NULL,
                concurso_alvo INTEGER NOT NULL,
                quantidade_jogos INTEGER NOT NULL,
                origem TEXT NOT NULL DEFAULT 'GERACAO',
                status TEXT NOT NULL DEFAULT 'AGUARDANDO RESULTADO'
            );
            CREATE TABLE IF NOT EXISTS jogos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                carteira_id INTEGER NOT NULL REFERENCES carteiras(id) ON DELETE CASCADE,
                perfil TEXT NOT NULL,
                dezenas TEXT NOT NULL,
                score REAL NOT NULL DEFAULT 0,
                soma INTEGER NOT NULL,
                pares INTEGER NOT NULL,
                impares INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'PENDENTE',
                acertos INTEGER NOT NULL DEFAULT 0,
                UNIQUE(carteira_id, perfil, dezenas)
            );
            CREATE TABLE IF NOT EXISTS estado_sistema (
                chave TEXT PRIMARY KEY,
                valor TEXT NOT NULL,
                atualizado_em TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_carteiras_concurso ON carteiras(concurso_alvo);
            CREATE INDEX IF NOT EXISTS idx_jogos_status ON jogos(status);
            """
        )


def _dezenas_texto(row: pd.Series) -> str:
    return "-".join(f"{int(row[f'Bola{i}']):02d}" for i in range(1, 16))


def salvar_carteira_sqlite(
    jogos: pd.DataFrame,
    numero_carteira: int,
    concurso_alvo: int,
    caminho: Path = CAMINHO_BANCO_V5,
    data_hora: datetime | None = None,
    origem: str = "GERACAO AUTOMATICA",
) -> int:
    validar_carteira(([int(row[f"Bola{i}"]) for i in range(1, 16)] for _, row in jogos.iterrows()))
    instante = (data_hora or datetime.now().astimezone()).isoformat(timespec="seconds")
    partes = [f"{row.get('Perfil', '')}:{_dezenas_texto(row)}" for _, row in jogos.iterrows()]
    assinatura = sha256(f"{concurso_alvo}|{numero_carteira}|{'|'.join(partes)}".encode("utf-8")).hexdigest()
    inicializar_banco(caminho)
    with _conectar(caminho) as conexao:
        existente = conexao.execute("SELECT id FROM carteiras WHERE assinatura = ?", (assinatura,)).fetchone()
        if existente:
            return int(existente["id"])
        cursor = conexao.execute(
            "INSERT INTO carteiras (assinatura, data_hora, numero_carteira, concurso_alvo, quantidade_jogos, origem) VALUES (?, ?, ?, ?, ?, ?)",
            (assinatura, instante, int(numero_carteira), int(concurso_alvo), len(jogos), origem),
        )
        carteira_id = int(cursor.lastrowid)
        for _, row in jogos.iterrows():
            conexao.execute(
                "INSERT INTO jogos (carteira_id, perfil, dezenas, score, soma, pares, impares) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    carteira_id,
                    str(row.get("Perfil", "Sem perfil")),
                    _dezenas_texto(row),
                    float(row.get("Score", row.get("Elite Score Temporal", 0.0))),
                    int(row.get("Soma", 0)),
                    int(row.get("Pares", 0)),
                    int(row.get("Impares", row.get("Ímpares", 0))),
                ),
            )
        return carteira_id


def conferir_historico_sqlite(base_historica: pd.DataFrame, caminho: Path = CAMINHO_BANCO_V5) -> int:
    inicializar_banco(caminho)
    resultados = {
        int(row["Concurso"]): {int(row[coluna]) for coluna in COLUNAS_DEZENAS}
        for _, row in base_historica.iterrows()
    }
    atualizados = 0
    with _conectar(caminho) as conexao:
        carteiras = conexao.execute("SELECT id, concurso_alvo FROM carteiras").fetchall()
        for carteira in carteiras:
            sorteadas = resultados.get(int(carteira["concurso_alvo"]))
            if sorteadas is None:
                continue
            jogos = conexao.execute("SELECT id, dezenas FROM jogos WHERE carteira_id = ?", (carteira["id"],)).fetchall()
            melhores = []
            for jogo in jogos:
                dezenas = {int(item) for item in str(jogo["dezenas"]).split("-") if item}
                acertos = len(dezenas & sorteadas)
                melhores.append(acertos)
                conexao.execute("UPDATE jogos SET status = 'CONFERIDO', acertos = ? WHERE id = ?", (acertos, jogo["id"]))
                atualizados += 1
            status = "PREMIADO" if melhores and max(melhores) >= 11 else "SEM PREMIO"
            conexao.execute("UPDATE carteiras SET status = ? WHERE id = ?", (status, carteira["id"]))
    return atualizados


def listar_historico_sqlite(caminho: Path = CAMINHO_BANCO_V5, limite: int = 500) -> pd.DataFrame:
    inicializar_banco(caminho)
    consulta = """
        SELECT c.data_hora AS "Data/hora", c.numero_carteira AS "Carteira", c.concurso_alvo AS "Concurso Alvo",
               j.perfil AS "Perfil", j.dezenas AS "Dezenas", ROUND(j.score, 4) AS "Score",
               j.status AS "Status", j.acertos AS "Acertos"
        FROM jogos j JOIN carteiras c ON c.id = j.carteira_id
        ORDER BY c.id DESC, j.id ASC LIMIT ?
    """
    with _conectar(caminho) as conexao:
        return pd.read_sql_query(consulta, conexao, params=(int(limite),))


def registrar_concurso_visto(concurso: int, caminho: Path = CAMINHO_BANCO_V5) -> bool:
    inicializar_banco(caminho)
    agora = datetime.now().astimezone().isoformat(timespec="seconds")
    with _conectar(caminho) as conexao:
        anterior = conexao.execute("SELECT valor FROM estado_sistema WHERE chave = 'ultimo_concurso_visto'").fetchone()
        novo = anterior is not None and int(anterior["valor"]) < int(concurso)
        conexao.execute(
            "INSERT INTO estado_sistema (chave, valor, atualizado_em) VALUES ('ultimo_concurso_visto', ?, ?) "
            "ON CONFLICT(chave) DO UPDATE SET valor=excluded.valor, atualizado_em=excluded.atualizado_em",
            (str(int(concurso)), agora),
        )
        return novo


def migrar_historico_csv(caminho: Path = CAMINHO_BANCO_V5) -> int:
    from .jogos_salvos import ler_jogos_salvos

    salvos = ler_jogos_salvos()
    if salvos.empty:
        return 0
    def numero(valor: object, padrao: float) -> float:
        convertido = pd.to_numeric(valor, errors="coerce")
        return padrao if pd.isna(convertido) else float(convertido)

    inicializar_banco(caminho)
    importados = 0
    grupos = salvos.groupby(["DataHora", "Carteira", "Concurso Alvo"], dropna=False, sort=False)
    with _conectar(caminho) as conexao:
        for (data_hora, numero_carteira, concurso_alvo), grupo in grupos:
            assinatura = sha256(f"CSV|{data_hora}|{numero_carteira}|{concurso_alvo}".encode("utf-8")).hexdigest()
            existente = conexao.execute("SELECT id FROM carteiras WHERE assinatura = ?", (assinatura,)).fetchone()
            if existente:
                continue
            pendente = grupo["Status"].astype(str).str.upper().eq("PENDENTE").any()
            acertos_grupo = pd.to_numeric(grupo["Acertos"], errors="coerce").fillna(0).astype(int)
            status = "AGUARDANDO RESULTADO" if pendente else ("PREMIADO" if acertos_grupo.max() >= 11 else "SEM PREMIO")
            cursor = conexao.execute(
                "INSERT INTO carteiras (assinatura, data_hora, numero_carteira, concurso_alvo, quantidade_jogos, origem, status) VALUES (?, ?, ?, ?, ?, 'MIGRACAO CSV', ?)",
                (assinatura, str(data_hora), int(numero_carteira), int(concurso_alvo), len(grupo), status),
            )
            carteira_id = int(cursor.lastrowid)
            for _, row in grupo.iterrows():
                dezenas = [int(item) for item in str(row["Dezenas"]).split("-") if item]
                if len(dezenas) != 15:
                    continue
                conexao.execute(
                    "INSERT OR IGNORE INTO jogos (carteira_id, perfil, dezenas, score, soma, pares, impares, status, acertos) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        carteira_id,
                        str(row["Perfil"]),
                        "-".join(f"{dezena:02d}" for dezena in dezenas),
                        numero(row["Score"], 0),
                        int(numero(row["Soma"], sum(dezenas))),
                        int(numero(row["Pares"], sum(d % 2 == 0 for d in dezenas))),
                        int(numero(row["Impares"], sum(d % 2 != 0 for d in dezenas))),
                        str(row["Status"]),
                        int(numero(row["Acertos"], 0)),
                    ),
                )
            importados += 1
    return importados
