"""Physical property deduplication module.

Identifies listings published by different agencies that refer to the same physical
real estate asset, keeping the listing record with the highest data completeness.
"""

import logging
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

DEFAULT_INPUT = Path("data/raw/zap_dataset.csv")
DEFAULT_OUTPUT = Path("data/processed/zap_dataset_deduplicated.csv")

_TEMP_COLUMNS = [
    "bairro_norm",
    "rua_norm",
    "area_round",
    "preco_round",
    "quartos_clean",
    "banheiros_clean",
    "vagas_clean",
    "tipo_norm",
    "property_signature",
    "desc_len",
    "foto_count",
    "has_bairro",
    "has_rua",
]


def _normalise_text(series: pd.Series) -> pd.Series:
    """Lowercase and strip whitespace from text series."""
    return series.fillna("").astype(str).str.lower().str.strip()


def _make_physical_signature(row: pd.Series) -> str:
    """Generate a canonical signature string for physical property matching.

    Args:
        row: Pandas DataFrame row containing property attributes.

    Returns:
        Canonical string representing the physical asset.
    """
    if row["rua_norm"] and pd.notnull(row["area_round"]) and pd.notnull(row["preco_round"]):
        return (
            f"RUA:{row['rua_norm']}"
            f"|A:{row['area_round']}"
            f"|Q:{row['quartos_clean']}"
            f"|P:{row['preco_round']}"
        )
    return (
        f"B:{row['bairro_norm']}"
        f"|T:{row['tipo_norm']}"
        f"|A:{row['area_round']}"
        f"|Q:{row['quartos_clean']}"
        f"|BNH:{row['banheiros_clean']}"
        f"|V:{row['vagas_clean']}"
        f"|P:{row['preco_round']}"
    )


def _enrich_with_signature(df: pd.DataFrame) -> pd.DataFrame:
    """Add normalised attribute columns and canonical property signatures."""
    df = df.copy()
    df["bairro_norm"] = _normalise_text(df["bairro"])
    df["rua_norm"] = _normalise_text(df["rua"])
    df["area_round"] = pd.to_numeric(df["area_m2"], errors="coerce").round(0)
    df["preco_round"] = pd.to_numeric(df["preco"], errors="coerce").round(0)
    df["quartos_clean"] = pd.to_numeric(df["quartos"], errors="coerce").fillna(0).astype(int)
    df["banheiros_clean"] = pd.to_numeric(df["banheiros"], errors="coerce").fillna(0).astype(int)
    df["vagas_clean"] = pd.to_numeric(df["vagas"], errors="coerce").fillna(0).astype(int)
    df["tipo_norm"] = _normalise_text(df["tipo_imovel"])
    df["property_signature"] = df.apply(_make_physical_signature, axis=1)
    return df


def _score_richness(df: pd.DataFrame) -> pd.DataFrame:
    """Add helper metrics for evaluating record completeness."""
    df = df.copy()
    df["desc_len"] = df["descricao_completa"].fillna("").astype(str).str.len()
    df["foto_count"] = (
        df["fotos_urls"].fillna("").astype(str).apply(lambda x: len(x.split(",")) if x else 0)
    )
    df["has_bairro"] = df["bairro"].notnull().astype(int)
    df["has_rua"] = df["rua"].notnull().astype(int)
    return df


def deduplicate_dataset(
    input_file: Path = DEFAULT_INPUT,
    output_file: Path = DEFAULT_OUTPUT,
) -> Path:
    """Filter physical duplicate listings and write the deduplicated dataset.

    Args:
        input_file: Source raw CSV dataset path.
        output_file: Target deduplicated CSV dataset path.

    Returns:
        Resolved path to the output CSV file.
    """
    input_path = Path(input_file)
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not input_path.exists():
        logger.error("Input file not found: %s", input_path)
        return output_path

    logger.info("Reading raw dataset: %s", input_path)
    df = pd.read_csv(input_path, low_memory=False)
    initial_count = len(df)

    df = _enrich_with_signature(df)
    df = _score_richness(df)

    df_sorted = df.sort_values(
        by=["has_rua", "has_bairro", "foto_count", "desc_len"],
        ascending=[False, False, False, False],
    )
    df_clean = df_sorted.drop_duplicates(subset=["property_signature"], keep="first").copy()
    df_clean = df_clean.drop(columns=_TEMP_COLUMNS)

    df_clean.to_csv(output_path, index=False, encoding="utf-8")

    removed = initial_count - len(df_clean)
    logger.info("Deduplication complete:")
    logger.info("  Initial raw listings: %d", initial_count)
    logger.info("  Duplicates removed:   %d", removed)
    logger.info("  Unique physical assets: %d", len(df_clean))
    logger.info("Saved to: %s", output_path.resolve())

    return output_path


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    deduplicate_dataset()
