import pandas as pd
import numpy as np

from typing import Any, List

from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.cluster import KMeans
from sklearn.utils.validation import check_is_fitted


class ClusterTranformer(TransformerMixin, BaseEstimator):
    def __init__(
        self,
        n_clusters: int,
        random_state: int,
        lat_feature: str = "latitude",
        lon_feature: str = "longitude",
        feature: str = "cluster",
    ) -> None:
        """Initialize cluster transformer, that is, a transformer that
        use K-Means algorithm in coordinates features to calculate
        cluster and create a feature to sinalize the cluster of the
        sample.

        Args:
            n_clusters (int): Number of clusters.
            random_state (int): Random state.
            lat_feature (str, optional): Name of the latitude feature. Defaults to "latitude".
            lon_feature (str, optional): Name of the longitude feature. Defaults to "longitude".
            feature (str, optional): Name of the new feature that will
            indicate the cluster label. Defaults to "cluster".
        """
        self.n_clusters: int = n_clusters
        self.random_state: int = random_state
        self.lat_feature: str = lat_feature
        self.lon_feature: str = lon_feature
        self.feature: str = feature

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
        """Create new feature with the cluster label of each sample.

        Args:
            X (pd.DataFrame): Original dataset.

        Returns:
            pd.DataFrame: Updated dataset with new cluster label feature.
        """
        check_is_fitted(self)
        self._validate_input(X)

        X = X.copy()

        model = KMeans(
            n_clusters=self.n_clusters,
            random_state=self.random_state,
        )

        X_coord = X[[self.lat_feature, self.lon_feature]].values
        X[self.feature] = model.fit_predict(X_coord)

        return X

    def _validate_input(self, X: pd.DataFrame | Any) -> None:
        """Check if the input is valid, that is, if the input is 
        a pandas DataFrame and if it have the coordinates features
        given in lat_feature and lon_feature.

        Args:
            X (pd.DataFrame | Any): Original dataset.

        Raises:
            TypeError: Throw if the input is not a pandas DataFrame.
            ValueError: Throw if are missing features.
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
