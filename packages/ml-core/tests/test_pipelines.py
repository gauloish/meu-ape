"""Suíte de testes de integração e unidade para as pipelines do ml-core."""

import unittest

import numpy as np
import pandas as pd
from ml_core.estimators import Regressor
from ml_core.pipelines import (
    FeatureGroups,
    create_training_pipeline,
    get_default_feature_groups,
    get_preprocessor,
)
from sklearn.compose import ColumnTransformer
from sklearn.model_selection import cross_validate
from sklearn.pipeline import Pipeline


class TestTrainingPipeline(unittest.TestCase):
    """Testes para construção e execução do pipeline de treinamento."""

    def setUp(self) -> None:
        """Cria um dataset heterogêneo simulando dados brutos de imóveis com valores ausentes."""
        np.random.seed(42)
        n_samples = 300

        area = np.random.uniform(30.0, 300.0, n_samples)
        quartos = np.random.choice([1, 2, 3, 4, 5], size=n_samples)
        banheiros = np.random.choice([1, 2, 3, 4], size=n_samples)
        vagas = np.random.choice([1, 2, 3], size=n_samples)
        condominio = np.random.uniform(100.0, 1000.0, n_samples)
        latitude = np.random.uniform(-16.75, -16.65, n_samples)
        longitude = np.random.uniform(-49.30, -49.20, n_samples)

        # Injeta NaNs simulando dados brutos do mundo real
        area[np.random.choice(n_samples, size=15, replace=False)] = np.nan
        quartos_series = pd.Series(quartos, dtype="Int64")
        quartos_series[np.random.choice(n_samples, size=15, replace=False)] = pd.NA

        self.df = pd.DataFrame(
            {
                # Numéricas
                "area_m2": area,
                "quartos": quartos_series,
                "banheiros": banheiros,
                "vagas": vagas,
                "condominio": condominio,
                "latitude": latitude,
                "longitude": longitude,
                # Categóricas
                "tipo_imovel": np.random.choice(
                    ["apartamento", "casa", "cobertura", None],
                    size=n_samples,
                    p=[0.5, 0.3, 0.15, 0.05],
                ),
                "bairro": np.random.choice(
                    [
                        "Setor Bueno",
                        "Setor Marista",
                        "Jardim Goias",
                        "Setor Oeste",
                        None,
                    ],
                    size=n_samples,
                    p=[0.3, 0.3, 0.2, 0.15, 0.05],
                ),
                # Ordinais
                "faixa_area": np.random.choice(
                    ["pequeno", "medio", "grande", None],
                    size=n_samples,
                    p=[0.3, 0.4, 0.25, 0.05],
                ),
                # Booleanas
                "piscina": np.random.choice(
                    [True, False, None],
                    size=n_samples,
                    p=[0.45, 0.45, 0.1],
                ),
                "academia": np.random.choice(
                    [True, False, None],
                    size=n_samples,
                    p=[0.45, 0.45, 0.1],
                ),
            }
        )

        # Target contínuo realista com distribuição assimétrica
        base_price = (
            100_000
            + 4000.0 * np.nan_to_num(area, nan=70.0)
            + 30_000.0 * np.nan_to_num(quartos, nan=2)
            + np.random.normal(0, 25_000, n_samples)
        )
        self.y = pd.Series(np.maximum(80_000, base_price), name="preco")

        self.groups = FeatureGroups(
            numeric_features=["area_m2", "quartos", "banheiros", "vagas", "condominio", "latitude", "longitude"],
            categorical_features=["tipo_imovel", "bairro"],
            ordinal_features=["faixa_area"],
            boolean_features=["piscina", "academia"],
        )

    def test_feature_groups_properties(self) -> None:
        """Testa o agrupamento de features e a resolução de get_default_feature_groups."""
        self.assertEqual(len(self.groups.all_features), 12)

        default_groups = get_default_feature_groups()
        self.assertIsInstance(default_groups, FeatureGroups)
        self.assertIn("area_m2", default_groups.numeric_features)

    def test_get_preprocessor_structure(self) -> None:
        """Testa se o get_preprocessor constrói um ColumnTransformer com os 4 sub-pipelines."""
        preprocessor = get_preprocessor(self.groups)

        self.assertIsInstance(preprocessor, ColumnTransformer)
        transformer_names = [name for name, _, _ in preprocessor.transformers]

        self.assertIn("numeric", transformer_names)
        self.assertIn("categorical", transformer_names)
        self.assertIn("ordinal", transformer_names)
        self.assertIn("boolean", transformer_names)

    def test_preprocessor_transform_dense(self) -> None:
        """Testa a transformação do preprocessor tratando valores ausentes."""
        preprocessor = get_preprocessor(self.groups)
        X_trans = preprocessor.fit_transform(self.df)

        self.assertIsInstance(X_trans, np.ndarray)
        self.assertEqual(X_trans.shape[0], len(self.df))
        self.assertTrue(np.all(np.isfinite(X_trans)))
        self.assertFalse(np.isnan(X_trans).any())

    def test_create_training_pipeline_structure(self) -> None:
        """Testa a criação da pipeline completa com o Regressor anexado."""
        pipeline = create_training_pipeline(feature_groups=self.groups, random_state=42)

        self.assertIsInstance(pipeline, Pipeline)
        self.assertEqual(len(pipeline.steps), 3)
        self.assertEqual(pipeline.steps[0][0], "transformers")
        self.assertEqual(pipeline.steps[1][0], "preprocessor")
        self.assertIsInstance(pipeline.steps[1][1], ColumnTransformer)
        self.assertEqual(pipeline.steps[2][0], "model")
        self.assertIsInstance(pipeline.steps[2][1], Regressor)

    def test_pipeline_fit_and_predict_end_to_end(self) -> None:
        """Testa o ciclo de vida completo (fit, predict, evaluate) da pipeline."""
        pipeline = create_training_pipeline(
            feature_groups=self.groups,
            random_state=42,
        )

        pipeline.fit(self.df, self.y)
        preds = pipeline.predict(self.df)

        self.assertEqual(preds.shape, (len(self.df),))
        self.assertTrue(np.all(np.isfinite(preds)))

        # Extração de métricas com o preprocessor aplicado no modelo final
        preprocessor = Pipeline([
            ("transformers", pipeline.named_steps["transformers"]),
            ("preprocessor", pipeline.named_steps["preprocessor"]),
        ])
        X_transformed = preprocessor.transform(self.df)
        metrics = pipeline.named_steps["model"].evaluate(X_transformed, self.y)

        self.assertGreater(metrics.rmse, 0.0)
        self.assertGreater(metrics.r2, 0.0)

    def test_pipeline_cross_validate(self) -> None:
        """Testa a execução de cross_validate no pipeline completo."""
        pipeline = create_training_pipeline(
            feature_groups=self.groups,
            random_state=42,
        )

        cv_results = cross_validate(
            pipeline,
            self.df,
            self.y,
            cv=2,
            scoring=["neg_root_mean_squared_error", "r2"],
        )

        self.assertIn("test_neg_root_mean_squared_error", cv_results)
        self.assertEqual(len(cv_results["test_neg_root_mean_squared_error"]), 2)


if __name__ == "__main__":
    unittest.main()
