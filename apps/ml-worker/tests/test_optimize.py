"""Testes unitários para o módulo de otimização de hiperparâmetros (optimize.py)."""

from unittest.mock import patch

import numpy as np
import optuna
import pandas as pd
import pytest
from ml_core.pipelines import FeatureGroups
from optimization.optimize import optimize_hyperparameters, search_space


@pytest.fixture
def synthetic_data() -> tuple[pd.DataFrame, pd.Series, FeatureGroups]:
    """Gera dados sintéticos simples para teste rápido de otimização."""
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


def test_search_space():
    """Testa se search_space define todos os parâmetros e opções obrigatórias."""
    study = optuna.create_study()
    trial = study.ask()

    params = search_space(trial, random_state=1234)

    assert "model__n_estimators" in params
    assert "model__learning_rate" in params
    assert "model__max_depth" in params
    assert "model__min_child_weight" in params
    assert "model__subsample" in params
    assert "model__colsample_bytree" in params
    assert "model__reg_alpha" in params
    assert "model__reg_lambda" in params
    assert params["model__objective"] == "reg:absoluteerror"
    assert params["model__log_c"] == 1.0
    assert params["model__random_state"] == 1234


def test_optimize_hyperparameters_execution(synthetic_data):
    """Testa a execução de optimize_hyperparameters com mocks para rapidez."""
    X, y, groups = synthetic_data

    with patch(
        "optimization.optimize.cross_val_score",
        return_value=np.array([-30000.0, -32000.0]),
    ):
        best_params, best_mae = optimize_hyperparameters(
            X=X,
            y=y,
            n_trials=2,
            k_folds=2,
            random_state=42,
            feature_groups=groups,
        )

        assert isinstance(best_params, dict)
        assert isinstance(best_mae, float)
        assert best_mae == 31000.0


def test_optimize_hyperparameters_trial_failure(synthetic_data):
    """Testa tratamento de erro quando um trial falha durante o cross_val_score."""
    X, y, groups = synthetic_data

    with patch(
        "optimization.optimize.cross_val_score",
        side_effect=RuntimeError("Falha proposital de cálculo"),
    ):
        best_params, best_mae = optimize_hyperparameters(
            X=X,
            y=y,
            n_trials=1,
            k_folds=2,
            random_state=42,
            feature_groups=groups,
        )

        assert isinstance(best_params, dict)
        assert best_mae == float("inf")
