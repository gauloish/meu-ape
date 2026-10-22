"""Configurações e fixtures compartilhadas do pytest para o backend."""

from collections.abc import Generator
from unittest.mock import MagicMock

import numpy as np
import pytest
from fastapi.testclient import TestClient

from src.main import app


@pytest.fixture
def mock_ml_model() -> MagicMock:
    """Fixture que fornece um mock de modelo ML com comportamento padrão de inferência."""
    model = MagicMock()
    model.predict.return_value = np.array([1250000.0])
    return model


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient, None, None]:
    """Fixture que cria o TestClient para a aplicação FastAPI.

    Substitui load_model_from_hub para evitar chamadas de rede e download de artefatos
    durante a execução dos testes unitários.
    """
    monkeypatch.setattr("src.main.load_model_from_hub", lambda: None)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def client_with_model(
    client: TestClient, mock_ml_model: MagicMock
) -> Generator[TestClient, None, None]:
    """Fixture do TestClient com um mock de modelo de ML já carregado em memória."""
    app.state.model = mock_ml_model
    yield client
    app.state.model = None


@pytest.fixture
def valid_payload_dict() -> dict:
    """Retorna um dicionário com payload válido para InferenceRequest."""
    return {
        "tipo_imovel": "apartamento",
        "condominio": 650,
        "area_m2": 85,
        "quartos": 3,
        "banheiros": 2,
        "vagas": 2,
        "piscina": True,
        "academia": True,
        "latitude": -16.68,
        "longitude": -49.25,
    }


@pytest.fixture
def valid_payload_minimal() -> dict:
    """Retorna um payload contendo apenas os campos obrigatórios."""
    return {
        "tipo_imovel": "casa",
        "condominio": 0,
        "area_m2": 150,
        "quartos": 4,
        "banheiros": 3,
        "vagas": 2,
    }


@pytest.fixture
def valid_payload_all_features() -> dict:
    """Retorna um payload com todas as 28 amenidades e coordenadas geográficas válidas."""
    return {
        "tipo_imovel": "cobertura",
        "condominio": 1800,
        "area_m2": 240,
        "quartos": 4,
        "banheiros": 5,
        "vagas": 4,
        "piscina": True,
        "espaco_gourmet": True,
        "academia": True,
        "spa_massagem": False,
        "espaco_lazer": True,
        "area_trabalho": True,
        "espaco_infantil": False,
        "area_esportiva": False,
        "portaria": True,
        "seguranca": True,
        "servicos_garagem": False,
        "acessibilidade": True,
        "pets": True,
        "varanda": True,
        "area_verde": True,
        "espaco_natural": False,
        "acabamento_premium": True,
        "moveis_embutidos": True,
        "layout_premium": True,
        "cozinha": True,
        "servicos": False,
        "conforto_interno": True,
        "mobiliado": False,
        "casa_inteligente": True,
        "servicos_conectividade": True,
        "infra_energetica": True,
        "infra_hidrica": False,
        "servicos_sustentaveis": True,
        "latitude": -16.705,
        "longitude": -49.261,
    }
