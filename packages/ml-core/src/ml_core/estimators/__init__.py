"""Módulo de estimadores customizados do pacote `ml-core`."""

from .estimator import Regressor
from .metrics import (
    RegressionMetrics,
    RegressionMetricsReport,
    calculate_aggregated_metrics,
    calculate_regression_metrics,
)

__all__: list[str] = [
    "RegressionMetrics",
    "RegressionMetricsReport",
    "Regressor",
    "calculate_aggregated_metrics",
    "calculate_regression_metrics",
]
