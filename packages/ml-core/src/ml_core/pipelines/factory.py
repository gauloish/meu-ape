"""Fábrica para construção de pipelines de Machine Learning com pré-processamento e estimador MoE."""

from typing import Any

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder, OrdinalEncoder

from ml_core.estimators import MoEEstimator

from .feature_groups import FeatureGroups, get_default_feature_groups


def _cast_bool_to_float(X: Any) -> np.ndarray:
    """Converte colunas booleanas (incluindo pd.NA, None e tipos nullable) para float com np.nan."""
    if isinstance(X, pd.DataFrame | pd.Series):
        return X.astype(float).to_numpy()
    return np.asarray(X, dtype=np.float64)


def get_preprocessor(
    feature_groups: FeatureGroups | None = None,
    remainder: str = "drop",
    sparse_threshold: float = 0.0,
) -> ColumnTransformer:
    """Constrói o `ColumnTransformer` com sub-pipelines dedicados para cada tipo de feature.

    Sub-pipelines aplicados:
    - **Numéricas (Discretas e Contínuas):** `SimpleImputer(strategy='median')`.
    - **Categóricas:** `SimpleImputer(strategy='most_frequent')` + `OneHotEncoder(handle_unknown='ignore')`.
    - **Ordinais:** `SimpleImputer(strategy='most_frequent')` + `OrdinalEncoder(handle_unknown='use_encoded_value', unknown_value=-1)`.
    - **Booleanas:** Conversão para float numérico + `SimpleImputer(strategy='most_frequent')`.

    Args:
        feature_groups (FeatureGroups | None): Agrupamento de features por tipo. Se None, utiliza `get_default_feature_groups()`.
        remainder (str): Ação para colunas não especificadas ('drop' ou 'passthrough'). Padrão: 'drop'.
        sparse_threshold (float): Limiar para saída esparsa no ColumnTransformer. Padrão: 0.0 (retorna arrays densos).

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
                ("imputer", SimpleImputer(strategy="median")),
            ]
        )
        transformers.append(
            ("numeric", numeric_pipeline, feature_groups.numeric_features)
        )

    # 2. Pipeline para Features Categóricas
    if feature_groups.categorical_features:
        categorical_pipeline = Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="most_frequent")),
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
                ("imputer", SimpleImputer(strategy="most_frequent")),
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
                ("imputer", SimpleImputer(strategy="most_frequent")),
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
    """Cria o pipeline completo conectando o pré-processamento ao modelo preditivo (MoEEstimator).

    Estrutura do pipeline:
    ```
    Pipeline(steps=[
        ('preprocessor', ColumnTransformer(...)),
        ('model', MoEEstimator(...))
    ])
    ```

    Args:
        model (BaseEstimator | None): Estimador final do pipeline. Se None, instancia `MoEEstimator(**model_kwargs)`.
        feature_groups (FeatureGroups | None): Agrupamento de features por tipo.
        remainder (str): Ação para colunas residuais ('drop' ou 'passthrough'). Padrão: 'drop'.
        **model_kwargs (Any): Argumentos opcionais repassados para a instanciação do `MoEEstimator` se `model` for None.

    Returns:
        Pipeline: Instância de `sklearn.pipeline.Pipeline` pronta para `fit`, `predict` e `cross_validate`.

    Example:
        >>> from ml_core.pipelines import FeatureGroups, create_training_pipeline
        >>> groups = FeatureGroups(
        ...     numeric_features=["area_m2", "quartos"],
        ...     categorical_features=["tipo_imovel"],
        ...     boolean_features=["piscina"],
        ... )
        >>> pipeline = create_training_pipeline(feature_groups=groups)
        >>> pipeline.fit(X_train, y_train)
        >>> y_pred = pipeline.predict(X_test)
    """
    preprocessor = get_preprocessor(
        feature_groups=feature_groups,
        remainder=remainder,
    )

    if model is None:
        model = MoEEstimator(**model_kwargs)

    return Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("model", model),
        ]
    )
