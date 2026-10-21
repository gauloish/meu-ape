"""Centralised configuration for the Zap Imóveis scraping pipeline."""

from typing import List, Optional, Tuple

BASE_URL = "https://www.zapimoveis.com.br"

USER_AGENTS: List[str] = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]

DEFAULT_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "cross-site",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}

PROPERTY_CATEGORIES: List[str] = [
    "apartamentos",
    "casas",
    "casas-de-condominio",
    "cobertura",
    "flat",
    "sobrado",
    "loft",
    "kitnet",
    "lotes-terrenos",
    "imoveis-comerciais",
]

PriceRange = Tuple[Optional[int], Optional[int]]

# Fine-grained price bounds designed to prevent partitions from exceeding 50 search pages.
PRICE_RANGES: List[PriceRange] = [
    (0, 100_000),
    (100_000, 150_000),
    (150_000, 180_000),
    (180_000, 210_000),
    (210_000, 240_000),
    (240_000, 270_000),
    (270_000, 300_000),
    (300_000, 330_000),
    (330_000, 360_000),
    (360_000, 390_000),
    (390_000, 420_000),
    (420_000, 450_000),
    (450_000, 480_000),
    (480_000, 510_000),
    (510_000, 550_000),
    (550_000, 600_000),
    (600_000, 650_000),
    (650_000, 700_000),
    (700_000, 750_000),
    (750_000, 800_000),
    (800_000, 850_000),
    (850_000, 900_000),
    (900_000, 950_000),
    (950_000, 1_000_000),
    (1_000_000, 1_100_000),
    (1_100_000, 1_200_000),
    (1_200_000, 1_300_000),
    (1_300_000, 1_400_000),
    (1_400_000, 1_500_000),
    (1_500_000, 1_700_000),
    (1_700_000, 2_000_000),
    (2_000_000, 2_400_000),
    (2_800_000, 3_300_000),
    (3_300_000, 4_000_000),
    (4_000_000, 5_000_000),
    (5_000_000, 7_000_000),
    (7_000_000, 10_000_000),
    (10_000_000, 15_000_000),
    (15_000_000, 25_000_000),
    (25_000_000, None),
]

MAX_PAGES_PER_PARTITION = 50
DEFAULT_CONCURRENCY = 1
DEFAULT_CITY_SLUG = "go+goiania"
DEFAULT_BUSINESS_TYPE = "venda"
DEFAULT_OUTPUT_FILENAME = "zap_dataset.csv"
CHECKPOINT_BUFFER_SIZE = 50
