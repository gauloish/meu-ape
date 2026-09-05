"""Suíte de testes de integração e unidade para o pacote ml-core."""

from logging_settings import setup_logger
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
from geocoding_client.schemas import BatchGeocodingResponse, GeocodingData, GeocodingResponse

from ml_core.preprocessing import DataCleaner, FeatureExtractor, GeocodingEnricher
from ml_core.transformers import (
    BinsDiscretizer,
    ClusterTransformer,
    GeodesicDistanceTransformer,
    RatioTransformer,
)

logger = setup_logger(__name__)


def test_geocoding_enricher_batch_integration():
    """Testa a integração do GeocodingEnricher com o cliente em lote e filtro de limites."""
    mock_client = MagicMock()

    # Simula resposta do batch_geocode_sync
    mock_client.batch_geocode_sync.return_value = BatchGeocodingResponse(
        results=[
            GeocodingResponse(
                source="nominatim",
                data=GeocodingData(
                    place_id="1",
                    address="Avenida Anhanguera, Setor Central",
                    latitude=-16.67,  # Dentro de Goiânia (-16.85 a -16.55)
                    longitude=-49.25,  # Dentro de Goiânia (-49.45 a -49.15)
                    formatted_address="Avenida Anhanguera, Setor Central, Goiânia, GO",
                ),
            ),
            GeocodingResponse(
                source="nominatim",
                data=GeocodingData(
                    place_id="2",
                    address="Fora de Goiânia, Bairro Distante",
                    latitude=-23.55,  # Fora (São Paulo)
                    longitude=-46.63,
                    formatted_address="São Paulo, SP",
                ),
            ),
        ]
    )

    enricher = GeocodingEnricher(client=mock_client)

    df_in = pd.DataFrame(
        {
            "rua": ["Avenida Anhanguera", "Fora de Goiânia"],
            "bairro": ["Setor Central", "Bairro Distante"],
            "outra_coluna": [10, 20],
        }
    )

    df_out = enricher(df_in)

    # Verifica se chamou a geocodificação em lote
    mock_client.batch_geocode_sync.assert_called_once()

    # O imóvel fora de Goiânia deve ter sido filtrado pelo _clip_out_of_bounds_samples
    assert len(df_out) == 1
    assert df_out.iloc[0]["latitude"] == -16.67
    assert df_out.iloc[0]["longitude"] == -49.25
    assert "endereco" not in df_out.columns
    print("[PASS] test_geocoding_enricher_batch_integration")


def test_cluster_transformer_no_data_leakage():
    """Testa se o ClusterTransformer treina o KMeans apenas no fit e usa predict no transform."""
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
    assert transformer.kmeans_.n_clusters == 2

    # Salva o estado dos centroides treinados
    centroids_after_fit = transformer.kmeans_.cluster_centers_.copy()

    df_train_trans = transformer.transform(X_train)
    df_test_trans = transformer.transform(X_test)

    # Os centroides do KMeans NÃO podem mudar após executar o transform no conjunto de teste!
    np.testing.assert_array_equal(transformer.kmeans_.cluster_centers_, centroids_after_fit)

    assert "cluster" in df_train_trans.columns
    assert "cluster" in df_test_trans.columns
    assert len(df_test_trans["cluster"].unique()) <= 2
    print("[PASS] test_cluster_transformer_no_data_leakage")


def test_cluster_transformer_handles_nan_coordinates():
    """Testa se o ClusterTransformer processa dados com valores NaN em latitude/longitude sem erro."""
    X_train = pd.DataFrame(
        {
            "latitude": [-16.67, np.nan, -16.69, -16.70],
            "longitude": [-49.25, -49.26, np.nan, -49.28],
        }
    )

    transformer = ClusterTransformer(n_clusters=2, random_state=42)
    transformer.fit(X_train)

    df_trans = transformer.transform(X_train)

    assert "cluster" in df_trans.columns
    # Linhas sem coordenadas válidas devem ter cluster como NaN
    assert pd.isna(df_trans.iloc[1]["cluster"])
    assert pd.isna(df_trans.iloc[2]["cluster"])
    # Linhas válidas devem receber cluster numérico
    assert not pd.isna(df_trans.iloc[0]["cluster"])
    assert not pd.isna(df_trans.iloc[3]["cluster"])
    print("[PASS] test_cluster_transformer_handles_nan_coordinates")


