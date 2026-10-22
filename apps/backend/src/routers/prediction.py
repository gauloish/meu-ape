"""Roteador para inferência de preços de imóveis via modelo de Machine Learning."""

from typing import Annotated, Any

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, status
from logging_config import config_logger
from loguru import logger

from src.dependencies import get_model
from src.schemas import InferenceRequest, PredictionResponse

config_logger()

router = APIRouter(tags=["Predição"])


def request_to_dataframe(payload: InferenceRequest) -> pd.DataFrame:
    """Transforma o schema pydantic da requisição de inferência em um objeto
    pandas DataFrame.

    Args:
        payload (InferenceRequest): Schema pydantic da requisição.

    Returns:
        pd.DataFrame: Objeto DataFrame.
    """
    data_dict = payload.model_dump()
    data_frame = pd.DataFrame([data_dict])

    return data_frame


@router.post(
    "/predict",
    response_model=PredictionResponse,
    status_code=status.HTTP_200_OK,
    summary="Previsão do preço de um imóvel",
)
def predict_imovel_price(
    payload: InferenceRequest,
    model: Annotated[Any, Depends(get_model)],
) -> PredictionResponse:
    """Recebe os dados do imóvel e executa a inferência utilizando o modelo XGBoost carregado."""
    try:
        # 1. Converte o request Pydantic para o DataFrame exigido pelo modelo
        df = request_to_dataframe(payload)

        # 2. Executa a predição no modelo Scikit-Learn/XGBoost
        prediction = model.predict(df)

        # 3. Extrai o valor previsto (assumindo formato escalar ou array unidimensional)
        if hasattr(prediction, "__getitem__"):
            estimated_price = float(prediction[0])
        else:
            estimated_price = float(prediction)

        logger.info(f"Inferência concluída com sucesso: R$ {estimated_price:,.2f}")

        return PredictionResponse(
            estimated_price=round(estimated_price, 2),
            currency="BRL",
        )

    except Exception as exc:
        logger.error(f"Erro durante a inferência do modelo: {exc}", exc_info=True)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Falha ao processar inferência do modelo: {exc!s}",
        ) from exc
