"""
Regressão linear por mínimos quadrados (implementada com numpy).

Modelo:  y = b0 + b1·x1 + b2·x2 + ... + ε

Os coeficientes minimizam a soma dos quadrados dos resíduos. Em forma matricial,
com X contendo uma coluna de 1s para o intercepto:

    b = (XᵀX)⁻¹ Xᵀy

Usamos `np.linalg.lstsq`, que resolve esse mesmo problema de forma numericamente
estável. Além dos coeficientes, calculamos erros-padrão e intervalos de 95%
para poder interpretar se cada variável é relevante.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

Z_95 = 1.96  # aproximação normal para o intervalo de confiança de 95%


@dataclass
class ModeloLinear:
    variaveis: list[str]
    alvo: str
    intercepto: float
    coeficientes: dict[str, float]
    erros_padrao: dict[str, float] = field(default_factory=dict)
    n_observacoes: int = 0

    def prever(self, dados: pd.DataFrame | dict) -> np.ndarray:
        """Previsão para um DataFrame (ou dicionário) com as variáveis do modelo."""
        if isinstance(dados, dict):
            dados = pd.DataFrame({k: np.atleast_1d(v) for k, v in dados.items()})
        faltando = [v for v in self.variaveis if v not in dados]
        if faltando:
            raise KeyError(f"Variáveis ausentes para a previsão: {faltando}")
        previsao = np.full(len(dados), self.intercepto, dtype=float)
        for nome in self.variaveis:
            previsao += self.coeficientes[nome] * dados[nome].to_numpy(dtype=float)
        return previsao

    def tabela_coeficientes(self) -> pd.DataFrame:
        """Coeficientes com erro-padrão, estatística t e intervalo de 95%."""
        nomes = ["intercepto", *self.variaveis]
        valores = [self.intercepto, *(self.coeficientes[v] for v in self.variaveis)]
        erros = [self.erros_padrao.get(n, np.nan) for n in nomes]
        tabela = pd.DataFrame({"coeficiente": valores, "erro_padrao": erros}, index=nomes)
        tabela["t"] = tabela["coeficiente"] / tabela["erro_padrao"]
        tabela["ic95_inferior"] = tabela["coeficiente"] - Z_95 * tabela["erro_padrao"]
        tabela["ic95_superior"] = tabela["coeficiente"] + Z_95 * tabela["erro_padrao"]
        return tabela

    def para_dict(self) -> dict:
        return {
            "alvo": self.alvo,
            "variaveis": self.variaveis,
            "intercepto": self.intercepto,
            "coeficientes": self.coeficientes,
            "erros_padrao": self.erros_padrao,
            "n_observacoes": self.n_observacoes,
        }


def ajustar(dados: pd.DataFrame, variaveis: list[str], alvo: str) -> ModeloLinear:
    """Ajusta y = b0 + Σ bi·xi por mínimos quadrados."""
    if not variaveis:
        raise ValueError("Informe ao menos uma variável explicativa.")
    colunas = [*variaveis, alvo]
    faltando = [c for c in colunas if c not in dados]
    if faltando:
        raise KeyError(f"Colunas inexistentes: {faltando}")
    limpos = dados[colunas].dropna()
    n, k = len(limpos), len(variaveis) + 1
    if n <= k:
        raise ValueError(f"Poucas observações ({n}) para estimar {k} parâmetros.")

    X = np.column_stack([np.ones(n), limpos[variaveis].to_numpy(dtype=float)])
    y = limpos[alvo].to_numpy(dtype=float)
    b, *_ = np.linalg.lstsq(X, y, rcond=None)

    # Erros-padrão: sqrt(diag(σ² (XᵀX)⁻¹)), com σ² = SQR / (n - k)
    residuos = y - X @ b
    sigma2 = residuos @ residuos / (n - k)
    covariancia = sigma2 * np.linalg.pinv(X.T @ X)
    erros = np.sqrt(np.diag(covariancia))

    nomes = ["intercepto", *variaveis]
    return ModeloLinear(
        variaveis=list(variaveis),
        alvo=alvo,
        intercepto=float(b[0]),
        coeficientes={v: float(c) for v, c in zip(variaveis, b[1:])},
        erros_padrao={nm: float(e) for nm, e in zip(nomes, erros)},
        n_observacoes=n,
    )


def metricas(y_real, y_previsto) -> dict[str, float]:
    """R², RMSE, MAE e MAPE (%)."""
    y = np.asarray(y_real, dtype=float)
    yp = np.asarray(y_previsto, dtype=float)
    if y.shape != yp.shape or y.size == 0:
        raise ValueError("Vetores real e previsto devem ter o mesmo tamanho (> 0).")
    residuos = y - yp
    sqr = float(residuos @ residuos)
    sqt = float(((y - y.mean()) ** 2).sum())
    return {
        "r2": 1 - sqr / sqt if sqt > 0 else float("nan"),
        "rmse": float(np.sqrt(sqr / y.size)),
        "mae": float(np.abs(residuos).mean()),
        "mape_pct": float(np.mean(np.abs(residuos / y)) * 100) if np.all(y != 0) else float("nan"),
    }


def dividir_treino_teste(
    dados: pd.DataFrame, fracao_teste: float = 0.2, semente: int = 42
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Separação aleatória (reprodutível) entre treino e teste."""
    if not 0 < fracao_teste < 1:
        raise ValueError("fracao_teste deve estar entre 0 e 1.")
    rng = np.random.default_rng(semente)
    indices = rng.permutation(len(dados))
    n_teste = max(1, int(round(len(dados) * fracao_teste)))
    teste = dados.iloc[np.sort(indices[:n_teste])]
    treino = dados.iloc[np.sort(indices[n_teste:])]
    return treino, teste
