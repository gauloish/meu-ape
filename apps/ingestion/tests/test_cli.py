"""Suíte de testes unitários para a interface de linha de comando da ingestion."""

from unittest.mock import MagicMock

import pytest

from src.cli import main as cli


def test_daily_scrape_defaults():
    """Valida os valores padrão do subcomando daily-scrape."""
    args = cli.build_parser().parse_args(["daily-scrape"])

    assert args.city == "go+goiania"
    assert args.concurrency == 1
    assert args.max_pages == 10
    assert args.dry_run is False
    assert args.func is cli.cmd_daily_scrape


def test_requires_subcommand():
    """Valida que a CLI exige um subcomando."""
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args([])


def test_main_dispatches_daily_scrape(monkeypatch: pytest.MonkeyPatch):
    """Valida que o subcomando daily-scrape repassa os argumentos ao pipeline."""
    fake_pipeline = MagicMock()
    monkeypatch.setattr("src.pipeline.daily_scrape.run_daily_pipeline", fake_pipeline)

    cli.main(["daily-scrape", "--concurrency", "3", "--max-pages", "7", "--dry-run"])

    fake_pipeline.assert_called_once_with(
        city_slug="go+goiania", concurrency=3, max_pages=7, dry_run=True
    )


def test_main_dispatches_load_csv(monkeypatch: pytest.MonkeyPatch, tmp_path):
    """Valida que o subcomando load-csv repassa caminho e tamanho do lote."""
    fake_loader = MagicMock()
    monkeypatch.setattr("src.pipeline.load_csv.load_csv_to_db", fake_loader)

    cli.main(["load-csv", "--input", str(tmp_path / "a.csv"), "--chunk-size", "10"])

    fake_loader.assert_called_once_with(csv_file=tmp_path / "a.csv", chunk_size=10)


def test_main_dispatches_apply_index(monkeypatch: pytest.MonkeyPatch):
    """Valida que o subcomando apply-index repassa os argumentos de correção FipeZAP."""
    fake_index = MagicMock(return_value=10)
    monkeypatch.setattr("src.pipeline.daily_scrape.run_fipezap_update", fake_index)

    cli.main(
        ["apply-index", "--months", "2026-02,2026-03", "--rate", "0.85", "--dry-run"]
    )

    fake_index.assert_called_once_with(
        months=["2026-02", "2026-03"], custom_rate_pct=0.85, dry_run=True
    )
