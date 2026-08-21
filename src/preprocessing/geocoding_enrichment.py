import numpy as np
import pandas as pd

from logging import Logger
from typing import List, Dict

from ..services.geocoder import (
    GeocodingFeatures,
    Geocoder,
)

GEOCODING_FEATURES_DEFAULT: GeocodingFeatures = GeocodingFeatures(
    latitude=np.nan,
    longitude=np.nan,
)

MIN_LATITUDE: float = -16.85
MAX_LATITUDE: float = -16.55

MIN_LONGITUDE: float = -49.45
MAX_LONGITUDE: float = -49.15


class GeocodingEnricher:
    def __init__(self, logger: Logger):
        self.logger: Logger = logger
        self.geocoded_addresses: Dict[str, GeocodingFeatures] = dict()

    def _get_address_feature(self, df: pd.DataFrame) -> pd.DataFrame:
        """Get complete address feature to use in geocoding step

        Args:
            df (pd.DataFrame): Dataset

        Returns:
            pd.Series: Complete address feature
        """
        self.logger.info("Generating address feature.")

        rua = df["rua"].fillna("")
        bairro = df["bairro"].fillna("")

        df["endereco"] = rua + ", " + bairro

        return df

    def _create_geocoded_features(self, register: pd.Series) -> pd.Series:
        """Create the geocoded features

        Args:
            register (pd.Series): Register of the dataset

        Returns:
            pd.Series: Register updated with `latitude` and `longitude` features
        """
        if isinstance(register["endereco"], str):
            coordinates = self.geocoded_addresses.get(
                register["endereco"],
                GEOCODING_FEATURES_DEFAULT
            )
        else:
            coordinates = GEOCODING_FEATURES_DEFAULT

        result = pd.Series()

        result["latitude"] = coordinates.latitude
        result["longitude"] = coordinates.longitude

        return result

    def _extract_geocoded_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract geocoded features from `rua` and `bairro` features

        Args:
            df (pd.DataFrame): Dataset

        Returns:
            pd.DataFrame: Dataset with new extracted features `latitude` and `longitude`
        """
        self.logger.info("Enriching the dataset with geocoded features.")

        df = self._get_address_feature(df)

        geocoder = Geocoder(self.logger)
        addresses = list(df["endereco"].dropna().unique())

        self.geocoded_addresses = geocoder.geocode(addresses)

        df[["latitude", "longitude"]] = (df["endereco"]
            .apply(self._create_geocoded_features, axis="columns")
        )

        return df.drop(["endereco", "rua", "bairro"], axis="columns")

    def _clip_out_of_bounds_samples(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clip samples with address out of bound of Goiânia

        Args:
            df (pd.DataFrame): Dataset

        Returns:
            pd.DataFrame: Dataset updated with the out of bound samples clipped
        """
        self.logger.info("Cliping samples out of Goiânia bounds.")

        mask_latitude = ((MIN_LATITUDE <= df["latitude"]) & (df["latitude"] <= MAX_LATITUDE))
        mask_longitude = ((MIN_LONGITUDE <= df["longitude"]) & (df["longitude"] <= MAX_LONGITUDE))

        return df[mask_latitude & mask_longitude].reset_index(drop=True)

    def _convert_dtypes(self, df: pd.DataFrame) -> pd.DataFrame:
        """Convert dtypes of the dataset

        Args:
            df (pd.DataFrame): Dataset

        Returns:
            pd.DataFrame: Dataset with the dtypes converted
        """
        return df.convert_dtypes()

    def __call__(self, df: pd.DataFrame) -> pd.DataFrame:
        """Geocode all address of dataset and create (enrich) two new features
        `latitude` and `longitude` from `rua` and `bairro`

        Args:
            df (pd.DataFrame): Dataset to be enriched

        Returns:
            pd.DataFrame: The new dataset with the features `latitude` and `longitude`
        """
        self.logger.info("Initializaing enrichment of features by geocoding of `rua` and `bairro`.")

        df = (df
            .pipe(self._extract_geocoded_features)
            .pipe(self._clip_out_of_bounds_samples)
            .pipe(self._convert_dtypes)
        )

        self.logger.info("Finalizing enrichment of features by geocoding.")

        return df