"""Pacote principal `ml-core` para pipelines, estimadores, transformadores e pré-processamento de ML."""

from . import estimators, pipelines, preprocessing, transformers
from .estimators import (
    RegressionMetrics,
    RegressionMetricsReport,
    Regressor,
    calculate_aggregated_metrics,
    calculate_regression_metrics,
)
from .pipelines import (
    FeatureGroups,
    create_training_pipeline,
    get_default_feature_groups,
    get_feature_groups,
    get_preprocessor,
    get_transformers,
)
from .preprocessing import DataCleaner, FeatureExtractor, GeocodingEnricher
from .transformers import (
    BinsDiscretizer,
    ClusterTransformer,
    GeodesicDistanceTransformer,
    RatioTransformer,
)

__all__ = [
    "BinsDiscretizer",
    "ClusterTransformer",
    "DataCleaner",
    "FeatureExtractor",
    "FeatureGroups",
    "GeocodingEnricher",
    "GeodesicDistanceTransformer",
    "RatioTransformer",
    "RegressionMetrics",
    "RegressionMetricsReport",
    "Regressor",
    "calculate_aggregated_metrics",
    "calculate_regression_metrics",
    "create_training_pipeline",
    "estimators",
    "get_default_feature_groups",
    "get_feature_groups",
    "get_preprocessor",
    "get_transformers",
    "pipelines",
    "preprocessing",
    "transformers",
]
