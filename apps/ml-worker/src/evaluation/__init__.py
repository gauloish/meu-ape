"""Módulo de avaliação por Nested Cross-Validation."""

from .evaluate import compute_metrics, evaluate_pipeline

__all__ = [
    "compute_metrics",
    "evaluate_pipeline",
]