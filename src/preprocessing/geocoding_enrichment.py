import numpy as np
import pandas as pd

from logging import Logger
from typing import List, Dict

from ..services.geocoder import (
    GeocodingFeatures,
    Geocoder,
)

GEOCODING_FEATURES_DEFAULT = GeocodingFeatures(
    latitude=-16.6670204,
    longitude=-49.2521725,
)


def _check_string_has_content(register: pd.Series) -> bool:
    """Check if string has some content, that is, whether the string
    is not empty nor NAN.

    Args:
        register (pd.Series): String to be checked.

    Returns:
        bool: True if string has content. Otherwise, False.
    """
    if isinstance(register, str):
        if register.strip():
            return True

    return False

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

        mask_rua = df["rua"].map(_check_string_has_content)
        mask_bairro = df["bairro"].map(_check_string_has_content)

        df.loc[~mask_rua, "rua"] = pd.NA
        df.loc[~mask_bairro, "bairro"] = pd.NA

        df["endereco"] = pd.NA

        mask_rua_not_bairro = (mask_rua & (~mask_bairro))
        mask_not_rua_bairro = ((~mask_rua) & mask_bairro)
        mask_rua_bairro = (mask_rua & mask_bairro)

        df.loc[mask_rua_not_bairro, "endereco"] = df.loc[mask_rua_not_bairro, "rua"]
        df.loc[mask_not_rua_bairro, "endereco"] = df.loc[mask_not_rua_bairro, "bairro"]
        df.loc[mask_rua_bairro, "endereco"] = df.loc[mask_rua_bairro, "rua"] + ", " + df.loc[mask_rua_bairro, "bairro"]

        df.loc[df["endereco"].notna(), "endereco"] += ", Goiânia - GO"

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
            coordinates = GeocodingFeatures(
                latitude=np.nan,
                longitude=np.nan
            )

        register["latitude"] = coordinates.latitude
        register["longitude"] = coordinates.longitude

        return register

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

        return (df
            .apply(self._create_geocoded_features, axis="columns")
            .drop(["endereco", "rua", "bairro"], axis="columns")
        )

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
            .pipe(self._convert_dtypes)
        )

        self.logger.info("Finalizing enrichment of features by geocoding.")

        return df