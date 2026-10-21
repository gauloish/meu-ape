"""Zap Imóveis dataset coverage validation module.

Queries official category counts directly from Zap Imóveis and prints a comparison
summary evaluating local dataset coverage.
"""

import logging
import re
import time
from pathlib import Path
from typing import Dict, List, Tuple

from bs4 import BeautifulSoup
import pandas as pd

try:
    from curl_cffi import requests as cffi_requests
    HAS_CURL_CFFI = True
except ImportError:
    HAS_CURL_CFFI = False

import requests

logger = logging.getLogger(__name__)

DATASET_PATH = Path("data/raw/zap_dataset.csv")
BASE_URL = "https://www.zapimoveis.com.br"
CITY_SLUG = "go+goiania"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
}

CATEGORIES: List[Tuple[str, str]] = [
    ("Apartamentos", "apartamentos"),
    ("Casas", "casas"),
    ("Casas de Condomínio", "casas-de-condominio"),
    ("Coberturas", "cobertura"),
    ("Flats", "flat"),
    ("Sobrados", "sobrado"),
    ("Lofts", "loft"),
    ("Kitnets", "kitnet"),
    ("Lotes / Terrenos", "lotes-terrenos"),
    ("Comerciais", "imoveis-comerciais"),
]


def _build_session():
    """Build a curl_cffi or standard requests session."""
    if HAS_CURL_CFFI:
        return cffi_requests.Session(impersonate="chrome124")
    return requests.Session()


def _fetch_count(session, url: str) -> int:
    """Fetch official listing count displayed in page H1 header.

    Args:
        session: Active HTTP session.
        url: Target category URL.

    Returns:
        Integer count of listings or 0 on failure.
    """
    for attempt in range(3):
        try:
            resp = session.get(url, headers=HEADERS, timeout=10)
            if resp.status_code == 200:
                h1 = BeautifulSoup(resp.text, "html.parser").find("h1")
                if h1:
                    match = re.search(r"([\d\.]+)", h1.text)
                    if match:
                        return int(match.group(1).replace(".", ""))
                return 0
            if resp.status_code == 429:
                time.sleep(3 * (attempt + 1))
        except Exception:
            time.sleep(2)
    return 0


def validate_coverage(dataset_path: Path = DATASET_PATH) -> None:
    """Compare official portal listing totals with local scraped dataset.

    Args:
        dataset_path: Path to the raw CSV dataset.
    """
    if not dataset_path.exists():
        logger.error("Dataset file not found: %s", dataset_path)
        return

    df = pd.read_csv(dataset_path, low_memory=False)
    scraped_total = df["id"].nunique()

    session = _build_session()

    print("Zap Imóveis Dataset Coverage Validation - Goiânia")
    print(f"Local unique listings: {scraped_total}\n")
    print(f"{'Category':<25} | {'Official Count':>14} | {'Local Count':>11}")

    counts: Dict[str, int] = {}
    for label, slug in CATEGORIES:
        url = f"{BASE_URL}/venda/{slug}/{CITY_SLUG}/"
        count = _fetch_count(session, url)
        counts[slug] = count
        print(f"{label:<25} | {count:>14,} | {'-':>11}")
        time.sleep(2)

    total_zap = _fetch_count(session, f"{BASE_URL}/venda/imoveis/{CITY_SLUG}/")

    print(f"\nSummary:")
    print(f"  Official total listings (Zap): {total_zap:>10,}")
    print(f"  Scraped unique listings:       {scraped_total:>10,}")

    if total_zap > 0:
        pct = (scraped_total / total_zap) * 100
        print(f"  Gross coverage rate:           {pct:>9.1f}%")
        print(
            "\nNote: Official Zap total counts duplicated agency listings.\n"
            f"Local dataset contains {scraped_total} unique listing IDs."
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    validate_coverage()
