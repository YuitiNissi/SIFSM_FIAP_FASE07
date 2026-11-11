"""
Ponte entre a simulação/análise e o sistema principal SIFSM.

O menu do sistema pode usar estas funções para:
  * exibir o resumo da simulação energética;
  * estimar o consumo diário com o modelo de regressão linear;
  * verificar o alerta de energia (regra booleana) a partir do estado da bateria.

Exemplo de uso no menu (src/database.py ou src/menu.py):

    from resultados_simulacao import exibir_resumo_simulacao, menu_previsao_consumo
    ...
    case 7:
        exibir_resumo_simulacao()
    case 8:
        menu_previsao_consumo()

Os resultados são lidos de data/simulacao/resultados_simulacao.json, gerado por
`python src/analise_simulacao.py`.
"""

from __future__ import annotations

import json
from pathlib import Path

ARQUIVO_RESULTADOS = Path(__file__).resolve().parents[1] / "data" / "simulacao" / "resultados_simulacao.json"
MARGEM = " " * 4


def carregar_resultados(caminho: Path | str = ARQUIVO_RESULTADOS) -> dict:
    """Lê o JSON de resultados. Gera a análise se o arquivo ainda não existir."""
    caminho = Path(caminho)
    if not caminho.exists():
        # Importação tardia: só carrega matplotlib/numpy se for preciso gerar
        from analise_simulacao import executar

        executar(verbose=False)
    try:
        with open(caminho, encoding="utf-8") as arquivo:
            return json.load(arquivo)
    except json.JSONDecodeError as erro:
        raise ValueError(f"Arquivo de resultados corrompido: {caminho}") from erro


def estimar_consumo_diario(temp_media_c: float, tripulantes: int, resultados: dict | None = None) -> float:
    """Previsão do consumo de um sol (kWh) pelo modelo de regressão linear."""
    resultados = resultados or carregar_resultados()
    modelo = resultados["regressao"]
    coef = modelo["coeficientes"]
    return (
        modelo["intercepto"]
        + coef["temp_media_c"] * float(temp_media_c)
        + coef["tripulantes"] * float(tripulantes)
    )


def alerta_energia(soc: float, energia_nao_suprida_kwh: float = 0.0, limite_soc: float = 0.20) -> bool:
    """Regra booleana usada na simulação: ALERTA = (SOC < limite) OU (falta de energia)."""
    return soc < limite_soc or energia_nao_suprida_kwh > 0


def _fmt(valor: float, casas: int = 0) -> str:
    """Formata números no padrão brasileiro (1.234,5)."""
    texto = f"{valor:,.{casas}f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def exibir_resumo_simulacao(resultados: dict | None = None) -> None:
    try:
        resultados = resultados or carregar_resultados()
    except (OSError, ValueError, ImportError) as erro:
        print(f"{MARGEM}Não foi possível carregar a simulação: {erro}")
        return

    ind = resultados["indicadores"]
    reg = resultados["regressao"]
    print(f"{MARGEM}==============================")
    print(f"{MARGEM}  SIMULAÇÃO ENERGÉTICA")
    print(f"{MARGEM}==============================")
    print(f"{MARGEM}Sóis simulados ............ {ind['sois_simulados']}")
    print(f"{MARGEM}Consumo médio por sol ..... {_fmt(ind['consumo_medio_diario_kwh'])} kWh")
    print(f"{MARGEM}Pico de potência .......... {_fmt(ind['potencia_pico_kw'])} kW")
    print(f"{MARGEM}Energia não suprida ....... {_fmt(ind['energia_nao_suprida_kwh'])} kWh")
    print(f"{MARGEM}Sóis com falta de energia . {ind['sois_com_falta_energia']}")
    print(f"{MARGEM}Horas em alerta ........... {_fmt(ind['horas_em_alerta'], 1)} h")
    if ind.get("tempestade_sois"):
        inicio, fim = ind["tempestade_sois"]
        print(f"{MARGEM}Tempestade de poeira ...... sóis {inicio} a {fim} "
              f"(saldo médio {_fmt(ind['tempestade_saldo_medio_kwh'])} kWh/sol)")
    print()
    print(f"{MARGEM}Modelo: {reg['equacao']}")
    teste = reg["metricas"]["teste"]
    print(f"{MARGEM}R² (teste) = {teste['r2']:.2f} | erro médio = {_fmt(teste['mae'])} kWh "
          f"({teste['mape_pct']:.1f}%)")
    print()
    print(f"{MARGEM}Cenários (energia não suprida):")
    for cenario in resultados["cenarios"]:
        print(f"{MARGEM}  - {cenario['cenario']:<28} {_fmt(cenario['energia_nao_suprida_kwh'])} kWh")
    print(f"\n{MARGEM}{resultados['recomendacao']}")


def menu_previsao_consumo() -> None:
    """Pergunta temperatura e tripulação e mostra o consumo previsto."""
    print(f"{MARGEM}==============================")
    print(f"{MARGEM}  PREVISÃO DE CONSUMO DIÁRIO")
    print(f"{MARGEM}==============================")
    try:
        temp = float(input(f"{MARGEM}Temperatura externa média prevista (°C): ").replace(",", "."))
        tripulantes = int(input(f"{MARGEM}Número de tripulantes: "))
        if tripulantes < 0:
            raise ValueError("número de tripulantes negativo")
        resultados = carregar_resultados()
    except ValueError as erro:
        print(f"{MARGEM}Valor inválido: {erro}")
        return
    except OSError as erro:
        print(f"{MARGEM}Não foi possível carregar o modelo: {erro}")
        return

    consumo = estimar_consumo_diario(temp, tripulantes, resultados)
    rmse = resultados["regressao"]["metricas"]["teste"]["rmse"]
    print(f"{MARGEM}Consumo previsto: {_fmt(consumo)} kWh/sol (± {_fmt(rmse)} kWh)")

    faixa = resultados["regressao"].get("faixa_treino", {})
    entradas = {"temp_media_c": temp, "tripulantes": tripulantes}
    fora = [nome for nome, (minimo, maximo) in faixa.items() if not minimo <= entradas[nome] <= maximo]
    if fora:
        print(f"{MARGEM}Atenção: {', '.join(fora)} fora da faixa usada no treino do modelo; "
              "a previsão é uma extrapolação e pode ser imprecisa.")


if __name__ == "__main__":
    exibir_resumo_simulacao()
