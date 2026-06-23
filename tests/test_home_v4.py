from __future__ import annotations

import pandas as pd

import app
import src.carregar_dados as carregar_dados


def _base(ultimo: int = 100) -> pd.DataFrame:
    linha = {"Concurso": ultimo, "Data": "01/01/2026"}
    linha.update({f"Bola{i}": i for i in range(1, 16)})
    return pd.DataFrame([linha])


def test_home_nao_mistura_api_atual_com_base_local_atrasada() -> None:
    meta = app.metadados_publicos(
        _base(100),
        {
            "fonte": "CAIXA",
            "concurso_atual": 120,
            "proximo_concurso": 121,
            "data_proximo_concurso": "02/01/2026",
            "premio_estimado": 2_000_000,
            "premiacao_resultado": {15: {"valor": 1_000_000, "ganhadores": 1}},
        },
    )
    assert meta["concurso_alvo"] == 101
    assert meta["premiacao_resultado"] == {}
    assert meta["fonte"] == "base_local_validada"


def test_home_exibe_metadados_e_rateio_quando_base_esta_sincronizada() -> None:
    rateio = {15: {"valor": 1_000_000, "ganhadores": 1}}
    meta = app.metadados_publicos(
        _base(120),
        {
            "fonte": "CAIXA",
            "concurso_atual": 120,
            "proximo_concurso": 121,
            "data_proximo_concurso": "02/01/2026",
            "premio_estimado": 2_000_000,
            "premiacao_resultado": rateio,
        },
    )
    assert meta["concurso_alvo"] == 121
    assert meta["premiacao_resultado"] == rateio
    assert meta["premio_estimado"] == "R$ 2.000.000,00"


def test_card_renderiza_premiacao_oficial_disponivel(monkeypatch) -> None:
    conteudos = []
    monkeypatch.setattr(app.st, "markdown", lambda conteudo, **_kwargs: conteudos.append(conteudo))
    app.render_card_publico(
        _base(120),
        {
            "concurso_alvo": 121,
            "data_sorteio": "02/01/2026",
            "premio_estimado": "R$ 2.000.000,00",
            "premiacao_resultado": {
                15: {"valor": 1_000_000, "ganhadores": 1},
                14: {"valor": 2_106.09, "ganhadores": 215},
            },
        },
    )
    html = "\n".join(conteudos)
    assert "Premiação oficial do concurso 120" in html
    assert "R$ 1.000.000,00" in html
    assert "R$ 2.106,09" in html
    assert "215 ganhador(es)" in html


def test_api_normaliza_rateio_oficial(monkeypatch) -> None:
    monkeypatch.setattr(
        carregar_dados,
        "_abrir_url_json",
        lambda *_args, **_kwargs: {
            "numero": 120,
            "dataApuracao": "01/01/2026",
            "numeroConcursoProximo": 121,
            "dataProximoConcurso": "02/01/2026",
            "valorEstimadoProximoConcurso": 2_000_000,
            "listaRateioPremio": [
                {"faixa": 1, "numeroDeGanhadores": 1, "valorPremio": 1_000_000},
                {"faixa": 5, "numeroDeGanhadores": 1000, "valorPremio": 7},
            ],
        },
    )
    info = carregar_dados.buscar_info_concurso_atual()
    assert info["premiacao_resultado"][15]["valor"] == 1_000_000
    assert info["premiacao_resultado"][11]["ganhadores"] == 1000


def test_download_valido_porem_atrasado_recebe_concursos_ausentes(monkeypatch) -> None:
    def linha(concurso: int) -> dict:
        return {
            "Concurso": concurso,
            "Data": f"0{concurso}/01/2026",
            **{f"Bola{i}": i for i in range(1, 16)},
        }

    respostas = {
        carregar_dados.API_CAIXA_LOTOFACIL_URL: {"numero": 3},
        f"{carregar_dados.API_CAIXA_LOTOFACIL_URL}/2": {
            "numero": 2,
            "dataApuracao": "02/01/2026",
            "listaDezenas": list(range(1, 16)),
        },
        f"{carregar_dados.API_CAIXA_LOTOFACIL_URL}/3": {
            "numero": 3,
            "dataApuracao": "03/01/2026",
            "listaDezenas": list(range(1, 16)),
        },
    }
    monkeypatch.setattr(carregar_dados, "_abrir_url_json", lambda url, **_kwargs: respostas[url])
    monkeypatch.setattr(carregar_dados, "_abrir_url_bytes", lambda *_args, **_kwargs: b"download")
    monkeypatch.setattr(carregar_dados, "_ler_tabela_download_caixa", lambda _conteudo: pd.DataFrame([linha(1)]))

    base = carregar_dados.baixar_base_oficial_completa()
    assert base["Concurso"].tolist() == [1, 2, 3]
