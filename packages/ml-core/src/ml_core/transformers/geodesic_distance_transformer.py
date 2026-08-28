"""Transformador de distâncias geodésicas (GeodesicDistanceTransformer).

Calcula a distância geodésica em quilômetros (usando a fórmula de Haversine) entre cada amostra
e um conjunto de pontos de referência fixos (ex: centro urbano, aeroporto, shoppings).
"""

from typing import Any, Dict, Self, Tuple

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.metrics.pairwise import haversine_distances
from sklearn.utils.validation import check_is_fitted

EARTH_RADIUS_KM: float = 6371.0088


class GeodesicDistanceTransformer(TransformerMixin, BaseEstimator):
    """Transformador scikit-learn para cálculo de distâncias geodésicas até pontos de referência.

    Atributos:
        points (Dict[str, Tuple[float, float]]): Dicionário mapeando nome do ponto para (latitude, longitude).
        lat_feature (str): Nome da coluna de latitude. Padrão: 'latitude'.
        lon_feature (str): Nome da coluna de longitude. Padrão: 'longitude'.
        prefix (str): Prefixo do nome da nova coluna. Padrão: 'distancia_'.
        suffix (str): Sufixo do nome da nova coluna. Padrão: '_km'.
    """

    def __init__(
        self,
        points: Dict[str, Tuple[float, float]],
        lat_feature: str = "latitude",
        lon_feature: str = "longitude",
        prefix: str = "distancia_",
        suffix: str = "_km",
    ) -> None:
        """Inicializa o transformador de distância geodésica.

        Args:
            points (Dict[str, Tuple[float, float]]): Pontos de referência para cálculo.
            lat_feature (str): Nome da coluna de latitude. Padrão: 'latitude'.
            lon_feature (str): Nome da coluna de longitude. Padrão: 'longitude'.
            prefix (str): Prefixo do nome das novas colunas. Padrão: 'distancia_'.
            suffix (str): Sufixo do nome das novas colunas. Padrão: '_km'.
        """
        self.points: Dict[str, Tuple[float, float]] = points
        self.lat_feature: str = lat_feature
        self.lon_feature: str = lon_feature
        self.prefix: str = prefix
        self.suffix: str = suffix

    def fit(self, X: pd.DataFrame, y: Any = None) -> Self:
        """Valida as colunas do conjunto de dados de entrada e marca como ajustado.

        Args:
            X (pd.DataFrame): DataFrame de entrada.
            y (Any, optional): Ignorado.

        Returns:
            Self: Instância do próprio transformador.
        """
        self._validate_input(X)

        self.n_features_in_ = X.shape[1]
        self.feature_names_in_ = np.array(X.columns, dtype=object)
        self._is_fitted = True

        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """Calcula a distância em quilômetros de cada ponto do DataFrame para os pontos de referência.

        Args:
            X (pd.DataFrame): DataFrame contendo as colunas de latitude e longitude.

        Returns:
            pd.DataFrame: DataFrame acrescido das colunas de distância calculadas.
        """
        check_is_fitted(self)
        self._validate_input(X)

        X_out = X.copy()

        coords = np.radians(X_out[[self.lat_feature, self.lon_feature]].to_numpy(dtype=np.float64))

        mask = np.all(~np.isnan(coords), axis=1)
        valid_coords = coords[mask]
        valid_indices = X_out.index[mask]

        for point_name, (lat, lon) in self.points.items():
            feature_name = f"{self.prefix}{point_name}{self.suffix}"
            X_out[feature_name] = np.nan

            if len(valid_coords) > 0:
                ref_point_rad = np.radians([[lat, lon]])
                distances = haversine_distances(valid_coords, ref_point_rad).ravel() * EARTH_RADIUS_KM

                X_out.loc[valid_indices, feature_name] = distances

        return X_out

    def _validate_input(self, X: pd.DataFrame | Any) -> None:
        """Valida se a entrada é um DataFrame e se possui as colunas de coordenadas especificadas.

        Args:
            X (pd.DataFrame | Any): Objeto de entrada.

        Raises:
            TypeError: Se a entrada não for um pandas DataFrame.
            ValueError: Se faltarem colunas de coordenadas.
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
