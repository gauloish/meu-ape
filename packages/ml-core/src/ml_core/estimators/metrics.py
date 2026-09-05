"""Modelos Pydantic e funções utilitárias para extração de métricas de regressão.

Fornece estruturas fortemente tipadas e imutáveis para relatórios de métricas
do modelo regressor e agregações estatísticas.
"""

from collections.abc import Sequence

import numpy as np
from pydantic import BaseModel, ConfigDict, Field
from sklearn.metrics import (
    max_error as calc_max_error,
    mean_absolute_error,
    mean_absolute_percentage_error,
    median_absolute_error,
    r2_score,
    root_mean_squared_error,
)


class RegressionMetrics(BaseModel):
    """Métricas de desempenho para tarefas de regressão contínua.

    Attributes:
        r2 (float): Coeficiente de Determinação R².
        rmse (float): Root Mean Squared Error (Raiz do Erro Quadrático Médio).
        mae (float): Mean Absolute Error (Erro Médio Absoluto).
        medae (float): Median Absolute Error (Mediana do Erro Absoluto).
        mape (float): Mean Absolute Percentage Error (Erro Percentual Médio Absoluto).
        max_error (float): Erro absoluto máximo observado.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    r2: float = Field(..., description="Coeficiente de Determinação R²")
    rmse: float = Field(..., description="Root Mean Squared Error")
    mae: float = Field(..., description="Mean Absolute Error")
    medae: float = Field(..., description="Median Absolute Error")
    mape: float = Field(..., description="Mean Absolute Percentage Error")
    max_error: float = Field(..., description="Erro absoluto máximo")


class RegressionMetricsReport(BaseModel):
    """Relatório estruturado consolidado de avaliação do Estimador.

    Attributes:
        regression_metrics (RegressionMetrics): Métricas de regressão do estimador.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    regression_metrics: RegressionMetrics = Field(
        ..., description="Métricas de regressão do estimador"
    )

    def get_report(self) -> str:
        """Retorna um relatório formatado com as métricas de regressão.

        Returns:
            str: String formatada contendo todas as métricas calculadas.
        """
        return (
            "Métricas("
            f"R2: {self.regression_metrics.r2:.2f}, "
            f"RMSE: {self.regression_metrics.rmse:.2f}, "
            f"MAE: {self.regression_metrics.mae:.2f}, "
            f"MedAE: {self.regression_metrics.medae:.2f}, "
            f"MAPE: {self.regression_metrics.mape:.2f}, "
            f"Max Error: {self.regression_metrics.max_error:.2f})"
        )


def calculate_aggregated_metrics(
    metrics: list[RegressionMetrics],
) -> tuple[RegressionMetrics, RegressionMetrics]:
    """Calcula a média e o desvio padrão de uma lista de métricas de regressão.

    Args:
        metrics (list[RegressionMetrics]): Lista de métricas obtidas (ex: folds da validação cruzada).

    Returns:
        tuple[RegressionMetrics, RegressionMetrics]: Tupla contendo (métricas_médias, métricas_desvio_padrão).
    """
    r2: list[float] = []
    rmse: list[float] = []
    mae: list[float] = []
    medae: list[float] = []
    mape: list[float] = []
    max_error: list[float] = []

    for metric in metrics:
        r2.append(metric.r2)
        rmse.append(metric.rmse)
        mae.append(metric.mae)
        medae.append(metric.medae)
        mape.append(metric.mape)
        max_error.append(metric.max_error)

    mean_metrics = RegressionMetrics(
        r2=float(np.mean(r2)),
        rmse=float(np.mean(rmse)),
        mae=float(np.mean(mae)),
        medae=float(np.mean(medae)),
        mape=float(np.mean(mape)),
        max_error=float(np.mean(max_error)),
    )

    std_metrics = RegressionMetrics(
        r2=float(np.std(r2)),
        rmse=float(np.std(rmse)),
        mae=float(np.std(mae)),
        medae=float(np.std(medae)),
        mape=float(np.std(mape)),
        max_error=float(np.std(max_error)),
    )

    return mean_metrics, std_metrics


def calculate_regression_metrics(
    y_true: Sequence[float] | np.ndarray,
    y_pred: Sequence[float] | np.ndarray,
) -> RegressionMetrics:
    """Calcula métricas de regressão padrão para um conjunto de predições.

    Args:
        y_true (Sequence[float] | np.ndarray): Vetor de valores alvo reais.
        y_pred (Sequence[float] | np.ndarray): Vetor de valores alvo preditos.

    Returns:
        RegressionMetrics: Objeto Pydantic imutável com as métricas calculadas.
    """
    y_t = np.asarray(y_true, dtype=np.float64).ravel()
    y_p = np.asarray(y_pred, dtype=np.float64).ravel()

    support = len(y_t)

    if support == 0:
        r2 = 0.0
        rmse = 0.0
        mae = 0.0
        medae = 0.0
        mape = 0.0
        max_err = 0.0
    else:
        if np.var(y_t) == 0.0:
            r2 = 1.0 if np.allclose(y_t, y_p) else 0.0
        else:
            r2 = float(r2_score(y_t, y_p))

        rmse = float(root_mean_squared_error(y_t, y_p))
        mae = float(mean_absolute_error(y_t, y_p))
        medae = float(median_absolute_error(y_t, y_p))
        mape = float(mean_absolute_percentage_error(y_t, y_p))
        max_err = float(calc_max_error(y_t, y_p))

    return RegressionMetrics(
        r2=r2,
        rmse=rmse,
        mae=mae,
        medae=medae,
        mape=mape,
        max_error=max_err,
    )
