"""Suíte de testes unitários para a classe Regressor e integração com Scikit-Learn."""

import numpy as np
import pandas as pd
import pytest
from ml_core.estimators import RegressionMetrics, Regressor
from sklearn.base import clone
from sklearn.exceptions import NotFittedError


@pytest.fixture
def sample_regression_data():
    """Gera conjunto sintético de dados para regressão."""
    np.random.seed(42)
    n_samples = 80
    X = pd.DataFrame(
        {
            "area_m2": np.random.uniform(40.0, 180.0, n_samples),
            "quartos": np.random.randint(1, 5, n_samples),
            "vagas": np.random.randint(1, 3, n_samples),
        }
    )
    y = pd.Series(
        60_000.0
        + 3500.0 * X["area_m2"]
        + 25_000.0 * X["quartos"]
        + np.random.normal(0, 5000, n_samples),
        name="preco",
    )
    return X, y


def test_default_initialization():
    """Garante inicialização correta com parâmetros padrão."""
    model = Regressor()
    assert model.n_estimators == 100
    assert model.max_depth == 6
    assert model.learning_rate == 0.1
    assert model.min_child_weight == 1
    assert model.subsample == 1.0
    assert model.colsample_bytree == 1.0
    assert model.reg_alpha == 0.0
    assert model.reg_lambda == 1.0
    assert model.objective == "reg:absoluteerror"
    assert model.log_c == 1.0
    assert model.random_state == 42
    assert not model.__sklearn_is_fitted__()


def test_fit_and_predict_dataframe(sample_regression_data):
    """Testa o ajuste e inferência com entradas do tipo pandas.DataFrame."""
    X, y = sample_regression_data
    model = Regressor(n_estimators=30, max_depth=3, random_state=42)
    fitted_model = model.fit(X, y)

    assert fitted_model is model
    assert model.__sklearn_is_fitted__()
    assert model.n_features_in_ == 3
    assert list(model.feature_names_in_) == ["area_m2", "quartos", "vagas"]

    preds = model.predict(X)
    assert isinstance(preds, np.ndarray)
    assert preds.shape == (len(X),)
    assert np.all(np.isfinite(preds))
    # Previsões revertidas da escala logarítmica devem ser valores monetários positivos
    assert np.all(preds > 10_000.0)


def test_fit_and_predict_numpy_array(sample_regression_data):
    """Testa o ajuste e inferência com entradas do tipo numpy.ndarray ou listas."""
    X_df, y_ser = sample_regression_data
    X_arr = X_df.to_numpy()
    y_arr = y_ser.to_numpy()

    model = Regressor(n_estimators=20, max_depth=3, random_state=42)
    model.fit(X_arr, y_arr)

    assert model.feature_names_in_ is None
    assert model.n_features_in_ == 3

    preds = model.predict(X_arr)
    assert preds.shape == (len(X_arr),)
    assert np.all(preds > 0)


def test_fit_empty_y_raises_value_error(sample_regression_data):
    """Valida que fit levanta ValueError quando y está vazio."""
    X, _ = sample_regression_data
    model = Regressor()

    with pytest.raises(ValueError, match="não pode estar vazio"):
        model.fit(X, [])


def test_predict_before_fit_raises_not_fitted_error(sample_regression_data):
    """Valida que predict e evaluate antes do fit disparam NotFittedError."""
    X, y = sample_regression_data
    model = Regressor()

    with pytest.raises(NotFittedError):
        model.predict(X)

    with pytest.raises(NotFittedError):
        model.evaluate(X, y)


def test_evaluate(sample_regression_data):
    """Testa o cálculo do relatório de métricas via método evaluate."""
    X, y = sample_regression_data
    model = Regressor(n_estimators=30, max_depth=4, random_state=42)
    model.fit(X, y)

    metrics = model.evaluate(X, y)
    assert isinstance(metrics, RegressionMetrics)
    assert metrics.r2 > 0.8
    assert metrics.rmse > 0.0
    assert metrics.mae > 0.0
    assert metrics.mape > 0.0


def test_set_params_updates_fitted_estimator(sample_regression_data):
    """Garante que set_params altera os parâmetros e reflete no novo fit."""
    X, y = sample_regression_data
    model = Regressor(n_estimators=10, max_depth=3, random_state=42)
    model.set_params(max_depth=5, n_estimators=25, learning_rate=0.05)

    assert model.max_depth == 5
    assert model.n_estimators == 25
    assert model.learning_rate == 0.05

    model.fit(X, y)
    regressor_inside = model.estimator_.regressor
    assert regressor_inside.max_depth == 5
    assert regressor_inside.n_estimators == 25
    assert regressor_inside.learning_rate == 0.05


def test_sklearn_clone_compatibility():
    """Verifica compatibilidade com a função clone do scikit-learn."""
    model = Regressor(n_estimators=40, max_depth=5, learning_rate=0.08)
    cloned_model = clone(model)

    assert cloned_model.n_estimators == 40
    assert cloned_model.max_depth == 5
    assert cloned_model.learning_rate == 0.08
    assert not cloned_model.__sklearn_is_fitted__()
