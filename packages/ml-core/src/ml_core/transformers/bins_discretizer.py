"""Transformador de discretização em intervalos (BinsDiscretizer).

Discretiza variáveis contínuas em categorias discretas (faixas de valores).
"""

from typing import Any, List, Self, Tuple

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.utils.validation import check_is_fitted


class BinsDiscretizer(TransformerMixin, BaseEstimator):
    """Transformador scikit-learn para discretização de variáveis contínuas em intervalos pré-definidos.

    Atributos:
        bins_info (List[Tuple[str, List[float], List[str]]]): Lista de tuplas contendo
            (nome_da_coluna, lista_de_limites_dos_intervalos, lista_de_rótulos).
        prefix (str): Prefixo do nome das novas colunas categóricas. Padrão: 'faixa_'.

    Example:
        >>> bins_info = [("area_m2", [0, 50, 100, float("inf")], ["pequeno", "medio", "grande"])]
        >>> discretizer = BinsDiscretizer(bins_info=bins_info)
        >>> df_binned = discretizer.fit_transform(df)
    """

    def __init__(
        self,
        bins_info: List[Tuple[str, List[float], List[str]]],
        prefix: str = "faixa_",
    ) -> None:
        """Inicializa o discretizador de intervalos.

        Args:
            bins_info (List[Tuple[str, List[float], List[str]]]): Informações sobre os limites e rótulos de cada coluna.
            prefix (str): Prefixo do nome da nova coluna gerada. Padrão: 'faixa_'.
        """
        self.bins_info: List[Tuple[str, List[float], List[str]]] = bins_info
        self.prefix: str = prefix

    def fit(self, X: pd.DataFrame, y: Any = None) -> Self:
        """Valida as colunas necessárias e marca o transformador como ajustado.

        Args:
            X (pd.DataFrame): DataFrame de entrada.
            y (Any, optional): Ignorado.

        Returns:
            Self: Instância do próprio transformador.
        """
        self._validate_input(X)

        self.n_features_in_ = X.shape[1]
        self.feature_names_in_ = np.array(X.columns, dtype=object)
        self._is_fitted = True

        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """Cria as novas colunas categóricas aplicando a discretização `pd.cut`.

        Args:
            X (pd.DataFrame): DataFrame de entrada.

        Returns:
            pd.DataFrame: DataFrame acrescido das colunas discretizadas.
        """
        check_is_fitted(self)
        self._validate_input(X)

        X_out = X.copy()

        for feature_name, bins, labels in self.bins_info:
            new_col_name = f"{self.prefix}{feature_name}"

            X_out[new_col_name] = pd.cut(
                X_out[feature_name],
                bins=bins,
                labels=labels,
                include_lowest=True,
            )

        return X_out

    def _validate_input(self, X: pd.DataFrame | Any) -> None:
        """Valida se a entrada é um DataFrame e se contém todas as colunas listadas em `bins_info`.

        Args:
            X (pd.DataFrame | Any): Objeto de entrada.

        Raises:
            TypeError: Se a entrada não for um pandas DataFrame.
            ValueError: Se faltarem colunas de entrada.
        """
        if not isinstance(X, pd.DataFrame):
            raise TypeError(f"{self.__class__.__name__} espera um pandas.DataFrame, mas recebeu {type(X).__name__}.")

        missing = []
        
        for info in self.bins_info:
            if info[0] not in X.columns:
                missing.append(info[0])

        if missing:
            raise ValueError(f"Colunas obrigatórias ausentes no DataFrame: {sorted(set(missing))}")

    def __sklearn_is_fitted__(self) -> bool:
        """Verifica se o transformador foi ajustado."""
        return hasattr(self, "_is_fitted") and self._is_fitted
