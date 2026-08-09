import pandas as pd
import numpy as np

from typing import Any, List, Tuple

from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.utils.validation import check_is_fitted



class RatioTransformer(TransformerMixin, BaseEstimator):
    def __init__(
        self,
        pairs: List[Tuple[str, str]],
        sep: str = "_por_",
    ) -> None:
        """Initialize ratio transformer to create ratio
        features from pair of continuous features.

        Args:
            pairs (List[Tuple[str, str]]): A list of pairs of features
            to generate the features ratios
            sep (str, optional): Separator of the name of the new
            ratio features. Defaults to "_por_".
        """
        self.pairs: List[Tuple[str, str]] = pairs
        self.sep: str = sep

    def fit(self, X: pd.DataFrame, y=None):
        """Fit the data.

        Args:
            X (pd.DataFrame): Original dataset
            y (None, optional): Ignored. Defaults to None.

        Returns:
            Self: Self
        """
        self._is_fitted = True

        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """Create the new category features discretizing
        continuous features from dataset.

        Args:
            X (pd.DataFrame): Original dataset

        Returns:
            pd.DataFrame: Updated dataset with the
            new category features.
        """
        check_is_fitted(self)
        self._validate_input(X)

        X = X.copy()

        for feature_a, feature_b in self.pairs:
            name = f"{feature_a}{self.sep}{feature_b}"

            X[name] = X[feature_a] / X[feature_b].replace(0, np.nan)

        return X

    def _validate_input(self, X: pd.DataFrame | Any) -> None:
        """Check if the input is valid, that is, if the input is 
        a pandas DataFrame and if it have the features in given
        pairs.

        Args:
            X (pd.DataFrame | Any): Original dataset.

        Raises:
            TypeError: Throw if the input is not a pandas DataFrame.
            ValueError: Throw if are missing features.
        """ 
        if not isinstance(X, pd.DataFrame):
            raise TypeError(
                f"{self.__class__.__name__} expects a pandas.DataFrame, "
                f"but received a {type(X).__name__}."
            )

        missing = []

        for features in self.pairs:
            for feature in features:
                if feature not in X.columns:
                    missing.append(feature)

        if len(missing) != 0:
            raise ValueError(
                f"Missing features: {sorted(missing)}"
            )

    def __sklearn_is_fitted__(self):
        """
        Check fitted status and return a Boolean value.
        """
        return hasattr(self, "_is_fitted") and self._is_fitted
