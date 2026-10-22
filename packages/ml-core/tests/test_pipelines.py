"""Suíte de testes unitários e de integração para a construção de pipelines do ml-core."""

import numpy as np
import pandas as pd
import pytest
from ml_core.estimators import Regressor
from ml_core.pipelines import (
    FeatureGroups,
    create_training_pipeline,
    get_feature_groups,
    get_preprocessor,
    get_transformers,
)
from ml_core.pipelines.factory import _cast_bool_to_float
from sklearn.compose import ColumnTransformer
from sklearn.model_selection import cross_validate
from sklearn.pipeline import Pipeline


@pytest.fixture
def sample_pipeline_data():
    """Gera um dataset heterogêneo simulando dados imobiliários com valores ausentes."""
    np.random.seed(42)
    n_samples = 150

    area = np.random.uniform(30.0, 300.0, n_samples)
    quartos = np.random.choice([1, 2, 3, 4, 5], size=n_samples)
    banheiros = np.random.choice([1, 2, 3, 4], size=n_samples)
    vagas = np.random.choice([1, 2, 3], size=n_samples)
    condominio = np.random.uniform(100.0, 1000.0, n_samples)
    latitude = np.random.uniform(-16.75, -16.65, n_samples)
    longitude = np.random.uniform(-49.30, -49.20, n_samples)

    # Injeta NaNs simulando dados brutos do mundo real
    area[np.random.choice(n_samples, size=10, replace=False)] = np.nan
    quartos_series = pd.Series(quartos, dtype="Int64")
    quartos_series[np.random.choice(n_samples, size=10, replace=False)] = pd.NA

    df = pd.DataFrame(
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
                ["Setor Bueno", "Setor Marista", "Jardim Goias", None],
                size=n_samples,
                p=[0.4, 0.3, 0.25, 0.05],
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

    base_price = (
        120_000.0
        + 4200.0 * np.nan_to_num(area, nan=70.0)
        + 30_000.0 * np.nan_to_num(quartos, nan=2)
        + np.random.normal(0, 15_000, n_samples)
    )
    y = pd.Series(np.maximum(90_000.0, base_price), name="preco")

    groups = FeatureGroups(
        numeric_features=[
            "area_m2",
            "quartos",
            "banheiros",
            "vagas",
            "condominio",
            "latitude",
            "longitude",
        ],
        categorical_features=["tipo_imovel", "bairro"],
        ordinal_features=["faixa_area"],
        boolean_features=["piscina", "academia"],
    )

    return df, y, groups


def test_feature_groups_properties_and_factory(sample_pipeline_data):
    """Testa agrupamento de features e geração automática via get_feature_groups."""
    df, _, groups = sample_pipeline_data
    assert len(groups.all_features) == 12

    # Geração dinâmica a partir do dataframe
    detected_groups = get_feature_groups(df)
    assert isinstance(detected_groups, FeatureGroups)
    assert "area_m2" in detected_groups.numeric_features
    assert "tipo_imovel" in detected_groups.categorical_features

    # TypeError para entrada inválida
    with pytest.raises(TypeError, match="deve ser um pd.DataFrame"):
        get_feature_groups([1, 2, 3])  # type: ignore


def test_cast_bool_to_float():
    """Valida a conversão de colunas booleanas com nulos para array float64."""
    s = pd.Series([True, False, None, pd.NA], dtype="boolean")
    arr = _cast_bool_to_float(s)
    assert isinstance(arr, np.ndarray)
    assert arr[0] == 1.0
    assert arr[1] == 0.0
    assert np.isnan(arr[2])
    assert np.isnan(arr[3])

    df_bool = pd.DataFrame({"b1": [True, False], "b2": [False, True]})
    arr_df = _cast_bool_to_float(df_bool)
    assert arr_df.shape == (2, 2)


def test_get_transformers():
    """Testa a construção de sub-pipeline de transformadores com ativação seletiva."""
    # Todos habilitados
    pipe_all = get_transformers()
    assert isinstance(pipe_all, Pipeline)
    assert len(pipe_all.steps) == 4
    step_names = [name for name, _ in pipe_all.steps]
    assert step_names == [
        "bins_discretizer",
        "cluster_transformer",
        "geodesic_distance_transformer",
        "ratio_transformer",
    ]

    # Desabilitando alguns
    pipe_partial = get_transformers(
        bins_discretizer_enabled=False,
        ratio_enabled=False,
    )
    partial_names = [name for name, _ in pipe_partial.steps]
    assert partial_names == ["cluster_transformer", "geodesic_distance_transformer"]


def test_get_preprocessor_structure_and_transform(sample_pipeline_data):
    """Testa se o ColumnTransformer processa corretamente todos os 4 grupos com dados densos."""
    df, _, groups = sample_pipeline_data
    preprocessor = get_preprocessor(groups)

    assert isinstance(preprocessor, ColumnTransformer)
    transformer_names = [name for name, _, _ in preprocessor.transformers]
    assert "numeric" in transformer_names
    assert "categorical" in transformer_names
    assert "ordinal" in transformer_names
    assert "boolean" in transformer_names

    X_trans = preprocessor.fit_transform(df)
    assert isinstance(X_trans, np.ndarray)
    assert X_trans.shape[0] == len(df)
    # Não devem sobrar NaNs após os imputers
    assert not np.isnan(X_trans).any()


def test_create_training_pipeline_structure(sample_pipeline_data):
    """Testa a criação da pipeline completa de treinamento."""
    _, _, groups = sample_pipeline_data
    pipeline = create_training_pipeline(feature_groups=groups, random_state=42)

    assert isinstance(pipeline, Pipeline)
    assert len(pipeline.steps) == 3
    assert pipeline.steps[0][0] == "transformers"
    assert pipeline.steps[1][0] == "preprocessor"
    assert isinstance(pipeline.steps[1][1], ColumnTransformer)
    assert pipeline.steps[2][0] == "model"
    assert isinstance(pipeline.steps[2][1], Regressor)


def test_pipeline_fit_and_predict_end_to_end(sample_pipeline_data):
    """Testa o ciclo ponta-a-ponta (fit, predict, evaluate) da pipeline completa."""
    df, y, groups = sample_pipeline_data
    pipeline = create_training_pipeline(
        feature_groups=groups,
        n_estimators=25,
        max_depth=3,
        random_state=42,
    )

    pipeline.fit(df, y)
    preds = pipeline.predict(df)

    assert preds.shape == (len(df),)
    assert np.all(np.isfinite(preds))
    assert np.all(preds > 50_000.0)

    # Avaliação do regressor
    feature_pipeline = Pipeline(
        [
            ("transformers", pipeline.named_steps["transformers"]),
            ("preprocessor", pipeline.named_steps["preprocessor"]),
        ]
    )
    X_transformed = feature_pipeline.transform(df)
    metrics = pipeline.named_steps["model"].evaluate(X_transformed, y)

    assert metrics.r2 > 0.3
    assert metrics.rmse > 0.0


def test_pipeline_cross_validate(sample_pipeline_data):
    """Testa a compatibilidade da pipeline completa com o scikit-learn cross_validate."""
    df, y, groups = sample_pipeline_data
    pipeline = create_training_pipeline(
        feature_groups=groups,
        n_estimators=15,
        max_depth=3,
        random_state=42,
    )

    cv_results = cross_validate(
        pipeline,
        df,
        y,
        cv=2,
        scoring=["neg_root_mean_squared_error", "r2"],
    )

    assert "test_neg_root_mean_squared_error" in cv_results
    assert len(cv_results["test_neg_root_mean_squared_error"]) == 2
    assert "test_r2" in cv_results
