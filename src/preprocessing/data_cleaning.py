import numpy as np
import pandas as pd

from logging import Logger

from .constants import UNUSED_FEATURES


class DataCleaner:
    def __init__(self, logger: Logger):
        self.logger = logger

    def _drop_duplicates(self, df: pd.DataFrame) -> pd.DataFrame:
        """Drop duplicated registers in dataset

        Args:
            df (pd.DataFrame): Dataset

        Returns:
            pd.DataFrame: Dataset with duplicated register dropped
        """
        self.logger.info("Removing duplicated registers from dataset.")

        return df.drop_duplicates(
            keep="first",
            ignore_index=True,
        )

    def _drop_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Drop feature that does not is available in inference
        step or that is not relevant for prediction

        Args:
            df (pd.DataFrame): Dataset

        Returns:
            pd.DataFrame: Dataset with the not used features droped
        """
        self.logger.info(f"Removing unused features from dataset (features {UNUSED_FEATURES}).")

        return df.drop(
            labels=UNUSED_FEATURES,
            axis="columns",
            errors="ignore"
        )
    
    def _drop_missing(self, df: pd.DataFrame) -> pd.DataFrame:
        """Drop registers with missing real state pricing

        Args:
            df (pd.DataFrame): Dataset

        Returns:
            pd.DataFrame: Dataset with registers without prices droped
        """
        self.logger.info("Removing register with missing real state pricing.")

        return df.dropna(
            subset="preco"
        )

    def _rename_classes(self, df: pd.DataFrame) -> pd.DataFrame:
        """Rename classes of some categorical features

        Args:
            df (pd.DataFrame): Dataset

        Returns:
            pd.DataFrame: Dataset with the classes renamed
        """
        self.logger.info("Renaming classes of categorical features.")

        return df.assign(
            tipo_imovel=lambda x: x["tipo_imovel"].map({
                "House": "casa",
                "Apartment": "apartamento",
                "Place": "outro",
            })
        )

    def _validate_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Show in logs the percentage of valid data between title data and
        extracted data

        Args:
            df (pd.DataFrame): Dataset

        Returns:
            pd.DataFrame: Same dataset
        """
        title_data = pd.DataFrame({
            "quartos": df["titulo"].str.extract(r"(?P<quarto>\d+) quarto[s]")["quarto"],
            "banheiros": df["titulo"].str.extract(r"(?P<banheiro>\d+) banheiro[s]")["banheiro"],
            "vagas": df["titulo"].str.extract(r"(?P<vaga>\d+) vaga[s]")["vaga"],
            "area_m2": df["titulo"].str.extract(r"(?P<area>\d+) m²")["area"],
        }, dtype=np.float64)

        extracted_data = df.filter(items=[
            "quartos",
            "banheiros",
            "vagas",
            "area_m2"
        ], axis="columns")

        title_data = title_data.values.reshape(-1)
        extracted_data = extracted_data.values.reshape(-1)
        notna_mask = pd.Series(title_data).notna()

        correct_count = (title_data[notna_mask] == extracted_data[notna_mask]).sum()
        total_count = notna_mask.sum()
        error_percentage = 100*correct_count / total_count

        self.logger.info(f"Percentage of valid data between title and extracted data: {error_percentage:.2f}%.")

        return df

    def _convert_dtypes(self, df: pd.DataFrame) -> pd.DataFrame:
        """Convert dtypes of the dataset

        Args:
            df (pd.DataFrame): Dataset

        Returns:
            pd.DataFrame: Dataset with the dtypes converted
        """
        return df.convert_dtypes()

    def __call__(self, df: pd.DataFrame) -> pd.DataFrame:
        """Cleaning dataset, removing duplicated registers,
        unused features, renaming classes, validating data
        and converting dtypes

        Args:
            df (pd.DataFrame): Extracted dataset from web data

        Returns:
            pd.DataFrame: Cleaned dataset
        """
        self.logger.info("Initializing cleaning step in the dataset.")

        df = (df
            .pipe(self._drop_duplicates)
            .pipe(self._drop_features)
            .pipe(self._drop_missing)
            .pipe(self._rename_classes)
            .pipe(self._validate_data)
            .pipe(self._convert_dtypes)
        )

        self.logger.info("Finalizing cleaning step in the dataset.")

        return df
