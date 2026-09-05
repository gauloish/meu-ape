"""Testes unitários para o módulo de treinamento e publicação no HF Hub (train.py)."""

from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from ml_core.pipelines import FeatureGroups
from training.train import prepare_data, train_model


@pytest.fixture
def synthetic_raw_df():
    """Gera DataFrame bruto sintético para teste."""
    np.random.seed(42)
    n_samples = 50
    return pd.DataFrame({
        "area_m2": np.random.uniform(40, 200, n_samples).astype(float),
        "condominio": np.random.uniform(100, 1000, n_samples).astype(float),
        "banheiros": np.random.randint(1, 4, n_samples).astype(float),
        "quartos": np.random.randint(1, 5, n_samples).astype(float),
        "vagas": np.random.randint(1, 3, n_samples).astype(float),
        "latitude": np.random.uniform(-16.75, -16.65, n_samples).astype(float),
        "longitude": np.random.uniform(-49.30, -49.20, n_samples).astype(float),
        "tipo_imovel": pd.Series(np.random.choice(["casa", "apartamento"], n_samples), dtype="string"),
        "piscina": pd.Series(np.random.choice([True, False], n_samples), dtype="boolean"),
        "preco": pd.Series(np.random.uniform(200000, 1200000, n_samples), dtype="float64"),
    })


@pytest.fixture
def synthetic_groups():
    """Retorna grupos de features para o teste."""
    return FeatureGroups(
        numeric_features=["area_m2", "condominio", "banheiros", "quartos", "vagas", "latitude", "longitude"],
        categorical_features=["tipo_imovel"],
        boolean_features=["piscina"],
    )


def test_prepare_data(synthetic_raw_df):
    """Testa a separação de X e y com mock no DataPreprocessor."""
    with patch("training.train.DataPreprocessor") as mock_dp_cls:
        mock_dp_instance = MagicMock()
        mock_dp_instance.return_value = synthetic_raw_df
        mock_dp_cls.return_value = mock_dp_instance

        X, y = prepare_data(synthetic_raw_df)

        assert "preco" not in X.columns
        assert y.name == "preco"
        assert len(X) == len(synthetic_raw_df)


def test_train_model_local_export(synthetic_raw_df, synthetic_groups, tmp_path):
    """Testa o treinamento e salvamento local dos artefatos (model.joblib e metrics.json)."""
    with patch("training.train.DataPreprocessor") as mock_dp_cls:
        mock_dp_instance = MagicMock()
        mock_dp_instance.return_value = synthetic_raw_df
        mock_dp_cls.return_value = mock_dp_instance

        result = train_model(
            dataset_source=synthetic_raw_df,
            repo_id=None,
            push_to_hub=False,
            n_trials=1,
            k_folds=2,
            run_evaluation=False,
            output_dir=tmp_path,
            random_state=42,
            feature_groups=synthetic_groups,
        )

        assert "best_cv_rmse" in result
        assert (tmp_path / "model.joblib").exists()
        assert (tmp_path / "metrics.json").exists()


def test_train_model_push_to_hub_mocked(synthetic_raw_df, synthetic_groups, tmp_path):
    """Garante que o upload para o Hugging Face Hub chama as APIs corretas via MOCK sem fazer chamadas reais."""
    with (
        patch("training.train.DataPreprocessor") as mock_dp_cls,
        patch("training.train.HfApi") as mock_hf_api_cls,
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
            token="hf_fake_token_12345",
            n_trials=1,
            k_folds=2,
            run_evaluation=False,
            output_dir=tmp_path,
            random_state=42,
            feature_groups=synthetic_groups,
        )

        assert "best_cv_rmse" in result

        # Verifica se as APIs do Hugging Face foram chamadas com os parâmetros de segurança esperados
        mock_hf_api_cls.assert_called_once()
        mock_api_instance.create_repo.assert_called_once_with(
            repo_id="usuario/meu-ape-model-test",
            repo_type="model",
            exist_ok=True,
            token="hf_fake_token_12345",
        )
        mock_api_instance.upload_folder.assert_called_once_with(
            folder_path=str(tmp_path),
            repo_id="usuario/meu-ape-model-test",
            repo_type="model",
            token="hf_fake_token_12345",
        )


def test_train_model_push_to_hub_missing_token_raises(synthetic_raw_df, synthetic_groups, tmp_path):
    """Testa se lança ValueError quando push_to_hub=True mas nenhum token é fornecido."""
    with (
        patch("training.train.DataPreprocessor") as mock_dp_cls,
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
                feature_groups=synthetic_groups,
            )
