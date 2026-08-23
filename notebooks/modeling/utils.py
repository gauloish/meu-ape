import optuna

import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

from sklearn.model_selection import (
    KFold,
    cross_val_score,
    cross_validate,
)

random_state = 1667

cv = KFold(
    n_splits=5,
    shuffle=True,
    random_state=random_state,
)

def get_study(
    get_pipeline,
    get_parameters,
    X_train,
    y_train,
    scoring="neg_root_mean_squared_error",
    pruner=optuna.pruners.NopPruner(),
    n_trials=100,
):
    def objective(trial):
        parameters = get_parameters(trial)
        pipeline = get_pipeline(parameters)

        scores = cross_val_score(
            pipeline,
            X_train,
            y_train,
            cv=cv,
            scoring=scoring,
        )

        return scores.mean()

    study = optuna.create_study(
        direction="maximize",
        pruner=pruner,
        sampler=optuna.samplers.TPESampler(
            seed=random_state
        )
    )

    study.optimize(
        objective,
        n_trials=n_trials,
        show_progress_bar=True,
    )

    return study


def report_scores(
    get_pipeline,
    study,
    X_test,
    y_test
):
    pipeline = get_pipeline(study.best_params)

    scoring = {
        "R2": "r2",
        "RMSE": "neg_root_mean_squared_error",
        "MAE": "neg_mean_absolute_error",
        "MedAE": "neg_median_absolute_error",
        "MAPE": "neg_mean_absolute_percentage_error",
    }

    scores = cross_validate(
        pipeline,
        X_test,
        y_test,
        cv=cv,
        scoring=scoring,
    )

    for score_name in scoring.keys():
        score_value = abs(scores[f"test_{score_name}"].mean())

        if score_name == "R2":
            print(f"{score_name}: {score_value:.2f}")
        elif score_name == "MAPE":
            print(f"{score_name}: {score_value:.2f}%")
        else:
            print(f"{score_name}: R$ {score_value:.2f}")

def _build_error_df(X_test, y_test, y_pred):
    error_df = X_test.copy()

    error_df["y_true"] = y_test
    error_df["y_pred"] = y_pred
    error_df["residual"] = error_df["y_true"] - error_df["y_pred"]
    error_df["abs_error"] = error_df["residual"].abs()
    error_df["sq_error"] = error_df["residual"] ** 2

    denominator = error_df["y_true"].replace(0, np.nan)

    error_df["relative_error"] = (
        error_df["residual"] / denominator
    )

    error_df["absolute_relative_error"] = (
        error_df["abs_error"] / denominator
    )

    return error_df


def _plot_residuals_vs_predictions(error_df):
    fig, ax = plt.subplots(figsize=(8, 5))

    sns.scatterplot(
        data=error_df,
        x="y_pred",
        y="residual",
        alpha=0.5,
        ax=ax,
    )

    ax.axhline(
        0,
        linestyle="--",
        linewidth=1.5,
    )

    ax.set(
        xlabel="Predição",
        ylabel="Resíduo",
        title="Resíduos vs Predição",
    )

    sns.despine()
    plt.tight_layout()
    plt.show()


def _plot_residual_distribution(error_df):
    fig, ax = plt.subplots(figsize=(8, 5))

    sns.histplot(
        data=error_df,
        x="residual",
        bins=50,
        kde=True,
        ax=ax,
    )

    ax.axvline(
        0,
        linestyle="--",
        linewidth=1.5,
    )

    ax.set(
        xlabel="Resíduo",
        ylabel="Frequência",
        title="Distribuição dos Resíduos",
    )

    sns.despine()
    plt.tight_layout()
    plt.show()


def _plot_features_vs_residuals(error_df, features):
    n_features = len(features)

    n_cols = 2
    n_rows = int(np.ceil(n_features / n_cols))

    fig, axes = plt.subplots(
        n_rows,
        n_cols,
        figsize=(12, 5 * n_rows),
    )

    axes = np.atleast_1d(axes).flatten()

    for ax, feature in zip(axes, features):

        sns.scatterplot(
            data=error_df,
            x=feature,
            y="residual",
            alpha=0.4,
            ax=ax,
        )

        ax.axhline(
            0,
            linestyle="--",
            linewidth=1.5,
        )

        ax.set(
            xlabel=feature,
            ylabel="Resíduo",
            title=f"Resíduo vs {feature}",
        )

    for ax in axes[n_features:]:
        ax.remove()

    fig.suptitle(
        "Resíduos vs Features",
        fontsize=16,
        y=1.02,
    )

    sns.despine()
    plt.tight_layout()
    plt.show()


def _plot_absolute_error_vs_predictions(error_df):
    fig, ax = plt.subplots(figsize=(8, 5))

    sns.scatterplot(
        data=error_df,
        x="y_pred",
        y="abs_error",
        alpha=0.5,
        ax=ax,
    )

    ax.set(
        xlabel="Predição",
        ylabel="|Erro|",
        title="Erro Absoluto vs Predição",
    )

    sns.despine()
    plt.tight_layout()
    plt.show()


def _print_error_statistics(error_df):
    print("\n=== Erro Relativo Absoluto ===")

    print(
        error_df["absolute_relative_error"]
        .describe()
    )


def _print_worst_predictions(error_df, n=20):
    print(f"\n=== {n} Maiores Erros Absolutos ===")

    worst = (
        error_df
        .sort_values(
            "abs_error",
            ascending=False,
        )
        .head(n)
    )

    print(worst.to_string())


def _print_worst_predictions_summary(
    error_df,
    features,
    n=30,
):
    columns = [
        "y_true",
        "y_pred",
        "residual",
        "abs_error",
        *features,
    ]

    columns = [
        column
        for column in columns
        if column in error_df.columns
    ]

    print(f"\n=== Resumo dos {n} Maiores Erros ===")

    worst = (
        error_df
        .sort_values(
            "abs_error",
            ascending=False,
        )
        .loc[:, columns]
        .head(n)
    )

    print(worst.to_string())


def get_residual_analysis(
    get_pipeline,
    study,
    X_train,
    y_train,
    X_test,
    y_test,
    features=None,
    n_worst=20,
):
    """
    Treina o melhor modelo do Optuna e executa análise
    de resíduos e erros no conjunto de teste.
    """

    if features is None:
        features = [
            "area_m2",
            "condominio",
            "quartos",
            "banheiros",
        ]

    parameters = study.best_params
    pipeline = get_pipeline(parameters)

    pipeline.fit(X_train, y_train)

    y_pred = pipeline.predict(X_test)

    error_df = _build_error_df(
        X_test=X_test,
        y_test=y_test,
        y_pred=y_pred,
    )

    _plot_residuals_vs_predictions(error_df)

    _plot_residual_distribution(error_df)

    _plot_features_vs_residuals(
        error_df,
        features,
    )

    _plot_absolute_error_vs_predictions(error_df)

    _print_error_statistics(error_df)

    _print_worst_predictions(
        error_df,
        n=n_worst,
    )

    _print_worst_predictions_summary(
        error_df,
        features=features,
        n=n_worst,
    )

    return error_df