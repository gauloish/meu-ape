"""Suíte abrangente de testes de unidade e integração para o MoEEstimator."""

import unittest

import numpy as np
import pandas as pd
from ml_core.estimators import (
    GatingMetrics,
    MoEEstimator,
    MoEMetricsReport,
    RegressionMetrics,
)
from sklearn.base import clone
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import cross_validate
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


class TestMoEEstimator(unittest.TestCase):
    """Testes unitários e de integração para a classe MoEEstimator."""

    def setUp(self) -> None:
        """Gera dataset sintético simulando dados imobiliários."""
        np.random.seed(42)
        n_samples = 300
        n_features = 5

        self.X_np = np.random.randn(n_samples, n_features)

        # Gera variável de preço contínua com distribuição assimétrica (típica de imóveis)
        base_price = (
            100_000 + 50_000 * np.abs(self.X_np[:, 0]) + 20_000 * (self.X_np[:, 1] ** 2)
        )
        noise = np.random.normal(0, 10_000, n_samples)
        self.y_np = np.maximum(50_000, base_price + noise)

        self.feature_names = [f"feat_{i}" for i in range(n_features)]
        self.X_df = pd.DataFrame(self.X_np, columns=self.feature_names)
        self.y_series = pd.Series(self.y_np, name="preco")

    def test_fit_and_predict_numpy(self) -> None:
        """Testa fit e predict com arrays NumPy."""
        moe = MoEEstimator(random_state=42)
        moe.fit(self.X_np, self.y_np)

        self.assertTrue(moe.__sklearn_is_fitted__())
        self.assertTrue(hasattr(moe, "gating_network_"))
        self.assertTrue(hasattr(moe, "experts_"))
        self.assertEqual(len(moe.experts_), 3)

        preds = moe.predict(self.X_np)
        self.assertIsInstance(preds, np.ndarray)
        self.assertEqual(preds.shape, (len(self.y_np),))
        self.assertTrue(np.all(np.isfinite(preds)))

    def test_fit_and_predict_pandas(self) -> None:
        """Testa fit e predict com DataFrame e Series do Pandas."""
        moe = MoEEstimator(random_state=42)
        moe.fit(self.X_df, self.y_series)

        self.assertEqual(moe.n_features_in_, 5)
        self.assertTrue(
            np.array_equal(
                moe.feature_names_in_, np.array(self.feature_names, dtype=object)
            )
        )

        preds = moe.predict(self.X_df)
        self.assertEqual(preds.shape, (len(self.y_series),))

    def test_soft_gating_mathematical_identity(self) -> None:
        """Testa se a predição final equivale exatamente à soma ponderada das probabilidades."""
        moe = MoEEstimator(random_state=42)
        moe.fit(self.X_df, self.y_series)

        probas = moe.predict_proba_gating(self.X_df)
        experts = moe.predict_experts(self.X_df)
        y_pred = moe.predict(self.X_df)

        # 1. Verifica propriedades das probabilidades
        self.assertEqual(probas.shape, (len(self.X_df), 3))
        np.testing.assert_allclose(np.sum(probas, axis=1), 1.0, rtol=1e-5)
        self.assertTrue(np.all(probas >= 0.0) and np.all(probas <= 1.0))

        # 2. Verifica se cada expert gerou predições
        self.assertEqual(set(experts.keys()), {"normal", "premium", "luxo"})
        expert_matrix = np.column_stack([experts[label] for label in moe.labels])

        # 3. Verifica a igualdade matemática da média ponderada
        expected_pred = np.sum(probas * expert_matrix, axis=1)
        np.testing.assert_allclose(y_pred, expected_pred, rtol=1e-6)

    def test_scikit_learn_get_set_params(self) -> None:
        """Testa conformidade com get_params e set_params para estimadores aninhados."""
        moe = MoEEstimator(random_state=42)
        params = moe.get_params(deep=True)

        self.assertIn("gating_estimator", params)
        self.assertIn("expert_normal", params)
        self.assertIn("calibration_method", params)
        self.assertIn("quantiles", params)

        # Atualiza parâmetros aninhados e de calibração
        custom_gating = RandomForestClassifier(n_estimators=10, random_state=42)
        moe.set_params(
            gating_estimator=custom_gating,
            calibration_method="isotonic",
            quantiles=(0.5, 0.85),
        )

        self.assertEqual(moe.calibration_method, "isotonic")
        self.assertEqual(moe.quantiles, (0.5, 0.85))
        self.assertIs(moe.gating_estimator, custom_gating)

    def test_clone_compatibility(self) -> None:
        """Testa se a instância pode ser clonada via sklearn.base.clone sem perda de parâmetros."""
        moe = MoEEstimator(
            calibration_method="sigmoid",
            calibration_cv=3,
            quantiles=(0.55, 0.85),
            random_state=99,
        )
        cloned_moe = clone(moe)

        self.assertEqual(cloned_moe.calibration_method, "sigmoid")
        self.assertEqual(cloned_moe.calibration_cv, 3)
        self.assertEqual(cloned_moe.quantiles, (0.55, 0.85))
        self.assertEqual(cloned_moe.random_state, 99)
        self.assertFalse(hasattr(cloned_moe, "_is_fitted"))

    def test_pipeline_and_cross_validate_integration(self) -> None:
        """Testa a integração em Pipeline e execução com cross_validate."""
        pipeline = Pipeline(
            steps=[
                ("scaler", StandardScaler()),
                ("moe", MoEEstimator(calibration_cv=2, random_state=42)),
            ]
        )

        cv_results = cross_validate(
            pipeline,
            self.X_np,
            self.y_np,
            cv=3,
            scoring=["neg_root_mean_squared_error", "r2"],
        )

        self.assertIn("test_neg_root_mean_squared_error", cv_results)
        self.assertIn("test_r2", cv_results)
        self.assertEqual(len(cv_results["test_r2"]), 3)

    def test_evaluate_method_and_pydantic_report(self) -> None:
        """Testa a extração de métricas com Pydantic V2 e invariância de estado."""
        moe = MoEEstimator(random_state=42)
        moe.fit(self.X_df, self.y_series)

        report = moe.evaluate(self.X_df, self.y_series)

        # 1. Verifica tipos Pydantic
        self.assertIsInstance(report, MoEMetricsReport)
        self.assertIsInstance(report.global_metrics, RegressionMetrics)
        self.assertIsInstance(report.gating_metrics, GatingMetrics)
        self.assertEqual(len(report.expert_metrics), 3)

        # 2. Verifica valores calculados
        self.assertGreater(report.gating_metrics.accuracy, 0.0)
        self.assertGreaterEqual(report.gating_metrics.brier_score, 0.0)
        self.assertGreater(report.global_metrics.rmse, 0.0)
        self.assertEqual(report.global_metrics.support, len(self.y_series))

        # 3. Testa conversão para dicionário e DataFrame
        report_dict = report.model_dump()
        self.assertIn("global_metrics", report_dict)
        self.assertIn("brier_score", report_dict["gating_metrics"])

        summary_df = report.summary_table()
        self.assertIsInstance(summary_df, pd.DataFrame)
        self.assertIn("RMSE", summary_df.columns)
        self.assertEqual(len(summary_df), 4)  # 3 experts + 1 global

    def test_custom_estimators_injection(self) -> None:
        """Testa injeção de dependências com estimadores heterogêneos."""
        custom_gating = RandomForestClassifier(n_estimators=10, random_state=42)
        custom_expert_normal = LinearRegression()
        custom_expert_premium = RandomForestRegressor(n_estimators=10, random_state=42)

        moe = MoEEstimator(
            gating_estimator=custom_gating,
            expert_normal=custom_expert_normal,
            expert_premium=custom_expert_premium,
            expert_luxo=None,  # Deve usar XGBoost default
            random_state=42,
        )

        moe.fit(self.X_df, self.y_series)
        preds = moe.predict(self.X_df)
        self.assertEqual(preds.shape, (len(self.y_series),))

    def test_invalid_quantiles_validation(self) -> None:
        """Testa se quantiles inválidos geram ValueError."""
        with self.assertRaises(ValueError):
            moe = MoEEstimator(quantiles=(0.9, 0.6))
            moe.fit(self.X_np, self.y_np)

        with self.assertRaises(ValueError):
            moe = MoEEstimator(quantiles=(0.5,))
            moe.fit(self.X_np, self.y_np)


if __name__ == "__main__":
    unittest.main()
