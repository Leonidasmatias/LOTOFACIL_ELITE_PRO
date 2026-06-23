from __future__ import annotations

from pathlib import Path

import pandas as pd

import src.carregar_dados as carregar_dados


def _base(concurso: int) -> pd.DataFrame:
    linha = {"Concurso": concurso, "Data": "22/06/2026"}
    linha.update({f"Bola{i}": i for i in range(1, 16)})
    return pd.DataFrame([linha])


def test_base_publicada_mais_nova_promove_volume_sem_api(tmp_path: Path, monkeypatch, capsys) -> None:
    embutida = tmp_path / "imagem" / "lotofacil_historico.csv"
    volume = tmp_path / "volume" / "lotofacil_historico.csv"
    embutida.parent.mkdir(parents=True)
    volume.parent.mkdir(parents=True)
    _base(3717).to_csv(embutida, index=False, encoding="utf-8-sig")
    _base(3716).to_csv(volume, index=False, encoding="utf-8-sig")
    monkeypatch.setattr(carregar_dados, "CAMINHO_BASE_EMBUTIDA", embutida)

    resultado = carregar_dados.carregar_base(volume)

    assert int(resultado["Concurso"].max()) == 3717
    assert int(pd.read_csv(volume, encoding="utf-8-sig")["Concurso"].max()) == 3717
    assert "[UPDATE] Volume promovido de 3716 para 3717" in capsys.readouterr().out


def test_falha_da_atualizacao_e_registrada_no_stdout(tmp_path: Path, monkeypatch, capsys) -> None:
    destino = tmp_path / "lotofacil_historico.csv"
    monkeypatch.setattr(carregar_dados, "CAMINHO_BASE_PADRAO", destino)
    monkeypatch.setattr(
        carregar_dados,
        "baixar_base_oficial_completa",
        lambda: (_ for _ in ()).throw(TimeoutError("Timeout API CAIXA")),
    )

    assert carregar_dados.atualizar_base_local() is False
    saida = capsys.readouterr().out
    assert "[UPDATE] ERRO: TimeoutError: Timeout API CAIXA" in saida
    assert not destino.with_suffix(".csv.tmp").exists()
