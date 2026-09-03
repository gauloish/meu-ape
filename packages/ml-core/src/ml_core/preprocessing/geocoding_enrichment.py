"""Módulo de enriquecimento de dados imobiliários por geocodificação.

Utiliza a API interna de Geocodificação através do pacote `geocoding-client`
para converter endereços em coordenadas de latitude e longitude de forma vetorizada.
"""

import logging
from typing import Dict

import numpy as np
import pandas as pd
from geocoding_client import GeocodingClient

logger = logging.getLogger(__name__)

# Limites geográficos padrão para o município de Goiânia - GO
MIN_LATITUDE: float = -16.85
MAX_LATITUDE: float = -16.55

MIN_LONGITUDE: float = -49.45
MAX_LONGITUDE: float = -49.15


class GeocodingEnricher:
    """Enriquece o DataFrame de imóveis com coordenadas geográficas de latitude e longitude.

    Atributos:
        client (GeocodingClient): Instância do cliente HTTP da API de Geocodificação.
    """

    def __init__(self, client: GeocodingClient | None = None) -> None:
        """Inicializa o enriquecedor de dados geográficos.

        Args:
            client (GeocodingClient | None): Instância customizada do cliente de geocodificação.
        """
        self.client: GeocodingClient = client or GeocodingClient()

    def _get_address_feature(self, df: pd.DataFrame) -> pd.DataFrame:
        """Combina as colunas `rua` e `bairro` em um campo de endereço completo.

        Args:
            df (pd.DataFrame): DataFrame de entrada contendo `rua` e `bairro`.

        Returns:
            pd.DataFrame: DataFrame atualizado com a coluna temporária `endereco`.
        """
        logger.info("Gerando coluna de endereço completo para geocodificação.")

        rua = (
            df["rua"].fillna("").astype(str).str.strip()
            if "rua" in df.columns
            else pd.Series("", index=df.index)
        )

        bairro = (
            df["bairro"].fillna("").astype(str).str.strip()
            if "bairro" in df.columns
            else pd.Series("", index=df.index)
        )

        df["endereco"] = (rua + ", " + bairro).str.strip(", ")

        return df

    def _extract_geocoded_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extrai coordenadas de latitude e longitude para os endereços do DataFrame de forma vetorizada.

        Args:
            df (pd.DataFrame): DataFrame de entrada.

        Returns:
            pd.DataFrame: DataFrame enriquecido com `latitude` e `longitude`, removendo `endereco`.
        """
        logger.info("Enriquecendo o conjunto de dados com coordenadas geográficas.")

        df = self._get_address_feature(df)

        valid_addresses = [
            addr
            for addr in df["endereco"].dropna().unique()
            if addr
        ]

        lat_map: Dict[str, float] = {}
        lon_map: Dict[str, float] = {}

        if valid_addresses:
            logger.info(f"Enviando {len(valid_addresses)} endereços únicos para geocodificação em lote.")

            try:
                batch_response = self.client.batch_geocode_sync(valid_addresses)

                for res in batch_response.results:
                    if res.data and res.source != "error":
                        lat_map[res.data.address] = res.data.latitude
                        lon_map[res.data.address] = res.data.longitude

            except Exception as err:
                logger.error(f"Falha ao executar geocodificação em lote: {err}")

        df["latitude"] = df["endereco"].map(lat_map).astype(np.float64)
        df["longitude"] = df["endereco"].map(lon_map).astype(np.float64)

        drop_cols = [
            c
            for c in ["endereco", "rua", "bairro"]
            if c in df.columns
        ]

        return df.drop(columns=drop_cols)

    def _clip_out_of_bounds_samples(self, df: pd.DataFrame) -> pd.DataFrame:
        """Filtra e remove registros cujas coordenadas estejam fora dos limites geográficos de Goiânia.

        Registros sem coordenadas (NaN) são mantidos para permitir a imputação pelo
        SimpleImputer do pipeline de Machine Learning.

        Args:
            df (pd.DataFrame): DataFrame contendo as colunas `latitude` e `longitude`.

        Returns:
            pd.DataFrame: DataFrame filtrado com os registros válidos ou não geocodificados.
        """
        logger.info("Filtrando amostras fora dos limites geográficos de Goiânia.")

        if "latitude" not in df.columns or "longitude" not in df.columns:
            return df

        mask_lat = df["latitude"].isna() | ((df["latitude"] >= MIN_LATITUDE) & (df["latitude"] <= MAX_LATITUDE))
        mask_lon = df["longitude"].isna() | ((df["longitude"] >= MIN_LONGITUDE) & (df["longitude"] <= MAX_LONGITUDE))

        valid_mask = (mask_lat & mask_lon)

        return df[valid_mask].reset_index(drop=True)

    def _convert_dtypes(self, df: pd.DataFrame) -> pd.DataFrame:
        """Converte os tipos de dados do DataFrame para tipos otimizados do Pandas.

        Args:
            df (pd.DataFrame): DataFrame de entrada.

        Returns:
            pd.DataFrame: DataFrame com os tipos convertidos.
        """
        return df.convert_dtypes()

    def __call__(self, df: pd.DataFrame) -> pd.DataFrame:
        """Executa o pipeline completo de enriquecimento geográfico.

        Args:
            df (pd.DataFrame): Conjunto de dados de imóveis a ser enriquecido.

        Returns:
            pd.DataFrame: Conjunto de dados enriquecido com `latitude` e `longitude`.
        """
        logger.info("Iniciando etapa de enriquecimento geográfico por geocodificação.")

        df = (df
            .pipe(self._extract_geocoded_features)
            .pipe(self._clip_out_of_bounds_samples)
            .pipe(self._convert_dtypes)
        )

        logger.info("Etapa de enriquecimento geográfico concluída com sucesso.")

        return df