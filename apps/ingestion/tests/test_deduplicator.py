"""Suíte de testes unitários para a deduplicação de imóveis físicos."""

from pathlib import Path

import pandas as pd

from src.data.deduplicator import deduplicate_dataset
from tests.conftest import make_record


def _write_csv(path: Path, records: list[dict]) -> Path:
    pd.DataFrame(records).to_csv(path, index=False)
    return path


def test_keeps_richest_listing_of_same_property(tmp_path: Path):
    """Valida que anúncios do mesmo imóvel colapsam no registro mais completo."""
    raw = _write_csv(
        tmp_path / "raw.csv",
        [
            make_record("1", fotos_urls="a", descricao_completa="curta"),
            make_record(
                "2", fotos_urls="a, b, c", descricao_completa="descrição bem mais longa"
            ),
            make_record("3", rua="Avenida 85", preco=900000.0),
        ],
    )

    output = deduplicate_dataset(raw, tmp_path / "out" / "dedup.csv")
    df = pd.read_csv(output)

    assert sorted(df["id"].tolist()) == [2, 3]


def test_falls_back_to_neighbourhood_signature_without_street(tmp_path: Path):
    """Valida a assinatura por bairro quando a rua está ausente."""
    raw = _write_csv(
        tmp_path / "raw.csv",
        [
            make_record("1", rua=None),
            make_record("2", rua=None),
            make_record("3", rua=None, vagas=1),
        ],
    )

    df = pd.read_csv(deduplicate_dataset(raw, tmp_path / "dedup.csv"))

    assert len(df) == 2


def test_removes_temporary_columns(tmp_path: Path):
    """Valida que as colunas auxiliares não vazam para o CSV final."""
    raw = _write_csv(tmp_path / "raw.csv", [make_record("1")])

    df = pd.read_csv(deduplicate_dataset(raw, tmp_path / "dedup.csv"))

    assert list(df.columns) == list(make_record("1").keys())


def test_missing_input_returns_output_path_without_writing(tmp_path: Path):
    """Valida o comportamento quando o arquivo de entrada não existe."""
    output = tmp_path / "dedup.csv"
    result = deduplicate_dataset(tmp_path / "inexistente.csv", output)

    assert result == output
    assert not output.exists()
