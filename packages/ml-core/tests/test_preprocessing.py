"""Suíte de testes unitários para os componentes de pré-processamento de dados do ml-core."""

from unittest.mock import MagicMock

import numpy as np
import pandas as pd
from geocoding_client.schemas import (
    BatchGeocodingResponse,
    GeocodingData,
    GeocodingResponse,
)
from ml_core.preprocessing import (
    DataCleaner,
    FeatureExtractor,
    GeocodingEnricher,
)
from ml_core.preprocessing.constants import UNUSED_FEATURES
from ml_core.preprocessing.data_preprocessor import DataPreprocessor

# ==============================================================================
# DataCleaner Tests
# ==============================================================================


def test_data_cleaner_drop_duplicates():
    """Valida a remoção de registros estritamente duplicados."""
    cleaner = DataCleaner()
    df = pd.DataFrame(
        {
            "id": [1, 1, 2],
            "bairro": ["Bueno", "Bueno", "Marista"],
        }
    )
    result = cleaner._drop_duplicates(df)
    assert len(result) == 2
    assert list(result["id"]) == [1, 2]


def test_data_cleaner_drop_features():
    """Valida remoção de colunas definidas em UNUSED_FEATURES."""
    cleaner = DataCleaner()
    df = pd.DataFrame(
        {
            "preco": [100000],
            "bairro": ["Bueno"],
        }
    )
    # Adiciona colunas não utilizadas
    for col in UNUSED_FEATURES:
        df[col] = "invalido"

    result = cleaner._drop_features(df)
    for col in UNUSED_FEATURES:
        assert col not in result.columns
    assert "preco" in result.columns
    assert "bairro" in result.columns


def test_data_cleaner_drop_missing():
    """Valida descarte de linhas sem preço e tolerância caso a coluna preço não exista."""
    cleaner = DataCleaner()

    # Com coluna preco
    df_with_price = pd.DataFrame({"preco": [100000.0, np.nan, 200000.0]})
    res_price = cleaner._drop_missing(df_with_price)
    assert len(res_price) == 2
    assert list(res_price["preco"]) == [100000.0, 200000.0]

    # Sem coluna preco (modo de inferência)
    df_no_price = pd.DataFrame({"area_m2": [50.0, 80.0]})
    res_no_price = cleaner._drop_missing(df_no_price)
    assert len(res_no_price) == 2


def test_data_cleaner_rename_classes():
    """Testa a padronização de categorias da variável tipo_imovel."""
    cleaner = DataCleaner()
    df = pd.DataFrame(
        {"tipo_imovel": ["House", "Apartment", "Place", "outra_coisa", np.nan]}
    )
    result = cleaner._rename_classes(df)
    assert result["tipo_imovel"].iloc[0] == "casa"
    assert result["tipo_imovel"].iloc[1] == "apartamento"
    assert result["tipo_imovel"].iloc[2] == "outro"
    assert result["tipo_imovel"].iloc[3] == "outra_coisa"


def test_data_cleaner_validate_data():
    """Testa validação de consistência entre a coluna titulo e dados extraídos."""
    cleaner = DataCleaner()

    # Consistência sem titulo não altera o dataframe
    df_no_title = pd.DataFrame({"area_m2": [50.0]})
    res_no_title = cleaner._validate_data(df_no_title)
    assert res_no_title.equals(df_no_title)

    # Consistência com titulo válido
    df_title = pd.DataFrame(
        {
            "titulo": ["Apartamento 2 quartos 1 banheiros 1 vagas 60 m²"],
            "quartos": [2],
            "banheiros": [1],
            "vagas": [1],
            "area_m2": [60.0],
        }
    )
    res_title = cleaner._validate_data(df_title)
    assert len(res_title) == 1


def test_data_cleaner_call_pipeline():
    """Testa a execução completa do callable DataCleaner."""
    cleaner = DataCleaner()
    df = pd.DataFrame(
        {
            "preco": [300000.0, 300000.0, np.nan],
            "tipo_imovel": ["House", "House", "Apartment"],
            "url": ["http://a.com", "http://a.com", "http://b.com"],
        }
    )
    result = cleaner(df)
    assert len(result) == 1
    assert result["tipo_imovel"].iloc[0] == "casa"
    assert "url" not in result.columns


# ==============================================================================
# FeatureExtractor Tests
# ==============================================================================


def test_feature_extractor_amenities_pattern():
    """Valida o escape de caracteres especiais no padrão regex de comodidades."""
    extractor = FeatureExtractor()
    pattern = extractor._get_amenities_pattern(["Piscina (Aquecida)", "Wi-Fi+"])
    assert r"Piscina\ \(Aquecida\)|Wi\-Fi\+" == pattern


def test_feature_extractor_amenities():
    """Testa a extração de comodidades a partir de texto."""
    extractor = FeatureExtractor()
    df = pd.DataFrame(
        {
            "comodidades": [
                "Pool, Gym, Barbecue Grill",
                "Playground, Coworking",
                None,
            ],
            "aceita_pets": [True, False, None],
        }
    )
    result = extractor._extract_amenities_features(df)

    assert bool(result["piscina"].iloc[0]) is True
    assert bool(result["academia"].iloc[0]) is True
    assert bool(result["espaco_gourmet"].iloc[0]) is True
    assert bool(result["piscina"].iloc[1]) is False
    assert bool(result["pets"].iloc[0]) is True

    # Colunas originais devem ser removidas
    assert "comodidades" not in result.columns
    assert "aceita_pets" not in result.columns


