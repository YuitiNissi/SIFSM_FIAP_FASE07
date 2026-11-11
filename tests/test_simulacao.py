"""Testes da simulação, da integração numérica e da regressão linear.

Executar:  python -m pytest tests/test_simulacao.py -v
"""

import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import regressao_linear as rl  # noqa: E402
import resultados_simulacao as rs  # noqa: E402
import simulacao_energia as sim  # noqa: E402

PARAMS_RAPIDOS = replace(sim.ParametrosSimulacao(), n_sois=20, tempestade_inicio_sol=10,
                         tempestade_duracao_sois=3)


# --- Integração numérica ---------------------------------------------------
def test_trapezio_e_exato_para_funcao_linear():
    t = np.linspace(0, 10, 11)
    assert sim.integrar_trapezio(2 * t + 1, 1.0) == pytest.approx(110.0)  # ∫(2t+1) = t²+t


def test_trapezio_aproxima_integral_do_seno():
    t = np.linspace(0, np.pi, 1001)
    assert sim.integrar_trapezio(np.sin(t), t[1] - t[0]) == pytest.approx(2.0, abs=1e-5)


def test_trapezio_converge_mais_rapido_que_retangulos():
    erros_trap, erros_ret = [], []
    for n in (11, 21, 41):
        t = np.linspace(0, 1, n)
        exata = np.e - 1  # ∫_0^1 e^t dt
        erros_trap.append(abs(sim.integrar_trapezio(np.exp(t), t[1] - t[0]) - exata))
        erros_ret.append(abs(sim.integrar_retangulos(np.exp(t), t[1] - t[0]) - exata))
    # dividir o passo por 2 => erro /4 no trapézio (ordem 2) e /2 nos retângulos (ordem 1)
    assert erros_trap[0] / erros_trap[1] == pytest.approx(4, rel=0.05)
    assert erros_ret[0] / erros_ret[1] == pytest.approx(2, rel=0.1)


def test_acumulado_termina_na_integral_total():
    y = np.random.default_rng(0).random(50)
    acumulado = sim.acumular_trapezio(y, 0.5)
    assert acumulado[0] == 0
    assert acumulado[-1] == pytest.approx(sim.integrar_trapezio(y, 0.5))
    assert np.all(np.diff(acumulado) >= 0)  # potência positiva => energia nunca diminui


def test_integracao_com_menos_de_dois_pontos_e_zero():
    assert sim.integrar_trapezio([5.0], 1.0) == 0.0
    assert sim.integrar_retangulos([], 1.0) == 0.0


# --- Simulação --------------------------------------------------------------
@pytest.fixture(scope="module")
def simulacao():
    return sim.simular(PARAMS_RAPIDOS)


def test_simulacao_e_reprodutivel(simulacao):
    serie, _ = simulacao
    serie2, _ = sim.simular(PARAMS_RAPIDOS)
    pd.testing.assert_frame_equal(serie, serie2)


def test_bateria_respeita_limites(simulacao):
    serie, _ = simulacao
    assert serie["soc"].between(0, 1).all()


def test_energia_diaria_bate_com_total(simulacao):
    serie, diario = simulacao
    total = sim.integrar_trapezio(serie["consumo_kw"], PARAMS_RAPIDOS.dt_h)
    assert diario["consumo_kwh"].sum() == pytest.approx(total)
    assert len(diario) == PARAMS_RAPIDOS.n_sois


def test_tempestade_reduz_geracao(simulacao):
    _, diario = simulacao
    medias = diario.groupby("tempestade")["geracao_solar_kwh"].mean()
    assert medias[True] < 0.5 * medias[False]


def test_regra_booleana_de_alerta(simulacao):
    serie, _ = simulacao
    esperado = (serie["soc"] < PARAMS_RAPIDOS.limite_alerta_soc) | (serie["energia_nao_suprida_kwh"] > 0)
    assert (serie["alerta_energia"] == esperado).all()


def test_alerta_energia_tabela_verdade():
    # (bateria baixa, falta de energia) -> alerta
    assert rs.alerta_energia(0.10, 0) is True
    assert rs.alerta_energia(0.50, 5) is True
    assert rs.alerta_energia(0.10, 5) is True
    assert rs.alerta_energia(0.50, 0) is False


def test_modulo_sem_campos_obrigatorios(tmp_path):
    arquivo = tmp_path / "modulos.json"
    arquivo.write_text('[{"nome": "X", "tipo": "HABITACAO"}]', encoding="utf-8")
    with pytest.raises(ValueError):
        sim.carregar_modulos(arquivo)


def test_arquivo_de_modulos_inexistente(tmp_path):
    with pytest.raises(FileNotFoundError):
        sim.carregar_modulos(tmp_path / "nao_existe.json")


def test_simulacao_sem_modulos():
    with pytest.raises(ValueError):
        sim.simular(PARAMS_RAPIDOS, modulos=[])


# --- Regressão linear -------------------------------------------------------
def test_regressao_recupera_coeficientes_conhecidos():
    rng = np.random.default_rng(1)
    dados = pd.DataFrame({"x1": rng.normal(0, 1, 200), "x2": rng.normal(5, 2, 200)})
    dados["y"] = 10 + 3 * dados["x1"] - 2 * dados["x2"] + rng.normal(0, 0.1, 200)
    modelo = rl.ajustar(dados, ["x1", "x2"], "y")
    assert modelo.intercepto == pytest.approx(10, abs=0.1)
    assert modelo.coeficientes["x1"] == pytest.approx(3, abs=0.05)
    assert modelo.coeficientes["x2"] == pytest.approx(-2, abs=0.05)
    assert rl.metricas(dados["y"], modelo.prever(dados))["r2"] > 0.99


def test_regressao_simples_igual_ao_polyfit():
    x = np.arange(10, dtype=float)
    y = 3 * x + 7 + np.sin(x)
    modelo = rl.ajustar(pd.DataFrame({"x": x, "y": y}), ["x"], "y")
    inclinacao, intercepto = np.polyfit(x, y, 1)
    assert modelo.coeficientes["x"] == pytest.approx(inclinacao)
    assert modelo.intercepto == pytest.approx(intercepto)


def test_metricas_previsao_perfeita():
    m = rl.metricas([1, 2, 3], [1, 2, 3])
    assert m["r2"] == 1 and m["rmse"] == 0 and m["mae"] == 0


def test_regressao_com_poucas_observacoes():
    with pytest.raises(ValueError):
        rl.ajustar(pd.DataFrame({"x": [1, 2], "y": [1, 2]}), ["x"], "y")


def test_divisao_treino_teste_sem_sobreposicao():
    dados = pd.DataFrame({"a": range(100)})
    treino, teste = rl.dividir_treino_teste(dados, 0.2, semente=3)
    assert len(teste) == 20 and len(treino) == 80
    assert set(treino.index).isdisjoint(teste.index)


def test_estimar_consumo_usa_equacao_do_modelo():
    resultados = {"regressao": {"intercepto": 100.0,
                                "coeficientes": {"temp_media_c": -2.0, "tripulantes": 10.0}}}
    assert rs.estimar_consumo_diario(-50, 4, resultados) == pytest.approx(100 + 100 + 40)
