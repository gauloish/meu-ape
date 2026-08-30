"""Pacote principal `ml-core` para pipelines, estimadores, transformadores e pré-processamento de ML."""

from . import estimators, pipelines, preprocessing, transformers
from .estimators import (
    GatingMetrics,
    MoEEstimator,
    MoEMetricsReport,
    RegressionMetrics,
)
from .pipelines import (
    FeatureGroups,
    create_training_pipeline,
    get_default_feature_groups,
    get_preprocessor,
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
    "GatingMetrics",
    "GeocodingEnricher",
    "GeodesicDistanceTransformer",
    "MoEEstimator",
    "MoEMetricsReport",
    "RatioTransformer",
    "RegressionMetrics",
    "create_training_pipeline",
    "estimators",
    "get_default_feature_groups",
    "get_preprocessor",
    "pipelines",
    "preprocessing",
    "transformers",
]
