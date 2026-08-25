import pandas as pd

from typing import List
from logging import Logger

from .constants import FEATURES_MAPPING


class FeatureExtractor:
    def __init__(self, logger: Logger):
        self.logger = logger

    def _get_amenities_pattern(self, amenities: List[str]) -> str:
        """Get regex pattern of amenities from amenities list

        Args:
            amenities (List[str]): List of amenities

        Returns:
            str: String pattern to catch amenities
        """
        return rf"{"|".join(amenities)}"

    def _extract_amenities_feature(self, df: pd.DataFrame, amenities: List[str]) -> pd.Series:
        """Extract amenities feature from `comodidades` feature and using the given amenities

        Args:
            df (pd.DataFrame): Dataset
            original_feature (str): Feature where the new feature will be extracted
            amenities (List[str]): Amenities of the new feature

        Returns:
            pd.Series: The new amenities feature extracted from original feature
        """
        return (df["comodidades"]
            .str
            .contains(
                pat=self._get_amenities_pattern(amenities),
                regex=True,
            )
            .fillna(False)
            .astype("boolean")
        )

    def _extract_amenities_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract amenities features from `comodidades` feature

        Args:
            df (pd.DataFrame): Dataset
            original_feature (str): Feature where the new feature will be extracted

        Returns:
            pd.DataFrame: The dataset updated with the new extracted amenities features
        """
        self.logger.info("Extracting amenities features.")

        for feature, amenities in FEATURES_MAPPING.items():
            self.logger.info(f"Extracting amenities feature for `{feature}`.")

            df[feature] = self._extract_amenities_feature(df, amenities)

        return (df
            .assign(
                pets=lambda x: x[["pets", "aceita_pets"]].any(axis="columns")
            )
            .drop("aceita_pets", axis="columns")
            .drop("comodidades", axis="columns")
        )

    def _extract_real_state_classes(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract classes of real state from `titulo` feature and put it
        on registers with class `"outro"` in the feature `tipo_imovel`

        Args:
            df (pd.DataFrame): Dataset

        Returns:
            pd.DataFrame: Dataset with new extracted classes to feature `tipo_imovel`
        """
        self.logger.info("Extracting real state classes from feature `titulo`.")

        real_state_classes = (df["titulo"]
            .str
            .split(n=1, expand=True)[0]
            .map({
                "Casa": "casa",
                "Apartamento": "apartamento",
                "Flat": "flat",
                "Cobertura": "cobertura",
                "Sobrado": "sobrado",
                "Studio": "studio",
            })
            .fillna("outro")
        )

        mask = (df["tipo_imovel"] == "outro")
        df.loc[mask, "tipo_imovel"] = real_state_classes[mask]

        return df.drop("titulo", axis="columns")

    def _convert_dtypes(self, df: pd.DataFrame) -> pd.DataFrame:
        """Convert dtypes of the dataset

        Args:
            df (pd.DataFrame): Dataset

        Returns:
            pd.DataFrame: Dataset with the dtypes converted
        """
        return df.convert_dtypes()

    def __call__(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract amenities features from `comodidades` and real state
        classes from `titulo`

        Args:
            df (pd.DataFrame): Dataset

        Returns:
            pd.DataFrame: The new dataset with the new extracted features
        """
        self.logger.info("Initializing feature extraction step in the dataset.")

        df = (df
            .pipe(self._extract_amenities_features)
            .pipe(self._extract_real_state_classes)
            .pipe(self._convert_dtypes)
        )

        self.logger.info("Finalizing feature extraction step in the dataset.")

        return df
