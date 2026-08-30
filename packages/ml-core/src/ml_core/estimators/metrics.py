"""Modelos Pydantic e funções utilitárias para extração de métricas do Mixture of Experts (MoE).

Fornece estruturas fortemente tipadas e imutáveis para relatório de métricas do Gating Network,
dos Experts de regressão e do estimador global MoE.
"""

from collections.abc import Sequence
from typing import Any

import numpy as np
import pandas as pd
from pydantic import BaseModel, ConfigDict, Field
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    log_loss,
    max_error,
    mean_absolute_error,
    mean_absolute_percentage_error,
    mean_squared_error,
    median_absolute_error,
    r2_score,
    roc_auc_score,
)


class RegressionMetrics(BaseModel):
    """Métricas de desempenho para tarefas de regressão contínua.

    Attributes:
        rmse (float): Root Mean Squared Error (Raiz do Erro Quadrático Médio).
        mae (float): Mean Absolute Error (Erro Médio Absoluto).
        medae (float): Median Absolute Error (Mediana do Erro Absoluto).
        r2 (float): Coeficiente de Determinação R².
        mape (float): Mean Absolute Percentage Error (Erro Percentual Médio Absoluto).
        max_error (float): Erro absoluto máximo observado.
        support (int): Quantidade de amostras avaliadas no subconjunto.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    rmse: float = Field(..., description="Root Mean Squared Error")
    mae: float = Field(..., description="Mean Absolute Error")
    medae: float = Field(..., description="Median Absolute Error")
    r2: float = Field(..., description="Coeficiente de Determinação R²")
    mape: float = Field(..., description="Mean Absolute Percentage Error")
    max_error: float = Field(..., description="Erro absoluto máximo")
    support: int = Field(..., description="Número de amostras avaliadas")


class GatingMetrics(BaseModel):
    """Métricas de desempenho e calibração para o classificador Gating Network.

    Attributes:
        accuracy (float): Acurácia global das predições de classe.
        balanced_accuracy (float): Acurácia balanceada por classe.
        f1_macro (float): F1-Score com média macro.
        f1_weighted (float): F1-Score ponderado pelo suporte de cada classe.
        brier_score (float): Brier Score multiclasse (quanto menor, mais calibrado).
        log_loss (float): Cross-Entropy / Log-Loss multiclasse.
        roc_auc_ovr (float | None): ROC-AUC Multiclasse One-vs-Rest (se calculável).
        confusion_matrix (list[list[int]]): Matriz de confusão no formato de lista 2D.
        classification_report (dict[str, Any]): Relatório detalhado por classe.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    accuracy: float = Field(..., description="Acurácia global do Gating")
    balanced_accuracy: float = Field(..., description="Acurácia balanceada")
    f1_macro: float = Field(..., description="F1-Score macro")
    f1_weighted: float = Field(..., description="F1-Score ponderado")
    brier_score: float = Field(
        ..., description="Brier Score multiclasse para calibração"
    )
    log_loss: float = Field(..., description="Cross-Entropy / Log-Loss multiclasse")
    roc_auc_ovr: float | None = Field(
        None, description="ROC-AUC Multiclasse One-vs-Rest"
    )
    confusion_matrix: list[list[int]] = Field(..., description="Matriz de confusão")
    classification_report: dict[str, Any] = Field(
        ..., description="Relatório detalhado por classe"
    )


