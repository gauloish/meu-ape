"""Testes unitários para o roteador de predição (routers/prediction.py)."""

from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest
from fastapi import HTTPException, status

from src.routers.prediction import predict_imovel_price, request_to_dataframe
from src.schemas import InferenceRequest, PredictionResponse


def test_request_to_dataframe_structure(valid_payload_all_features: dict):
    """Valida a estrutura do DataFrame gerado a partir do schema de inferência."""
    request = InferenceRequest(**valid_payload_all_features)
    df = request_to_dataframe(request)

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1

    # 1 tipo + 5 numéricas + 28 booleanas + 2 geográficas = 36 colunas
    assert df.shape == (1, 36)

    # Validação de colunas essenciais
    expected_cols = [
        "tipo_imovel",
        "condominio",
        "area_m2",
        "quartos",
        "banheiros",
        "vagas",
        "piscina",
        "academia",
        "portaria",
        "latitude",
        "longitude",
    ]
    for col in expected_cols:
        assert col in df.columns

    # Validação de valores convertidos
    assert df["tipo_imovel"].iloc[0] == "cobertura"
    assert df["area_m2"].iloc[0] == 240
    assert df["condominio"].iloc[0] == 1800
    assert df["quartos"].iloc[0] == 4
    assert bool(df["piscina"].iloc[0]) is True
    assert bool(df["spa_massagem"].iloc[0]) is False
    assert df["latitude"].iloc[0] == -16.705
    assert df["longitude"].iloc[0] == -49.261


def test_predict_imovel_price_numpy_array(valid_payload_dict: dict):
    """Valida inferência quando o modelo retorna array NumPy unidimensional."""
    payload = InferenceRequest(**valid_payload_dict)
    mock_model = MagicMock()
    mock_model.predict.return_value = np.array([850230.456])

    response = predict_imovel_price(payload=payload, model=mock_model)

    assert isinstance(response, PredictionResponse)
    assert response.estimated_price == 850230.46
    assert response.currency == "BRL"
    mock_model.predict.assert_called_once()


def test_predict_imovel_price_list_output(valid_payload_dict: dict):
    """Valida inferência quando o modelo retorna lista Python indexável."""
    payload = InferenceRequest(**valid_payload_dict)
    mock_model = MagicMock()
    mock_model.predict.return_value = [1420000.0]

    response = predict_imovel_price(payload=payload, model=mock_model)

    assert isinstance(response, PredictionResponse)
    assert response.estimated_price == 1420000.0
    assert response.currency == "BRL"


def test_predict_imovel_price_scalar_output(valid_payload_dict: dict):
    """Valida inferência quando o modelo retorna valor escalar (float puro)."""
    payload = InferenceRequest(**valid_payload_dict)

    class ScalarModel:
        def predict(self, _df: pd.DataFrame) -> float:
            return 600500.0

    response = predict_imovel_price(payload=payload, model=ScalarModel())

    assert isinstance(response, PredictionResponse)
    assert response.estimated_price == 600500.0
    assert response.currency == "BRL"


def test_predict_imovel_price_handles_model_exception(valid_payload_dict: dict):
    """Garante que exceções disparadas pelo modelo resultam em HTTPException 500."""
    payload = InferenceRequest(**valid_payload_dict)
    mock_model = MagicMock()
    mock_model.predict.side_effect = ValueError(
        "Incompatibilidade de dimensões de entrada no estimador"
    )

    with pytest.raises(HTTPException) as exc_info:
        predict_imovel_price(payload=payload, model=mock_model)

    assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "Falha ao processar inferência do modelo" in exc_info.value.detail
    assert "Incompatibilidade de dimensões" in exc_info.value.detail
