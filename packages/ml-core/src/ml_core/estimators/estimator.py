"""Estimador baseado em XGBoost com transformação logarítmica do target para regressão de preços de imóveis.

Fornece a classe `Regressor`, uma subclasse de `BaseEstimator` e `RegressorMixin` do scikit-learn
que encapsula o `XGBRegressor` envolvido por `TransformedTargetRegressor` e `LogCpTransformer` (feature-engine),
garantindo robustez contra outliers extremados (imóveis de alto padrão/luxo) e total compatibilidade com
pipelines do Scikit-Learn e otimizadores como Optuna.
"""

from collections.abc import Sequence
from typing import Any, Self

import numpy as np
from feature_engine.transformation import LogCpTransformer
from sklearn.base import BaseEstimator, RegressorMixin
from sklearn.compose import TransformedTargetRegressor
from sklearn.utils.validation import check_is_fitted
from xgboost import XGBRegressor

from .metrics import (
    RegressionMetrics,
    calculate_regression_metrics,
)


class Regressor(RegressorMixin, BaseEstimator):
    """Estimador de Regressão robusto a outliers baseado em Gradient Boosting (XGBoost).

    Orquestra um modelo `XGBRegressor` ajustado para predição contínua de preços
    de imóveis. O estimador utiliza a função de perda de erro absoluto (`reg:absoluteerror`) e
    envelopa o regressor interno com `TransformedTargetRegressor` acoplado ao
    `LogCpTransformer` (feature-engine) para transformar o target na escala logarítmica
    durante o `fit` e desfazê-la durante o `predict`.

    Atua como estimador principal do ecossistema `ml-core` e atende à interface
    padrão de estimadores do scikit-learn, integrando-se nativamente a `Pipeline`,
    `cross_val_score` e Optuna.

    Durante o `fit(X, y)`, o estimador:
    1. Valida as dimensões e nomes de colunas das características de entrada `X`.
    2. Garante a conversão defensiva do vetor alvo `y` para array unidimensional.
    3. Instancia o `XGBRegressor` com a função de perda configurada (padrão: `reg:absoluteerror`).
    4. Envelopa o modelo com `TransformedTargetRegressor` usando `LogCpTransformer(C=log_c)`.
    5. Executa o treinamento completo.

    Durante o `predict(X)`, realiza a inferência e reverte automaticamente a escala logarítmica,
    retornando os preços previstos na moeda original (Reais R$).

    Durante o `evaluate(X, y)`, gera um relatório imutável `RegressionMetrics`
    contendo as métricas R², RMSE, MAE, MedAE, MAPE e erro máximo.

    Attributes:
        n_estimators (int): Número total de árvores de decisão no ensemble. Padrão: 100.
        max_depth (int): Profundidade máxima de cada árvore individual. Padrão: 6.
        learning_rate (float): Taxa de aprendizado (shrinkage) aplicada a cada passo. Padrão: 0.1.
        min_child_weight (int): Peso mínimo exigido em um nó filho. Padrão: 1.
        subsample (float): Fração de amostragem de dados por árvore. Padrão: 1.0.
        colsample_bytree (float): Fração de amostragem de características por árvore. Padrão: 1.0.
        reg_alpha (float): Termo de regularização L1 (Lasso). Padrão: 0.0.
        reg_lambda (float): Termo de regularização L2 (Ridge). Padrão: 1.0.
        objective (str): Função de perda do XGBoost (ex: 'reg:absoluteerror'). Padrão: 'reg:absoluteerror'.
        log_c (float): Constante C adicionada ao target no LogCpTransformer. Padrão: 1.0.
        random_state (int | None): Semente aleatória para reprodutibilidade. Padrão: 42.

    Attributes Ajustados (após `fit`):
        estimator_ (TransformedTargetRegressor): Instância ajustada do regressor envelopado.
        n_features_in_ (int): Número de características observadas no treinamento.
        feature_names_in_ (np.ndarray | None): Nomes das colunas de entrada, se fornecido DataFrame.

    Example:
        >>> from ml_core.estimators import Regressor
        >>> model = Regressor(
        ...     n_estimators=100,
        ...     max_depth=5,
        ...     learning_rate=0.05,
        ...     objective="reg:absoluteerror",
        ... )
        >>> model.fit(X_train, y_train)
        >>> y_pred = model.predict(X_test)
        >>> metrics = model.evaluate(X_test, y_test)
        >>> print(metrics.rmse)
    """

    def __init__(
        self,
        n_estimators: int = 100,
        max_depth: int = 6,
        learning_rate: float = 0.1,
        min_child_weight: int = 1,
        subsample: float = 1.0,
        colsample_bytree: float = 1.0,
        reg_alpha: float = 0.0,
        reg_lambda: float = 1.0,
        objective: str = "reg:absoluteerror",
        log_c: float = 1.0,
        random_state: int | None = 42,
    ) -> None:
        """Inicializa o estimador Regressor encapsulando o XGBoost e LogCpTransformer.

        Args:
            n_estimators (int): Número total de árvores no ensemble. Padrão: 100.
            max_depth (int): Profundidade máxima de cada árvore. Padrão: 6.
            learning_rate (float): Taxa de aprendizado. Padrão: 0.1.
            min_child_weight (int): Peso mínimo para divisão de nó. Padrão: 1.
            subsample (float): Proporção de amostragem de dados. Padrão: 1.0.
            colsample_bytree (float): Proporção de amostragem de características. Padrão: 1.0.
            reg_alpha (float): Regularização L1. Padrão: 0.0.
            reg_lambda (float): Regularização L2. Padrão: 1.0.
            objective (str): Função de perda do XGBoost. Padrão: 'reg:absoluteerror'.
            log_c (float): Constante C do LogCpTransformer. Padrão: 1.0.
            random_state (int | None): Semente aleatória. Padrão: 42.
        """
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.learning_rate = learning_rate
        self.min_child_weight = min_child_weight
        self.subsample = subsample
        self.colsample_bytree = colsample_bytree
        self.reg_alpha = reg_alpha
        self.reg_lambda = reg_lambda
        self.objective = objective
        self.log_c = log_c
        self.random_state = random_state

    def fit(self, X: Any, y: Any) -> Self:
        """Ajusta o modelo com transformação de target nos dados de treinamento.

        Args:
            X (Any): Matriz de características de entrada (pd.DataFrame, np.ndarray, etc.).
            y (Any): Vetor alvo contínuo (preço do imóvel).

        Returns:
            Self: Instância do próprio estimador ajustado.

        Raises:
            ValueError: Se o vetor alvo `y` estiver vazio.
        """
        if hasattr(X, "columns"):
            self.feature_names_in_ = np.array(X.columns, dtype=object)
        else:
            self.feature_names_in_ = None

        if hasattr(X, "shape"):
            self.n_features_in_ = int(X.shape[1])
        else:
            self.n_features_in_ = len(X[0])

        y_arr = np.asarray(y, dtype=np.float64).ravel()
        n_samples = len(y_arr)

        if n_samples == 0:
            raise ValueError("O vetor de target `y` não pode estar vazio.")

        base_xgb = XGBRegressor(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            learning_rate=self.learning_rate,
            min_child_weight=self.min_child_weight,
            subsample=self.subsample,
            colsample_bytree=self.colsample_bytree,
            reg_alpha=self.reg_alpha,
            reg_lambda=self.reg_lambda,
            objective=self.objective,
            random_state=self.random_state,
        )

        transformer = LogCpTransformer(C=self.log_c)

        self.estimator_ = TransformedTargetRegressor(
            regressor=base_xgb,
            transformer=transformer,
        )

        self.estimator_.fit(X, y_arr)
        self._is_fitted = True

        return self

    def predict(self, X: Any) -> np.ndarray:
        """Realiza a inferência de preços revertendo automaticamente a escala logarítmica.

        Args:
            X (Any): Matriz de características de entrada (pd.DataFrame, np.ndarray, etc.).

        Returns:
            np.ndarray: Vetor 1D com as previsões de preços em Reais (R$).
        """
        check_is_fitted(self, attributes=["estimator_"])

        y_pred = self.estimator_.predict(X)
        return np.asarray(y_pred, dtype=np.float64).ravel()

    def evaluate(self, X: Any, y: Sequence[float] | np.ndarray) -> RegressionMetrics:
        """Calcula o conjunto padronizado de métricas de regressão na escala original.

        Args:
            X (Any): Matriz de características de entrada.
            y (Sequence[float] | np.ndarray): Vetor de preços reais contínuos em Reais (R$).

        Returns:
            RegressionMetrics: Objeto Pydantic imutável contendo R², RMSE, MAE, MedAE, MAPE e erro máximo.
        """
        check_is_fitted(self, attributes=["estimator_"])

        y_true = np.asarray(y, dtype=np.float64).ravel()
        y_pred = self.predict(X)

        return calculate_regression_metrics(y_true, y_pred)

    def __sklearn_is_fitted__(self) -> bool:
        """Verifica se o estimador foi devidamente ajustado."""
        return hasattr(self, "_is_fitted") and self._is_fitted
