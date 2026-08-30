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

    Este é o ponto de entrada (placeholder) onde a lógica de seleção de colunas
    (manual ou inferida dinamicamente pelo DataFrame `X`) deve ser inserida.

    Args:
        X (pd.DataFrame | Any | None): DataFrame opcional para inferência dinâmica de tipos.

    Returns:
        FeatureGroups: Instância configurada com as listas de colunas para cada sub-pipeline.
    """
    # =========================================================================
    # TODO: Adicione suas colunas aqui
    # =========================================================================
    # Exemplo de preenchimento manual:
    # numeric_features = ["area_m2", "quartos", "banheiros", "vagas", "latitude", "longitude"]
    # categorical_features = ["tipo_imovel", "bairro"]
    # ordinal_features = ["faixa_area", "faixa_condominio"]
    # boolean_features = ["piscina", "academia", "varanda"]

    numeric_features: list[str] = []
    categorical_features: list[str] = []
    ordinal_features: list[str] = []
    boolean_features: list[str] = []

    if isinstance(X, pd.DataFrame):
        # TODO: Se desejar, implemente aqui a lógica de separação automática baseada no DataFrame X:
        # e.g. numeric_features = X.select_dtypes(include=["int64", "float64"]).columns.tolist()
        pass

    return FeatureGroups(
        numeric_features=numeric_features,
        categorical_features=categorical_features,
        ordinal_features=ordinal_features,
        boolean_features=boolean_features,
    )
