"""Testes da fronteira de ingestao/persistencia da Lotofacil (Fase LF-03).

Cobrem exclusivamente `src/repository/base_repository.py`: a boundary
canonica onde dados de fonte externa (API CAIXA) sao validados de forma
estrita (fail-closed) ANTES de qualquer persistencia em
`dados/lotofacil_historico.csv`.

Todos os testes sao herméticos: nenhuma chamada de rede real (toda
comunicacao com a "CAIXA" e mockada via monkeypatch em
`_abrir_url_json`/`_abrir_url_bytes`), nenhuma escrita no CSV ou SQLite
reais (todos os caminhos de arquivo usam `tmp_path`).
"""
from __future__ import annotations

import hashlib

import pandas as pd
import pytest

from src.repository import base_repository as br


COLUNAS_DEZENAS = br.COLUNAS_DEZENAS
COLUNAS_OBRIGATORIAS = br.COLUNAS_OBRIGATORIAS


def _linha(concurso: object, dezenas: list | None = None, data: object = "01/01/2026") -> dict:
    dezenas = dezenas if dezenas is not None else list(range(1, 16))
    linha = {"Concurso": concurso, "Data": data}
    for indice in range(15):
        linha[f"Bola{indice + 1}"] = dezenas[indice] if indice < len(dezenas) else None
    return linha


