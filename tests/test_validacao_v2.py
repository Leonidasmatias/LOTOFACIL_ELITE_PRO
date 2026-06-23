from __future__ import annotations

import pandas as pd
import pytest

import src.carregar_dados as carregar_dados
from src.validacao_jogos import ConfiguracaoMotor, sequencia_maxima, validar_carteira, validar_jogo


def test_validador_rejeita_quantidade_duplicidade_e_intervalo() -> None:
    with pytest.raises(ValueError, match="exatamente 15"):
        validar_jogo(range(1, 15))
    with pytest.raises(ValueError, match="duplicadas"):
        validar_jogo([1] * 15)
    with pytest.raises(ValueError, match="entre 1 e 25"):
        validar_jogo([0, *range(1, 15)])


def test_validador_respeita_soma_e_paridade_configuraveis() -> None:
    jogo = list(range(1, 16))
    with pytest.raises(ValueError, match="Soma"):
        validar_jogo(jogo, ConfiguracaoMotor(soma_minima=180, soma_maxima=220))
    with pytest.raises(ValueError, match="pares"):
        validar_jogo(jogo, ConfiguracaoMotor(soma_minima=100, soma_maxima=220, pares_minimo=8, pares_maximo=9))


def test_carteira_rejeita_jogos_iguais_ou_parecidos() -> None:
    jogo = list(range(1, 16))
    config = ConfiguracaoMotor(soma_minima=100, soma_maxima=230, repetidas_minimo=0, repetidas_maximo=15, sequencia_maxima=15)
    with pytest.raises(ValueError, match="diferentes"):
        validar_carteira([jogo, jogo], config)
    parecido = list(range(1, 15)) + [16]
    with pytest.raises(ValueError, match="parecidos"):
        validar_carteira([jogo, parecido], config)


def test_sequencia_maxima() -> None:
    assert sequencia_maxima([1, 2, 3, 7, 8, 10]) == 3


@pytest.mark.parametrize("etapa", ["download", "processamento", "escrita", "leitura", "validacao"])
def test_atualizacao_atomica_preserva_base_em_todas_as_falhas(tmp_path, monkeypatch, etapa: str) -> None:
    base = tmp_path / "lotofacil_historico.csv"
    conteudo_original = b"base-local-preservada\n"
    base.write_bytes(conteudo_original)
    dados = pd.DataFrame([{"Concurso": 1, "Data": "01/01/2026", **{f"Bola{i}": i for i in range(1, 16)}}])

    monkeypatch.setattr(carregar_dados, "CAMINHO_BASE_PADRAO", base)
    if etapa in {"download", "processamento"}:
        monkeypatch.setattr(
            carregar_dados,
            "baixar_base_oficial_completa",
            lambda: (_ for _ in ()).throw(RuntimeError(f"falha de {etapa}")),
        )
    else:
        monkeypatch.setattr(carregar_dados, "baixar_base_oficial_completa", lambda: dados)
    if etapa == "escrita":
        monkeypatch.setattr(pd.DataFrame, "to_csv", lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("falha de escrita")))
    if etapa == "leitura":
        monkeypatch.setattr(carregar_dados.pd, "read_csv", lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("falha de leitura")))
    if etapa == "validacao":
        monkeypatch.setattr(carregar_dados, "validar_base", lambda _df: (_ for _ in ()).throw(ValueError("falha de validação")))

    assert carregar_dados.atualizar_base_local() is False
    assert base.read_bytes() == conteudo_original
    assert not base.with_suffix(".csv.tmp").exists()
