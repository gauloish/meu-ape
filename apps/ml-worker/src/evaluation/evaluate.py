"""Módulo de avaliação por Nested Cross-Validation."""

from typing import Any

import numpy as np
from logging_settings import setup_logger
from ml_core.estimators import (
    RegressionMetrics,
    RegressionMetricsReport,
    calculate_aggregated_metrics,
    calculate_regression_metrics,
)
from ml_core.pipelines import FeatureGroups, create_training_pipeline
from optimization.optimize import optimize_hyperparameters
from sklearn.metrics import (
    mean_absolute_error,
    mean_absolute_percentage_error,
    median_absolute_error,
    r2_score,
    root_mean_squared_error,
)
from sklearn.model_selection import KFold
from sklearn.utils import _safe_indexing

logger = setup_logger(__name__)


def compute_metrics(y_true: Any, y_pred: Any) -> dict[str, float]:
    """Calcula as métricas de regressão principais: R², RMSE, MAE, MedAE e MAPE.

    Args:
        y_true (Any): Valores alvo reais.
        y_pred (Any): Valores preditos pelo modelo.

    Returns:
        dict[str, float]: Dicionário contendo o valor numérico de cada métrica.
    """
    y_true_arr = np.asarray(y_true, dtype=np.float64).ravel()
    y_pred_arr = np.asarray(y_pred, dtype=np.float64).ravel()

    rmse = float(root_mean_squared_error(y_true_arr, y_pred_arr))
    r2 = float(r2_score(y_true_arr, y_pred_arr))
    mae = float(mean_absolute_error(y_true_arr, y_pred_arr))
    medae = float(median_absolute_error(y_true_arr, y_pred_arr))
    mape = float(mean_absolute_percentage_error(y_true_arr, y_pred_arr))

    return {
        "r2": r2,
        "rmse": rmse,
        "mae": mae,
        "medae": medae,
        "mape": mape,
    }


def run_nested_cv(
    X: Any,
    y: Any,
    k_outer: int = 5,
    k_inner: int = 5,
    n_trials: int = 20,
    random_state: int | None = 42,
    feature_groups: FeatureGroups | None = None,
) -> dict[str, Any]:
    """Executa a Validação Cruzada Aninhada (Nested CV) para estimar a performance não-enviesada do modelo.

    Estrutura:
    1. Divide os dados em `k_outer` folds externos.
    2. Em cada fold externo, executa `optimize_hyperparameters()` usando apenas os dados de treino
       externos (`k_inner` folds internos e `n_trials`).
    3. Treina o pipeline final do fold com os melhores hiperparâmetros no treino externo.
    4. Avalia no conjunto de teste externo.
    5. Retorna agregação de média e desvio padrão das métricas R², RMSE, MAE, MedAE e MAPE.

    Args:
        X (Any): Matriz de características.
        y (Any): Vetor alvo contínuo (preço do imóvel).
        k_outer (int): Número de folds do loop externo. Padrão: 5.
        k_inner (int): Número de folds do loop interno de otimização. Padrão: 5.
        n_trials (int): Número de trials do Optuna no loop interno. Padrão: 20.
        random_state (int | None): Semente aleatória para reprodutibilidade. Padrão: 42.
        feature_groups (FeatureGroups | None): Grupos de colunas para o pré-processador.

    Returns:
        dict[str, Any]: Dicionário com `metrics_summary` (média e desvio padrão) e `fold_metrics`.
    """
    logger.info(
        f"Iniciando Nested CV: k_outer={k_outer}, k_inner={k_inner}, n_trials={n_trials}."
    )

    outer_cv = KFold(
        n_splits=k_outer,
        shuffle=True,
        random_state=random_state,
    )

    fold_results: list[RegressionMetrics] = []

    for fold_idx, (train_idx, test_idx) in enumerate(outer_cv.split(X), start=1):
        logger.info(f"--- Processando Fold Externo {fold_idx}/{k_outer} ---")

        X_train_outer = _safe_indexing(X, train_idx)
        y_train_outer = _safe_indexing(y, train_idx)
        X_test_outer = _safe_indexing(X, test_idx)
        y_test_outer = _safe_indexing(y, test_idx)

        best_params, best_inner_score = optimize_hyperparameters(
            X=X_train_outer,
            y=y_train_outer,
            n_trials=n_trials,
            k_folds=k_inner,
            random_state=random_state,
            feature_groups=feature_groups,
        )

        logger.info(
            f"Fold {fold_idx}: Otimização interna concluída (Melhor MAE interno: {best_inner_score:.2f})."
        )

        pipeline = create_training_pipeline(feature_groups=feature_groups)
        pipeline.set_params(**best_params)
        pipeline.fit(X_train_outer, y_train_outer)

        y_pred = pipeline.predict(X_test_outer)
        metrics = calculate_regression_metrics(y_test_outer, y_pred)

        fold_results.append(metrics)

        report = RegressionMetricsReport(
            regression_metrics=metrics,
        )

        logger.info(f"Fold {fold_idx}, {report.get_report()}")

    mean_metrics, std_metrics = calculate_aggregated_metrics(fold_results)

    return {
        "metrics_summary": {
            "r2_mean": float(mean_metrics.r2),
            "r2_std": float(std_metrics.r2),
            "rmse_mean": float(mean_metrics.rmse),
            "rmse_std": float(std_metrics.rmse),
            "mae_mean": float(mean_metrics.mae),
            "mae_std": float(std_metrics.mae),
            "medae_mean": float(mean_metrics.medae),
            "medae_std": float(std_metrics.medae),
            "mape_mean": float(mean_metrics.mape),
            "mape_std": float(std_metrics.mape),
            "mean": mean_metrics.model_dump(),
            "std": std_metrics.model_dump(),
        },
        "k_inner": k_inner,
        "k_outer": k_outer,
        "n_trials": n_trials,
        "random_state": random_state,
        "fold_metrics": [metric.model_dump() for metric in fold_results],
    }
