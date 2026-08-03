# Meu Apê — Real Estate Analytics & Valuation Pipeline

A data processing and machine learning pipeline for scraping, deduplicating, analyzing, and predicting real estate property prices in Goiânia, Brazil.

## Architecture & Project Structure

```
meu-ape/
├── src/
│   ├── scraping/
│   │   ├── config.py           # Pipeline configuration, categories, and price ranges
│   │   ├── zap_parser.py       # JSON-LD property item parser
│   │   ├── http_client.py      # Synchronous and asynchronous HTTP clients (curl_cffi)
│   │   ├── zap_scraper_sync.py # Synchronous multi-threaded partition scraper
│   │   └── zap_scraper_async.py# Asynchronous partition scraper
│   ├── data/
│   │   ├── checkpoint.py       # Resilient CSV buffer and persistence manager
│   │   ├── deduplicator.py     # Physical asset deduplication engine
│   │   └── validator.py        # Coverage validator comparing local dataset vs portal totals
│   └── cli/
│       └── main.py             # Command-line interface subcommands
├── notebooks/                  # EDA, feature engineering, and model training
├── data/
│   ├── raw/                    # Extracted raw CSV datasets
│   └── processed/              # Deduplicated and cleaned datasets
├── pyproject.toml              # Dependency and package configuration
└── main.py                     # CLI wrapper script
```

## Installation

Ensure Python 3.12+ and `uv` package manager are installed.

```bash
uv sync
```

## Usage

The project provides a unified Command-Line Interface (`meu-ape`) with dedicated subcommands.

### 1. Data Extraction (Scraping)

Execute full partition scraping across categories and price ranges:

```bash
# Synchronous multi-threaded extraction
uv run python main.py scrape --workers 2

# High-speed asynchronous extraction
uv run python main.py scrape-async --concurrency 5
```

### 2. Dataset Deduplication

Identify physical properties listed across multiple agencies and extract unique assets:

```bash
uv run python main.py deduplicate
```

### 3. Catalog Coverage Validation

Compare local dataset coverage against total listings published on Zap Imóveis:

```bash
uv run python main.py validate
```

## Exploratory Data Analysis & Modeling

Data analysis and machine learning workflows are located in the `notebooks/` directory:

- `01_data_cleaning.ipynb` — Data sanitization and missing value imputation
- `02_data_enrichment.ipynb` — Geocoding and spatial metadata enrichment
- `03_data_exploration.ipynb` — Market distributions and price correlation analysis
- `04_feature_engineering.ipynb` — Spatial and structural feature extraction
- `05_modeling.ipynb` — Model training (XGBoost, LightGBM) and evaluation
