"""
Simulação do balanço energético da colônia SIFSM em Marte.

Fenômeno simulado
-----------------
Consumo e geração de energia da colônia ao longo de vários sóis (dias marcianos).
A cada passo de tempo calculamos:

* a temperatura externa (ciclo diário + variação sazonal + ruído);
* a potência consumida por cada módulo cadastrado no sistema (carga base,
  aquecimento para manter a temperatura interna e carga da tripulação);
* a potência gerada (painéis solares + reator de fissão);
* a energia armazenada na bateria, obtida por ACUMULAÇÃO (integração numérica)
  do saldo entre geração e consumo.

Conceito matemático
-------------------
Energia é a integral da potência no tempo:  E = ∫ P(t) dt.
Como só conhecemos P(t) em instantes discretos, usamos a regra dos trapézios:

    E ≈ Σ (P[k] + P[k+1]) / 2 · Δt

As funções `integrar_trapezio`, `integrar_retangulos` e `acumular_trapezio`
implementam isso "à mão" (sem depender de bibliotecas) para fins didáticos.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ_PROJETO = Path(__file__).resolve().parents[1]
ARQUIVO_MODULOS = RAIZ_PROJETO / "data" / "dados_teste.json"

SOL_HORAS = 24.66  # duração de um sol (dia marciano), em horas
HORA_NASCER_SOL = 6.17  # o "dia" ocupa metade do sol
DURACAO_DIA_H = SOL_HORAS / 2
HORA_ACORDAR = 7.0  # tripulação acordada entre 7h e 23h (horário local)
HORA_DORMIR = 23.0


# ---------------------------------------------------------------------------
# Parâmetros (variáveis de entrada e hipóteses)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ParametrosSimulacao:
    """Variáveis de entrada da simulação. Todos os valores são didáticos."""

    # Tempo
    n_sois: int = 120
    dt_h: float = 0.25  # passo de 15 minutos
    semente: int = 42  # torna a simulação reprodutível

    # Ambiente marciano
    temp_ext_media_c: float = -60.0
    temp_ext_amplitude_sazonal_c: float = 12.0
    temp_ext_amplitude_diaria_c: float = 35.0
    ruido_temp_sol_c: float = 3.0
    irradiancia_pico_w_m2: float = 500.0

    # Tempestade de poeira
    tempestade_inicio_sol: int = 70
    tempestade_duracao_sois: int = 10
    opacidade_tempestade: float = 0.65  # fração da luz solar bloqueada
    aquecimento_tempestade_c: float = 5.0  # a poeira retém calor à noite

    # Consumo dos módulos
    coef_aquecimento_kw_por_c: float = 0.35  # perda térmica por módulo (kW/°C)
    fator_manutencao: float = 0.6  # módulo em manutenção opera com 60% da carga
    kw_por_tripulante: float = 2.5  # suporte de vida + equipamentos, acordado
    tripulantes_min: int = 6
    tripulantes_max: int = 14
    dias_por_turno: int = 5  # a tripulação muda a cada 5 sóis
    ruido_operacional_sol: float = 0.025  # variação diária da carga base (2,5%)
    ruido_consumo_passo: float = 0.03  # flutuação a cada passo (3%)

    # Geração
    area_paineis_m2: float = 7000.0
    eficiencia_paineis: float = 0.22
    reator_kw: float = 40.0

    # Bateria
    bateria_capacidade_kwh: float = 6000.0
    bateria_soc_inicial: float = 0.6
    limite_alerta_soc: float = 0.20  # alerta abaixo de 20% de carga


# ---------------------------------------------------------------------------
# Integração numérica (conceito matemático central)
# ---------------------------------------------------------------------------
def integrar_trapezio(valores, dt: float) -> float:
    """Integral de uma série amostrada com passo constante (regra dos trapézios)."""
    y = np.asarray(valores, dtype=float)
    if y.size < 2:
        return 0.0
    return float(dt * (y[0] / 2 + y[1:-1].sum() + y[-1] / 2))


def integrar_retangulos(valores, dt: float) -> float:
    """Soma de Riemann à esquerda — usada para comparar com o trapézio."""
    y = np.asarray(valores, dtype=float)
    if y.size < 2:
        return 0.0
    return float(dt * y[:-1].sum())


def energia_por_passo(valores, dt: float) -> np.ndarray:
    """Energia de cada intervalo [k, k+1] pela regra dos trapézios.

    O último elemento é zero (não há intervalo depois da última amostra),
    assim o vetor tem o mesmo tamanho da série original.
    """
    y = np.asarray(valores, dtype=float)
    passos = np.zeros_like(y)
    passos[:-1] = (y[:-1] + y[1:]) / 2 * dt
    return passos


def acumular_trapezio(valores, dt: float) -> np.ndarray:
    """Integral acumulada: E(t_k) = ∫_0^{t_k} P(t) dt, com E(t_0) = 0."""
    passos = energia_por_passo(valores, dt)
    acumulado = np.zeros_like(passos)
    acumulado[1:] = np.cumsum(passos[:-1])
    return acumulado


# ---------------------------------------------------------------------------
# Dados de entrada vindos do sistema principal
# ---------------------------------------------------------------------------
def carregar_modulos(caminho: Path | str = ARQUIVO_MODULOS) -> list[dict]:
    """Lê os módulos cadastrados (mesmo formato da tabela MODULOS)."""
    try:
        with open(caminho, encoding="utf-8") as arquivo:
            modulos = json.load(arquivo)
    except FileNotFoundError as erro:
        raise FileNotFoundError(f"Arquivo de módulos não encontrado: {caminho}") from erro
    except json.JSONDecodeError as erro:
        raise ValueError(f"Arquivo de módulos com JSON inválido: {caminho}") from erro

    campos = {"nome", "tipo", "consumo_kwh", "temperatura_c", "status"}
    for modulo in modulos:
        faltando = campos - modulo.keys()
        if faltando:
            raise ValueError(f"Módulo {modulo.get('nome', '?')} sem os campos {sorted(faltando)}")
    return modulos


# ---------------------------------------------------------------------------
# Modelo físico simplificado
# ---------------------------------------------------------------------------
def _perfil_sazonal(sol: np.ndarray, p: ParametrosSimulacao) -> np.ndarray:
    """Varia de -1 a 1 ao longo do período simulado (estação fria → quente)."""
    return np.sin(2 * np.pi * sol / p.n_sois - np.pi / 2)


def _sorteios_por_sol(p: ParametrosSimulacao, rng: np.random.Generator) -> pd.DataFrame:
    """Valores aleatórios que mudam uma vez por sol (ou por turno)."""
    sois = np.arange(p.n_sois)
    em_tempestade = (sois >= p.tempestade_inicio_sol) & (
        sois < p.tempestade_inicio_sol + p.tempestade_duracao_sois
    )

    temp_media = (
        p.temp_ext_media_c
        + p.temp_ext_amplitude_sazonal_c * _perfil_sazonal(sois, p)
        + rng.normal(0, p.ruido_temp_sol_c, p.n_sois)
        + np.where(em_tempestade, p.aquecimento_tempestade_c, 0.0)
    )

    n_turnos = int(np.ceil(p.n_sois / p.dias_por_turno))
    tripulantes_turno = rng.integers(p.tripulantes_min, p.tripulantes_max + 1, n_turnos)
    tripulantes = np.repeat(tripulantes_turno, p.dias_por_turno)[: p.n_sois]

    return pd.DataFrame(
        {
            "sol": sois,
            "temp_media_sol_c": temp_media,
            "tripulantes": tripulantes,
            "tempestade": em_tempestade,
            "opacidade": np.where(em_tempestade, p.opacidade_tempestade, 0.0),
            "fator_operacional": 1 + rng.normal(0, p.ruido_operacional_sol, p.n_sois),
        }
    )


def simular(
    parametros: ParametrosSimulacao | None = None,
    modulos: list[dict] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Executa a simulação.

    Retorna
    -------
    serie : DataFrame com um registro por passo de tempo (dt_h).
    diario : DataFrame com um registro por sol (energias já integradas).
    """
    p = parametros or ParametrosSimulacao()
    modulos = modulos if modulos is not None else carregar_modulos()
    if p.n_sois <= 0 or p.dt_h <= 0:
        raise ValueError("n_sois e dt_h devem ser positivos.")
    if not modulos:
        raise ValueError("É necessário ao menos um módulo para simular.")

    rng = np.random.default_rng(p.semente)
    por_sol = _sorteios_por_sol(p, rng)

    tempo = np.arange(0, p.n_sois * SOL_HORAS, p.dt_h)
    sol = np.minimum((tempo // SOL_HORAS).astype(int), p.n_sois - 1)
    hora = tempo - sol * SOL_HORAS

    diario_sorteado = por_sol.set_index("sol").loc[sol]
    em_tempestade = diario_sorteado["tempestade"].to_numpy()
    opacidade = diario_sorteado["opacidade"].to_numpy()
    tripulantes = diario_sorteado["tripulantes"].to_numpy()
    fator_oper = diario_sorteado["fator_operacional"].to_numpy()

    # Temperatura externa: pico no meio da tarde; tempestade reduz a amplitude.
    amplitude = p.temp_ext_amplitude_diaria_c * np.where(em_tempestade, 0.5, 1.0)
    temp_ext = diario_sorteado["temp_media_sol_c"].to_numpy() + amplitude * np.sin(
        2 * np.pi * (hora - 9.0) / SOL_HORAS
    )

    # Irradiância solar: meia senoide durante o dia, atenuada pela poeira.
    fase_dia = (hora - HORA_NASCER_SOL) / DURACAO_DIA_H
    sazonal_luz = 1 + 0.08 * _perfil_sazonal(sol, p)
    irradiancia = (
        p.irradiancia_pico_w_m2
        * np.clip(np.sin(np.pi * fase_dia), 0, None)
        * ((fase_dia >= 0) & (fase_dia <= 1))
        * sazonal_luz
        * (1 - opacidade)
    )

    acordados = (hora >= HORA_ACORDAR) & (hora < HORA_DORMIR)

    # Potência de cada módulo (kW)
    serie = {
        "tempo_h": tempo,
        "sol": sol,
        "hora_sol": hora,
        "temp_ext_c": temp_ext,
        "irradiancia_w_m2": irradiancia,
        "tripulantes": tripulantes,
        "tempestade": em_tempestade,
    }
    consumo_total = np.zeros_like(tempo)
    for modulo in modulos:
        fator_status = p.fator_manutencao if modulo["status"].upper() == "MANUTENCAO" else 1.0
        if modulo["status"].upper() == "INATIVO":
            fator_status = 0.0
        base = float(modulo["consumo_kwh"]) * fator_status * fator_oper
        aquecimento = p.coef_aquecimento_kw_por_c * np.clip(
            float(modulo["temperatura_c"]) - temp_ext, 0, None
        )
        carga_tripulacao = 0.0
        if modulo["tipo"].upper() == "HABITACAO":
            carga_tripulacao = p.kw_por_tripulante * tripulantes * acordados
        ruido = 1 + rng.normal(0, p.ruido_consumo_passo, tempo.size)
        potencia = np.clip((base + aquecimento + carga_tripulacao) * ruido, 0, None)

        serie[f"potencia_{modulo['tipo'].lower()}_kw"] = potencia
        consumo_total += potencia

    geracao_solar = irradiancia * p.area_paineis_m2 * p.eficiencia_paineis / 1000  # W → kW
    geracao_total = geracao_solar + p.reator_kw
    saldo = geracao_total - consumo_total

    # Bateria: acumulação do saldo (trapézio), limitada entre 0 e a capacidade.
    energia_saldo = energia_por_passo(saldo, p.dt_h)
    energia_bateria = np.empty_like(tempo)
    nao_suprida = np.zeros_like(tempo)
    desperdicada = np.zeros_like(tempo)
    carga = p.bateria_soc_inicial * p.bateria_capacidade_kwh
    for k in range(tempo.size):
        energia_bateria[k] = carga
        proxima = carga + energia_saldo[k]
        if proxima < 0:
            nao_suprida[k] = -proxima
            proxima = 0.0
        elif proxima > p.bateria_capacidade_kwh:
            desperdicada[k] = proxima - p.bateria_capacidade_kwh
            proxima = p.bateria_capacidade_kwh
        carga = proxima

    soc = energia_bateria / p.bateria_capacidade_kwh
    serie.update(
        {
            "consumo_kw": consumo_total,
            "geracao_solar_kw": geracao_solar,
            "geracao_total_kw": geracao_total,
            "saldo_kw": saldo,
            "consumo_acumulado_kwh": acumular_trapezio(consumo_total, p.dt_h),
            "energia_bateria_kwh": energia_bateria,
            "soc": soc,
            "energia_nao_suprida_kwh": nao_suprida,
            "energia_desperdicada_kwh": desperdicada,
            # Regra booleana de alerta: bateria baixa OU houve falta de energia.
            "alerta_energia": (soc < p.limite_alerta_soc) | (nao_suprida > 0),
        }
    )
    serie = pd.DataFrame(serie)

    diario = resumir_por_sol(serie, por_sol, p)
    return serie, diario


def resumir_por_sol(
    serie: pd.DataFrame, por_sol: pd.DataFrame, p: ParametrosSimulacao
) -> pd.DataFrame:
    """Agrega a série temporal em indicadores diários (um registro por sol)."""
    energia = pd.DataFrame(
        {
            "sol": serie["sol"],
            "consumo_kwh": energia_por_passo(serie["consumo_kw"], p.dt_h),
            "geracao_kwh": energia_por_passo(serie["geracao_total_kw"], p.dt_h),
            "geracao_solar_kwh": energia_por_passo(serie["geracao_solar_kw"], p.dt_h),
            "energia_nao_suprida_kwh": serie["energia_nao_suprida_kwh"],
            "horas_em_alerta": serie["alerta_energia"] * p.dt_h,
        }
    )
    somas = energia.groupby("sol").sum()
    extremos = serie.groupby("sol").agg(
        temp_min_c=("temp_ext_c", "min"),
        temp_max_c=("temp_ext_c", "max"),
        temp_media_c=("temp_ext_c", "mean"),
        soc_min=("soc", "min"),
    )
    diario = por_sol.set_index("sol")[["tripulantes", "tempestade", "opacidade"]]
    diario = diario.join(extremos).join(somas)
    diario["saldo_kwh"] = diario["geracao_kwh"] - diario["consumo_kwh"]
    return diario.reset_index()


def comparar_cenarios(
    cenarios: dict[str, dict], base: ParametrosSimulacao | None = None
) -> pd.DataFrame:
    """Roda a simulação com parâmetros alterados e compara indicadores-chave.

    Exemplo: comparar_cenarios({"Reator 80 kW": {"reator_kw": 80}})
    """
    base = base or ParametrosSimulacao()
    modulos = carregar_modulos()
    linhas = []
    for nome, alteracoes in cenarios.items():
        p = replace(base, **alteracoes)
        serie, diario = simular(p, modulos)
        linhas.append(
            {
                "cenario": nome,
                "energia_nao_suprida_kwh": serie["energia_nao_suprida_kwh"].sum(),
                "sois_com_falta": int((diario["energia_nao_suprida_kwh"] > 0).sum()),
                "horas_em_alerta": diario["horas_em_alerta"].sum(),
                "soc_minimo": serie["soc"].min(),
            }
        )
    return pd.DataFrame(linhas)
