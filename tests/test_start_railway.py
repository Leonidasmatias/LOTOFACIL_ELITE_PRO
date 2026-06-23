from __future__ import annotations

import sys

import pytest

from scripts.start_railway import comando_streamlit, obter_porta


def test_porta_railway_e_padrao() -> None:
    assert obter_porta({"PORT": "18234"}) == 18234
    assert obter_porta({}) == 8501


@pytest.mark.parametrize("valor", ["abc", "0", "65536", ""])
def test_porta_invalida_interrompe_startup(valor: str) -> None:
    with pytest.raises(SystemExit):
        obter_porta({"PORT": valor})


def test_comando_faz_bind_publico_na_porta_fornecida() -> None:
    comando = comando_streamlit(18234)
    assert comando[:4] == [sys.executable, "-m", "streamlit", "run"]
    assert "app.py" in comando
    assert "--server.address=0.0.0.0" in comando
    assert "--server.port=18234" in comando
