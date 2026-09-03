"""Definição de agrupamento e esquemas de features para o pipeline de Machine Learning."""

from dataclasses import dataclass, field
from typing import Any

import pandas as pd


@dataclass
class FeatureGroups:
    """Estrutura de dados que armazena os nomes das colunas agrupados por tipo.

    Attributes:
        numeric_features (list[str]): Colunas numéricas contínuas e discretas (imputação por mediana).
        categorical_features (list[str]): Colunas categóricas nominais (imputação por moda + OneHotEncoder).
        ordinal_features (list[str]): Colunas categóricas ordinais (imputação por moda + OrdinalEncoder).
        boolean_features (list[str]): Colunas booleanas (imputação por moda + pass-through).
    """

    numeric_features: list[str] = field(default_factory=list)
    categorical_features: list[str] = field(default_factory=list)
    ordinal_features: list[str] = field(default_factory=list)
    boolean_features: list[str] = field(default_factory=list)

    @property
    def all_features(self) -> list[str]:
        """Retorna todas as features combinadas de todos os grupos."""
        return (
            self.numeric_features
            + self.categorical_features
            + self.ordinal_features
            + self.boolean_features
        )


def get_default_feature_groups(X: pd.DataFrame | Any | None = None) -> FeatureGroups:
    """Função de configuração para resolução dos grupos de features.

    Inferência dinâmica quando um `pd.DataFrame` é fornecido, ou lista completa padrão
    do domínio quando `X` for `None`.

    Args:
        X (pd.DataFrame | Any | None): DataFrame opcional para inferência dinâmica de tipos.

    Returns:
        FeatureGroups: Instância configurada com as listas de colunas para cada sub-pipeline.
    """
    if isinstance(X, pd.DataFrame):
        numeric_features = X.select_dtypes(
            include=["number", "Int64", "Float64", "int64", "float64", "int32", "float32"]
        ).columns.to_list()

        categorical_features = X.select_dtypes(
            include=["object", "string"]
        ).columns.to_list()

        ordinal_features = X.select_dtypes(
            include=["category"]
        ).columns.to_list()

        boolean_features = X.select_dtypes(
            include=["bool", "boolean"]
        ).columns.to_list()

    return FeatureGroups(
        numeric_features=numeric_features,
        categorical_features=categorical_features,
        ordinal_features=ordinal_features,
        boolean_features=boolean_features,
    )
