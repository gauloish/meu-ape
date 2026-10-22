"""Testes unitários para o módulo de treinamento e publicação (train.py)."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest
from training.train import load_data, prepare_data, train_model


@pytest.fixture
def synthetic_raw_df() -> pd.DataFrame:
    """Gera DataFrame bruto sintético para teste."""
    np.random.seed(42)
    n_samples = 30
    return pd.DataFrame(
        {
            "area_m2": np.random.uniform(40, 200, n_samples).astype(float),
            "condominio": np.random.uniform(100, 1000, n_samples).astype(float),
            "banheiros": np.random.randint(1, 4, n_samples).astype(float),
            "quartos": np.random.randint(1, 5, n_samples).astype(float),
            "vagas": np.random.randint(1, 3, n_samples).astype(float),
            "latitude": np.random.uniform(-16.75, -16.65, n_samples).astype(float),
            "longitude": np.random.uniform(-49.30, -49.20, n_samples).astype(float),
            "tipo_imovel": pd.Series(
                np.random.choice(["casa", "apartamento"], n_samples), dtype="string"
            ),
            "piscina": pd.Series(
                np.random.choice([True, False], n_samples), dtype="boolean"
            ),
            "preco": pd.Series(
                np.random.uniform(200000, 1200000, n_samples), dtype="float64"
            ),
        }
    )


def test_load_data_dataframe(synthetic_raw_df):
    """Testa load_data recebendo DataFrame diretamente."""
    result = load_data(synthetic_raw_df)
    assert isinstance(result, pd.DataFrame)
    assert len(result) == len(synthetic_raw_df)


def test_load_data_parquet():
    """Testa load_data com caminho terminando em .parquet."""
    dummy_df = pd.DataFrame({"col": [1, 2]})
    with patch("pandas.read_parquet", return_value=dummy_df) as mock_read:
        result = load_data("data/dataset.parquet")
        mock_read.assert_called_once_with("data/dataset.parquet")
        assert len(result) == 2


def test_load_data_csv():
    """Testa load_data com caminho terminando em .csv."""
    dummy_df = pd.DataFrame({"col": [10, 20]})
    with patch("pandas.read_csv", return_value=dummy_df) as mock_read:
        result = load_data("data/dataset.csv")
        mock_read.assert_called_once_with("data/dataset.csv")
        assert len(result) == 2


def test_load_data_huggingface_hub():
    """Testa load_data com identificador do Hugging Face Hub."""
    mock_dataset_item = MagicMock()
    mock_dataset_item.to_pandas.return_value = pd.DataFrame({"hf_col": [100]})
    with patch(
        "training.train.load_dataset", return_value=mock_dataset_item
    ) as mock_load:
        result = load_data("usuario/dataset-teste")
        mock_load.assert_called_once_with("usuario/dataset-teste", split="train")
        assert "hf_col" in result.columns


def test_load_data_invalid_source():
    """Testa load_data com tipo de fonte inválido."""
    from typing import Any, cast

    with pytest.raises(ValueError, match="Fonte de dados inválida"):
        load_data(cast(Any, 12345))


def test_prepare_data_success(synthetic_raw_df):
    """Testa a separação de X e y com mock no DataPreprocessor."""
    with patch("training.train.DataPreprocessor") as mock_dp_cls:
        mock_dp_instance = MagicMock()
        mock_dp_instance.return_value = synthetic_raw_df
        mock_dp_cls.return_value = mock_dp_instance

        X, y = prepare_data(synthetic_raw_df)

        assert "preco" not in X.columns
        assert y.name == "preco"
        assert len(X) == len(synthetic_raw_df)


def test_prepare_data_missing_target(synthetic_raw_df):
    """Testa se lança KeyError se a coluna 'preco' não existir após pré-processamento."""
    df_no_price = synthetic_raw_df.drop(columns=["preco"])
    with patch("training.train.DataPreprocessor") as mock_dp_cls:
        mock_dp_instance = MagicMock()
        mock_dp_instance.return_value = df_no_price
        mock_dp_cls.return_value = mock_dp_instance

        with pytest.raises(KeyError, match="preco"):
            prepare_data(df_no_price)


def test_train_model_local_export(synthetic_raw_df, tmp_path: Path):
    """Testa o treinamento e salvamento local de artefatos (model.joblib e metrics.json)."""
    with (
        patch("training.train.DataPreprocessor") as mock_dp_cls,
        patch(
            "training.train.optimize_hyperparameters",
            return_value=({"model__max_depth": 3}, 25000.0),
        ),
        patch(
            "training.train.evaluate_pipeline",
            return_value={"metrics_summary": {"mae": {"mean": 25000.0}}},
        ),
        patch("joblib.dump") as mock_joblib_dump,
    ):
        mock_dp_instance = MagicMock()
        mock_dp_instance.return_value = synthetic_raw_df
        mock_dp_cls.return_value = mock_dp_instance

        result = train_model(
            dataset_source=synthetic_raw_df,
            repo_id=None,
            push_to_hub=False,
            n_trials=1,
            k_folds=2,
            run_evaluation=True,
            output_dir=tmp_path,
            random_state=42,
        )

        assert "best_cv_mae" in result
        assert result["best_cv_mae"] == 25000.0
        assert "evaluation" in result
        mock_joblib_dump.assert_called_once()
        assert (tmp_path / "metrics.json").exists()


def test_train_model_push_to_hub_success(synthetic_raw_df, tmp_path: Path):
    """Garante que o upload para o Hugging Face Hub chama as APIs corretas via mock."""
    with (
        patch("training.train.DataPreprocessor") as mock_dp_cls,
        patch(
            "training.train.optimize_hyperparameters",
            return_value=({"model__max_depth": 3}, 30000.0),
        ),
        patch("training.train.HfApi") as mock_hf_api_cls,
        patch("joblib.dump"),
    ):
        mock_dp_instance = MagicMock()
        mock_dp_instance.return_value = synthetic_raw_df
        mock_dp_cls.return_value = mock_dp_instance

        mock_api_instance = MagicMock()
        mock_hf_api_cls.return_value = mock_api_instance

        result = train_model(
            dataset_source=synthetic_raw_df,
            repo_id="usuario/meu-ape-model-test",
            push_to_hub=True,
            token="hf_test_token_secret",
            n_trials=1,
            k_folds=2,
            run_evaluation=False,
            output_dir=tmp_path,
            random_state=42,
        )

        assert result["best_cv_mae"] == 30000.0
        mock_api_instance.create_repo.assert_called_once_with(
            repo_id="usuario/meu-ape-model-test",
            repo_type="model",
            exist_ok=True,
            token="hf_test_token_secret",
        )
        mock_api_instance.upload_folder.assert_called_once_with(
            folder_path=str(tmp_path),
            repo_id="usuario/meu-ape-model-test",
            repo_type="model",
            token="hf_test_token_secret",
        )


def test_train_model_push_to_hub_missing_token_raises(synthetic_raw_df, tmp_path: Path):
    """Testa se lança ValueError quando push_to_hub=True mas nenhum token é fornecido."""
    with (
        patch("training.train.DataPreprocessor") as mock_dp_cls,
        patch(
            "training.train.optimize_hyperparameters",
            return_value=({"model__max_depth": 3}, 30000.0),
        ),
        patch("joblib.dump"),
        patch("os.getenv", return_value=None),
    ):
        mock_dp_instance = MagicMock()
        mock_dp_instance.return_value = synthetic_raw_df
        mock_dp_cls.return_value = mock_dp_instance

        with pytest.raises(ValueError, match="HF_TOKEN"):
            train_model(
                dataset_source=synthetic_raw_df,
                repo_id="usuario/meu-ape-model-test",
                push_to_hub=True,
                token=None,
                n_trials=1,
                k_folds=2,
                run_evaluation=False,
                output_dir=tmp_path,
                random_state=42,
            )


def test_train_model_push_to_hub_missing_repo_id_raises(
    synthetic_raw_df, tmp_path: Path
):
    """Testa se lança ValueError quando push_to_hub=True mas repo_id é None."""
    with (
        patch("training.train.DataPreprocessor") as mock_dp_cls,
        patch(
            "training.train.optimize_hyperparameters",
            return_value=({"model__max_depth": 3}, 30000.0),
        ),
        patch("joblib.dump"),
    ):
        mock_dp_instance = MagicMock()
        mock_dp_instance.return_value = synthetic_raw_df
        mock_dp_cls.return_value = mock_dp_instance

        with pytest.raises(ValueError, match="repo_id"):
            train_model(
                dataset_source=synthetic_raw_df,
                repo_id=None,
                push_to_hub=True,
                token="hf_some_token",
                n_trials=1,
                k_folds=2,
                run_evaluation=False,
                output_dir=tmp_path,
                random_state=42,
            )
