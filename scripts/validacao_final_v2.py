from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from urllib.error import URLError

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from streamlit.testing.v1 import AppTest

import src.carregar_dados as dados_modulo
from src.carregar_dados import CAMINHO_BASE_PADRAO, carregar_base
from src.backtest_lotofacil import executar_backtest_comparativo
from src.jogos_salvos import conferir_jogos_salvos, ler_jogos_salvos, salvar_carteira
from src.motor_elite_v2 import gerar_jogos_v2
from src.validacao_jogos import ConfiguracaoMotor, validar_carteira


def hash_arquivo(caminho: Path) -> str:
    return sha256(caminho.read_bytes()).hexdigest()


def executar() -> dict:
    base = carregar_base(CAMINHO_BASE_PADRAO)
    config = ConfiguracaoMotor(candidatos_por_perfil=120)
    jogos = gerar_jogos_v2(base, configuracao=config, semente=20260620)
    carteira = [[int(row[f"Bola{i}"]) for i in range(1, 16)] for _, row in jogos.iterrows()]
    ultimo = [int(base.iloc[-1][f"Bola{i}"]) for i in range(1, 16)]
    validar_carteira(carteira, config, ultimo)

    backtests_quantidades = {}
    amostra_backtest = base.tail(115).reset_index(drop=True)
    for quantidade in (5, 10, 20, 30):
        comparativo = executar_backtest_comparativo(
            amostra_backtest,
            quantidade_concursos=1,
            quantidade_jogos=quantidade,
            historico_minimo=100,
            configuracao=ConfiguracaoMotor(candidatos_por_perfil=60),
            candidatos_por_perfil=60,
        )
        backtests_quantidades[str(quantidade)] = bool(
            set(comparativo.resumo["Motor"]) == {"Motor Elite", "Aleatório"}
            and comparativo.detalhes["Quantidade de jogos"].eq(quantidade).all()
        )

    with TemporaryDirectory() as pasta:
        caminho = Path(pasta) / "carteira.csv"
        concurso = int(base.iloc[-1]["Concurso"])
        salvar_carteira(jogos, 1, concurso, caminho)
        salvos = ler_jogos_salvos(caminho)
        conferidos = conferir_jogos_salvos(base, caminho)
        carteira_ok = len(salvos) == 5 and set(conferidos["Status"]) == {"CONFERIDO"}

    hash_antes = hash_arquivo(CAMINHO_BASE_PADRAO)
    download_original = dados_modulo.baixar_base_oficial_completa
    try:
        dados_modulo.baixar_base_oficial_completa = lambda: (_ for _ in ()).throw(URLError("falha simulada"))
        retorno_atualizacao = dados_modulo.atualizar_base_local()
    finally:
        dados_modulo.baixar_base_oficial_completa = download_original
    hash_depois = hash_arquivo(CAMINHO_BASE_PADRAO)

    app = AppTest.from_file("app.py").run(timeout=90)
    abas = [item.label for item in app.tabs]
    html = "\n".join(item.value for item in app.markdown)
    downloads_iniciais = [item.label for item in app.get("download_button")]
    exports_estrategia = {
        "CSV": "EXPORTAR ESTRATÉGIA CSV" in downloads_iniciais,
        "TXT": "EXPORTAR ESTRATÉGIA TXT" in downloads_iniciais,
    }

    next(item for item in app.button if item.label == "GERAR / ATUALIZAR CARTEIRA").click().run(timeout=90)
    html_gerado = "\n".join(item.value for item in app.markdown)

    app.selectbox[0].select("30").run(timeout=150)
    next(item for item in app.button if item.label == "GERAR / ATUALIZAR CARTEIRA").click().run(timeout=150)
    html_expandido = "\n".join(item.value for item in app.markdown)
    custo_30_ok = any("R$ 105.00" in item.value for item in app.caption)

    app.slider[0].set_value(10)
    app.slider[1].set_value(100)
    app.selectbox[1].set_value(10)
    next(item for item in app.button if item.label == "EXECUTAR BACKTEST").click().run(timeout=240)
    downloads_backtest = [item.label for item in app.get("download_button")]
    backtest_ok = any("Melhor perfil" in item.value for item in app.success)

    next(item for item in app.button if item.label == "CONFERIR JOGOS SALVOS").click().run(timeout=90)
    ranking_ok = any("Score da dezena" in tabela.value.columns for tabela in app.dataframe)

    esperado_abas = ["Gerar Jogos", "Estratégia Inteligente", "Backtest", "Conferir Jogos", "Ranking das Dezenas", "Configurações"]
    resultado = {
        "abas": abas,
        "abas_ok": abas == esperado_abas,
        "sem_excecoes_streamlit": len(app.exception) == 0,
        "jogos_html": html_gerado.count('class="elite-game-card"'),
        "dezenas_html": html_gerado.count('class="elite-ball"'),
        "jogos_html_30": html_expandido.count('class="elite-game-card"'),
        "dezenas_html_30": html_expandido.count('class="elite-ball"'),
        "carteira_30_jogos_ok": html_expandido.count('class="elite-game-card"') == 30 and html_expandido.count('class="elite-ball"') == 450,
        "custo_estimado_30_ok": custo_30_ok,
        "backtest_quantidades": backtests_quantidades,
        "backtest_5_10_20_30_ok": all(backtests_quantidades.values()),
        "jogos_validos": len(carteira) == 5 and all(len(jogo) == len(set(jogo)) == 15 for jogo in carteira),
        "csv_jogos_disponivel": "DOWNLOAD CSV" in downloads_iniciais,
        "csv_backtest_disponivel": "EXPORTAR RELATÓRIO DE BACKTEST CSV" in downloads_backtest,
        "exports_estrategia": exports_estrategia,
        "exports_estrategia_ok": all(exports_estrategia.values()),
        "salvar_e_conferir_ok": carteira_ok,
        "backtest_ok": backtest_ok,
        "ranking_ok": ranking_ok,
        "configuracoes_ok": any(item.label == "ATUALIZAR BASE OFICIAL" for item in app.button),
        "estrategia_inteligente_ok": any(item.label == "Melhor perfil do dia" for item in app.metric),
        "falha_atualizacao_preserva_base": retorno_atualizacao is False and hash_antes == hash_depois,
        "aviso_responsavel": "sem garantia de prêmio" in html.lower(),
    }
    if not all(valor for chave, valor in resultado.items() if chave.endswith("_ok") or chave in {"sem_excecoes_streamlit", "jogos_validos", "csv_jogos_disponivel", "csv_backtest_disponivel", "salvar_e_conferir_ok", "falha_atualizacao_preserva_base", "aviso_responsavel"}):
        raise AssertionError(f"Validação final incompleta: {resultado}")
    return resultado


if __name__ == "__main__":
    print(json.dumps(executar(), ensure_ascii=False, indent=2))