def test_feature_extractor_real_state_classes_refinement():
    """Valida o refinamento do tipo de imóvel a partir do título para tipos 'outro'."""
    extractor = FeatureExtractor()
    df = pd.DataFrame(
        {
            "tipo_imovel": ["outro", "outro", "apartamento"],
            "titulo": ["Flat no Setor Bueno", "Casa térrea", "Cobertura duplex"],
        }
    )
    result = extractor._extract_real_state_classes(df)

    assert result["tipo_imovel"].iloc[0] == "flat"
    assert result["tipo_imovel"].iloc[1] == "casa"
    # Não sobrescreve quando não era 'outro'
    assert result["tipo_imovel"].iloc[2] == "apartamento"
    assert "titulo" not in result.columns


def test_feature_extractor_call():
    """Testa o pipeline completo do callable FeatureExtractor."""
    extractor = FeatureExtractor()
    df = pd.DataFrame(
        {
            "tipo_imovel": ["outro"],
            "titulo": ["Studio moderno"],
            "comodidades": ["Pool, Gym"],
        }
    )
    result = extractor(df)
    assert result["tipo_imovel"].iloc[0] == "studio"
    assert "piscina" in result.columns
    assert bool(result["piscina"].iloc[0]) is True
    assert bool(result["academia"].iloc[0]) is True


# ==============================================================================
# GeocodingEnricher Tests
# ==============================================================================


def test_geocoding_enricher_address_feature():
    """Testa concatenação de rua e bairro em campo de endereço unificado."""
    enricher = GeocodingEnricher(client=MagicMock())
    df = pd.DataFrame(
        {
            "rua": ["Avenida 85", None, "Rua T-63"],
            "bairro": ["Setor Marista", "Setor Sul", None],
        }
    )
    result = enricher._get_address_feature(df)
    assert result["endereco"].iloc[0] == "Avenida 85, Setor Marista"
    assert result["endereco"].iloc[1] == "Setor Sul"
    assert result["endereco"].iloc[2] == "Rua T-63"


def test_geocoding_enricher_batch_integration_and_clipping():
    """Testa integração com cliente de geocodificação e corte geográfico de Goiânia."""
    mock_client = MagicMock()
    mock_client.batch_geocode_sync.return_value = BatchGeocodingResponse(
        results=[
            GeocodingResponse(
                source="nominatim",
                data=GeocodingData(
                    place_id="1",
                    address="Avenida Anhanguera, Setor Central",
                    latitude=-16.67,  # Dentro de Goiânia
                    longitude=-49.25,  # Dentro de Goiânia
                    formatted_address="Avenida Anhanguera, Setor Central, Goiânia, GO",
                ),
            ),
            GeocodingResponse(
                source="nominatim",
                data=GeocodingData(
                    place_id="2",
                    address="Avenida Paulista, Bela Vista",
                    latitude=-23.55,  # Fora de Goiânia (São Paulo)
                    longitude=-46.63,
                    formatted_address="São Paulo, SP",
                ),
            ),
        ]
    )

    enricher = GeocodingEnricher(client=mock_client)
    df_in = pd.DataFrame(
        {
            "rua": ["Avenida Anhanguera", "Avenida Paulista", "Rua Sem Coordenada"],
            "bairro": ["Setor Central", "Bela Vista", "Setor Desconhecido"],
        }
    )

    df_out = enricher(df_in)
    mock_client.batch_geocode_sync.assert_called_once()

    # O endereço de SP deve ser filtrado; o endereço válido e o NaN devem permanecer
    assert len(df_out) == 2
    assert df_out.iloc[0]["latitude"] == -16.67
    assert pd.isna(df_out.iloc[1]["latitude"])
    assert "endereco" not in df_out.columns
    assert "rua" not in df_out.columns
    assert "bairro" not in df_out.columns


def test_geocoding_enricher_client_exception_resilience():
    """Verifica que exceções no cliente HTTP não derrubam o pipeline de pré-processamento."""
    mock_client = MagicMock()
    mock_client.batch_geocode_sync.side_effect = RuntimeError("API indisponível")

    enricher = GeocodingEnricher(client=mock_client)
    df = pd.DataFrame({"rua": ["Rua T-55"], "bairro": ["Bueno"]})

    df_out = enricher(df)
    assert "latitude" in df_out.columns
    assert "longitude" in df_out.columns
    assert pd.isna(df_out["latitude"].iloc[0])


# ==============================================================================
# DataPreprocessor Integration Tests
# ==============================================================================


def test_data_preprocessor_end_to_end():
    """Valida a execução ponta-a-ponta do DataPreprocessor encadeando as 3 etapas."""
    mock_client = MagicMock()
    mock_client.batch_geocode_sync.return_value = BatchGeocodingResponse(
        results=[
            GeocodingResponse(
                source="nominatim",
                data=GeocodingData(
                    place_id="1",
                    address="Rua T-55, Setor Bueno",
                    latitude=-16.70,
                    longitude=-49.27,
                    formatted_address="Rua T-55, Setor Bueno, Goiânia, GO",
                ),
            )
        ]
    )

    preprocessor = DataPreprocessor(geocoding_client=mock_client)

    df_raw = pd.DataFrame(
        {
            "preco": [500_000.0],
            "tipo_imovel": ["Apartment"],
            "rua": ["Rua T-55"],
            "bairro": ["Setor Bueno"],
            "comodidades": ["Pool, Gym"],
            "url": ["http://exemplo.com/1"],
        }
    )

    df_processed = preprocessor(df_raw)

    assert len(df_processed) == 1
    assert df_processed["tipo_imovel"].iloc[0] == "apartamento"
    assert bool(df_processed["piscina"].iloc[0]) is True
    assert bool(df_processed["academia"].iloc[0]) is True
    assert df_processed["latitude"].iloc[0] == -16.70
    assert df_processed["longitude"].iloc[0] == -49.27
    assert "url" not in df_processed.columns
    assert "rua" not in df_processed.columns
