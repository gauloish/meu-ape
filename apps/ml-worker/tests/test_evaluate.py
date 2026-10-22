"""Testes unitários para o módulo de avaliação por Nested Cross-Validation (evaluate.py)."""

from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest
from evaluation.evaluate import compute_metrics, evaluate_pipeline
from ml_core.estimators import RegressionMetrics
from ml_core.pipelines import FeatureGroups


@pytest.fixture
def synthetic_data() -> tuple[pd.DataFrame, pd.Series, FeatureGroups]:
    """Gera dados sintéticos simples para teste de avaliação."""
    np.random.seed(42)
    n_samples = 30

    X = pd.DataFrame(
        {
            "area_m2": np.random.uniform(40, 200, n_samples).astype(float),
            "condominio": np.random.uniform(100, 1000, n_samples).astype(float),
            "banheiros": np.random.randint(1, 4, n_samples).astype(float),
            "quartos": np.random.randint(1, 5, n_samples).astype(float),
            "vagas": np.random.randint(1, 3, n_samples).astype(float),
            "latitude": np.random.uniform(-16.75, -16.65, n_samples).astype(float),
            "longitude": np.random.uniform(-49.30, -49.20, n_samples).astype(float),
            "tipo_imovel": pd.Series(
                np.random.choice(["casa", "apartamento"], n_samples), dtype="string"
            ),
            "piscina": pd.Series(
                np.random.choice([True, False], n_samples), dtype="boolean"
            ),
        }
    )
    y = pd.Series(np.random.uniform(200000, 1200000, n_samples), name="preco")

    groups = FeatureGroups(
        numeric_features=[
            "area_m2",
            "condominio",
            "banheiros",
            "quartos",
            "vagas",
            "latitude",
            "longitude",
        ],
        categorical_features=["tipo_imovel"],
        boolean_features=["piscina"],
    )

    return X, y, groups


def test_compute_metrics():
    """Testa o cálculo isolado das 5 métricas de regressão."""
    y_true = [100.0, 200.0, 300.0, 400.0]
    y_pred = [110.0, 190.0, 310.0, 390.0]

    metrics = compute_metrics(y_true, y_pred)

    assert set(metrics.keys()) == {"r2", "rmse", "mae", "medae", "mape"}
    assert metrics["rmse"] > 0.0
    assert metrics["mae"] == 10.0
    assert metrics["medae"] == 10.0
    assert metrics["r2"] > 0.9


def test_evaluate_pipeline_with_mocks(synthetic_data):
    """Testa evaluate_pipeline com mocks para otimização e treinamento rápido."""
    X, y, groups = synthetic_data

    mock_metrics = RegressionMetrics(
        r2=0.85,
        rmse=50000.0,
        mae=35000.0,
        medae=28000.0,
        mape=0.08,
        max_error=60000.0,
    )

    with (
        patch(
            "evaluation.evaluate.optimize_hyperparameters",
            return_value=({"model__max_depth": 3}, 35000.0),
        ),
        patch("evaluation.evaluate.create_training_pipeline") as mock_pipeline_cls,
        patch(
            "evaluation.evaluate.calculate_regression_metrics",
            return_value=mock_metrics,
        ),
    ):
        mock_pipeline = MagicMock()
        mock_pipeline.predict.return_value = np.array([300000.0] * 10)
        mock_pipeline_cls.return_value = mock_pipeline

        results = evaluate_pipeline(
            X=X,
            y=y,
            feature_groups=groups,
            k_outer=2,
            k_inner=2,
            n_trials=1,
            random_state=42,
        )

        assert "metrics_summary" in results
        assert "fold_metrics" in results
        assert results["k_outer"] == 2
        assert results["k_inner"] == 2
        assert len(results["fold_metrics"]) == 2

        summary = results["metrics_summary"]
        assert "r2" in summary
        assert "rmse" in summary
        assert "mae" in summary
        assert "medae" in summary
        assert "mape" in summary
        assert summary["r2"]["mean"] == 0.85
        assert summary["mae"]["mean"] == 35000.0
