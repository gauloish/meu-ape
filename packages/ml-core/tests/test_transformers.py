"""Suíte de testes unitários para os transformadores scikit-learn customizados do ml-core."""

import numpy as np
import pandas as pd
import pytest
from ml_core.transformers import (
    BinsDiscretizer,
    ClusterTransformer,
    GeodesicDistanceTransformer,
    RatioTransformer,
)
from sklearn.exceptions import NotFittedError

# ==============================================================================
# BinsDiscretizer Tests
# ==============================================================================


def test_bins_discretizer_validation():
    """Valida tratamento de tipos de entrada e verificação de colunas obrigatórias."""
    discretizer = BinsDiscretizer(bins_info=[("area_m2", [0, 50, 100], ["P", "M"])])

    # Entrada não DataFrame
    with pytest.raises(TypeError, match="espera um pandas.DataFrame"):
        discretizer.fit([1, 2, 3])  # type: ignore

    # Coluna ausente
    df_missing = pd.DataFrame({"outra_coluna": [10, 20]})
    with pytest.raises(ValueError, match="Colunas obrigatórias ausentes"):
        discretizer.fit(df_missing)

    # Transform sem fit prévio
    discretizer_unfitted = BinsDiscretizer(
        bins_info=[("area_m2", [0, 50, 100], ["P", "M"])]
    )
    with pytest.raises(NotFittedError):
        discretizer_unfitted.transform(pd.DataFrame({"area_m2": [30.0]}))


def test_bins_discretizer_fit_transform():
    """Testa a transformação de variáveis contínuas em faixas categóricas."""
    df = pd.DataFrame({"area_m2": [25.0, 75.0, 150.0], "valor": [1, 2, 3]})
    bins_info = [
        ("area_m2", [0, 50, 100, float("inf")], ["pequeno", "medio", "grande"])
    ]

    discretizer = BinsDiscretizer(bins_info=bins_info, prefix="categoria_")
    df_trans = discretizer.fit_transform(df)

    assert discretizer.__sklearn_is_fitted__()
    assert "categoria_area_m2" in df_trans.columns
    assert list(df_trans["categoria_area_m2"]) == ["pequeno", "medio", "grande"]
    # Garante que as colunas originais não foram removidas
    assert "area_m2" in df_trans.columns
    assert "valor" in df_trans.columns


# ==============================================================================
# ClusterTransformer Tests
# ==============================================================================


def test_cluster_transformer_validation():
    """Valida exceções de tipo e ausência de colunas em ClusterTransformer."""
    transformer = ClusterTransformer()

    with pytest.raises(TypeError, match="espera um pandas.DataFrame"):
        transformer.fit([[1, 2], [3, 4]])  # type: ignore

    with pytest.raises(ValueError, match="Colunas obrigatórias ausentes"):
        transformer.fit(pd.DataFrame({"lat": [1], "lon": [2]}))

    unfitted = ClusterTransformer()
    with pytest.raises(NotFittedError):
        unfitted.transform(pd.DataFrame({"latitude": [-16.6], "longitude": [-49.2]}))


def test_cluster_transformer_no_data_leakage():
    """Garante que os centroides do KMeans não são alterados durante a inferência (transform)."""
    X_train = pd.DataFrame(
        {
            "latitude": [-16.67, -16.68, -16.69, -16.70],
            "longitude": [-49.25, -49.26, -49.27, -49.28],
        }
    )
    X_test = pd.DataFrame(
        {
            "latitude": [-16.675, -16.695],
            "longitude": [-49.255, -49.275],
        }
    )

    transformer = ClusterTransformer(n_clusters=2, random_state=42)
    transformer.fit(X_train)

    assert hasattr(transformer, "kmeans_")
    assert transformer.__sklearn_is_fitted__()

    centroids_after_fit = transformer.kmeans_.cluster_centers_.copy()

    df_train_trans = transformer.transform(X_train)
    df_test_trans = transformer.transform(X_test)

    # Centroides não podem ter sofrido mutação
    np.testing.assert_array_equal(
        transformer.kmeans_.cluster_centers_, centroids_after_fit
    )

    assert "cluster" in df_train_trans.columns
    assert "cluster" in df_test_trans.columns
    assert len(df_test_trans["cluster"].unique()) <= 2


