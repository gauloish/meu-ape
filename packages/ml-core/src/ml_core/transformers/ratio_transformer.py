"""Transformador de razão de características (RatioTransformer).

Cria novas variáveis contínuas calculando a razão entre pares de características especificadas.
"""

from typing import Any, List, Self, Tuple

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.utils.validation import check_is_fitted


class RatioTransformer(TransformerMixin, BaseEstimator):
    """Transformador scikit-learn para geração de razões entre pares de colunas contínuas.

    Atributos:
        pairs (List[Tuple[str, str]]): Lista de pares (coluna_numerador, coluna_denominador).
        sep (str): Separador textual usado no nome da nova coluna. Padrão: '_por_'.

    Example:
        >>> transformer = RatioTransformer(pairs=[("preco", "area_m2")])
        >>> df_ratios = transformer.fit_transform(df)
        >>> # Gera a coluna 'preco_por_area_m2'
    """

    def __init__(
        self,
        pairs: List[Tuple[str, str]],
        sep: str = "_por_",
    ) -> None:
        """Inicializa o transformador de razões.

        Args:
            pairs (List[Tuple[str, str]]): Lista de pares de nomes de características.
            sep (str): Separador utilizado no nome da nova variável. Padrão: '_por_'.
        """
        self.pairs: List[Tuple[str, str]] = pairs
        self.sep: str = sep

    def fit(self, X: pd.DataFrame, y: Any = None) -> Self:
        """Valida as colunas do conjunto de dados de entrada e marca o transformador como ajustado.

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
        """Gera as novas colunas de razão dividindo o numerador pelo denominador.

        Trata divisão por zero substituindo denominadores nulos ou iguais a zero por `NaN`,
        e converte potenciais valores `inf` ou `-inf` em `NaN`.

        Args:
            X (pd.DataFrame): DataFrame de entrada.

        Returns:
            pd.DataFrame: DataFrame acrescido das colunas de razão.
        """
        check_is_fitted(self)
        self._validate_input(X)

        X_out = X.copy()

        for num_col, den_col in self.pairs:
            feature_name = f"{num_col}{self.sep}{den_col}"

            denominator = X_out[den_col].replace(0, np.nan)
            ratio = X_out[num_col] / denominator

            X_out[feature_name] = ratio.replace([np.inf, -np.inf], np.nan)

        return X_out

    def _validate_input(self, X: pd.DataFrame | Any) -> None:
        """Valida se a entrada é um DataFrame e se contém todas as colunas de cada par.

        Args:
            X (pd.DataFrame | Any): Objeto de entrada.

        Raises:
            TypeError: Se a entrada não for um pandas DataFrame.
            ValueError: Se faltarem colunas necessárias.
        """
        if not isinstance(X, pd.DataFrame):
            raise TypeError(f"{self.__class__.__name__} espera um pandas.DataFrame, mas recebeu {type(X).__name__}.")

        missing = []
        for num_col, den_col in self.pairs:
            if num_col not in X.columns:
                missing.append(num_col)
                
            if den_col not in X.columns:
                missing.append(den_col)

        if missing:
            raise ValueError(f"Colunas obrigatórias ausentes no DataFrame: {sorted(set(missing))}")

    def __sklearn_is_fitted__(self) -> bool:
        """Verifica se o transformador foi ajustado."""
        return hasattr(self, "_is_fitted") and self._is_fitted
