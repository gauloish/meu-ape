"""Suíte de testes unitários para o armazenamento incremental em CSV (CheckpointStore)."""

import asyncio
from pathlib import Path

import pandas as pd

from src.data.checkpoint import CheckpointStore


def test_add_many_ignores_duplicates_and_missing_ids(tmp_path: Path):
    """Valida que IDs repetidos ou vazios não entram no buffer."""
    store = CheckpointStore(output_path=tmp_path / "out.csv", buffer_size=10)

    added = store.add_many(
        [{"id": "1"}, {"id": "1"}, {"id": ""}, {"titulo": "sem id"}, {"id": "2"}]
    )

    assert added == 2
    assert store.total_seen == 2
    assert not store.is_new("1")
    assert store.is_new("3")


def test_buffer_full(tmp_path: Path):
    """Valida o sinalizador de buffer cheio."""
    store = CheckpointStore(output_path=tmp_path / "out.csv", buffer_size=2)
    store.add_many([{"id": "1"}])
    assert not store.buffer_full
    store.add_many([{"id": "2"}])
    assert store.buffer_full


def test_flush_sync_writes_header_once_and_appends(tmp_path: Path):
    """Valida que flushes sucessivos anexam linhas mantendo um único cabeçalho."""
    output = tmp_path / "out.csv"
    store = CheckpointStore(output_path=output, buffer_size=10)

    store.add_many([{"id": "1", "preco": 10}])
    store.flush_sync()
    store.add_many([{"id": "2", "preco": 20}])
    store.flush_sync()
    store.flush_sync()

    df = pd.read_csv(output)
    assert df["id"].tolist() == [1, 2]
    assert not store.buffer_full


def test_flush_async_respects_force_flag(tmp_path: Path):
    """Valida que o flush assíncrono só escreve com buffer cheio ou quando forçado."""
    output = tmp_path / "out.csv"
    store = CheckpointStore(output_path=output, buffer_size=5)
    store.add_many([{"id": "1"}])

    asyncio.run(store.flush_async())
    assert not output.exists()

    asyncio.run(store.flush_async(force=True))
    assert output.exists()


def test_resumes_ids_from_existing_file(tmp_path: Path):
    """Valida a retomada dos IDs já gravados em uma execução anterior."""
    output = tmp_path / "out.csv"
    pd.DataFrame({"id": [10, 20], "preco": [1, 2]}).to_csv(output, index=False)

    store = CheckpointStore(output_path=output)

    assert store.seen_ids == {"10", "20"}
    assert store.add_many([{"id": "10"}, {"id": "30"}]) == 1


def test_creates_parent_directory(tmp_path: Path):
    """Valida a criação automática do diretório de saída."""
    output = tmp_path / "data" / "raw" / "out.csv"
    CheckpointStore(output_path=output)
    assert output.parent.is_dir()
