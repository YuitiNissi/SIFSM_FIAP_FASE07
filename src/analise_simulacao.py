"""
Análise completa da simulação energética do SIFSM.

Executa, em ordem:
  1. a simulação do balanço energético (simulacao_energia.py);
  2. a verificação da integração numérica (trapézio x retângulos);
  3. a análise exploratória dos dados diários;
  4. a regressão linear do consumo diário (regressao_linear.py);
  5. a comparação de cenários para apoiar decisões;
  6. a geração dos gráficos e do arquivo de resultados para o sistema principal.

Uso:
    python src/analise_simulacao.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # gera arquivos sem precisar de janela gráfica
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import Patch

import regressao_linear as rl
import simulacao_energia as sim

RAIZ = sim.RAIZ_PROJETO
PASTA_DADOS = RAIZ / "data" / "simulacao"
PASTA_GRAFICOS = RAIZ / "docs" / "graficos"
ARQUIVO_RESULTADOS = PASTA_DADOS / "resultados_simulacao.json"

# Variáveis explicativas e alvo da regressão
VARIAVEIS_MODELO = ["temp_media_c", "tripulantes"]
ALVO_MODELO = "consumo_kwh"

CENARIOS = {
    "Base (reator 40 kW)": {},
    "Painéis +20%": {"area_paineis_m2": 8400.0},
    "Bateria 2x (12 MWh)": {"bateria_capacidade_kwh": 12000.0},
    "Reator 100 kW": {"reator_kw": 100.0},
    "Reator 100 kW + bateria 2x": {"reator_kw": 100.0, "bateria_capacidade_kwh": 12000.0},
    "Reator 160 kW": {"reator_kw": 160.0},
}

# ---------------------------------------------------------------------------
# Estilo dos gráficos (paleta validada para daltonismo)
# ---------------------------------------------------------------------------
COR = {
    "consumo": "#2a78d6",  # azul
    "geracao": "#eb6834",  # laranja
    "temperatura": "#1baf7a",  # verde-água
    "bateria": "#6250d6",  # violeta
    "teste": "#1baf7a",
    "tempestade": "#ebeae5",  # faixa neutra
    "texto": "#0b0b0b",
    "texto_sec": "#52514e",
    "eixo": "#898781",
    "grade": "#e1e0d9",
    "fundo": "#fcfcfb",
}
MAPA_DIVERGENTE = LinearSegmentedColormap.from_list(
    "azul_cinza_vermelho", ["#1c5cab", "#86b6ef", "#f0efec", "#ef9a99", "#c23434"]
)

plt.rcParams.update(
    {
        "figure.facecolor": COR["fundo"],
        "axes.facecolor": COR["fundo"],
        "savefig.facecolor": COR["fundo"],
        "axes.edgecolor": COR["eixo"],
        "axes.linewidth": 0.8,
        "axes.labelcolor": COR["texto_sec"],
        "axes.titlecolor": COR["texto"],
        "axes.titlesize": 12,
        "axes.titleweight": "bold",
        "axes.titlelocation": "left",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "axes.axisbelow": True,
        "grid.color": COR["grade"],
        "grid.linewidth": 0.6,
        "grid.linestyle": "-",
        "xtick.color": COR["texto_sec"],
        "ytick.color": COR["texto_sec"],
        "xtick.major.size": 0,
        "ytick.major.size": 0,
        "lines.linewidth": 2,
        "legend.frameon": False,
        "legend.labelcolor": COR["texto_sec"],
        "font.size": 10,
        "figure.dpi": 110,
    }
)


def _salvar(fig: plt.Figure, nome: str) -> Path:
    PASTA_GRAFICOS.mkdir(parents=True, exist_ok=True)
    caminho = PASTA_GRAFICOS / nome
    fig.savefig(caminho, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return caminho


def _sombrear_tempestade(ax, diario: pd.DataFrame, em_horas: bool = False) -> None:
    sois = diario.loc[diario["tempestade"], "sol"]
    if sois.empty:
        return
    inicio, fim = sois.min(), sois.max() + 1
    escala = sim.SOL_HORAS if em_horas else 1
    ax.axvspan(inicio * escala, fim * escala, color=COR["tempestade"], zorder=0, lw=0)


def _legenda_tempestade() -> Patch:
    return Patch(facecolor=COR["tempestade"], label="Tempestade de poeira")


# ---------------------------------------------------------------------------
# Etapas da análise
# ---------------------------------------------------------------------------
def verificar_integracao(p: sim.ParametrosSimulacao) -> pd.DataFrame:
    """Compara trapézio e retângulos com a integral exata da geração solar.

    Num sol sem poeira, a potência solar é uma meia senoide:
        P(h) = Pmax · sen(π (h - h0) / D),  0 ≤ h - h0 ≤ D
    Integramos a manhã (do nascer ao meio-dia, 0 ≤ h - h0 ≤ D/2), cuja
    integral exata é  Pmax · D / π.

    Obs.: no dia inteiro os dois métodos coincidem, porque P = 0 nas duas
    extremidades; na manhã P vai de 0 a Pmax e a diferença aparece.
    """
    pmax = p.irradiancia_pico_w_m2 * p.area_paineis_m2 * p.eficiencia_paineis / 1000
    meio_dia = sim.DURACAO_DIA_H / 2
    exata = pmax * sim.DURACAO_DIA_H / np.pi
    linhas = []
    for dt in [2.0, 1.0, 0.5, 0.25, 0.1]:
        # n pontos igualmente espaçados do nascer do sol ao meio-dia
        n = int(round(meio_dia / dt)) + 1
        h = np.linspace(0, meio_dia, n)
        passo = h[1] - h[0]
        potencia = pmax * np.sin(np.pi * h / sim.DURACAO_DIA_H)
        trap = sim.integrar_trapezio(potencia, passo)
        ret = sim.integrar_retangulos(potencia, passo)
        linhas.append(
            {
                "dt_h": round(passo, 3),
                "exata_kwh": exata,
                "trapezio_kwh": trap,
                "retangulos_kwh": ret,
                "erro_trapezio_pct": abs(trap - exata) / exata * 100,
                "erro_retangulos_pct": abs(ret - exata) / exata * 100,
            }
        )
    return pd.DataFrame(linhas)


def analise_exploratoria(diario: pd.DataFrame) -> dict:
    colunas = ["consumo_kwh", "geracao_kwh", "saldo_kwh", "temp_media_c", "tripulantes", "soc_min"]
    descricao = diario[colunas].describe().T
    correlacao = diario[
        ["consumo_kwh", "temp_media_c", "temp_min_c", "tripulantes", "geracao_kwh", "opacidade", "soc_min"]
    ].corr()
    comparacao_tempestade = diario.groupby("tempestade")[
        ["consumo_kwh", "geracao_kwh", "saldo_kwh", "soc_min", "horas_em_alerta"]
    ].mean()
    return {"descricao": descricao, "correlacao": correlacao, "tempestade": comparacao_tempestade}


def treinar_modelos(diario: pd.DataFrame) -> dict:
    treino, teste = rl.dividir_treino_teste(diario, fracao_teste=0.2, semente=7)
    simples = rl.ajustar(treino, ["temp_media_c"], ALVO_MODELO)
    multiplo = rl.ajustar(treino, VARIAVEIS_MODELO, ALVO_MODELO)
    resultado = {"treino": treino, "teste": teste, "simples": simples, "multiplo": multiplo}
    for nome in ("simples", "multiplo"):
        modelo = resultado[nome]
        resultado[f"metricas_{nome}"] = {
            "treino": rl.metricas(treino[ALVO_MODELO], modelo.prever(treino)),
            "teste": rl.metricas(teste[ALVO_MODELO], modelo.prever(teste)),
        }
    return resultado


def coeficientes_teoricos(p: sim.ParametrosSimulacao, modulos: list[dict]) -> dict:
    """Valores que a regressão deveria recuperar, derivados das hipóteses do modelo."""
    horas_acordado = sim.HORA_DORMIR - sim.HORA_ACORDAR
    return {
        "temp_media_c": -p.coef_aquecimento_kw_por_c * len(modulos) * sim.SOL_HORAS,
        "tripulantes": p.kw_por_tripulante * horas_acordado,
    }


# ---------------------------------------------------------------------------
# Gráficos
# ---------------------------------------------------------------------------
def grafico_perfil_sois(serie: pd.DataFrame, sol_inicio: int = 10, n_sois: int = 3) -> Path:
    trecho = serie[(serie["sol"] >= sol_inicio) & (serie["sol"] < sol_inicio + n_sois)]
    x = trecho["tempo_h"] / sim.SOL_HORAS
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 6), sharex=True, height_ratios=[1, 1.4])

    ax1.plot(x, trecho["temp_ext_c"], color=COR["temperatura"])
    ax1.set_title(f"Ciclo diário — sóis {sol_inicio} a {sol_inicio + n_sois - 1}")
    ax1.set_ylabel("Temperatura externa (°C)")

    ax2.plot(x, trecho["consumo_kw"], color=COR["consumo"], label="Consumo")
    ax2.plot(x, trecho["geracao_total_kw"], color=COR["geracao"], label="Geração (solar + reator)")
    ax2.set_ylabel("Potência (kW)")
    ax2.set_xlabel("Sol")
    ax2.legend(loc="upper left", ncols=2)
    fig.tight_layout()
    return _salvar(fig, "01_ciclo_diario.png")


def grafico_balanco_diario(diario: pd.DataFrame) -> Path:
    fig, ax = plt.subplots(figsize=(10, 4.5))
    _sombrear_tempestade(ax, diario)
    ax.plot(diario["sol"], diario["consumo_kwh"], color=COR["consumo"], label="Consumo")
    ax.plot(diario["sol"], diario["geracao_kwh"], color=COR["geracao"], label="Geração")
    ax.set_title("Energia diária consumida e gerada")
    ax.set_xlabel("Sol")
    ax.set_ylabel("Energia por sol (kWh)")
    handles, _ = ax.get_legend_handles_labels()
    ax.legend(handles=[*handles, _legenda_tempestade()], loc="lower left", ncols=3)
    fig.tight_layout()
    return _salvar(fig, "02_balanco_diario.png")


def grafico_bateria(serie: pd.DataFrame, diario: pd.DataFrame, p: sim.ParametrosSimulacao) -> Path:
    fig, ax = plt.subplots(figsize=(10, 4.2))
    _sombrear_tempestade(ax, diario)
    ax.plot(serie["tempo_h"] / sim.SOL_HORAS, serie["soc"] * 100, color=COR["bateria"], lw=1.2,
            label="Carga da bateria")
    ax.axhline(p.limite_alerta_soc * 100, color=COR["texto_sec"], lw=1, ls="--",
               label=f"Limite de alerta ({p.limite_alerta_soc:.0%})")
    ax.set_ylim(-2, 102)
    ax.set_title("Estado de carga da bateria (acumulação do saldo energético)")
    ax.set_xlabel("Sol")
    ax.set_ylabel("Carga (%)")
    handles, _ = ax.get_legend_handles_labels()
    ax.legend(handles=[*handles, _legenda_tempestade()], loc="upper center",
              bbox_to_anchor=(0.5, -0.17), ncols=3)
    fig.tight_layout()
    return _salvar(fig, "03_bateria.png")


def grafico_integracao(serie: pd.DataFrame, erros: pd.DataFrame, p: sim.ParametrosSimulacao,
                       sol: int = 10) -> Path:
    trecho = serie[serie["sol"] == sol]
    energia = sim.integrar_trapezio(trecho["consumo_kw"], p.dt_h)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.2), width_ratios=[1.4, 1])

    ax1.fill_between(trecho["hora_sol"], trecho["consumo_kw"], color=COR["consumo"], alpha=0.18, lw=0)
    ax1.plot(trecho["hora_sol"], trecho["consumo_kw"], color=COR["consumo"])
    ax1.set_ylim(0, None)
    ax1.set_title(f"Energia = área sob a curva de potência (sol {sol})")
    ax1.set_xlabel("Hora do sol (h)")
    ax1.set_ylabel("Consumo (kW)")
    ax1.text(0.5, 0.35, f"E = ∫ P(t) dt ≈ {energia:,.0f} kWh".replace(",", "."),
             transform=ax1.transAxes, ha="center", color=COR["texto"], fontsize=11)

    ax2.plot(erros["dt_h"], erros["erro_retangulos_pct"], color=COR["geracao"], marker="o",
             ms=6, label="Retângulos")
    ax2.plot(erros["dt_h"], erros["erro_trapezio_pct"], color=COR["consumo"], marker="o",
             ms=6, label="Trapézios")
    ax2.set_xscale("log")
    ax2.set_yscale("log")
    ax2.invert_xaxis()
    ax2.set_title("Erro da integração vs. passo de tempo")
    ax2.set_xlabel("Passo Δt (h) — menor à direita")
    ax2.set_ylabel("Erro relativo (%)")
    ax2.legend(loc="lower left")
    fig.tight_layout()
    return _salvar(fig, "04_integracao_numerica.png")


def grafico_distribuicoes(diario: pd.DataFrame) -> Path:
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.6))
    itens = [
        ("consumo_kwh", "Consumo diário (kWh)", 14),
        ("temp_media_c", "Temperatura média do sol (°C)", 14),
        ("tripulantes", "Tripulantes", np.arange(5.5, 15.5, 1)),
    ]
    for ax, (coluna, rotulo, bins) in zip(axes, itens):
        ax.hist(diario[coluna], bins=bins, color=COR["consumo"], edgecolor=COR["fundo"], lw=2)
        ax.set_xlabel(rotulo)
        ax.grid(axis="x", visible=False)
    axes[0].set_ylabel("Nº de sóis")
    axes[0].set_title("Distribuição das variáveis diárias")
    fig.tight_layout()
    return _salvar(fig, "05_distribuicoes.png")


def grafico_correlacao(correlacao: pd.DataFrame) -> Path:
    rotulos = {
        "consumo_kwh": "Consumo", "temp_media_c": "Temp. média", "temp_min_c": "Temp. mínima",
        "tripulantes": "Tripulantes", "geracao_kwh": "Geração", "opacidade": "Opacidade (poeira)",
        "soc_min": "Bateria mín.",
    }
    nomes = [rotulos[c] for c in correlacao.columns]
    fig, ax = plt.subplots(figsize=(7.2, 6))
    imagem = ax.imshow(correlacao, cmap=MAPA_DIVERGENTE, vmin=-1, vmax=1)
    ax.set_xticks(range(len(nomes)), nomes, rotation=40, ha="right")
    ax.set_yticks(range(len(nomes)), nomes)
    ax.grid(False)
    for spine in ax.spines.values():
        spine.set_visible(False)
    for i in range(len(nomes)):
        for j in range(len(nomes)):
            valor = correlacao.iloc[i, j]
            ax.text(j, i, f"{valor:.2f}", ha="center", va="center", fontsize=8.5,
                    color="#ffffff" if abs(valor) > 0.6 else COR["texto"])
    ax.set_title("Correlação entre os indicadores diários")
    barra = fig.colorbar(imagem, ax=ax, fraction=0.046, pad=0.04)
    barra.outline.set_visible(False)
    fig.tight_layout()
    return _salvar(fig, "06_correlacao.png")


def grafico_dispersao(diario: pd.DataFrame, modelo_simples: rl.ModeloLinear) -> Path:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.2), sharey=True)
    normal, tempestade = diario[~diario["tempestade"]], diario[diario["tempestade"]]

    for ax, coluna, rotulo in [(ax1, "temp_media_c", "Temperatura média do sol (°C)"),
                               (ax2, "tripulantes", "Tripulantes")]:
        ax.scatter(normal[coluna], normal[ALVO_MODELO], s=30, color=COR["consumo"],
                   edgecolor=COR["fundo"], lw=1, label="Sol normal")
        ax.scatter(tempestade[coluna], tempestade[ALVO_MODELO], s=34, facecolor="none",
                   edgecolor=COR["consumo"], lw=1.4, label="Sol com tempestade")
        ax.set_xlabel(rotulo)

    x = np.linspace(diario["temp_media_c"].min(), diario["temp_media_c"].max(), 50)
    ax1.plot(x, modelo_simples.prever({"temp_media_c": x}), color=COR["texto_sec"], lw=1.5,
             label="Reta de regressão")
    b1 = modelo_simples.coeficientes["temp_media_c"]
    ax1.set_title(f"Consumo cai {abs(b1):.1f} kWh a cada +1 °C")
    ax1.set_ylabel("Consumo diário (kWh)")
    ax1.legend(loc="upper right")
    ax2.set_title("Mais tripulantes, mais consumo")
    fig.tight_layout()
    return _salvar(fig, "07_dispersao_regressao.png")


def grafico_avaliacao(modelos: dict) -> Path:
    modelo = modelos["multiplo"]
    treino, teste = modelos["treino"], modelos["teste"]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.4))

    for dados, cor, nome in [(treino, COR["consumo"], "Treino"), (teste, COR["teste"], "Teste")]:
        previsto = modelo.prever(dados)
        ax1.scatter(dados[ALVO_MODELO], previsto, s=30, color=cor, edgecolor=COR["fundo"], lw=1, label=nome)
        ax2.scatter(previsto, dados[ALVO_MODELO] - previsto, s=30, color=cor, edgecolor=COR["fundo"],
                    lw=1, label=nome)

    limites = [modelos["treino"][ALVO_MODELO].min() - 100, modelos["treino"][ALVO_MODELO].max() + 100]
    ax1.plot(limites, limites, color=COR["texto_sec"], lw=1, label="Previsão perfeita")
    r2 = modelos["metricas_multiplo"]["teste"]["r2"]
    ax1.set_title(f"Real vs. previsto (R² teste = {r2:.2f})")
    ax1.set_xlabel("Consumo real (kWh)")
    ax1.set_ylabel("Consumo previsto (kWh)")
    ax1.legend(loc="upper left")

    ax2.axhline(0, color=COR["texto_sec"], lw=1)
    ax2.set_title("Resíduos (real − previsto)")
    ax2.set_xlabel("Consumo previsto (kWh)")
    ax2.set_ylabel("Resíduo (kWh)")
    ax2.legend(loc="upper left")
    fig.tight_layout()
    return _salvar(fig, "08_avaliacao_modelo.png")


def grafico_cenarios(cenarios: pd.DataFrame) -> Path:
    dados = cenarios.iloc[::-1]
    fig, ax = plt.subplots(figsize=(9, 3.8))
    barras = ax.barh(dados["cenario"], dados["energia_nao_suprida_kwh"] / 1000, color=COR["consumo"],
                     height=0.55)
    for barra, horas in zip(barras, dados["horas_em_alerta"]):
        ax.text(barra.get_width() + 0.2, barra.get_y() + barra.get_height() / 2,
                f"{barra.get_width():.1f} MWh · {horas:.0f} h em alerta",
                va="center", color=COR["texto_sec"], fontsize=9)
    ax.set_title("Energia não suprida em 120 sóis, por cenário")
    ax.set_xlabel("Energia não suprida (MWh)")
    ax.grid(axis="y", visible=False)
    ax.set_xlim(0, dados["energia_nao_suprida_kwh"].max() / 1000 * 1.45)
    fig.tight_layout()
    return _salvar(fig, "09_cenarios.png")


# ---------------------------------------------------------------------------
# Exportação para o sistema principal
# ---------------------------------------------------------------------------
def montar_resultados(p, modulos, serie, diario, modelos, cenarios, erros, teoricos) -> dict:
    multiplo = modelos["multiplo"]
    tempestade = diario[diario["tempestade"]]
    melhor = cenarios.sort_values(["energia_nao_suprida_kwh", "horas_em_alerta"]).iloc[0]
    return {
        "gerado_em": datetime.now().isoformat(timespec="seconds"),
        "parametros": p.__dict__,
        "modulos_simulados": [m["nome"] for m in modulos],
        "indicadores": {
            "sois_simulados": int(p.n_sois),
            "consumo_total_kwh": float(diario["consumo_kwh"].sum()),
            "geracao_total_kwh": float(diario["geracao_kwh"].sum()),
            "consumo_medio_diario_kwh": float(diario["consumo_kwh"].mean()),
            "potencia_pico_kw": float(serie["consumo_kw"].max()),
            "energia_nao_suprida_kwh": float(serie["energia_nao_suprida_kwh"].sum()),
            "energia_desperdicada_kwh": float(serie["energia_desperdicada_kwh"].sum()),
            "sois_com_falta_energia": int((diario["energia_nao_suprida_kwh"] > 0).sum()),
            "horas_em_alerta": float(diario["horas_em_alerta"].sum()),
            "soc_minimo": float(serie["soc"].min()),
            "tempestade_sois": [int(tempestade["sol"].min()), int(tempestade["sol"].max())]
            if not tempestade.empty else None,
            "tempestade_saldo_medio_kwh": float(tempestade["saldo_kwh"].mean()) if not tempestade.empty else None,
        },
        "integracao_numerica": erros.round(6).to_dict(orient="records"),
        "regressao": {
            **multiplo.para_dict(),
            "coeficientes_teoricos": teoricos,
            "faixa_treino": {
                v: [float(modelos["treino"][v].min()), float(modelos["treino"][v].max())]
                for v in VARIAVEIS_MODELO
            },
            "metricas": modelos["metricas_multiplo"],
            "metricas_modelo_simples": modelos["metricas_simples"],
            "equacao": (
                f"consumo_kwh = {multiplo.intercepto:.1f} "
                f"{multiplo.coeficientes['temp_media_c']:+.2f}·temp_media_c "
                f"{multiplo.coeficientes['tripulantes']:+.2f}·tripulantes"
            ),
        },
        "cenarios": cenarios.round(3).to_dict(orient="records"),
        "recomendacao": (
            f"O cenário '{melhor['cenario']}' elimina "
            f"{(1 - melhor['energia_nao_suprida_kwh'] / max(cenarios.iloc[0]['energia_nao_suprida_kwh'], 1e-9)):.0%} "
            "da energia não suprida em relação ao cenário base."
        ),
        "graficos": sorted(str(c.relative_to(RAIZ)).replace("\\", "/") for c in PASTA_GRAFICOS.glob("*.png")),
    }


def executar(gerar_graficos: bool = True, verbose: bool = True) -> dict:
    p = sim.ParametrosSimulacao()
    modulos = sim.carregar_modulos()
    serie, diario = sim.simular(p, modulos)
    erros = verificar_integracao(p)
    eda = analise_exploratoria(diario)
    modelos = treinar_modelos(diario)
    teoricos = coeficientes_teoricos(p, modulos)
    cenarios = sim.comparar_cenarios(CENARIOS, p)

    PASTA_DADOS.mkdir(parents=True, exist_ok=True)
    serie.round(4).to_csv(PASTA_DADOS / "serie_temporal.csv", index=False)
    diario.round(4).to_csv(PASTA_DADOS / "indicadores_diarios.csv", index=False)
    cenarios.round(3).to_csv(PASTA_DADOS / "cenarios.csv", index=False)

    if gerar_graficos:
        grafico_perfil_sois(serie)
        grafico_balanco_diario(diario)
        grafico_bateria(serie, diario, p)
        grafico_integracao(serie, erros, p)
        grafico_distribuicoes(diario)
        grafico_correlacao(eda["correlacao"])
        grafico_dispersao(diario, modelos["simples"])
        grafico_avaliacao(modelos)
        grafico_cenarios(cenarios)

    resultados = montar_resultados(p, modulos, serie, diario, modelos, cenarios, erros, teoricos)
    with open(ARQUIVO_RESULTADOS, "w", encoding="utf-8") as arquivo:
        json.dump(resultados, arquivo, ensure_ascii=False, indent=2, default=float)

    if verbose:
        _imprimir_relatorio(eda, modelos, erros, cenarios, teoricos, resultados)
    return resultados


def _imprimir_relatorio(eda, modelos, erros, cenarios, teoricos, resultados) -> None:
    pd.set_option("display.width", 140)
    pd.set_option("display.float_format", lambda v: f"{v:,.2f}")
    linha = "=" * 70
    print(linha, "\nSIMULAÇÃO ENERGÉTICA — SIFSM\n", linha, sep="")
    for chave, valor in resultados["indicadores"].items():
        print(f"  {chave:<30} {valor}")
    print("\n--- Integração numérica (geração solar: nascer do sol até o meio-dia) ---")
    print(erros.to_string(index=False))
    print("\n--- Estatística descritiva (por sol) ---")
    print(eda["descricao"][["mean", "std", "min", "max"]])
    print("\n--- Médias: sóis normais (False) x tempestade (True) ---")
    print(eda["tempestade"])
    print("\n--- Correlação com o consumo ---")
    print(eda["correlacao"]["consumo_kwh"].sort_values())
    print("\n--- Regressão linear múltipla ---")
    print(" ", resultados["regressao"]["equacao"])
    print(modelos["multiplo"].tabela_coeficientes())
    print("  Coeficientes teóricos:", {k: round(v, 2) for k, v in teoricos.items()})
    for nome in ("simples", "multiplo"):
        m = modelos[f"metricas_{nome}"]
        print(f"  {nome:<9} treino R²={m['treino']['r2']:.3f} | teste R²={m['teste']['r2']:.3f} "
              f"RMSE={m['teste']['rmse']:.1f} kWh MAPE={m['teste']['mape_pct']:.2f}%")
    print("\n--- Cenários ---")
    print(cenarios.to_string(index=False))
    print("\n ", resultados["recomendacao"])
    print(f"\nArquivos gerados em {PASTA_DADOS.relative_to(RAIZ)} e {PASTA_GRAFICOS.relative_to(RAIZ)}")


if __name__ == "__main__":
    # Evita erro em consoles Windows (cp1252) ao imprimir caracteres especiais
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    executar()