def _df(linhas: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(linhas, columns=COLUNAS_OBRIGATORIAS)


def _sha256(caminho) -> str:
    return hashlib.sha256(caminho.read_bytes()).hexdigest()


# --- LF-03A: separacao parser externo (permissivo) vs canonico (estrito) --
#
# _parse_inteiro_externo: usado SOMENTE ao ler a resposta JSON crua da
# CAIXA, antes de qualquer valor entrar no DataFrame candidato -- aceita o
# formato textual documentado da API.
#
# _inteiro_canonico_estrito: usado SOMENTE dentro de validar_base_estrita,
# sobre celulas do DataFrame candidato ja construido -- NAO aceita mais
# texto, so int/np.integer real.


@pytest.mark.parametrize("bruto,esperado", [("01", 1), ("15", 15), ("3780", 3780), (7, 7)])
def test_parse_inteiro_externo_aceita_formato_documentado_da_api(bruto, esperado) -> None:
    assert br._parse_inteiro_externo(bruto, "teste") == esperado


@pytest.mark.parametrize(
    "bruto",
    ["", "1.0", "abc", True, False, None, 1.0, 5.5],
)
def test_parse_inteiro_externo_rejeita_formato_nao_documentado(bruto) -> None:
    with pytest.raises(ValueError):
        br._parse_inteiro_externo(bruto, "teste")


def test_inteiro_canonico_estrito_aceita_int_e_numpy_integer() -> None:
    import numpy as np

    assert br._inteiro_canonico_estrito(5, "teste") == 5
    assert br._inteiro_canonico_estrito(np.int64(5), "teste") == 5


@pytest.mark.parametrize("bruto", ["5", "05", 5.0, True, False, None, "", "abc"])
def test_inteiro_canonico_estrito_rejeita_tudo_que_nao_for_int_real(bruto) -> None:
    with pytest.raises(ValueError):
        br._inteiro_canonico_estrito(bruto, "teste")


# --- validar_base_estrita: casos VALIDOS ---------------------------------


def test_validar_base_estrita_aceita_dataset_valido_sequencial() -> None:
    linhas = [_linha(c, data=f"0{c}/01/2026") for c in (1, 2, 3)]
    resultado = br.validar_base_estrita(_df(linhas))
    assert resultado["Concurso"].tolist() == [1, 2, 3]
    assert list(resultado.columns) == COLUNAS_OBRIGATORIAS
    for coluna in COLUNAS_DEZENAS:
        assert resultado[coluna].dtype == int or str(resultado[coluna].dtype).startswith("int")


def test_validar_base_estrita_rejeita_dezena_string_com_zero_a_esquerda() -> None:
    # LF-03A: validar_base_estrita exige tipo CANONICO (int/np.integer) no
    # dataset candidato -- string, mesmo puramente numerica e com zero a
    # esquerda (formato aceito pelo PARSER externo, nao pela validacao
    # canonica), deve ser rejeitada aqui. A conversao string->int e
    # responsabilidade exclusiva de _parse_inteiro_externo, executada ANTES
    # da construcao do DataFrame candidato.
    dezenas_texto = [f"{d:02d}" for d in range(1, 16)]
    with pytest.raises(ValueError, match="resultado invalido"):
        br.validar_base_estrita(_df([_linha(1, dezenas=dezenas_texto)]))


def test_validar_base_estrita_rejeita_dezena_string_sem_zero_a_esquerda() -> None:
    dezenas_texto = [str(d) for d in range(1, 16)]
    with pytest.raises(ValueError, match="resultado invalido"):
        br.validar_base_estrita(_df([_linha(1, dezenas=dezenas_texto)]))


def test_validar_base_estrita_e_deterministica() -> None:
    linhas = [_linha(1), _linha(2)]
    r1 = br.validar_base_estrita(_df(linhas))
    r2 = br.validar_base_estrita(_df(linhas))
    pd.testing.assert_frame_equal(r1, r2)


def test_validar_base_estrita_normaliza_ordem_das_dezenas() -> None:
    dezenas_desordenadas = [15, 1, 14, 2, 13, 3, 12, 4, 11, 5, 10, 6, 9, 7, 8]
    resultado = br.validar_base_estrita(_df([_linha(1, dezenas=dezenas_desordenadas)]))
    assert resultado.iloc[0][COLUNAS_DEZENAS].tolist() == list(range(1, 16))


# --- validar_base_estrita: casos INVALIDOS -- dezenas --------------------


def test_validar_base_estrita_rejeita_duplicata_interna() -> None:
    dezenas = [1, 1, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
    with pytest.raises(ValueError, match="resultado invalido"):
        br.validar_base_estrita(_df([_linha(1, dezenas=dezenas)]))


def test_validar_base_estrita_rejeita_dezena_zero() -> None:
    dezenas = [0, *range(2, 16)]
    with pytest.raises(ValueError, match="resultado invalido"):
        br.validar_base_estrita(_df([_linha(1, dezenas=dezenas)]))


def test_validar_base_estrita_rejeita_dezena_26() -> None:
    dezenas = [26, *range(2, 16)]
    with pytest.raises(ValueError, match="resultado invalido"):
        br.validar_base_estrita(_df([_linha(1, dezenas=dezenas)]))


def test_validar_base_estrita_rejeita_dezena_60() -> None:
    dezenas = [60, *range(2, 16)]
    with pytest.raises(ValueError, match="resultado invalido"):
        br.validar_base_estrita(_df([_linha(1, dezenas=dezenas)]))


def test_validar_base_estrita_rejeita_dezena_negativa() -> None:
    dezenas = [-1, *range(2, 16)]
    with pytest.raises(ValueError, match="resultado invalido"):
        br.validar_base_estrita(_df([_linha(1, dezenas=dezenas)]))


def test_validar_base_estrita_rejeita_float_inteiro_15_0() -> None:
    # O caso mais perigoso de aceitacao silenciosa: 15.0 "parece" 15, mas e
    # float, nao int -- deve ser rejeitado explicitamente, nao truncado.
    dezenas = [15.0, *range(2, 16)]
    with pytest.raises(ValueError, match="resultado invalido"):
        br.validar_base_estrita(_df([_linha(1, dezenas=dezenas)]))


def test_validar_base_estrita_rejeita_float_fracionario() -> None:
    dezenas = [3.5, *range(2, 16)]
    with pytest.raises(ValueError, match="resultado invalido"):
        br.validar_base_estrita(_df([_linha(1, dezenas=dezenas)]))


def test_validar_base_estrita_rejeita_string_nao_numerica() -> None:
    dezenas = ["abc", *range(2, 16)]
    with pytest.raises(ValueError, match="resultado invalido"):
        br.validar_base_estrita(_df([_linha(1, dezenas=dezenas)]))


def test_validar_base_estrita_rejeita_bool_como_dezena() -> None:
    dezenas = [True, *range(2, 16)]
    with pytest.raises(ValueError, match="resultado invalido"):
        br.validar_base_estrita(_df([_linha(1, dezenas=dezenas)]))


def test_validar_base_estrita_rejeita_none_como_dezena() -> None:
    dezenas = [None, *range(2, 16)]
    with pytest.raises(ValueError, match="resultado invalido"):
        br.validar_base_estrita(_df([_linha(1, dezenas=dezenas)]))


def test_validar_base_estrita_rejeita_linha_incompleta_14_dezenas() -> None:
    # Uma das 15 colunas Bola vem vazia/None -- "14 dezenas reais" disfarçadas
    # de 15 colunas.
    linha = _linha(1)
    linha["Bola15"] = None
    with pytest.raises(ValueError, match="resultado invalido"):
        br.validar_base_estrita(_df([linha]))


def test_validar_base_estrita_rejeita_estrutura_de_6_dezenas_mega_sena() -> None:
    # Simula semantica de outra loteria: so 6 dezenas relevantes, o resto
    # None -- deve ser rejeitado como resultado invalido, nunca aceito como
    # "jogo parcial".
    dezenas = [4, 9, 15, 23, 41, 55] + [None] * 9
    with pytest.raises(ValueError, match="resultado invalido"):
        br.validar_base_estrita(_df([_linha(1, dezenas=dezenas)]))


# --- validar_base_estrita: casos INVALIDOS -- concurso -------------------


def test_validar_base_estrita_rejeita_concurso_zero() -> None:
    with pytest.raises(ValueError, match="positivo"):
        br.validar_base_estrita(_df([_linha(0)]))


def test_validar_base_estrita_rejeita_concurso_negativo() -> None:
    with pytest.raises(ValueError, match="positivo"):
        br.validar_base_estrita(_df([_linha(-5)]))


def test_validar_base_estrita_rejeita_concurso_bool() -> None:
    with pytest.raises(ValueError, match="booleano"):
        br.validar_base_estrita(_df([_linha(True)]))


def test_validar_base_estrita_rejeita_concurso_string_nao_numerica() -> None:
    with pytest.raises(ValueError, match="Concurso"):
        br.validar_base_estrita(_df([_linha("abc")]))


def test_validar_base_estrita_rejeita_concurso_float() -> None:
    with pytest.raises(ValueError, match="Concurso"):
        br.validar_base_estrita(_df([_linha(1.5)]))


def test_validar_base_estrita_rejeita_concurso_string_numerica() -> None:
    # LF-03A: mesmo uma string puramente numerica ("1") e rejeitada pela
    # validacao CANONICA -- ela e aceita apenas pelo parser explicito de
    # fonte externa (_parse_inteiro_externo), executado antes de qualquer
    # valor chegar ao DataFrame candidato.
    with pytest.raises(ValueError, match="Concurso"):
        br.validar_base_estrita(_df([_linha("1")]))


def test_validar_base_estrita_rejeita_concurso_duplicado_fail_closed() -> None:
    # Duas linhas com o MESMO concurso, mesmo com dezenas diferentes --
    # nunca deve ser silenciosamente resolvido (ex.: keep=last); deve
    # invalidar o dataset inteiro.
    linhas = [
        _linha(5, dezenas=list(range(1, 16))),
        _linha(5, dezenas=list(range(2, 17))),
    ]
    with pytest.raises(ValueError, match="duplicado"):
        br.validar_base_estrita(_df(linhas))


def test_validar_base_estrita_rejeita_data_ausente() -> None:
    with pytest.raises(ValueError, match="Data"):
        br.validar_base_estrita(_df([_linha(1, data=None)]))


def test_validar_base_estrita_rejeita_data_nan() -> None:
    with pytest.raises(ValueError, match="Data"):
        br.validar_base_estrita(_df([_linha(1, data=float("nan"))]))


# --- validar_base_estrita: estrutura geral / gaps -------------------------


def test_validar_base_estrita_rejeita_coluna_obrigatoria_ausente() -> None:
    df_sem_data = pd.DataFrame([{"Concurso": 1, **{f"Bola{i}": i for i in range(1, 16)}}])
    with pytest.raises(ValueError, match="colunas obrigatorias"):
        br.validar_base_estrita(df_sem_data)


def test_validar_base_estrita_rejeita_dataset_vazio() -> None:
    with pytest.raises(ValueError, match="vazia"):
        br.validar_base_estrita(pd.DataFrame(columns=COLUNAS_OBRIGATORIAS))


def test_validar_base_estrita_rejeita_lacuna_na_sequencia_por_padrao() -> None:
    # Concursos 1, 2, 4 -- falta o 3. Contexto "base completa" (padrao):
    # deve invalidar o dataset inteiro.
    linhas = [_linha(1), _linha(2), _linha(4)]
    with pytest.raises(ValueError, match="lacuna"):
        br.validar_base_estrita(_df(linhas))


def test_validar_base_estrita_permite_lacuna_quando_fragmento_explicito() -> None:
    # Distincao explicita pedida no gate: um caller que declare
    # explicitamente estar validando um FRAGMENTO/janela parcial (nao a
    # serie historica completa) pode desligar a exigencia de continuidade
    # -- as demais checagens (tipo/unicidade/faixa/duplicidade) continuam
    # valendo incondicionalmente.
    linhas = [_linha(1), _linha(2), _linha(4)]
    resultado = br.validar_base_estrita(_df(linhas), exigir_sequencia_continua=False)
    assert resultado["Concurso"].tolist() == [1, 2, 4]


def test_validar_base_estrita_ainda_rejeita_duplicata_mesmo_sem_exigir_continuidade() -> None:
    linhas = [_linha(1), _linha(1, dezenas=list(range(2, 17)))]
    with pytest.raises(ValueError, match="duplicado"):
        br.validar_base_estrita(_df(linhas), exigir_sequencia_continua=False)


def test_validar_base_estrita_rejeita_dataset_com_uma_linha_invalida_entre_varias_validas() -> None:
    # Base majoritariamente valida + UMA linha contaminada -- o dataset
    # inteiro deve ser rejeitado (fail closed), nao filtrado/saneado.
    linhas = [_linha(1), _linha(2), _linha(3, dezenas=[60, *range(2, 16)]), _linha(4)]
    with pytest.raises(ValueError):
        br.validar_base_estrita(_df(linhas))


# --- baixar_base_oficial_completa: mocks de API CAIXA (Fase 9) ----------


def _mock_download_vazio(monkeypatch) -> None:
    """Forca o caminho de download em massa a falhar, para exercitar
    exclusivamente o loop por-concurso da API JSON nos testes abaixo."""
    monkeypatch.setattr(br, "_abrir_url_bytes", lambda *_a, **_k: (_ for _ in ()).throw(OSError("sem download em massa")))


def test_baixar_base_oficial_completa_aceita_resposta_valida(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(br, "CAMINHO_BASE_PADRAO", tmp_path / "historico.csv")
    _mock_download_vazio(monkeypatch)
    respostas = {
        br.API_CAIXA_LOTOFACIL_URL: {"numero": 2},
        f"{br.API_CAIXA_LOTOFACIL_URL}/1": {"numero": 1, "dataApuracao": "01/01/2026", "listaDezenas": list(range(1, 16))},
        f"{br.API_CAIXA_LOTOFACIL_URL}/2": {"numero": 2, "dataApuracao": "02/01/2026", "listaDezenas": list(range(2, 17))},
    }
    monkeypatch.setattr(br, "_abrir_url_json", lambda url, **_k: respostas[url])
    base = br.baixar_base_oficial_completa()
    assert base["Concurso"].tolist() == [1, 2]


def test_baixar_base_oficial_completa_aceita_resposta_com_strings_numericas_legitimas(monkeypatch, tmp_path) -> None:
    """Fase 3D: resposta CAIXA sintetica com concurso e dezenas serializados
    como texto (formato documentado da API) -- prova o pipeline completo:
    parser explicito (_parse_inteiro_externo) converte para inteiros
    canonicos ANTES da construcao do DataFrame, validar_base_estrita (que
    ja NAO aceita mais string) recebe apenas inteiros e aprova."""
    monkeypatch.setattr(br, "CAMINHO_BASE_PADRAO", tmp_path / "historico.csv")
    _mock_download_vazio(monkeypatch)
    respostas = {
        br.API_CAIXA_LOTOFACIL_URL: {"numero": 1},
        f"{br.API_CAIXA_LOTOFACIL_URL}/1": {
            "numero": "01",
            "dataApuracao": "01/01/2026",
            "listaDezenas": [f"{d:02d}" for d in range(1, 16)],
        },
    }
    monkeypatch.setattr(br, "_abrir_url_json", lambda url, **_k: respostas[url])
    base = br.baixar_base_oficial_completa()
    assert base["Concurso"].tolist() == [1]
    assert base.iloc[0][COLUNAS_DEZENAS].tolist() == list(range(1, 16))
    assert base["Concurso"].dtype == int or str(base["Concurso"].dtype).startswith("int")


def test_baixar_base_oficial_completa_rejeita_resposta_com_14_dezenas(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(br, "CAMINHO_BASE_PADRAO", tmp_path / "historico.csv")
    _mock_download_vazio(monkeypatch)
    respostas = {
        br.API_CAIXA_LOTOFACIL_URL: {"numero": 1},
        f"{br.API_CAIXA_LOTOFACIL_URL}/1": {"numero": 1, "dataApuracao": "01/01/2026", "listaDezenas": list(range(1, 15))},
    }
    monkeypatch.setattr(br, "_abrir_url_json", lambda url, **_k: respostas[url])
    with pytest.raises(ValueError, match="resultado invalido"):
        br.baixar_base_oficial_completa()


def test_baixar_base_oficial_completa_rejeita_resposta_com_16_dezenas_sem_truncar(monkeypatch, tmp_path) -> None:
    # Regressao especifica LF-03/Fase R4: 16 dezenas NUNCA deve ser
    # silenciosamente truncado para as primeiras 15.
    monkeypatch.setattr(br, "CAMINHO_BASE_PADRAO", tmp_path / "historico.csv")
    _mock_download_vazio(monkeypatch)
    respostas = {
        br.API_CAIXA_LOTOFACIL_URL: {"numero": 1},
        f"{br.API_CAIXA_LOTOFACIL_URL}/1": {"numero": 1, "dataApuracao": "01/01/2026", "listaDezenas": list(range(1, 17))},
    }
    monkeypatch.setattr(br, "_abrir_url_json", lambda url, **_k: respostas[url])
    with pytest.raises(ValueError, match="resultado invalido"):
        br.baixar_base_oficial_completa()


def test_baixar_base_oficial_completa_fallback_seguro_em_erro_http(monkeypatch, tmp_path) -> None:
    # Erro HTTP na PRIMEIRA chamada (consulta do concurso atual) deve
    # propagar (nao ha o que "baixar" sem saber o concurso mais recente) --
    # nenhuma escrita, nenhum candidato invalido persistido.
    monkeypatch.setattr(br, "CAMINHO_BASE_PADRAO", tmp_path / "historico.csv")
    monkeypatch.setattr(br, "_abrir_url_json", lambda *_a, **_k: (_ for _ in ()).throw(TimeoutError("egress indisponivel")))
    with pytest.raises(TimeoutError):
        br.baixar_base_oficial_completa()


def test_baixar_base_oficial_completa_rejeita_json_incompleto_sem_dezenas(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(br, "CAMINHO_BASE_PADRAO", tmp_path / "historico.csv")
    _mock_download_vazio(monkeypatch)
    respostas = {
        br.API_CAIXA_LOTOFACIL_URL: {"numero": 1},
        f"{br.API_CAIXA_LOTOFACIL_URL}/1": {"numero": 1, "dataApuracao": "01/01/2026"},  # sem listaDezenas
    }
    monkeypatch.setattr(br, "_abrir_url_json", lambda url, **_k: respostas[url])
    with pytest.raises(ValueError, match="sem dezenas"):
        br.baixar_base_oficial_completa()


def test_baixar_base_oficial_completa_rejeita_semantica_de_outra_loteria(monkeypatch, tmp_path) -> None:
    # Resposta com 6 dezenas em 1..60 (padrao Mega-Sena) -- deve ser
    # rejeitada pelo contrato LF-02 (validar_resultado), nao aceita como um
    # "jogo diferente".
    monkeypatch.setattr(br, "CAMINHO_BASE_PADRAO", tmp_path / "historico.csv")
    _mock_download_vazio(monkeypatch)
    respostas = {
        br.API_CAIXA_LOTOFACIL_URL: {"numero": 1},
        f"{br.API_CAIXA_LOTOFACIL_URL}/1": {
            "numero": 1,
            "dataApuracao": "01/01/2026",
            "listaDezenas": [4, 9, 15, 23, 41, 55],
        },
    }
    monkeypatch.setattr(br, "_abrir_url_json", lambda url, **_k: respostas[url])
    with pytest.raises(ValueError, match="resultado invalido"):
        br.baixar_base_oficial_completa()


def test_nenhum_teste_desta_suite_faz_chamada_de_rede_real(monkeypatch) -> None:
    """Guarda de regressao: garante que `urlopen` (unico ponto de saida
    HTTP do modulo) nunca e chamado de verdade por nenhum teste desta
    bateria -- todos usam monkeypatch em `_abrir_url_json`/`_abrir_url_bytes`."""
    chamadas = []
    monkeypatch.setattr(br, "urlopen", lambda *a, **k: chamadas.append((a, k)))
    # Nenhuma chamada real e feita aqui; este teste apenas documenta e
    # prova que o ponto de bloqueio existe e e o unico (mesmo padrao do
    # isolamento LF-01A).
    assert chamadas == []


# --- atualizar_base_local: write safety (Fase 7/8) ------------------------


def test_atualizar_base_local_preserva_base_quando_candidato_invalido(monkeypatch, tmp_path) -> None:
    destino = tmp_path / "lotofacil_historico.csv"
    conteudo_original = b"Concurso,Data,Bola1\n1,01/01/2026,5\n"
    destino.write_bytes(conteudo_original)
    hash_antes = _sha256(destino)

    monkeypatch.setattr(br, "CAMINHO_BASE_PADRAO", destino)
    monkeypatch.setattr(
        br,
        "baixar_base_oficial_completa",
        lambda: (_ for _ in ()).throw(ValueError("Concurso 1: resultado invalido -- simulado")),
    )

    assert br.atualizar_base_local() is False
    assert destino.read_bytes() == conteudo_original
    assert _sha256(destino) == hash_antes
    assert not destino.with_suffix(".csv.tmp").exists()


def test_atualizar_base_local_writer_nao_confia_apenas_no_downloader(monkeypatch, tmp_path) -> None:
    """Fase 3E (defesa em profundidade): o WRITER tem sua PROPRIA barreira
    de validacao, independente da que baixar_base_oficial_completa ja
    aplica. Aqui o downloader e mockado para devolver um DataFrame
    diretamente INVALIDO (dezena 60, fora de 1..25) SEM levantar excecao --
    simula um caller futuro cuja validacao interna quebrou/mudou. O writer
    ainda assim precisa rejeitar, sem escrever nada e sem chamar replace."""
    destino = tmp_path / "lotofacil_historico.csv"
    conteudo_original = b"Concurso,Data,Bola1\n1,01/01/2026,5\n"
    destino.write_bytes(conteudo_original)
    hash_antes = _sha256(destino)

    dataframe_invalido = pd.DataFrame(
        [_linha(1, dezenas=[60, *range(2, 16)])], columns=COLUNAS_OBRIGATORIAS
    )
    monkeypatch.setattr(br, "CAMINHO_BASE_PADRAO", destino)
    monkeypatch.setattr(br, "baixar_base_oficial_completa", lambda: dataframe_invalido)

    temporario_esperado = destino.with_suffix(destino.suffix + ".tmp")
    assert br.atualizar_base_local() is False
    assert destino.read_bytes() == conteudo_original
    assert _sha256(destino) == hash_antes
    assert not temporario_esperado.exists()  # open()/to_csv() nunca chegou a ser executado


def test_atualizar_base_local_so_persiste_apos_validacao_completa_bem_sucedida(monkeypatch, tmp_path) -> None:
    destino = tmp_path / "lotofacil_historico.csv"
    destino.write_bytes(b"Concurso,Data,Bola1\n1,01/01/2026,5\n")

    dados_validos = pd.DataFrame([_linha(1)], columns=COLUNAS_OBRIGATORIAS)
    monkeypatch.setattr(br, "CAMINHO_BASE_PADRAO", destino)
    monkeypatch.setattr(br, "baixar_base_oficial_completa", lambda: dados_validos)

    assert br.atualizar_base_local() is True
    persistido = pd.read_csv(destino, encoding="utf-8-sig")
    assert persistido["Concurso"].tolist() == [1]
    assert not destino.with_suffix(".csv.tmp").exists()


def test_atualizar_base_local_preserva_base_em_falha_de_fsync(monkeypatch, tmp_path) -> None:
    """Prova de atomicidade no ponto de falha introduzido nesta gate
    (fsync): mesmo que a escrita do temporario tenha comecado, uma falha no
    fsync ainda preserva o arquivo oficial anterior intacto."""
    destino = tmp_path / "lotofacil_historico.csv"
    conteudo_original = b"Concurso,Data,Bola1\n1,01/01/2026,5\n"
    destino.write_bytes(conteudo_original)
    hash_antes = _sha256(destino)

    dados_validos = pd.DataFrame([_linha(1)], columns=COLUNAS_OBRIGATORIAS)
    monkeypatch.setattr(br, "CAMINHO_BASE_PADRAO", destino)
    monkeypatch.setattr(br, "baixar_base_oficial_completa", lambda: dados_validos)
    monkeypatch.setattr(br.os, "fsync", lambda *_a, **_k: (_ for _ in ()).throw(OSError("falha de fsync simulada")))

    assert br.atualizar_base_local() is False
    assert destino.read_bytes() == conteudo_original
    assert _sha256(destino) == hash_antes
    assert not destino.with_suffix(".csv.tmp").exists()