class MoEMetricsReport(BaseModel):
    """Relatório estruturado consolidado de avaliação do Mixture of Experts.

    Attributes:
        global_metrics (RegressionMetrics): Métricas do estimador MoE no dataset completo.
        gating_metrics (GatingMetrics): Métricas de classificação e calibração do Gating.
        expert_metrics (dict[str, RegressionMetrics]): Métricas isoladas de cada expert em sua fatia de dados.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    global_metrics: RegressionMetrics = Field(
        ..., description="Métricas de regressão globais do MoE"
    )
    gating_metrics: GatingMetrics = Field(
        ..., description="Métricas do classificador Gating"
    )
    expert_metrics: dict[str, RegressionMetrics] = Field(
        ..., description="Métricas isoladas de cada expert em sua fatia de dados"
    )

    def summary_table(self) -> pd.DataFrame:
        """Gera um DataFrame tabular comparativo das métricas de regressão.

        Returns:
            pd.DataFrame: Tabela contendo RMSE, MAE, MedAE, R², MAPE e Suporte para cada componente.
        """
        rows: list[dict[str, Any]] = []

        for name, metrics in self.expert_metrics.items():
            rows.append(
                {
                    "Componente": f"Expert ({name})",
                    "RMSE": metrics.rmse,
                    "MAE": metrics.mae,
                    "MedAE": metrics.medae,
                    "R²": metrics.r2,
                    "MAPE": metrics.mape,
                    "Max Error": metrics.max_error,
                    "Suporte": metrics.support,
                }
            )

        rows.append(
            {
                "Componente": "MoE Global",
                "RMSE": self.global_metrics.rmse,
                "MAE": self.global_metrics.mae,
                "MedAE": self.global_metrics.medae,
                "R²": self.global_metrics.r2,
                "MAPE": self.global_metrics.mape,
                "Max Error": self.global_metrics.max_error,
                "Suporte": self.global_metrics.support,
            }
        )

        df = pd.DataFrame(rows)
        return df.set_index("Componente")

    def print_report(self) -> None:
        """Exibe o relatório formatado no console de maneira legível."""
        print("=" * 70)
        print("                   RELATÓRIO DE AVALIAÇÃO DO MoE                    ")
        print("=" * 70)
        print("\n--- 1. DESEMPENHO DO GATING NETWORK (CALIBRADO) ---")
        print(f"Acurácia:            {self.gating_metrics.accuracy:.4f}")
        print(f"Acurácia Balanceada: {self.gating_metrics.balanced_accuracy:.4f}")
        print(f"F1-Score (Macro):    {self.gating_metrics.f1_macro:.4f}")
        print(f"F1-Score (Weighted): {self.gating_metrics.f1_weighted:.4f}")
        print(
            f"Brier Score:         {self.gating_metrics.brier_score:.4f} (Menor = mais calibrado)"
        )
        print(f"Log-Loss:            {self.gating_metrics.log_loss:.4f}")
        if self.gating_metrics.roc_auc_ovr is not None:
            print(f"ROC-AUC (OvR):       {self.gating_metrics.roc_auc_ovr:.4f}")

        print("\n--- 2. DESEMPENHO DOS EXPERTS E GLOBAL (REGRESSÃO) ---")
        print(self.summary_table().to_string())
        print("=" * 70)


def calculate_regression_metrics(
    y_true: Sequence[float] | np.ndarray, y_pred: Sequence[float] | np.ndarray
) -> RegressionMetrics:
    """Calcula métricas de regressão padrão para um conjunto de predições.

    Args:
        y_true (Sequence[float] | np.ndarray): Vetor de valores alvo reais.
        y_pred (Sequence[float] | np.ndarray): Vetor de valores alvo preditos.

    Returns:
        RegressionMetrics: Objeto Pydantic imutável com as métricas calculadas.
    """
    y_t = np.asarray(y_true, dtype=np.float64).ravel()
    y_p = np.asarray(y_pred, dtype=np.float64).ravel()

    support = len(y_t)
    if support == 0:
        return RegressionMetrics(
            rmse=0.0,
            mae=0.0,
            medae=0.0,
            r2=0.0,
            mape=0.0,
            max_error=0.0,
            support=0,
        )

    mse = float(mean_squared_error(y_t, y_p))
    rmse = float(np.sqrt(mse))
    mae = float(mean_absolute_error(y_t, y_p))
    medae = float(median_absolute_error(y_t, y_p))

    # R² pode ser indefinido se a variância de y_true for zero
    if np.var(y_t) == 0.0:
        r2 = 1.0 if np.allclose(y_t, y_p) else 0.0
    else:
        r2 = float(r2_score(y_t, y_p))

    mape = float(mean_absolute_percentage_error(y_t, y_p))
    max_err = float(max_error(y_t, y_p))

    return RegressionMetrics(
        rmse=rmse,
        mae=mae,
        medae=medae,
        r2=r2,
        mape=mape,
        max_error=max_err,
        support=support,
    )


def calculate_multiclass_brier_score(
    y_true: Sequence[Any] | np.ndarray,
    y_proba: np.ndarray,
    classes: Sequence[Any],
) -> float:
    """Calcula o Brier Score multiclasse: média da soma das diferenças quadráticas.

    $$\\text{Brier Score} = \\frac{1}{N} \\sum_{i=1}^N \\sum_{k=1}^K (P_{ik} - Y_{ik})^2$$

    Args:
        y_true (Sequence[Any] | np.ndarray): Vetor de classes reais.
        y_proba (np.ndarray): Matriz de probabilidades preditas de formato (N, K).
        classes (Sequence[Any]): Lista ordenada de classes correspondente às colunas de `y_proba`.

    Returns:
        float: Valor do Brier Score (no intervalo [0, 2], onde 0 indica predições perfeitas).
    """
    y_t = np.asarray(y_true)
    n_samples = len(y_t)
    if n_samples == 0:
        return 0.0

    n_classes = len(classes)
    y_one_hot = np.zeros((n_samples, n_classes), dtype=np.float64)

    for idx, c in enumerate(classes):
        y_one_hot[:, idx] = (y_t == c).astype(np.float64)

    return float(np.mean(np.sum((y_proba - y_one_hot) ** 2, axis=1)))


def calculate_gating_metrics(
    y_true: Sequence[Any] | np.ndarray,
    y_pred: Sequence[Any] | np.ndarray,
    y_proba: np.ndarray,
    classes: Sequence[Any],
) -> GatingMetrics:
    """Calcula métricas de classificação e calibração para a rede Gating.

    Args:
        y_true (Sequence[Any] | np.ndarray): Classes reais.
        y_pred (Sequence[Any] | np.ndarray): Classes preditas pelo modelo.
        y_proba (np.ndarray): Probabilidades preditas com formato (N, K).
        classes (Sequence[Any]): Lista ordenada de classes correspondentes às colunas de y_proba.

    Returns:
        GatingMetrics: Objeto Pydantic contendo acurácia, F1, Brier Score, Log-Loss, ROC-AUC, etc.
    """
    y_t = np.asarray(y_true)
    y_p = np.asarray(y_pred)
    classes_list = list(classes)

    acc = float(accuracy_score(y_t, y_p))
    bal_acc = float(balanced_accuracy_score(y_t, y_p))
    f1_m = float(f1_score(y_t, y_p, average="macro", zero_division=0))
    f1_w = float(f1_score(y_t, y_p, average="weighted", zero_division=0))

    brier = calculate_multiclass_brier_score(y_t, y_proba, classes_list)

    sorted_classes = sorted(classes_list)
    sorted_proba = np.zeros_like(y_proba)
    for new_idx, cls_name in enumerate(sorted_classes):
        old_idx = classes_list.index(cls_name)
        sorted_proba[:, new_idx] = y_proba[:, old_idx]

    # Log-loss multiclasse
    try:
        ll = float(log_loss(y_t, sorted_proba, labels=sorted_classes))
    except (ValueError, TypeError):
        ll = float("nan")

    # ROC-AUC Multiclasse One-vs-Rest (com ordenação lexicográfica)
    roc_auc: float | None = None
    try:
        if len(np.unique(y_t)) > 1:
            roc_auc = float(
                roc_auc_score(
                    y_t,
                    sorted_proba,
                    multi_class="ovr",
                    labels=sorted_classes,
                )
            )
    except (ValueError, TypeError):
        roc_auc = None

    cm = confusion_matrix(y_t, y_p, labels=classes_list).tolist()
    clf_report = classification_report(
        y_t,
        y_p,
        labels=classes_list,
        output_dict=True,
        zero_division=0,
    )

    return GatingMetrics(
        accuracy=acc,
        balanced_accuracy=bal_acc,
        f1_macro=f1_m,
        f1_weighted=f1_w,
        brier_score=brier,
        log_loss=ll,
        roc_auc_ovr=roc_auc,
        confusion_matrix=cm,
        classification_report=clf_report,
    )
