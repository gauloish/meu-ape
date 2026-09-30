"""Módulo de pipelines e transformações compostas do pacote `ml-core`."""

from ml_core.pipelines.factory import (
    create_training_pipeline,
    get_preprocessor,
    get_transformers,
)
from ml_core.pipelines.feature_groups import FeatureGroups, get_feature_groups

__all__: list[str] = [
    "FeatureGroups",
    "create_training_pipeline",
    "get_feature_groups",
    "get_preprocessor",
    "get_transformers",
]
