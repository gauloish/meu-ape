"""Módulo de pipelines e transformações compostas do pacote `ml-core`."""

from .factory import create_training_pipeline, get_preprocessor
from .feature_groups import FeatureGroups, get_default_feature_groups

__all__ = [
    "FeatureGroups",
    "create_training_pipeline",
    "get_default_feature_groups",
    "get_preprocessor",
]
