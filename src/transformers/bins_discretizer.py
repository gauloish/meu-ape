import pandas as pd

from typing import Any, List, Tuple

from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.utils.validation import check_is_fitted



class BinsDiscretizer(TransformerMixin, BaseEstimator):
    def __init__(
        self,
        bins_info: List[Tuple[str, List[float], List[str]]],
        prefix: str = "faixa_",
    ) -> None:
        """Initialize bins discretizer, is that, a transformer that divide
        the variable in a category variable, discretizing it.

        Args:
            bins_info (List[Tuple[str, List[float], List[str]]]): Information of
            the bins, a list of variables to discretize with the name of the variable,
            the bins and the category of each bin.
            prefix (str, optional): Prefix of the name of the new features. Defaults to "faixa_".
        """
        self.bins_info: List[Tuple[str, List[float], List[str]]] = bins_info
        self.prefix: str = prefix

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

        for feature, bins, labels in self.bins_info:
            name = f"{self.prefix}{feature}"

            X[name] = pd.cut(
                X[feature],
                bins=bins,
                labels=labels
            )

        return X

    def _validate_input(self, X: pd.DataFrame | Any) -> None:
        """Check if the input is valid, that is, if the input is 
        a pandas DataFrame and if it have the features in given
        bins_info.

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

        for info in self.bins_info:
            if info[0] not in X.columns:
                missing.append(info[0])

        if len(missing) != 0:
            raise ValueError(
                f"Missing features: {sorted(missing)}"
            )

    def __sklearn_is_fitted__(self):
        """
        Check fitted status and return a Boolean value.
        """
        return hasattr(self, "_is_fitted") and self._is_fitted
