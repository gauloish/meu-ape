"""Módulo de extração de características (Feature Extraction) de imóveis.

Extrai variáveis booleanas de comodidades (ex: piscina, academia, churrasqueira) a partir da coluna `comodidades`
e refina a classificação do imóvel em `tipo_imovel` a partir dos textos da coluna `titulo`.
"""

import re
from typing import List

import pandas as pd

from logging_settings import setup_logger

from .constants import FEATURES_MAPPING

logger = setup_logger(__name__)


class FeatureExtractor:
    """Extrai novas variáveis descritivas e estruturadas a partir de campos textuais."""

    def __init__(self) -> None:
        """Inicializa o extrator de características."""
        pass

    def _get_amenities_pattern(self, amenities: List[str]) -> str:
        """Gera o padrão Regex seguro contendo as palavras-chave da comodidade, escapando caracteres especiais.

        Args:
            amenities (List[str]): Lista de palavras-chave de comodidades.

        Returns:
            str: Padrão Regex pronto para busca textual (ex: "Piscina|Piscina Aquecida").
        """
        escaped_amenities = [re.escape(a) for a in amenities]

        return "|".join(escaped_amenities)

    def _extract_amenities_feature(self, df: pd.DataFrame, amenities: List[str]) -> pd.Series:
        """Extrai uma coluna booleana indicando se o texto da coluna `comodidades` contém alguma palavra-chave.

        Args:
            df (pd.DataFrame): DataFrame contendo a coluna `comodidades`.
            amenities (List[str]): Lista de palavras-chave.

        Returns:
            pd.Series: Serie booleana indicando a presença da comodidade.
        """
        if "comodidades" not in df.columns:
            return pd.Series(False, index=df.index, dtype="boolean")

        pattern = self._get_amenities_pattern(amenities)

        return (df["comodidades"]
            .fillna("")
            .astype(str)
            .str
            .contains(pat=pattern, regex=True, case=False)
            .astype("boolean")
        )

    def _extract_amenities_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extrai todas as variáveis de comodidades mapeadas em `FEATURES_MAPPING`.

        Args:
            df (pd.DataFrame): DataFrame de entrada.

        Returns:
            pd.DataFrame: DataFrame atualizado com as novas colunas de comodidade.
        """
        logger.info("Extraindo variáveis de comodidades.")

        for feature_name, amenities in FEATURES_MAPPING.items():
            logger.info(f"Extraindo comodidade para '{feature_name}'.")

            df[feature_name] = self._extract_amenities_feature(df, amenities)

        if "aceita_pets" in df.columns:
            df["pets"] = df["pets"] | df["aceita_pets"].fillna(False).astype("boolean")

            df = df.drop(columns=["aceita_pets"])

        if "comodidades" in df.columns:
            df = df.drop(columns=["comodidades"])

        return df

    def _extract_real_state_classes(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extrai a categoria do imóvel da coluna `titulo` para preencher valores genéricos ('outro') em `tipo_imovel`.

        Args:
            df (pd.DataFrame): DataFrame de entrada.

        Returns:
            pd.DataFrame: DataFrame com a coluna `tipo_imovel` refinada.
        """
        if "titulo" not in df.columns or "tipo_imovel" not in df.columns:
            return df.drop(columns=["titulo"], errors="ignore")

        logger.info("Extraindo tipo do imóvel a partir da coluna 'titulo'.")

        first_word = (df["titulo"]
            .fillna("")
            .astype(str)
            .str
            .split(n=1, expand=True)[0]
        )

        class_mapping = {
            "Casa": "casa",
            "Apartamento": "apartamento",
            "Flat": "flat",
            "Cobertura": "cobertura",
            "Sobrado": "sobrado",
            "Studio": "studio",
        }

        extracted_classes = first_word.map(class_mapping).fillna("outro")

        mask = (df["tipo_imovel"] == "outro")
        df.loc[mask, "tipo_imovel"] = extracted_classes[mask]

        return df.drop(columns=["titulo"], errors="ignore")

    def _convert_dtypes(self, df: pd.DataFrame) -> pd.DataFrame:
        """Converte os dtypes do DataFrame para tipos de dados nativos otimizados.

        Args:
            df (pd.DataFrame): DataFrame de entrada.

        Returns:
            pd.DataFrame: DataFrame com dtypes convertidos.
        """
        return df.convert_dtypes()

    def __call__(self, df: pd.DataFrame) -> pd.DataFrame:
        """Executa a pipeline de extração de características.

        Args:
            df (pd.DataFrame): DataFrame de entrada.

        Returns:
            pd.DataFrame: DataFrame com as novas características extraídas.
        """
        logger.info("Iniciando etapa de extração de características.")

        df = (df
            .pipe(self._extract_amenities_features)
            .pipe(self._extract_real_state_classes)
            .pipe(self._convert_dtypes)
        )

        logger.info("Etapa de extração de características finalizada com sucesso.")

        return df
