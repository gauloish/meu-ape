"""Módulo de avaliação por Nested Cross-Validation."""

from typing import Any

import numpy as np
from logging_config import config_logger
from loguru import logger
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

config_logger()


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


def evaluate_pipeline(
    X: Any,
    y: Any,
    feature_groups: FeatureGroups,
    k_outer: int = 5,
    k_inner: int = 5,
    n_trials: int = 20,
    random_state: int | None = 1667,
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
        feature_groups (FeatureGroups): Grupos de colunas para o pré-processador.
        k_outer (int): Número de folds do loop externo. Defaults: 5.
        k_inner (int): Número de folds do loop interno de otimização. Defaults: 5.
        n_trials (int): Número de trials do Optuna no loop interno. Defaults: 20.
        random_state (int | None): Semente aleatória para reprodutibilidade. Defaults: 42.

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

        X_train = X[train_idx]
        y_train = y[train_idx]
        X_test = X[test_idx]
        y_test = y[test_idx]

        best_params, best_score = optimize_hyperparameters(
            X=X_train,
            y=y_train,
            n_trials=n_trials,
            k_folds=k_inner,
            random_state=random_state,
            feature_groups=feature_groups,
        )

        logger.info(
            f"Fold {fold_idx}: Otimização interna concluída (Melhor MAE interno: {best_score:.2f})."
        )

        pipeline = create_training_pipeline(feature_groups=feature_groups)
        pipeline.set_params(**best_params)
        pipeline.fit(X_train, y_train)

        y_pred = pipeline.predict(X_test)
        metrics = calculate_regression_metrics(y_test, y_pred)

        fold_results.append(metrics)

        report = RegressionMetricsReport(
            regression_metrics=metrics,
        )

        logger.info(f"Fold {fold_idx}, {report.get_report()}")

    mean_metrics, std_metrics = calculate_aggregated_metrics(fold_results)

    return {
        "metrics_summary": {
            "r2": {
                "mean": float(mean_metrics.r2),
                "std": float(std_metrics.r2),
            },
            "rmse": {
                "mean": float(mean_metrics.rmse),
                "std": float(std_metrics.rmse),
            },
            "mae": {
                "mean": float(mean_metrics.mae),
                "std": float(std_metrics.mae),
            },
            "medae": {
                "mean": float(mean_metrics.medae),
                "std": float(std_metrics.medae),
            },
            "mape": {
                "mean": float(mean_metrics.mape),
                "std": float(std_metrics.mape),
            },
            "mean": mean_metrics.model_dump(),
            "std": std_metrics.model_dump(),
        },
        "k_inner": k_inner,
        "k_outer": k_outer,
        "n_trials": n_trials,
        "random_state": random_state,
        "fold_metrics": [metric.model_dump() for metric in fold_results],
    }
