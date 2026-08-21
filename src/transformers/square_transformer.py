import pandas as pd
import numpy as np

from typing import Any, List

from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.utils.validation import check_is_fitted


class SquareTransformer(TransformerMixin, BaseEstimator):
    def __init__(
        self,
        features: List[str],
        suffix: str = "_square"
    ) -> None:
        """Initialize square transformers that create features with square
        transformation from given features.

        Args:
            features (List[str]): List of features to transform.
            suffix (str, optional): Suffix to name of the
            new features. Defaults to "_square".
        """
        self.features: List[str] = features
        self.suffix: str = suffix

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
        """Create new features with square transformation.

        Args:
            X (pd.DataFrame): Original dataset.

        Returns:
            pd.DataFrame: Updated dataset with new features
            with the square transformation.
        """
        check_is_fitted(self)
        self._validate_input(X)

        X = X.copy()

        for feature in self.features:
            name = f"{feature}{self.suffix}"
            mask = X[feature].notna()

            X[name] = np.nan
            X.loc[mask, name] = np.square(X.loc[mask, name])

        return X

    def _validate_input(self, X: pd.DataFrame | Any) -> None:
        """Check if the input is valid, that is, if the input is 
        a pandas DataFrame and if it have the features in given
        features.

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

        for feature in self.features:
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
