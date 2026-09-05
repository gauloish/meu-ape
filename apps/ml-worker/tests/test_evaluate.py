"""Testes unitários para o módulo de avaliação por Nested CV (evaluate.py)."""

import numpy as np
import pandas as pd
import pytest

from evaluation.evaluate import compute_metrics, run_nested_cv
from ml_core.pipelines import FeatureGroups


@pytest.fixture
def synthetic_data():
    """Gera dados sintéticos simples para teste rápido."""
    np.random.seed(42)
    n_samples = 50

    X = pd.DataFrame({
        "area_m2": np.random.uniform(40, 200, n_samples).astype(float),
        "condominio": np.random.uniform(100, 1000, n_samples).astype(float),
        "banheiros": np.random.randint(1, 4, n_samples).astype(float),
        "quartos": np.random.randint(1, 5, n_samples).astype(float),
        "vagas": np.random.randint(1, 3, n_samples).astype(float),
        "latitude": np.random.uniform(-16.75, -16.65, n_samples).astype(float),
        "longitude": np.random.uniform(-49.30, -49.20, n_samples).astype(float),
        "tipo_imovel": pd.Series(np.random.choice(["casa", "apartamento"], n_samples), dtype="string"),
        "piscina": pd.Series(np.random.choice([True, False], n_samples), dtype="boolean"),
    })
    y = pd.Series(np.random.uniform(200000, 1200000, n_samples), name="preco")

    groups = FeatureGroups(
        numeric_features=["area_m2", "condominio", "banheiros", "quartos", "vagas", "latitude", "longitude"],
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
    assert metrics["r2"] > 0.9


def test_run_nested_cv_fast(synthetic_data):
    """Garante que o Nested CV executa rapidamente com k_outer=2, k_inner=2 e n_trials=1."""
    X, y, groups = synthetic_data

    results = run_nested_cv(
        X=X,
        y=y,
        k_outer=2,
        k_inner=2,
        n_trials=1,
        random_state=42,
        feature_groups=groups,
    )

    assert "metrics_summary" in results
    assert "fold_metrics" in results
    assert len(results["fold_metrics"]) == 2

    summary = results["metrics_summary"]
    expected_keys = {
        "r2_mean", "r2_std",
        "rmse_mean", "rmse_std",
        "mae_mean", "mae_std",
        "medae_mean", "medae_std",
        "mape_mean", "mape_std",
    }
    assert expected_keys.issubset(summary.keys())