def test_ratio_transformer_zero_division():
    """Testa o RatioTransformer tratando divisão por zero e inf de forma segura."""
    df = pd.DataFrame(
        {
            "preco": [100000.0, 200000.0, 300000.0],
            "area_m2": [50.0, 0.0, np.nan],
        }
    )

    transformer = RatioTransformer(pairs=[("preco", "area_m2")])
    df_trans = transformer.fit_transform(df)

    col_name = "preco_por_area_m2"
    assert col_name in df_trans.columns
    assert df_trans[col_name].iloc[0] == 2000.0
    # Divisão por zero ou por NaN deve resultar em NaN sem levantar ZeroDivisionError ou inf
    assert pd.isna(df_trans[col_name].iloc[1])
    assert pd.isna(df_trans[col_name].iloc[2])
    print("[PASS] test_ratio_transformer_zero_division")


def test_geodesic_distance_transformer_index_alignment():
    """Testa se o GeodesicDistanceTransformer lida corretamente com índices não sequenciais."""
    df = pd.DataFrame(
        {
            "latitude": [-16.67, np.nan, -16.68],
            "longitude": [-49.25, -49.26, -49.27],
        },
        index=["imovel_a", "imovel_b", "imovel_c"],
    )

    points = {"centro": (-16.679, -49.255)}
    transformer = GeodesicDistanceTransformer(points=points)

    df_trans = transformer.fit_transform(df)

    col = "distancia_centro_km"
    assert col in df_trans.columns
    assert df_trans.loc["imovel_a", col] > 0
    assert pd.isna(df_trans.loc["imovel_b", col])
    assert df_trans.loc["imovel_c", col] > 0
    print("[PASS] test_geodesic_distance_transformer_index_alignment")


def test_bins_discretizer():
    """Testa a discretização de colunas contínuas em faixas categóricas."""
    df = pd.DataFrame({"area_m2": [30.0, 75.0, 150.0]})
    bins_info = [("area_m2", [0, 50, 100, float("inf")], ["pequeno", "medio", "grande"])]

    transformer = BinsDiscretizer(bins_info=bins_info)
    df_trans = transformer.fit_transform(df)

    assert "faixa_area_m2" in df_trans.columns
    assert list(df_trans["faixa_area_m2"]) == ["pequeno", "medio", "grande"]
    print("[PASS] test_bins_discretizer")


def test_data_cleaner_and_feature_extractor_inference_mode():
    """Testa se o DataCleaner e FeatureExtractor funcionam em modo de inferência (sem preço ou titulo)."""
    df_inference = pd.DataFrame(
        {
            "rua": ["Rua T-55"],
            "bairro": ["Setor Bueno"],
            "comodidades": ["Heated Pool, Gym and Gourmet Space"],
            "tipo_imovel": ["Apartment"],
        }
    )

    cleaner = DataCleaner()
    extractor = FeatureExtractor()

    df_cleaned = cleaner(df_inference)
    df_extracted = extractor(df_cleaned)

    # Verifica limpeza
    assert df_cleaned["tipo_imovel"].iloc[0] == "apartamento"

    # Verifica extração de comodidades (com regex com re.escape)
    assert bool(df_extracted["piscina"].iloc[0]) is True
    assert bool(df_extracted["academia"].iloc[0]) is True
    assert bool(df_extracted["espaco_gourmet"].iloc[0]) is True
    print("[PASS] test_data_cleaner_and_feature_extractor_inference_mode")


if __name__ == "__main__":
    print("Iniciando testes do pacote ml-core...")
    test_geocoding_enricher_batch_integration()
    test_cluster_transformer_no_data_leakage()
    test_cluster_transformer_handles_nan_coordinates()
    test_ratio_transformer_zero_division()
    test_geodesic_distance_transformer_index_alignment()
    test_bins_discretizer()
    test_data_cleaner_and_feature_extractor_inference_mode()
    print("Todos os testes do ml-core passaram com sucesso!")
