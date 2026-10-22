"""Testes unitários para o CLI principal do ml-worker (main.py)."""

import sys
from unittest.mock import MagicMock, patch

import pandas as pd

from src.main import main


def test_cli_train_mode():
    """Testa execução da CLI no modo 'train'."""
    test_args = [
        "main.py",
        "--mode",
        "train",
        "--dataset-source",
        "data/test.parquet",
        "--n-trials",
        "5",
        "--k-folds",
        "3",
        "--push-to-hub",
        "--repo-id",
        "user/model-repo",
    ]

    with (
        patch.object(sys, "argv", test_args),
        patch("src.main.train_model") as mock_train,
    ):
        main()

        mock_train.assert_called_once_with(
            dataset_source="data/test.parquet",
            repo_id="user/model-repo",
            push_to_hub=True,
            n_trials=5,
            k_folds=3,
        )


def test_cli_evaluate_mode():
    """Testa execução da CLI no modo 'evaluate'."""
    test_args = [
        "main.py",
        "--mode",
        "evaluate",
        "--dataset-source",
        "data/test.parquet",
        "--n-trials",
        "4",
        "--k-folds",
        "2",
    ]

    dummy_df = pd.DataFrame({"col": [1, 2]})
    dummy_X = pd.DataFrame({"feat": [1, 2]})
    dummy_y = pd.Series([100, 200])

    with (
        patch.object(sys, "argv", test_args),
        patch("src.main.load_data", return_value=dummy_df),
        patch("src.main.prepare_data", return_value=(dummy_X, dummy_y)),
        patch("src.main.get_feature_groups", return_value=MagicMock()),
        patch(
            "src.main.evaluate_pipeline",
            return_value={"metrics_summary": {"mae": {"mean": 1000.0}}},
        ) as mock_eval,
    ):
        main()

        mock_eval.assert_called_once()
        assert mock_eval.call_args.kwargs["k_outer"] == 2
        assert mock_eval.call_args.kwargs["k_inner"] == 2
        assert mock_eval.call_args.kwargs["n_trials"] == 4


def test_cli_optimize_mode():
    """Testa execução da CLI no modo 'optimize'."""
    test_args = [
        "main.py",
        "--mode",
        "optimize",
        "--dataset-source",
        "data/test.parquet",
        "--n-trials",
        "10",
        "--k-folds",
        "3",
    ]

    dummy_df = pd.DataFrame({"col": [1, 2]})
    dummy_X = pd.DataFrame({"feat": [1, 2]})
    dummy_y = pd.Series([100, 200])

    with (
        patch.object(sys, "argv", test_args),
        patch("src.main.load_data", return_value=dummy_df),
        patch("src.main.prepare_data", return_value=(dummy_X, dummy_y)),
        patch("src.main.get_feature_groups", return_value=MagicMock()),
        patch(
            "src.main.optimize_hyperparameters",
            return_value=({"model__max_depth": 5}, 24000.0),
        ) as mock_opt,
    ):
        main()

        mock_opt.assert_called_once()
        assert mock_opt.call_args.kwargs["n_trials"] == 10
        assert mock_opt.call_args.kwargs["k_folds"] == 3
