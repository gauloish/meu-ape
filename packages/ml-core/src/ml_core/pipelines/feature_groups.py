"""Definição de agrupamento e esquemas de features para o pipeline de Machine Learning."""

from dataclasses import dataclass, field
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
        """Retorna todas as features combinadas de todos os grupos.

        Returns:
            list[str]: Lista contendo todos os nomes de colunas.
        """
        return (
            self.numeric_features
            + self.categorical_features
            + self.ordinal_features
            + self.boolean_features
        )


def get_default_feature_groups() -> FeatureGroups:
    """Retorna os grupos de características padrão do esquema de dados imobiliários.

    Returns:
        FeatureGroups: Agrupamento padrão de colunas numéricas, categóricas, ordinais e booleanas.
    """
    return FeatureGroups(
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


def get_feature_groups(X: pd.DataFrame | None = None) -> FeatureGroups:
    """Obtém os grupos de features dinamicamente a partir de um DataFrame ou retorna o agrupamento padrão.

    Args:
        X (pd.DataFrame | None): DataFrame com os dados de entrada. Se None, retorna o esquema padrão.

    Returns:
        FeatureGroups: Instância contendo as colunas agrupadas por tipo.

    Raises:
        TypeError: Se X for fornecido mas não for um pd.DataFrame.
    """
    if X is None:
        return get_default_feature_groups()

    if not isinstance(X, pd.DataFrame):
        raise TypeError("X deve ser um pd.DataFrame.")

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