def test_cluster_transformer_handles_nan_and_empty():
    """Valida o tratamento de coordenadas com NaN e datasets com poucos pontos válidos."""
    X_train = pd.DataFrame(
        {
            "latitude": [-16.67, np.nan, -16.69, -16.70],
            "longitude": [-49.25, -49.26, np.nan, -49.28],
        }
    )

    transformer = ClusterTransformer(n_clusters=2, random_state=42)
    transformer.fit(X_train)

    df_trans = transformer.transform(X_train)
    assert pd.isna(df_trans.iloc[1]["cluster"])
    assert pd.isna(df_trans.iloc[2]["cluster"])
    assert not pd.isna(df_trans.iloc[0]["cluster"])
    assert not pd.isna(df_trans.iloc[3]["cluster"])

    # Dataset com apenas coordenadas NaN
    X_all_nan = pd.DataFrame(
        {"latitude": [np.nan, np.nan], "longitude": [np.nan, np.nan]}
    )
    transformer_nan = ClusterTransformer(n_clusters=3)
    transformer_nan.fit(X_all_nan)
    df_nan_trans = transformer_nan.transform(X_all_nan)
    assert df_nan_trans["cluster"].isna().all()


# ==============================================================================
# GeodesicDistanceTransformer Tests
# ==============================================================================


def test_geodesic_distance_transformer_validation():
    """Valida validações de tipo e ausência de colunas em GeodesicDistanceTransformer."""
    points = {"centro": (-16.679, -49.255)}
    transformer = GeodesicDistanceTransformer(points=points)

    with pytest.raises(TypeError, match="espera um pandas.DataFrame"):
        transformer.fit("string_invalida")  # type: ignore

    with pytest.raises(ValueError, match="Colunas obrigatórias ausentes"):
        transformer.fit(pd.DataFrame({"latitude": [-16.6]}))

    unfitted = GeodesicDistanceTransformer(points=points)
    with pytest.raises(NotFittedError):
        unfitted.transform(pd.DataFrame({"latitude": [-16.6], "longitude": [-49.2]}))


def test_geodesic_distance_transformer_distance_calculation():
    """Testa cálculo de distâncias geodésicas (Haversine) e alinhamento de índices não contíguos."""
    points = {"centro": (-16.679, -49.255)}
    transformer = GeodesicDistanceTransformer(
        points=points, prefix="dist_", suffix="_quilometros"
    )

    df = pd.DataFrame(
        {
            "latitude": [-16.679, np.nan, -16.709],
            "longitude": [-49.255, -49.26, -49.273],
        },
        index=["ponto_exato", "ponto_nan", "ponto_distante"],
    )

    df_trans = transformer.fit_transform(df)

    assert transformer.__sklearn_is_fitted__()
    col_name = "dist_centro_quilometros"
    assert col_name in df_trans.columns

    # Ponto idêntico ao de referência deve ter distância ~ 0 km
    assert pytest.approx(df_trans.loc["ponto_exato", col_name], abs=0.01) == 0.0
    # Ponto com latitude NaN deve ter distância NaN
    assert pd.isna(df_trans.loc["ponto_nan", col_name])
    # Ponto distante deve ter distância positiva realista (entre 1 e 10 km)
    dist = df_trans.loc["ponto_distante", col_name]
    assert 2.0 < dist < 6.0


# ==============================================================================
# RatioTransformer Tests
# ==============================================================================


def test_ratio_transformer_validation():
    """Valida tratamento de tipos e colunas ausentes em RatioTransformer."""
    transformer = RatioTransformer(pairs=[("preco", "area_m2")])

    with pytest.raises(TypeError, match="espera um pandas.DataFrame"):
        transformer.fit(123)  # type: ignore

    with pytest.raises(ValueError, match="Colunas obrigatórias ausentes"):
        transformer.fit(pd.DataFrame({"preco": [1000]}))

    unfitted = RatioTransformer(pairs=[("preco", "area_m2")])
    with pytest.raises(NotFittedError):
        unfitted.transform(pd.DataFrame({"preco": [1000], "area_m2": [50]}))


def test_ratio_transformer_division_and_inf_handling():
    """Valida o cálculo de razão tratando divisão por zero e valores NaN com segurança."""
    df = pd.DataFrame(
        {
            "preco": [100_000.0, 200_000.0, 300_000.0, 400_000.0],
            "area_m2": [50.0, 0.0, np.nan, -100.0],
        }
    )

    transformer = RatioTransformer(pairs=[("preco", "area_m2")], sep="_dividido_por_")
    df_trans = transformer.fit_transform(df)

    col = "preco_dividido_por_area_m2"
    assert col in df_trans.columns
    assert df_trans[col].iloc[0] == 2000.0
    # Divisão por zero resulta em NaN (evita inf)
    assert pd.isna(df_trans[col].iloc[1])
    # Divisão por NaN resulta em NaN
    assert pd.isna(df_trans[col].iloc[2])
    # Valor negativo
    assert df_trans[col].iloc[3] == -4000.0
