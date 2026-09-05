"""Módulo de otimização de hiperparâmetros do ml-worker utilizando Optuna e Cross-Validation sem vazamento de dados."""

from typing import Any

import numpy as np
import optuna
from ml_core.pipelines import FeatureGroups, create_training_pipeline
from logging_settings import setup_logger
from sklearn.model_selection import KFold, cross_val_score

logger = setup_logger(__name__)


def search_space(
    trial: optuna.Trial,
    random_state: int | None = 42,
) -> dict[str, Any]:
    """Define o espaço de busca de hiperparâmetros para o modelo XGBRegressor no pipeline.

    Args:
        trial (optuna.Trial): Instância do trial do Optuna.
        random_state (int | None): Semente aleatória para reprodutibilidade. Padrão: 42.

    Returns:
        dict[str, Any]: Dicionário com os hiperparâmetros sugeridos prefixados para o modelo.
    """
    return {
        "model__n_estimators": trial.suggest_int("n_estimators", 100, 1000, step=50),
        "model__learning_rate": trial.suggest_float("learning_rate", 1e-3, 1e-1, log=True),
        "model__max_depth": trial.suggest_int("max_depth", 2, 20),
        "model__min_child_weight": trial.suggest_int("min_child_weight", 1, 10),
        "model__subsample": trial.suggest_float("subsample", 0.5, 1.0, step=0.1),
        "model__colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0, step=0.1),
        "model__reg_alpha": trial.suggest_float("reg_alpha", 1e-8, 1e2, log=True),
        "model__reg_lambda": trial.suggest_float("reg_lambda", 1e-3, 1e2, log=True),
        "model__objective": "reg:absoluteerror",
        "model__log_c": 1.0,
        "model__random_state": random_state,
    }


def optimize_hyperparameters(
    X: Any,
    y: Any,
    n_trials: int = 20,
    k_folds: int = 5,
    random_state: int | None = 42,
    show_progress_bar: bool = False,
    feature_groups: FeatureGroups | None = None,
) -> tuple[dict[str, Any], float]:
    """Executa a otimização de hiperparâmetros utilizando Optuna.

    Args:
        X (Any): Matriz de características de entrada.
        y (Any): Vetor alvo contínuo (preço do imóvel).
        n_trials (int): Número de trials do Optuna. Padrão: 20.
        k_folds (int): Número de folds para a Validação Cruzada interna. Padrão: 5.
        random_state (int | None): Semente aleatória para reprodutibilidade. Padrão: 42.
        show_progress_bar (bool): Se deve exibir a barra de progresso do Optuna. Padrão: False.
        feature_groups (FeatureGroups | None): Grupos de colunas para o pré-processador.

    Returns:
        tuple[dict[str, Any], float]: Tupla contendo o dicionário dos melhores hiperparâmetros e a melhor pontuação de RMSE.
    """
    logger.info(f"Iniciando otimização com Optuna: n_trials={n_trials}, k_folds={k_folds}.")

    # optuna.logging.set_verbosity(optuna.logging.WARNING)

    cv = KFold(
        n_splits=k_folds,
        shuffle=True,
        random_state=random_state,
    )

    cv_splits = list(cv.split(X))

    def objective(trial: optuna.Trial) -> float:
        params = search_space(trial, random_state)
        base_pipeline = create_training_pipeline(feature_groups=feature_groups)
        base_pipeline.set_params(**params)

        try:
            scores = cross_val_score(
                base_pipeline,
                X,
                y,
                cv=cv_splits,
                scoring="neg_mean_absolute_error",
                n_jobs=1,
                error_score="raise",
            )

            rmse = -float(np.mean(scores))

        except Exception as exc:
            logger.warning(f"Trial {trial.number} falhou com erro: {exc}")
            rmse = 1e9

        return rmse

    sampler = optuna.samplers.TPESampler(
        seed=random_state,
    )

    study = optuna.create_study(
        direction="minimize",
        sampler=sampler,
    )

    study.optimize(
        objective,
        n_trials=n_trials,
        show_progress_bar=show_progress_bar,
    )

    logger.info(f"Otimização finalizada. Melhor MAE: {study.best_value:.4f}")

    best_params = search_space(study.best_trial, random_state)

    return best_params, float(study.best_value)
