"""Suíte de testes unitários para os modelos e utilitários de métricas do ml-core."""

import numpy as np
import pytest
from ml_core.estimators.metrics import (
    RegressionMetrics,
    RegressionMetricsReport,
    calculate_aggregated_metrics,
    calculate_regression_metrics,
)
from pydantic import ValidationError


def test_regression_metrics_immutability():
    """Garante que RegressionMetrics é imutável e valida campos extras."""
    metrics = RegressionMetrics(
        r2=0.85,
        rmse=15000.0,
        mae=12000.0,
        medae=9000.0,
        mape=0.08,
        max_error=45000.0,
    )

    assert metrics.r2 == 0.85
    assert metrics.rmse == 15000.0
    assert metrics.mae == 12000.0
    assert metrics.medae == 9000.0
    assert metrics.mape == 0.08
    assert metrics.max_error == 45000.0

    # Imutabilidade (frozen=True)
    with pytest.raises(ValidationError):
        metrics.r2 = 0.90  # type: ignore

    # Bloqueio de campos extras (extra='forbid')
    with pytest.raises(ValidationError):
        RegressionMetrics(
            r2=0.85,
            rmse=15000.0,
            mae=12000.0,
            medae=9000.0,
            mape=0.08,
            max_error=45000.0,
            extra_field=123,  # type: ignore
        )


def test_regression_metrics_report():
    """Valida a formatação de string gerada por RegressionMetricsReport."""
    metrics = RegressionMetrics(
        r2=0.8512,
        rmse=15432.10,
        mae=12345.67,
        medae=9876.54,
        mape=0.085,
        max_error=45678.90,
    )
    report = RegressionMetricsReport(regression_metrics=metrics)
    report_text = report.get_report()

    assert "R2: 0.85" in report_text
    assert "RMSE: 15432.10" in report_text
    assert "MAE: 12345.67" in report_text
    assert "MedAE: 9876.54" in report_text
    assert ("MAPE: 0.08" in report_text) or ("MAPE: 0.09" in report_text)
    assert "Max Error: 45678.90" in report_text


def test_calculate_regression_metrics_normal():
    """Valida o cálculo de métricas para previsões numéricas convencionais."""
    y_true = np.array([100.0, 200.0, 300.0, 400.0])
    y_pred = np.array([110.0, 190.0, 310.0, 390.0])

    metrics = calculate_regression_metrics(y_true, y_pred)

    assert isinstance(metrics, RegressionMetrics)
    assert metrics.mae == 10.0
    assert metrics.medae == 10.0
    assert metrics.max_error == 10.0
    assert metrics.rmse == 10.0
    assert metrics.r2 > 0.95
    assert metrics.mape > 0.0


def test_calculate_regression_metrics_empty_arrays():
    """Garante retorno zerado quando arrays vazios são informados."""
    metrics = calculate_regression_metrics([], [])

    assert metrics.r2 == 0.0
    assert metrics.rmse == 0.0
    assert metrics.mae == 0.0
    assert metrics.medae == 0.0
    assert metrics.mape == 0.0
    assert metrics.max_error == 0.0


def test_calculate_regression_metrics_constant_target():
    """Verifica comportamento quando o vetor de target possui variância zero."""
    y_true = np.array([250.0, 250.0, 250.0])
    y_pred_identical = np.array([250.0, 250.0, 250.0])
    y_pred_different = np.array([260.0, 240.0, 250.0])

    metrics_perf = calculate_regression_metrics(y_true, y_pred_identical)
    assert metrics_perf.r2 == 1.0
    assert metrics_perf.rmse == 0.0

    metrics_diff = calculate_regression_metrics(y_true, y_pred_different)
    assert metrics_diff.r2 == 0.0
    assert metrics_diff.rmse > 0.0


def test_calculate_aggregated_metrics():
    """Valida o cálculo de média e desvio padrão para conjuntos de métricas."""
    m1 = RegressionMetrics(
        r2=0.80, rmse=20.0, mae=15.0, medae=10.0, mape=0.10, max_error=50.0
    )
    m2 = RegressionMetrics(
        r2=0.90, rmse=10.0, mae=5.0, medae=4.0, mape=0.04, max_error=30.0
    )

    mean_metrics, std_metrics = calculate_aggregated_metrics([m1, m2])

    assert isinstance(mean_metrics, RegressionMetrics)
    assert isinstance(std_metrics, RegressionMetrics)

    assert pytest.approx(mean_metrics.r2, 1e-4) == 0.85
    assert pytest.approx(mean_metrics.rmse, 1e-4) == 15.0
    assert pytest.approx(mean_metrics.mae, 1e-4) == 10.0
    assert pytest.approx(mean_metrics.medae, 1e-4) == 7.0
    assert pytest.approx(mean_metrics.mape, 1e-4) == 0.07
    assert pytest.approx(mean_metrics.max_error, 1e-4) == 40.0

    assert pytest.approx(std_metrics.r2, 1e-4) == 0.05
    assert pytest.approx(std_metrics.rmse, 1e-4) == 5.0
