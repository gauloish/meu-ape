"""Módulo de limpeza de dados imobiliários.

Executa a remoção de registros duplicados, remoção de colunas irrelevantes para predição,
higienização de registros sem preço, padronização de classes categóricas e conversão de dtypes.
"""

import logging
from logging import Logger

import numpy as np
import pandas as pd

from .constants import UNUSED_FEATURES

logger = logging.getLogger(__name__)


class DataCleaner:
    """Higieniza o DataFrame bruto extraído do scraping de imóveis."""

    def __init__(self) -> None:
        """Inicializa o limpador de dados."""
        pass

    def _drop_duplicates(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove registros totalmente duplicados do conjunto de dados.

        Args:
            df (pd.DataFrame): DataFrame de entrada.

        Returns:
            pd.DataFrame: DataFrame sem registros duplicados.
        """
        logger.info("Removendo registros duplicados do conjunto de dados.")

        return df.drop_duplicates(keep="first", ignore_index=True)

    def _drop_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove colunas que não estão disponíveis no momento da inferência ou que são irrelevantes.

        Args:
            df (pd.DataFrame): DataFrame de entrada.

        Returns:
            pd.DataFrame: DataFrame sem as colunas não utilizadas.
        """
        logger.info(f"Removendo colunas não utilizadas: {UNUSED_FEATURES}.")

        cols_to_drop = [
            c
            for c in UNUSED_FEATURES
            if c in df.columns
        ]

        return df.drop(columns=cols_to_drop, axis="columns", errors="ignore")

    def _drop_missing(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove registros com o preço de venda ausente (`NaN`), caso a coluna `preco` esteja presente.

        Args:
            df (pd.DataFrame): DataFrame de entrada.

        Returns:
            pd.DataFrame: DataFrame filtrado.
        """
        if "preco" not in df.columns:
            logger.info("Coluna 'preco' não encontrada. Etapa de remoção por falta de preço ignorada.")
            return df

        logger.info("Removendo registros sem informação de preço ('preco').")

        return (df
            .dropna(subset=["preco"])
            .reset_index(drop=True)
        )

    def _rename_classes(self, df: pd.DataFrame) -> pd.DataFrame:
        """Padroniza os nomes das categorias da variável `tipo_imovel`.

        Args:
            df (pd.DataFrame): DataFrame de entrada.

        Returns:
            pd.DataFrame: DataFrame com as categorias traduzidas/padronizadas.
        """
        if "tipo_imovel" not in df.columns:
            return df

        logger.info("Padronizando categorias da coluna 'tipo_imovel'.")

        mapping = {
            "House": "casa",
            "Apartment": "apartamento",
            "Place": "outro",
        }

        df["tipo_imovel"] = df["tipo_imovel"].map(lambda val: mapping.get(val, val))

        return df

    def _validate_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcula e exibe nos logs o percentual de consistência entre a coluna `titulo` e dados extraídos.

        Args:
            df (pd.DataFrame): DataFrame de entrada.

        Returns:
            pd.DataFrame: O mesmo DataFrame recebido.
        """
        if "titulo" not in df.columns:
            return df

        logger.info("Validando consistência entre a coluna 'titulo' e características extraídas.")

        try:
            titulo_str = df["titulo"].fillna("").astype(str)

            title_data = pd.DataFrame(
                {
                    "quartos": titulo_str.str.extract(r"(?P<quarto>\d+) quarto[s]?")["quarto"],
                    "banheiros": titulo_str.str.extract(r"(?P<banheiro>\d+) banheiro[s]?")["banheiro"],
                    "vagas": titulo_str.str.extract(r"(?P<vaga>\d+) vaga[s]?")["vaga"],
                    "area_m2": titulo_str.str.extract(r"(?P<area>\d+) m²")["area"],
                },
                dtype=np.float64,
            )

            extracted_data = df.filter(items=["quartos", "banheiros", "vagas", "area_m2"], axis="columns")

            title_arr = title_data.to_numpy().reshape(-1)
            extracted_arr = extracted_data.to_numpy().reshape(-1)
            notna_mask = pd.Series(title_arr).notna().to_numpy()

            if notna_mask.sum() > 0:
                correct_count = (title_arr[notna_mask] == extracted_arr[notna_mask]).sum()
                total_count = notna_mask.sum()
                accuracy_pct = 100.0 * (correct_count / total_count)

                logger.info(f"Percentual de consistência dos dados do título: {accuracy_pct:.2f}%.")

        except Exception as exc:
            logger.warning(f"Não foi possível validar consistência dos dados do título: {exc}")

        return df

    def _convert_dtypes(self, df: pd.DataFrame) -> pd.DataFrame:
        """Converte os dtypes do DataFrame para tipos de dados nativos otimizados.

        Args:
            df (pd.DataFrame): DataFrame de entrada.

        Returns:
            pd.DataFrame: DataFrame com dtypes convertidos.
        """
        return df.convert_dtypes()

    def __call__(self, df: pd.DataFrame) -> pd.DataFrame:
        """Executa a pipeline completa de limpeza de dados.

        Args:
            df (pd.DataFrame): DataFrame de entrada bruto.

        Returns:
            pd.DataFrame: DataFrame higienizado.
        """
        logger.info("Iniciando pipeline de limpeza dos dados.")

        df = (df
            .pipe(self._drop_duplicates)
            .pipe(self._drop_features)
            .pipe(self._drop_missing)
            .pipe(self._rename_classes)
            .pipe(self._validate_data)
            .pipe(self._convert_dtypes)
        )

        logger.info("Pipeline de limpeza finalizada com sucesso.")

        return df
