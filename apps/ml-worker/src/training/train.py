"""Módulo de treinamento para produção e publicação de artefatos no Hugging Face Hub."""

import json
import os
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from datasets import load_dataset
from dotenv import load_dotenv
from evaluation.evaluate import evaluate_pipeline
from huggingface_hub import HfApi
from logging_config import config_logger
from loguru import logger
from ml_core.pipelines import (
    create_training_pipeline,
    get_feature_groups,
)
from ml_core.preprocessing.data_preprocessor import DataPreprocessor
from optimization.optimize import optimize_hyperparameters

config_logger()
load_dotenv()


def load_data(dataset_source: str | pd.DataFrame) -> pd.DataFrame:
    """Carrega o dataset bruto a partir do Hugging Face Hub, caminho de arquivo ou DataFrame.

    Args:
        dataset_source (str | pd.DataFrame): Nome do dataset HF Hub, caminho local Parquet/CSV, ou DataFrame.

    Returns:
        pd.DataFrame: DataFrame bruto carregado.

    Raises:
        ValueError: Se o tipo de fonte de dados for inválido.
    """
    if isinstance(dataset_source, pd.DataFrame):
        return dataset_source.copy()

    if isinstance(dataset_source, str):
        df: pd.DataFrame

        if dataset_source.endswith(".parquet"):
            logger.info(f"Carregando dataset (Parquet) local: {dataset_source}")
            df = pd.read_parquet(dataset_source)

        elif dataset_source.endswith(".csv"):
            logger.info(f"Carregando dataset (CSV) local: {dataset_source}")
            df = pd.read_csv(dataset_source)

        else:
            logger.info(f"Carregando dataset do Hugging Face Hub: {dataset_source}")
            df = pd.DataFrame(load_dataset(dataset_source, split="train").to_pandas())

        return df

    raise ValueError(f"Fonte de dados inválida: {type(dataset_source)}")  # noqa: RUF100, TRY004


def prepare_data(df_raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Passa os dados brutos pelo DataPreprocessor e separa X e y (preco).

    Args:
        df_raw (pd.DataFrame): DataFrame bruto.

    Returns:
        tuple[pd.DataFrame, pd.Series]: Tupla contendo (X, y).

    Raises:
        KeyError: Se a coluna alvo 'preco' não for encontrada.
    """
    logger.info("Executando DataPreprocessor sobre o dataset bruto.")

    preprocessor = DataPreprocessor()
    df_processed = preprocessor(df_raw)

    if "preco" not in df_processed.columns:
        raise KeyError(
            "A coluna alvo 'preco' não foi encontrada após o pré-processamento."
        )

    y = df_processed["preco"]
    X = df_processed.drop(columns=["preco"])

    logger.info(
        f"Dados preparados com sucesso: {X.shape[0]} amostras, {X.shape[1]} features."
    )

    return X, y


def train_model(
    dataset_source: str | pd.DataFrame,
    repo_id: str | None = None,
    push_to_hub: bool = False,
    token: str | None = None,
    n_trials: int = 20,
    k_folds: int = 5,
    run_evaluation: bool = True,
    output_dir: str | Path = "artifacts",
    random_state: int | None = 1667,
) -> dict[str, Any]:
    """Orquestra o ciclo completo de treinamento para produção e publicação no Hugging Face Hub.

    Fluxo:
    1. Carrega dados brutos e executa `DataPreprocessor`.
    2. Separa X e y.
    3. Se `run_evaluation=True`, roda Validação Cruzada Aninhada (`evaluate.py`) para extrair métricas confiáveis.
    4. Otimiza os hiperparâmetros no dataset total (`optimize.py`).
    5. Treina o pipeline final com 100% dos dados.
    6. Salva `model.joblib` e `metrics.json`.
    7. Envia os artefatos para o Hugging Face Hub se `push_to_hub=True`.

    Args:
        dataset_source (str | pd.DataFrame): Nome do dataset HF Hub ou DataFrame bruto.
        repo_id (str | None): Repositório do Hugging Face para envio (ex: 'usuario/meu-ape-model').
        push_to_hub (bool): Se True, publica os artefatos no HF Hub.
        token (str | None): Token do HF Hub. Se None, tenta ler de `os.getenv("HF_TOKEN")`.
        n_trials (int): Número de trials do Optuna. Padrão: 20.
        k_folds (int): Número de folds para CV. Padrão: 5.
        run_evaluation (bool): Se True, executa Nested CV para extração de métricas.
        output_dir (str | Path): Diretório local para salvar os artefatos antes do upload.
        random_state (int | None): Semente aleatória. Padrão: 42.

    Returns:
        dict[str, Any]: Dicionário com metadados do treino, melhores parâmetros e métricas.

    Raises:
        ValueError: Se `push_to_hub` for True mas o token ou repo_id não for informado.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    df = load_data(dataset_source)
    X, y = prepare_data(df)
    feature_groups = get_feature_groups(X)

    evaluation_metrics: dict[str, Any] = {}

    if run_evaluation:
        logger.info("Executando Nested CV para extração de métricas do modelo...")

        evaluation_metrics = evaluate_pipeline(
            X=X,
            y=y,
            k_outer=k_folds,
            k_inner=k_folds,
            n_trials=n_trials,
            random_state=random_state,
            feature_groups=feature_groups,
        )

    logger.info("Otimizando hiperparâmetros no dataset completo...")

    best_params, best_score = optimize_hyperparameters(
        X=X,
        y=y,
        n_trials=n_trials * k_folds,
        k_folds=k_folds,
        random_state=random_state,
        feature_groups=feature_groups,
    )

    logger.info("Treinando pipeline final com 100% dos dados...")

    pipeline = create_training_pipeline(feature_groups=feature_groups)
    pipeline.set_params(**best_params)
    pipeline.fit(X, y)

    model_file_path = output_path / "model.joblib"
    metrics_file_path = output_path / "metrics.json"

    best_params_jsonable = {
        k: (v if not hasattr(v, "get_params") else v.__class__.__name__)
        for k, v in best_params.items()
    }

    metrics_payload = {
        "best_cv_mae": best_score,
        "best_params": best_params_jsonable,
        "n_samples": len(y),
        "n_features": int(X.shape[1]),
        "evaluation": evaluation_metrics,
    }

    joblib.dump(pipeline, model_file_path)

    with open(metrics_file_path, "w", encoding="utf-8") as f:
        json.dump(metrics_payload, f, indent=2, ensure_ascii=False)

    logger.info(f"Artefatos salvos em: {output_path}")

    if push_to_hub:
        hf_token = token or os.getenv("HF_TOKEN")

        if not hf_token:
            raise ValueError(
                "O parâmetro 'push_to_hub' é True, mas nenhum token do Hugging Face foi encontrado em 'token' ou na variável de ambiente 'HF_TOKEN'."
            )

        if not repo_id:
            raise ValueError(
                "O parâmetro 'repo_id' deve ser informado para publicar no Hugging Face Hub."
            )

        logger.info(f"Enviando artefatos para o Hugging Face Hub (Repo: {repo_id})...")

        api = HfApi()
        api.create_repo(
            repo_id=repo_id, repo_type="model", exist_ok=True, token=hf_token
        )

        api.upload_folder(
            folder_path=str(output_path),
            repo_id=repo_id,
            repo_type="model",
            token=hf_token,
        )

        logger.info("Upload para o Hugging Face Hub concluído com sucesso!")

    return metrics_payload
