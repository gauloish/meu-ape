"""Pacote principal `ml-core` para estimadores, transformadores e pré-processamento de ML."""

from . import estimators, preprocessing, transformers
from .estimators import (
    GatingMetrics,
    MoEEstimator,
    MoEMetricsReport,
    RegressionMetrics,
)
from .preprocessing import DataCleaner, FeatureExtractor, GeocodingEnricher
from .transformers import (
    BinsDiscretizer,
    ClusterTransformer,
    GeodesicDistanceTransformer,
    RatioTransformer,
)

__all__ = [
    "estimators",
    "preprocessing",
    "transformers",
    "MoEEstimator",
    "MoEMetricsReport",
    "GatingMetrics",
    "RegressionMetrics",
    "DataCleaner",
    "FeatureExtractor",
    "GeocodingEnricher",
    "BinsDiscretizer",
    "ClusterTransformer",
    "GeodesicDistanceTransformer",
    "RatioTransformer",
]
