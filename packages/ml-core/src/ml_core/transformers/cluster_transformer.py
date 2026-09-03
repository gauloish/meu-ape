"""Transformador de agrupamento espacial (ClusterTransformer) baseado em K-Means.

Agrupa coordenadas de latitude e longitude em clusters espaciais identificados por rótulos numéricos.
"""

from typing import Any, Self

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.cluster import KMeans
from sklearn.utils.validation import check_is_fitted


class ClusterTransformer(TransformerMixin, BaseEstimator):
    """Transformador scikit-learn que aplica o algoritmo K-Means nas coordenadas geográficas.

    Ajusta o modelo K-Means durante a etapa `fit` e atribui rótulos de cluster
    durante a etapa `transform`, garantindo que não haja vazamento de dados (Data Leakage).

    Atributos:
        n_clusters (int): Número de clusters a serem formados pelo K-Means. Padrão: 8.
        random_state (int): Semente aleatória para reprodutibilidade. Padrão: 42.
        lat_feature (str): Nome da coluna de latitude. Padrão: 'latitude'.
        lon_feature (str): Nome da coluna de longitude. Padrão: 'longitude'.
        feature (str): Nome da nova coluna contendo o rótulo do cluster. Padrão: 'cluster'.
        kmeans_ (KMeans): Instância treinada do modelo KMeans após a execução de `fit`.

    Example:
        >>> transformer = ClusterTransformer(n_clusters=5, random_state=42)
        >>> transformer.fit(df_train)
        >>> df_transformed = transformer.transform(df_test)
    """

    def __init__(
        self,
        n_clusters: int = 8,
        random_state: int = 42,
        lat_feature: str = "latitude",
        lon_feature: str = "longitude",
        feature: str = "cluster",
    ) -> None:
        """Inicializa o transformador de cluster espacial.

        Args:
            n_clusters (int): Número de clusters espaciais. Padrão: 5.
            random_state (int): Semente de aleatoriedade. Padrão: 42.
            lat_feature (str): Nome da coluna de latitude. Padrão: 'latitude'.
            lon_feature (str): Nome da coluna de longitude. Padrão: 'longitude'.
            feature (str): Nome da coluna resultante. Padrão: 'cluster'.
        """
        self.n_clusters: int = n_clusters
        self.random_state: int = random_state
        self.lat_feature: str = lat_feature
        self.lon_feature: str = lon_feature
        self.feature: str = feature

    def fit(self, X: pd.DataFrame, y: Any = None) -> Self:
        """Ajusta o modelo K-Means utilizando os dados de treinamento com coordenadas válidas.

        Args:
            X (pd.DataFrame): DataFrame de treinamento contendo as colunas de coordenadas.
            y (Any, optional): Ignorado. Mantido por compatibilidade com a API scikit-learn.

        Returns:
            Self: Instância do próprio transformador ajustado.
        """
        self._validate_input(X)

        coords = X[[self.lat_feature, self.lon_feature]].to_numpy(dtype=np.float64)
        valid_mask = ~np.isnan(coords).any(axis=1)
        valid_coords = coords[valid_mask]

        if len(valid_coords) > 0:
            actual_n_clusters = min(self.n_clusters, len(valid_coords))
            self.kmeans_ = KMeans(
                n_clusters=actual_n_clusters,
                random_state=self.random_state,
                n_init="auto",
            )
            self.kmeans_.fit(valid_coords)
        else:
            self.kmeans_ = KMeans(
                n_clusters=1,
                random_state=self.random_state,
                n_init="auto",
            )
            self.kmeans_.fit(np.zeros((1, 2)))

        self.n_features_in_ = X.shape[1]
        self.feature_names_in_ = np.array(X.columns, dtype=object)
        self._is_fitted = True

        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """Atribui cada amostra ao cluster mais próximo utilizando o modelo treinado.

        Args:
            X (pd.DataFrame): DataFrame de entrada contendo as coordenadas geográficas.

        Returns:
            pd.DataFrame: Novo DataFrame com a coluna de cluster adicionada (NaN para amostras sem coordenadas).

        Raises:
            NotFittedError: Se o transformador ainda não tiver sido ajustado via `fit`.
        """
        check_is_fitted(self, attributes=["kmeans_"])
        self._validate_input(X)

        X_out = X.copy()
        coords = X_out[[self.lat_feature, self.lon_feature]].to_numpy(dtype=np.float64)
        valid_mask = ~np.isnan(coords).any(axis=1)

        X_out[self.feature] = np.nan

        if valid_mask.any():
            preds = self.kmeans_.predict(coords[valid_mask])
            X_out.loc[valid_mask, self.feature] = preds

        return X_out

    def _validate_input(self, X: pd.DataFrame | Any) -> None:
        """Valida se a entrada é um DataFrame e se contém as colunas de coordenadas necessárias.

        Args:
            X (pd.DataFrame | Any): Objeto de entrada.

        Raises:
            TypeError: Se a entrada não for um pandas DataFrame.
            ValueError: Se faltarem colunas de coordenadas necessárias.
        """
        if not isinstance(X, pd.DataFrame):
            raise TypeError(f"{self.__class__.__name__} espera um pandas.DataFrame, mas recebeu {type(X).__name__}.")

        required = {self.lat_feature, self.lon_feature}
        missing = required - set(X.columns)

        if missing:
            raise ValueError(f"Colunas obrigatórias ausentes no DataFrame: {sorted(missing)}")

    def __sklearn_is_fitted__(self) -> bool:
        """Verifica se o transformador foi ajustado."""
        return hasattr(self, "_is_fitted") and self._is_fitted
