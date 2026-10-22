"""Testes unitários para o módulo principal da aplicação e lifespan (main.py)."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import settings
from src.main import app, lifespan, load_model_from_hub


def test_load_model_from_hub_when_repo_id_empty(monkeypatch: pytest.MonkeyPatch):
    """Retorna None quando REPO_ID não está configurado nas variáveis de ambiente."""
    monkeypatch.setattr(settings, "repo_id", "")

    with patch("src.main.hf_hub_download") as mock_download:
        model = load_model_from_hub()
        assert model is None
        mock_download.assert_not_called()


def test_load_model_from_hub_success(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Valida fluxo de download e deserialização do modelo com Hugging Face Hub."""
    monkeypatch.setattr(settings, "repo_id", "usuario/meu-ape-xgboost")
    monkeypatch.setattr(settings, "model_filename", "pipeline.joblib")
    monkeypatch.setattr(settings, "hf_token", "hf_test_secret_token")
    monkeypatch.setattr(settings, "hf_cache_dir", tmp_path)

    expected_path = str(tmp_path / "pipeline.joblib")
    mock_loaded_model = MagicMock()

    with (
        patch("src.main.hf_hub_download", return_value=expected_path) as mock_download,
        patch("src.main.joblib.load", return_value=mock_loaded_model) as mock_joblib,
    ):
        model = load_model_from_hub()

        assert model is mock_loaded_model
        mock_download.assert_called_once_with(
            repo_id="usuario/meu-ape-xgboost",
            filename="pipeline.joblib",
            token="hf_test_secret_token",
            cache_dir=str(tmp_path),
        )
        mock_joblib.assert_called_once_with(expected_path)


def test_load_model_from_hub_without_token_and_cache(
    monkeypatch: pytest.MonkeyPatch,
):
    """Valida download de modelo em repositório público sem token e sem cache customizado."""
    monkeypatch.setattr(settings, "repo_id", "publico/meu-ape")
    monkeypatch.setattr(settings, "model_filename", "model.joblib")
    monkeypatch.setattr(settings, "hf_token", None)
    monkeypatch.setattr(settings, "hf_cache_dir", None)

    with (
        patch(
            "src.main.hf_hub_download", return_value="/tmp/model.joblib"
        ) as mock_download,
        patch("src.main.joblib.load", return_value=MagicMock()),
    ):
        load_model_from_hub()

        mock_download.assert_called_once_with(
            repo_id="publico/meu-ape",
            filename="model.joblib",
            token=None,
            cache_dir=None,
        )


def test_load_model_from_hub_download_error_propagates(
    monkeypatch: pytest.MonkeyPatch,
):
    """Valida propagação de exceção quando hf_hub_download falha."""
    monkeypatch.setattr(settings, "repo_id", "usuario/meu-ape")

    with (
        patch(
            "src.main.hf_hub_download",
            side_effect=RuntimeError("Falha de rede ao conectar no Hugging Face"),
        ),
        pytest.raises(RuntimeError, match="Falha de rede"),
    ):
        load_model_from_hub()


@pytest.mark.anyio
async def test_lifespan_startup_success():
    """Valida carregamento do modelo no startup e desalocação no shutdown da aplicação."""
    test_app = FastAPI()
    mock_model = MagicMock()

    with patch("src.main.load_model_from_hub", return_value=mock_model):
        async with lifespan(test_app):
            assert test_app.state.model is mock_model

        assert test_app.state.model is None


@pytest.mark.anyio
async def test_lifespan_startup_handles_download_exception():
    """Garante que falha no download do modelo não interrompe a inicialização do FastAPI."""
    test_app = FastAPI()

    with patch(
        "src.main.load_model_from_hub",
        side_effect=RuntimeError("Hub fora do ar"),
    ):
        async with lifespan(test_app):
            assert test_app.state.model is None

        assert test_app.state.model is None


def test_app_configuration_metadata():
    """Valida metadados e registro de rotas e middlewares no objeto app FastAPI."""
    assert app.title == "Meu Apê - API de Inferência"
    assert app.version == "0.1.0"

    openapi_paths = app.openapi()["paths"]
    assert "/health" in openapi_paths
    assert "/predict" in openapi_paths

    middleware_classes = [m.cls for m in app.user_middleware]
    assert CORSMiddleware in middleware_classes
