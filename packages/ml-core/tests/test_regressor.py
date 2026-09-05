"""Suíte de testes unitários para o estimador Regressor encapsulado em XGBoost com LogCpTransformer."""

import unittest

import numpy as np
import pandas as pd
from sklearn.base import clone
from ml_core.estimators import Regressor, RegressionMetrics


class TestRegressor(unittest.TestCase):
    """Testes unitários para a classe Regressor."""

    def setUp(self) -> None:
        """Gera dados sintéticos para treinamento e testes."""
        np.random.seed(42)
        n_samples = 100

        self.X = pd.DataFrame({
            "area_m2": np.random.uniform(30.0, 200.0, n_samples),
            "quartos": np.random.randint(1, 5, n_samples),
            "vagas": np.random.randint(1, 3, n_samples),
        })

        self.y = pd.Series(
            50000.0 + 3000.0 * self.X["area_m2"] + 20000.0 * self.X["quartos"] + np.random.normal(0, 10000, n_samples),
            name="preco",
        )

    def test_default_initialization(self) -> None:
        """Garante que o Regressor pode ser instanciado com as configurações padrão."""
        model = Regressor()
        self.assertEqual(model.n_estimators, 100)
        self.assertEqual(model.max_depth, 6)
        self.assertEqual(model.learning_rate, 0.1)
        self.assertEqual(model.objective, "reg:absoluteerror")
        self.assertEqual(model.log_c, 1.0)

    def test_fit_and_predict(self) -> None:
        """Testa o ciclo de fit e predict do estimador com conversão logarítmica desfeita."""
        model = Regressor(n_estimators=50, max_depth=4, random_state=42)
        model.fit(self.X, self.y)

        self.assertTrue(model.__sklearn_is_fitted__())
        self.assertEqual(model.n_features_in_, 3)

        preds = model.predict(self.X)
        self.assertEqual(preds.shape, (len(self.X),))
        self.assertTrue(np.all(np.isfinite(preds)))
        # Previsões devem estar na faixa de preços em reais (positivas e > 10.000)
        self.assertTrue(np.all(preds > 10000.0))

    def test_evaluate(self) -> None:
        """Testa a geração do relatório de métricas via método evaluate."""
        model = Regressor(n_estimators=50, max_depth=4, random_state=42)
        model.fit(self.X, self.y)

        metrics = model.evaluate(self.X, self.y)
        self.assertIsInstance(metrics, RegressionMetrics)
        self.assertGreater(metrics.r2, 0.8)
        self.assertGreater(metrics.rmse, 0.0)

    def test_set_params_updates_fitted_estimator(self) -> None:
        """Garante que set_params altera os parâmetros e reflete no novo fit."""
        model = Regressor(n_estimators=10, max_depth=3, random_state=42)
        model.set_params(max_depth=8, n_estimators=20, objective="reg:absoluteerror")
        self.assertEqual(model.max_depth, 8)
        self.assertEqual(model.n_estimators, 20)

        model.fit(self.X, self.y)
        self.assertEqual(model.estimator_.regressor.max_depth, 8)
        self.assertEqual(model.estimator_.regressor.n_estimators, 20)
        self.assertEqual(model.estimator_.regressor.objective, "reg:absoluteerror")

    def test_sklearn_clone_compatibility(self) -> None:
        """Verifica se o modelo é compatível com sklearn.base.clone."""
        model = Regressor(n_estimators=30, max_depth=5, objective="reg:absoluteerror")
        cloned_model = clone(model)

        self.assertEqual(cloned_model.n_estimators, 30)
        self.assertEqual(cloned_model.max_depth, 5)
        self.assertEqual(cloned_model.objective, "reg:absoluteerror")
        self.assertFalse(cloned_model.__sklearn_is_fitted__())


if __name__ == "__main__":
    unittest.main()
