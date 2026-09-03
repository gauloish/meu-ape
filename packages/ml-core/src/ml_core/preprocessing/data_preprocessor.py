"""Módulo do pré-processador de dados do pipeline de treinamento.

Executa todas as etapas de limpeza e tratamento dos dados, extração de features e enriquecimento
dos dados com geocodificação.
"""

import logging
from logging import Logger

import numpy as np
import pandas as pd

from .data_cleaning import DataCleaner
from .feature_extraction import FeatureExtractor
from .geocoding_enrichment import GeocodingEnricher

from geocoding_client import GeocodingClient

logger = logging.getLogger(__name__)


class DataPreprocessor:
    """Executa todas as etapas de preprocessamento do pipeline."""

    def __init__(self, geocoding_client: GeocodingClient | None = None) -> None:
        """Inicializa o pré-processador.

        Args:
            geocoding_client (GeocodingClient | None): Instância do cliente de geocodificação.
        """
        self.data_cleaner = DataCleaner()
        self.feature_extractor = FeatureExtractor()
        self.geocoding_enricher = GeocodingEnricher(client=geocoding_client)

    def __call__(self, df: pd.DataFrame) -> pd.DataFrame:
        """Executa a pipeline completa do pré-processador.

        Args:
            df (pd.DataFrame): DataFrame de entrada bruto.

        Returns:
            pd.DataFrame: DataFrame pré-processado.
        """
        logger.info("Iniciando pipeline de pré-processamento.")

        df = (df
            .pipe(self.data_cleaner)
            .pipe(self.feature_extractor)
            .pipe(self.geocoding_enricher)
        )

        df.to_parquet("train_clean.parquet", index=False)

        logger.info("Pipeline de pré-processamento finalizada com sucesso.")

        return df
