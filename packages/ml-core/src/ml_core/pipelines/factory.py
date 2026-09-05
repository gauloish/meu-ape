"""Fábrica para construção de pipelines de Machine Learning com pré-processamento e estimador Regressor (XGBoost)."""

from typing import Any

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder, OrdinalEncoder

from ml_core.estimators import Regressor

from .constants import BINS_INFO, PAIRS, POINTS
from .feature_groups import FeatureGroups, get_default_feature_groups
from ..transformers import (
    BinsDiscretizer,
    ClusterTransformer,
    GeodesicDistanceTransformer,
    RatioTransformer,
)


def _cast_bool_to_float(X: Any) -> np.ndarray:
    """Converte colunas booleanas (incluindo pd.NA, None e tipos nullable) para float com np.nan.

    Args:
        X (Any): Estrutura de dados contendo valores booleanos.

    Returns:
        np.ndarray: Array numpy com valores convertidos para float64.
    """
    if isinstance(X, pd.DataFrame | pd.Series):
        return X.astype(float).to_numpy()

    return np.asarray(X, dtype=np.float64)


def get_transformers(
    bins_discretizer_enabled: bool = True,
    cluster_enabled: bool = True,
    geodesic_distance_enabled: bool = True,
    ratio_enabled: bool = True,
) -> Pipeline:
    """Constrói o pipeline de engenharia de características composto.

    Args:
        bins_discretizer_enabled (bool): Se True, ativa a discretização por bins. Padrão: True.
        cluster_enabled (bool): Se True, ativa a transformação por clusters. Padrão: True.
        geodesic_distance_enabled (bool): Se True, calcula distâncias geodésicas. Padrão: True.
        ratio_enabled (bool): Se True, calcula razões entre colunas numéricas. Padrão: True.

    Returns:
        Pipeline: Pipeline do scikit-learn contendo os transformadores selecionados.
    """
    steps: list[tuple[str, TransformerMixin]] = []

    # 1. Transformer para Discretizador por Bins
    if bins_discretizer_enabled:
        bin_discretizer = BinsDiscretizer(bins_info=BINS_INFO)
        steps.append(("bins_discretizer", bin_discretizer))

    # 2. Transformer para Clusterizador
    if cluster_enabled:
        cluster_transformer = ClusterTransformer()
        steps.append(("cluster_transformer", cluster_transformer))

    # 3. Transformer para Distâncias Geodésicas
    if geodesic_distance_enabled:
        geodesic_distance_transformer = GeodesicDistanceTransformer(points=POINTS)
        steps.append(("geodesic_distance_transformer", geodesic_distance_transformer))

    # 4. Transformer para Razões entre Features
    if ratio_enabled:
        ratio_transformer = RatioTransformer(pairs=PAIRS)
        steps.append(("ratio_transformer", ratio_transformer))

    return Pipeline(steps=steps)


def get_preprocessor(
    feature_groups: FeatureGroups | None = None,
    remainder: str = "drop",
    sparse_threshold: float = 0.0,
) -> ColumnTransformer:
    """Constrói o `ColumnTransformer` com sub-pipelines dedicados para cada tipo de feature.

    Sub-pipelines aplicados:
    - **Numéricas:** `SimpleImputer(strategy='median')`.
    - **Categóricas:** `SimpleImputer(strategy='most_frequent')` + `OneHotEncoder(handle_unknown='ignore')`.
    - **Ordinais:** `SimpleImputer(strategy='most_frequent')` + `OrdinalEncoder(unknown_value=-1)`.
    - **Booleanas:** Conversão para float numérico + `SimpleImputer(strategy='most_frequent')`.

    Args:
        feature_groups (FeatureGroups | None): Agrupamento de features por tipo. Se None, utiliza `get_default_feature_groups()`.
        remainder (str): Ação para colunas não especificadas ('drop' ou 'passthrough'). Padrão: 'drop'.
        sparse_threshold (float): Limiar para saída esparsa no ColumnTransformer. Padrão: 0.0.

    Returns:
        ColumnTransformer: Transformador de colunas configurado.
    """
    if feature_groups is None:
        feature_groups = get_default_feature_groups()

    transformers: list[tuple[str, Pipeline, list[str]]] = []

    # 1. Pipeline para Features Numéricas
    if feature_groups.numeric_features:
        numeric_pipeline = Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="median", keep_empty_features=True)),
            ]
        )
        transformers.append(
            ("numeric", numeric_pipeline, feature_groups.numeric_features)
        )

    # 2. Pipeline para Features Categóricas
    if feature_groups.categorical_features:
        categorical_pipeline = Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="most_frequent", keep_empty_features=True)),
                (
                    "encoder",
                    OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                ),
            ]
        )
        transformers.append(
            ("categorical", categorical_pipeline, feature_groups.categorical_features)
        )

    # 3. Pipeline para Features Ordinais
    if feature_groups.ordinal_features:
        ordinal_pipeline = Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="most_frequent", keep_empty_features=True)),
                (
                    "encoder",
                    OrdinalEncoder(
                        handle_unknown="use_encoded_value",
                        unknown_value=-1,
                    ),
                ),
            ]
        )
        transformers.append(
            ("ordinal", ordinal_pipeline, feature_groups.ordinal_features)
        )

    # 4. Pipeline para Features Booleanas
    if feature_groups.boolean_features:
        boolean_pipeline = Pipeline(
            steps=[
                (
                    "cast",
                    FunctionTransformer(
                        _cast_bool_to_float,
                        feature_names_out="one-to-one",
                    ),
                ),
                ("imputer", SimpleImputer(strategy="most_frequent", keep_empty_features=True)),
            ]
        )
        transformers.append(
            ("boolean", boolean_pipeline, feature_groups.boolean_features)
        )

    return ColumnTransformer(
        transformers=transformers,
        remainder=remainder,
        sparse_threshold=sparse_threshold,
    )


def create_training_pipeline(
    model: BaseEstimator | None = None,
    feature_groups: FeatureGroups | None = None,
    remainder: str = "drop",
    **model_kwargs: Any,
) -> Pipeline:
    """Cria a pipeline completa de treinamento contendo transformadores, pré-processamento e o estimador Regressor.

    Args:
        model (BaseEstimator | None): Instância do estimador a utilizar. Se None, instancia um `Regressor`.
        feature_groups (FeatureGroups | None): Definição de grupos de colunas por tipo.
        remainder (str): Comportamento para colunas extras no preprocessor. Padrão: 'drop'.
        **model_kwargs (Any): Argumentos adicionais para inicializar o `Regressor` caso `model` seja None.

    Returns:
        Pipeline: Pipeline de Machine Learning completo e pronto para fit/predict.
    """
    transformers = get_transformers()
    preprocessor = get_preprocessor(
        feature_groups=feature_groups,
        remainder=remainder,
    )

    if model is None:
        model = Regressor(**model_kwargs)

    return Pipeline(
        steps=[
            ("transformers", transformers),
            ("preprocessor", preprocessor),
            ("model", model),
        ]
    )
