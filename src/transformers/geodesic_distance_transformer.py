import pandas as pd

from typing import List, Dict

from feature_engine.creation import GeoDistanceFeatures
from sklearn.base import BaseEstimator, TransformerMixin


class GeodesicDistanceTransformer(TransformerMixin, BaseEstimator):
    def __init__(
        self,
        places: Dict[str, List[int]],
        lat_feature: str = "latitude",
        lon_feature: str = "longitude",
        prefix: str = "distancia",
    ) -> None:
        """Initialize geodesic distance transformer.

        Args:
            places (Dict[str, List[int]]): Dicionary with places names and its coordinates
            lat_feature (str, optional): Name of the feature that represents latitude. Defaults to "latitude".
            lon_feature (str, optional): Name of the feature that represents longitude. Defaults to "longitude".
            prefix (str, optional): Prefix of the distance feature names. Defaults to "distancia".
        """
        self.places: Dict[str, List[int]] = places
        self.lat_feature: str = lat_feature
        self.lon_feature: str = lon_feature
        self.prefix: str = prefix
        self.data: pd.DataFrame

    def fit(self, X: pd.DataFrame, y=None) -> None:
        """Calculate the geodesic distances between original feature and the given places.

        Args:
            X (pd.DataFrame): Original dataset.
            y (None, optional): Unused. Defaults to None.
        """
        self.data = X[[self.lat_feature, self.lon_feature]]

        for place, coordinates in self.places.items():
            self.data[f"{place}_lat"] = coordinates[0]
            self.data[f"{place}_lon"] = coordinates[1]

            gdt = GeoDistanceFeatures(
                lat1="latitude", lon1="longitude",
                lat2=f"{place}_lat", lon2=f"{place}_lon",
            )

            result = gdt.fit_transform(self.data)

            self.data[f"{self.prefix}_{place}"] = result["geo_distance"]

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """Put the calculated geodesic distances in the dataset.

        Args:
            X (pd.DataFrame): Original dataset.

        Returns:
            pd.DataFrame: New dataset with the distance features.
        """
        for place in self.places.keys():
            X[f"{self.prefix}_{place}"] = self.data[f"{self.prefix}_{place}"]
        
        return X