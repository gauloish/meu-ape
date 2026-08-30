"""Estimador Mixture of Experts (MoE) customizado para regressão de preços de imóveis.

Combina um classificador de roteamento (Gating Network) calibrado com regressores
especializados independentes para cada faixa de preço (Soft Gating).
"""

from collections.abc import Sequence
from typing import Any, Literal, Self

import numpy as np
from sklearn.base import BaseEstimator, RegressorMixin, clone
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import BaseCrossValidator
from sklearn.utils import _safe_indexing
from sklearn.utils.validation import check_is_fitted
from xgboost import XGBClassifier, XGBRegressor

from .metrics import (
    MoEMetricsReport,
    calculate_gating_metrics,
    calculate_regression_metrics,
)


class MoEEstimator(RegressorMixin, BaseEstimator):
    """Estimador Mixture of Experts (MoE) com Calibração de Probabilidades e Soft Gating.

    Orquestra múltiplos regressores especializados para faixas de valores (experts)
    e um classificador de roteamento (gating network) devidamente calibrado via
    `CalibratedClassifierCV`.

    Durante o `fit(X, y)`, o estimador:
    1. Calcula os percentis definidos em `quantiles` (default: 0.6 e 0.9) do target `y`
       para categorizar as amostras em classes (default: "normal", "premium", "luxo").
    2. Treina o `Gating Network` calibrado para prever as probabilidades a posteriori de cada classe.
    3. Treina cada regressor especialista exclusivamente com a fatia de dados da sua respectiva classe.

    Durante o `predict(X)`, realiza o Soft Gating:
    $$\\hat{y}_{\\text{MoE}}(X) = \\sum_{k=1}^K P(\\text{classe} = k \\mid X) \\cdot \\hat{y}_k(X)$$

    Atributos:
        gating_estimator (BaseEstimator | None): Classificador base para o Gating (default: XGBClassifier).
        expert_normal (BaseEstimator | None): Regressor para a classe normal (default: XGBRegressor).
        expert_premium (BaseEstimator | None): Regressor para a classe premium (default: XGBRegressor).
        expert_luxo (BaseEstimator | None): Regressor para a classe luxo (default: XGBRegressor).
        quantiles (tuple[float, float]): Percentis de corte para discretização de `y`. Padrão: (0.6, 0.9).
        labels (tuple[str, str, str]): Rótulos das 3 classes correspondentes. Padrão: ("normal", "premium", "luxo").
        calibration_method (Literal["sigmoid", "isotonic"]): Método de calibração do CalibratedClassifierCV.
        calibration_cv (int | str | BaseCrossValidator | None): Esquema de cross-validation do calibrador. Padrão: 5.
        random_state (int | None): Semente aleatória para reprodutibilidade. Padrão: 42.

    Atributos Ajustados (após `fit`):
        gating_network_ (CalibratedClassifierCV): Instância ajustada do classificador calibrado.
        experts_ (dict[str, BaseEstimator]): Dicionário com os 3 regressores ajustados.
        thresholds_ (tuple[float, float]): Valores reais calculados dos percentis do target.
        classes_ (np.ndarray): Array com os nomes das classes configuradas.
        n_features_in_ (int): Número de features de entrada.
        feature_names_in_ (np.ndarray | None): Nomes das colunas de entrada, se fornecido DataFrame.

    Example:
        >>> from ml_core.estimators import MoEEstimator
        >>> moe = MoEEstimator()
        >>> moe.fit(X_train, y_train)
        >>> y_pred = moe.predict(X_test)
        >>> report = moe.evaluate(X_test, y_test)
        >>> report.print_report()
    """

    def __init__(
        self,
        gating_estimator: BaseEstimator | None = None,
        expert_normal: BaseEstimator | None = None,
        expert_premium: BaseEstimator | None = None,
        expert_luxo: BaseEstimator | None = None,
        quantiles: tuple[float, float] = (0.6, 0.9),
        labels: tuple[str, str, str] = ("normal", "premium", "luxo"),
        calibration_method: Literal["sigmoid", "isotonic"] = "sigmoid",
        calibration_cv: int | str | BaseCrossValidator | None = 5,
        random_state: int | None = 42,
    ) -> None:
        """Inicializa o estimador Mixture of Experts.

        Args:
            gating_estimator (BaseEstimator | None): Classificador base para o Gating.
            expert_normal (BaseEstimator | None): Regressor para a classe normal.
            expert_premium (BaseEstimator | None): Regressor para a classe premium.
            expert_luxo (BaseEstimator | None): Regressor para a classe luxo.
            quantiles (tuple[float, float]): Tupla com dois percentis em (0, 1) em ordem crescente.
            labels (tuple[str, str, str]): Tupla com 3 rótulos ("normal", "premium", "luxo").
            calibration_method (Literal["sigmoid", "isotonic"]): Método para CalibratedClassifierCV.
            calibration_cv (int | str | BaseCrossValidator | None): Estratégia de validação cruzada do calibrador.
            random_state (int | None): Semente aleatória para reprodutibilidade.
        """
        self.gating_estimator = gating_estimator
        self.expert_normal = expert_normal
        self.expert_premium = expert_premium
        self.expert_luxo = expert_luxo
        self.quantiles = quantiles
        self.labels = labels
        self.calibration_method = calibration_method
        self.calibration_cv = calibration_cv
        self.random_state = random_state

    def _get_default_gating_estimator(self) -> BaseEstimator:
        """Gera a instância padrão do classificador XGBoost para o Gating Network."""
        return XGBClassifier(
            n_estimators=100,
            max_depth=4,
            learning_rate=0.05,
            random_state=self.random_state,
            eval_metric="mlogloss",
            tree_method="hist",
        )

    def _get_default_expert_estimator(self) -> BaseEstimator:
        """Gera a instância padrão do regressor XGBoost para os especialistas."""
        return XGBRegressor(
            n_estimators=500,
            max_depth=6,
            learning_rate=0.03,
            random_state=self.random_state,
            tree_method="hist",
        )

    def _discretize_target(
        self, y: np.ndarray, thresholds: tuple[float, float]
    ) -> np.ndarray:
        """Mapeia os valores contínuos de target `y` para os índices inteiros de classe [0, 1, 2].

        0: normal (y <= q_low)
        1: premium (q_low < y <= q_high)
        2: luxo (y > q_high)

        Args:
            y (np.ndarray): Vetor de valores alvo 1D.
            thresholds (tuple[float, float]): Limites (q_low, q_high).

        Returns:
            np.ndarray: Vetor de inteiros com os índices das classes correspondentes.
        """
        q_low, q_high = thresholds
        y_classes = np.zeros(len(y), dtype=np.int64)

        y_classes[y <= q_low] = 0
        y_classes[(y > q_low) & (y <= q_high)] = 1
        y_classes[y > q_high] = 2

        return y_classes

    def fit(self, X: Any, y: Any) -> Self:
        """Ajusta o Gating Network calibrado e os especialistas em seus respectivos subconjuntos.

        Args:
            X (Any): Matriz de features de entrada (pd.DataFrame, np.ndarray, etc.).
            y (Any): Vetor de variável alvo contínua (preço do imóvel).

        Returns:
            Self: Instância do próprio estimador ajustado.

        Raises:
            ValueError: Se os percentis forem inválidos ou se alguma classe não tiver amostras.
        """
        if len(self.quantiles) != 2 or not (
            0.0 < self.quantiles[0] < self.quantiles[1] < 1.0
        ):
            raise ValueError(
                f"`quantiles` deve ser uma tupla de 2 floats ordenados em (0, 1), mas recebeu {self.quantiles}."
            )

        if len(self.labels) != 3:
            raise ValueError(
                f"`labels` deve conter exatamente 3 strings, mas recebeu {self.labels}."
            )

        # Extração e validação de metadados
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

        # 1. Cálculo dos limiares de percentil
        q_low = float(np.quantile(y_arr, self.quantiles[0]))
        q_high = float(np.quantile(y_arr, self.quantiles[1]))

        if q_low >= q_high:
            raise ValueError(
                f"Os percentis calculados não são estritamente crescentes: q[{self.quantiles[0]}]={q_low}, "
                f"q[{self.quantiles[1]}]={q_high}. Verifique a distribuição do target."
            )

        self.thresholds_ = (q_low, q_high)
        self.classes_ = np.array(self.labels, dtype=object)

        # 2. Discretização de y em inteiros 0, 1, 2 para compatibilidade total com classificadores
        y_classes_int = self._discretize_target(y_arr, self.thresholds_)

        # 3. Treinamento do Gating Network com CalibratedClassifierCV
        base_gating = (
            clone(self.gating_estimator)
            if self.gating_estimator is not None
            else self._get_default_gating_estimator()
        )

        self.gating_network_ = CalibratedClassifierCV(
            estimator=base_gating,
            method=self.calibration_method,
            cv=self.calibration_cv,
        )
        self.gating_network_.fit(X, y_classes_int)

        # 4. Treinamento isolado de cada Expert
        self.experts_: dict[str, BaseEstimator] = {}

        expert_templates = {
            self.labels[0]: self.expert_normal,
            self.labels[1]: self.expert_premium,
            self.labels[2]: self.expert_luxo,
        }

        for class_idx, label in enumerate(self.labels):
            mask = y_classes_int == class_idx
            indices = np.where(mask)[0]

            if len(indices) == 0:
                raise ValueError(
                    f"Nenhuma amostra encontrada para a classe '{label}' (índice {class_idx}). "
                    "Verifique se o dataset possui volume suficiente."
                )

            X_subset = _safe_indexing(X, indices)
            y_subset = _safe_indexing(y_arr, indices)

            template = expert_templates[label]
            expert_clf = (
                clone(template)
                if template is not None
                else self._get_default_expert_estimator()
            )

            expert_clf.fit(X_subset, y_subset)
            self.experts_[label] = expert_clf

        self._is_fitted = True
        return self

    def predict_proba_gating(self, X: Any) -> np.ndarray:
        """Prediz as probabilidades calibradas de roteamento do Gating Network para cada classe.

        Garante que a ordem das colunas da matriz de probabilidades retornada coincida exatamente
        com a ordem declarada em `self.labels` (índices 0, 1, 2).

        Args:
            X (Any): Matriz de features de entrada.

        Returns:
            np.ndarray: Matriz de probabilidades de formato (N, 3), onde as somas das linhas equivalem a 1.0.
        """
        check_is_fitted(self, attributes=["gating_network_", "experts_", "thresholds_"])

        raw_probas = self.gating_network_.predict_proba(X)
        gating_classes = list(self.gating_network_.classes_)

        n_samples = raw_probas.shape[0]
        n_labels = len(self.labels)
        aligned_probas = np.zeros((n_samples, n_labels), dtype=np.float64)

        for target_idx in range(n_labels):
            if target_idx in gating_classes:
                src_idx = gating_classes.index(target_idx)
                aligned_probas[:, target_idx] = raw_probas[:, src_idx]

        # Normalização de segurança para garantir estritamente soma 1.0 em todas as linhas
        row_sums = np.sum(aligned_probas, axis=1, keepdims=True)
        row_sums[row_sums == 0.0] = 1.0
        aligned_probas = aligned_probas / row_sums

        return aligned_probas

    def predict_experts(self, X: Any) -> dict[str, np.ndarray]:
        """Gera as predições de regressão contínua individuais de cada um dos especialistas.

        Args:
            X (Any): Matriz de features de entrada.

        Returns:
            dict[str, np.ndarray]: Dicionário com chaves correspondentes aos labels e arrays 1D de predições.
        """
        check_is_fitted(self, attributes=["gating_network_", "experts_", "thresholds_"])

        return {
            label: np.asarray(self.experts_[label].predict(X), dtype=np.float64).ravel()
            for label in self.labels
        }

    def predict(self, X: Any) -> np.ndarray:
        """Prediz o valor contínuo do target aplicando a média ponderada do Soft Gating.

        $$\\hat{y}_{\\text{MoE}}(X) = \\sum_{k=1}^K P_{\\text{calibrado}}(\\text{classe} = k \\mid X) \\cdot \\hat{y}_k(X)$$

        Args:
            X (Any): Matriz de features de entrada.

        Returns:
            np.ndarray: Vetor 1D contendo os preços preditos finais.
        """
        check_is_fitted(self, attributes=["gating_network_", "experts_", "thresholds_"])

        probas = self.predict_proba_gating(X)  # (N, 3)
        experts_dict = self.predict_experts(X)

        expert_matrix = np.column_stack(
            [experts_dict[label] for label in self.labels]
        )  # (N, 3)

        y_pred = np.sum(probas * expert_matrix, axis=1)
        return y_pred

    def evaluate(self, X: Any, y: Sequence[float] | np.ndarray) -> MoEMetricsReport:
        """Executa a extração completa e 'stateless' de métricas de calibração, classificação e regressão.

        Não altera o estado interno do estimador.

        Args:
            X (Any): Matriz de features de teste/validação.
            y (Sequence[float] | np.ndarray): Vetor de valores alvo reais contínuos.

        Returns:
            MoEMetricsReport: Relatório Pydantic imutável com métricas globais, do gating e dos experts.
        """
        check_is_fitted(self, attributes=["gating_network_", "experts_", "thresholds_"])

        y_arr = np.asarray(y, dtype=np.float64).ravel()

        # 1. Discretização de referência usando thresholds_ do treino
        y_true_indices = self._discretize_target(y_arr, self.thresholds_)
        y_true_classes = np.array(
            [self.labels[i] for i in y_true_indices], dtype=object
        )

        # 2. Métricas do Gating Network
        gating_proba = self.predict_proba_gating(X)
        gating_pred_indices = np.argmax(gating_proba, axis=1)
        gating_pred_classes = np.array(
            [self.labels[i] for i in gating_pred_indices], dtype=object
        )

        gating_metrics = calculate_gating_metrics(
            y_true=y_true_classes,
            y_pred=gating_pred_classes,
            y_proba=gating_proba,
            classes=self.labels,
        )

        # 3. Métricas isoladas de cada Expert na sua respectiva fatia real
        expert_metrics_dict = {}

        for class_idx, label in enumerate(self.labels):
            mask = y_true_indices == class_idx
            indices = np.where(mask)[0]

            if len(indices) > 0:
                X_k = _safe_indexing(X, indices)
                y_k = _safe_indexing(y_arr, indices)
                y_pred_k = self.experts_[label].predict(X_k)
                expert_metrics_dict[label] = calculate_regression_metrics(y_k, y_pred_k)
            else:
                expert_metrics_dict[label] = calculate_regression_metrics([], [])

        # 4. Métricas globais do MoE
        y_pred_moe = self.predict(X)
        global_metrics = calculate_regression_metrics(y_arr, y_pred_moe)

        return MoEMetricsReport(
            global_metrics=global_metrics,
            gating_metrics=gating_metrics,
            expert_metrics=expert_metrics_dict,
        )

    def __sklearn_is_fitted__(self) -> bool:
        """Verifica se o estimador foi devidamente ajustado."""
        return hasattr(self, "_is_fitted") and self._is_fitted
