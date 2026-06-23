from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.analises_v5 import JANELAS_V5, paineis_tendencias_v5, ranking_janelas_v5
from src.carregar_dados import CAMINHO_BASE_PADRAO, carregar_base
from src.historico_sqlite import (
    conferir_historico_sqlite,
    listar_historico_sqlite,
    registrar_concurso_visto,
    salvar_carteira_sqlite,
)
from src.motor_elite_v2 import gerar_jogos_v2
from src.validacao_jogos import ConfiguracaoMotor


@pytest.fixture(scope="module")
def base() -> pd.DataFrame:
    return carregar_base(CAMINHO_BASE_PADRAO)


def test_ranking_v5_cobre_20_50_100_200(base: pd.DataFrame) -> None:
    ranking = ranking_janelas_v5(base)
    assert len(ranking) == 25
    assert set(ranking["Dezena"]) == set(range(1, 26))
    for janela in JANELAS_V5:
        assert {f"Frequência {janela}", f"Taxa {janela} (%)", f"Posição {janela}"}.issubset(ranking.columns)
        assert ranking[f"Frequência {janela}"].between(0, janela).all()
        assert ranking[f"Posição {janela}"].between(1, 25).all()


def test_paineis_v5_quentes_frias_atrasadas_repetidas(base: pd.DataFrame) -> None:
    paineis = paineis_tendencias_v5(base)
    assert set(paineis) == {"Quentes", "Frias", "Atrasadas", "Repetidas"}
    assert len(paineis["Quentes"]) == 8
    assert len(paineis["Frias"]) == 8
    assert len(paineis["Atrasadas"]) == 8
    assert not paineis["Repetidas"].empty
    assert paineis["Quentes"]["Índice recente"].min() >= paineis["Frias"]["Índice recente"].min()
    assert paineis["Atrasadas"]["Atraso"].is_monotonic_decreasing


def test_sqlite_salva_sem_duplicar_e_confere(base: pd.DataFrame, tmp_path: Path) -> None:
    caminho = tmp_path / "historico.sqlite3"
    jogos = gerar_jogos_v2(
        base,
        quantidade=5,
        configuracao=ConfiguracaoMotor(candidatos_por_perfil=50),
        semente=20260622,
    )
    concurso = int(base.iloc[-1]["Concurso"])
    primeiro = salvar_carteira_sqlite(jogos, 1, concurso, caminho)
    segundo = salvar_carteira_sqlite(jogos, 1, concurso, caminho)
    assert primeiro == segundo
    antes = listar_historico_sqlite(caminho)
    assert len(antes) == 5
    assert antes["Status"].eq("PENDENTE").all()

    atualizados = conferir_historico_sqlite(base, caminho)
    depois = listar_historico_sqlite(caminho)
    assert atualizados == 5
    assert depois["Status"].eq("CONFERIDO").all()
    assert depois["Acertos"].between(0, 15).all()


def test_alerta_persistente_detecta_apenas_avanco(tmp_path: Path) -> None:
    caminho = tmp_path / "estado.sqlite3"
    assert registrar_concurso_visto(100, caminho) is False
    assert registrar_concurso_visto(100, caminho) is False
    assert registrar_concurso_visto(101, caminho) is True
    assert registrar_concurso_visto(101, caminho) is False


def test_arquivos_railway_e_rodape_institucional() -> None:
    raiz = Path(__file__).resolve().parents[1]
    procfile = (raiz / "Procfile").read_text(encoding="utf-8")
    railway = (raiz / "railway.json").read_text(encoding="utf-8")
    app = (raiz / "app.py").read_text(encoding="utf-8")
    requirements = (raiz / "requirements.txt").read_text(encoding="utf-8")
    assert "python scripts/start_railway.py" in procfile
    assert "/_stcore/health" in railway
    assert "LEONIDAS TECH" in app and "Conectando o Futuro" in app
    assert "streamlit==" in requirements and "pandas==" in requirements
