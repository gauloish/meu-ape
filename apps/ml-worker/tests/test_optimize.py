"""Testes unitários para o módulo de otimização (optimize.py)."""

import numpy as np
import pandas as pd
import pytest
from ml_core.pipelines import FeatureGroups
from optimization.optimize import optimize_hyperparameters


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


def test_optimize_hyperparameters_fast(synthetic_data):
    """Garante que a otimização executa com n_trials=1 e k_folds=2 em milissegundos."""
    X, y, groups = synthetic_data

    best_params, best_rmse = optimize_hyperparameters(
        X=X,
        y=y,
        n_trials=1,
        k_folds=2,
        random_state=42,
        feature_groups=groups,
    )

    assert isinstance(best_params, dict)
    assert "model__max_depth" in best_params
    assert "model__n_estimators" in best_params
    assert "model__learning_rate" in best_params
    assert isinstance(best_rmse, float)
    assert best_rmse > 0.0
