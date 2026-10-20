"""Pacote principal `ml-core` para pipelines, estimadores, transformadores e pré-processamento de ML."""

from ml_core import estimators, pipelines, preprocessing, transformers
from ml_core.estimators import (
    RegressionMetrics,
    RegressionMetricsReport,
    Regressor,
    calculate_aggregated_metrics,
    calculate_regression_metrics,
)
from ml_core.pipelines import (
    FeatureGroups,
    create_training_pipeline,
    get_feature_groups,
    get_preprocessor,
    get_transformers,
)
from ml_core.preprocessing import DataCleaner, FeatureExtractor, GeocodingEnricher
from ml_core.transformers import (
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
    "get_feature_groups",
    "get_preprocessor",
    "get_transformers",
    "pipelines",
    "preprocessing",
    "transformers",
]
