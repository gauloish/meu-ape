"""Roteador para inferência de preços de imóveis via modelo de Machine Learning."""

from typing import Any
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, status
from logging_settings import setup_logger

from ..dependencies import get_model
from ..schemas import InferenceRequest, PredictionResponse

logger = setup_logger(__name__)

router = APIRouter(tags=["Predição"])


def request_to_dataframe(payload: InferenceRequest) -> pd.DataFrame:
    """Converte o payload Pydantic validado em um pandas DataFrame para o modelo.

    =============================================================================
    TODO: Injetar a lógica de construção do DataFrame a partir do request.
    =============================================================================
    Instruções:
    1. O Scikit-Learn e o pipeline do XGBoost exigem que os dados de entrada
       estejam em formato tabular (pd.DataFrame) com as mesmas colunas e tipos
       utilizados durante a etapa de treinamento.
    2. Você pode ajustar este método para mapear nomes de colunas, calcular
       features derivadas ou criar dummies caso não estejam no pipeline.
    
    Exemplo básico:
        data_dict = payload.model_dump()
        return pd.DataFrame([data_dict])
    =============================================================================
    """
    data_dict = payload.model_dump()
    return pd.DataFrame([data_dict])


@router.post(
    "/predict",
    response_model=PredictionResponse,
    status_code=status.HTTP_200_OK,
    summary="Previsão do preço de um imóvel",
)
def predict_imovel_price(
    payload: InferenceRequest,
    model: Any = Depends(get_model),
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
            detail=f"Falha ao processar inferência do modelo: {str(exc)}",
        )
