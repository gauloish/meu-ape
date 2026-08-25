import pandas as pd
import numpy as np

from typing import Any, Tuple, Dict

from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.metrics.pairwise import haversine_distances
from sklearn.utils.validation import check_is_fitted

EARTH_RADIUS_KM: float = 6371.0088


class GeodesicDistanceTransformer(TransformerMixin, BaseEstimator):
    def __init__(
        self,
        points: Dict[str, Tuple[float, float]],
        lat_feature: str = "latitude",
        lon_feature: str = "longitude",
        prefix: str = "distancia_",
        suffix: str = "_km",
    ) -> None:
        """Initialize transformer that create geodesic distance features.

        Args:
            points (Dict[str, Tuple[float, float]]): Points from the distances will be calculated.
            lat_feature (str, optional): Name of the latitude feature. Defaults to "latitude".
            lon_feature (str, optional): Name of the longitude feature. Defaults to "longitude".
            prefix (str, optional): Prefix of the result distance feature name. Defaults to "distancia_".
            suffix (str, optional): Suffix of the result distance feature name. Defaults to "_km".
        """
        self.points: Dict[str, Tuple[float, float]] = points
        self.lat_feature: str = lat_feature
        self.lon_feature: str = lon_feature
        self.prefix: str = prefix
        self.suffix: str = suffix

    def fit(self, X: pd.DataFrame, y=None):
        """Fit the data.

        Args:
            X (pd.DataFrame): Original dataset
            y (None, optional): Ignored. Defaults to None.

        Returns:
            Self: Self
        """
        self._is_fitted = True

        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """Calculate the geodesic distance features from `latitude` and
        `longitude` features.

        Args:
            X (pd.DataFrame): Original dataset.

        Returns:
            pd.DataFrame: Dataset updated with the distance features.
        """
        check_is_fitted(self)
        self._validate_input(X)

        X = X.copy()

        coordinates = np.radians(
            X[[self.lat_feature, self.lon_feature]]
            .to_numpy(dtype=np.float64)
        )

        mask = np.all(
            ~np.isnan(coordinates),
            axis=1
        )

        coordinates = coordinates[mask]

        for name, (latitude, longitude) in self.points.items():
            radians = np.radians([[latitude, longitude]])

            distance = (
                haversine_distances(coordinates, radians).ravel()
                * EARTH_RADIUS_KM
            )

            feature_name = f"{self.prefix}{name}{self.suffix}"

            X[feature_name] = np.nan
            X.loc[mask, feature_name] = distance

        return X

    def _validate_input(self, X: pd.DataFrame | Any) -> None:
        """Check if input is valid, that is, the input is
        a pandas DataFrame and if has the `latitude` and 
        `longitude` features.

        Args:
            X (pd.DataFrame | Any): Original dataset.

        Raises:
            TypeError: If given data is not a pandas DataFrame.
            ValueError: If the features `latitude` and `longitude`
            are missing.
        """
        if not isinstance(X, pd.DataFrame):
            raise TypeError(
                f"{self.__class__.__name__} expects a pandas.DataFrame, "
                f"but received a {type(X).__name__}."
            )

        required = {
            self.lat_feature,
            self.lon_feature,
        }

        missing = required - set(X.columns)

        if missing:
            raise ValueError(
                f"Missing features: {sorted(missing)}"
            )

    def __sklearn_is_fitted__(self):
        """
        Check fitted status and return a Boolean value.
        """
        return hasattr(self, "_is_fitted") and self._is_fitted
