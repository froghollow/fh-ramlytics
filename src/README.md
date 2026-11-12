# src/ — Ramlytics Source Code

This directory contains the core analytics tools and data pipeline for Ramlytics, a portfolio analytics platform for tracking and analyzing E*Trade equity and bond portfolios, ETF holdings, and market data.

## Directory Structure

```
src/
├── ramlytics/              # Main Python package
│   └── __init__.py         # Package entry point
├── data/                   # Sample data outputs and intermediate results
│   ├── *.json              # Parsed ETF report cards and holdings data
│   └── *.csv               # Generated holdings summaries and analysis outputs
├── *.py                    # Standalone analysis modules
└── *.ipynb                 # Interactive notebooks for development and exploration
```

## Python Modules

### [`bollinger.py`](/home/richa/projects/ramlytics/src/bollinger.py) (150 LOC)

Technical analysis module for detecting Bollinger Band squeeze events.

**Key Functions:**
- `compute_bollinger_bands()` — Calculates Bollinger Bands with configurable period and standard deviation
- `detect_squeeze()` — Identifies periods where band width contracts to multi-period minimums
- `process_tickers()` — Processes OHLC data across multiple ticker symbols
- `squeeze_alerts()` — Extracts rows where squeeze conditions are met

**Dependencies:** pandas, numpy

**Use Case:** Portfolio momentum analysis; identifies volatility compression preceding price breakouts.

---

### [`etrade_process_csv.py`](/home/richa/projects/ramlytics/src/etrade_process_csv.py) (128 LOC)

Data pipeline for converting E*Trade portfolio CSV exports into structured JSON and uploading to AWS S3 for DynamoDB ingestion.

**Key Functions:**
- `get_df()` — Parses CSV strings into normalized pandas DataFrames with sanitized column names
- `export_and_upload_json()` — Transforms header and holdings data into JSON format with metadata (account ID, Clerk user ID, timestamps) and uploads to S3
- `process_etrade_csv_downloads()` — Batch processes multiple E*Trade portfolio export files, separating stocks/ETFs from bonds

**Dependencies:** boto3, pandas, json, datetime

**Integration:** Connects to AWS S3 bucket (`fh-danelfin-289755104220` by default) in the `inbound/account_data/` prefix for Lambda-based DynamoDB loading.

**Key Output Format:** JSON with structure:
```json
{
  "account_id": "...",
  "clerk_user_id": "...",
  "account_name": "...",
  "market_dt": "YYYY-MM-DD",
  "update_dt": "YYYY-MM-DD HH:MM:SS",
  "symbols": ["TICKER1", "TICKER2", ...],
  "header": { /* account summary data */ },
  "holdings": { /* symbol-indexed position data */ }
}
```

---

### [`ramlytics/__init__.py`](/home/richa/projects/ramlytics/src/ramlytics/__init__.py)

Main package entry point with placeholder main function.

---

## Jupyter Notebooks

### Development & Exploration

- **[`etrade.ipynb`](/home/richa/projects/ramlytics/src/etrade.ipynb)** — Export, process, and upload E*Trade portfolios; main workflow orchestration
- **[`email_ingest.ipynb`](/home/richa/projects/ramlytics/src/email_ingest.ipynb)** — Email-based data ingest pipeline
- **[`excel_pipeline.ipynb`](/home/richa/projects/ramlytics/src/excel_pipeline.ipynb)** — Excel data refresh and transformation workflow
- **[`etrade_morningstar_extract.ipynb`](/home/richa/projects/ramlytics/src/etrade_morningstar_extract.ipynb)** — Extract tabular data from E*Trade/Morningstar ETF report card PDFs
- **[`mineru.ipynb`](/home/richa/projects/ramlytics/src/mineru.ipynb)** — MinerU intelligent document parsing for PDF extraction
- **[`obsidian.ipynb`](/home/richa/projects/ramlytics/src/obsidian.ipynb)** — Sandbox experiments with Obsidian knowledge management integration
- **[`top10x.ipynb`](/home/richa/projects/ramlytics/src/top10x.ipynb)** — Top 10 holdings analysis and visualization

---

## Data Directory

The `data/` folder contains sample outputs and intermediate analysis files:

- **`*.msReportCard.json`** — Parsed Morningstar ETF report card data
- **`*.msReportCard.pdf`** — Source Morningstar PDF documents
- **`eft_holdings_by_secname_*.csv`** — ETF holdings grouped by security type with timestamps
- **`eft_summary_holdings_*.csv`** — Aggregated ETF summary data
- **`holdings_by_secname_*.csv`** — Account holdings indexed by security name

---

## Workflow Overview

```
E*Trade Portfolio Export (CSV)
    ↓
etrade_process_csv.py
    ├─→ Parse account header & holdings
    ├─→ Normalize column names
    └─→ Generate JSON + upload to S3
            ↓
        AWS Lambda (DynamoDB Load)
            ↓
        DynamoDB (Account Data Store)
    ↓
Analytics Pipeline
    ├─→ Bollinger Band squeeze detection
    ├─→ Holdings analysis
    ├─→ Report generation
    └─→ Portfolio recommendations
```

---

## Assets

- **[`EtradePortfolio.png`](/home/richa/projects/ramlytics/src/EtradePortfolio.png)** — Portfolio visualization reference image

---

## Quick Start

### Prerequisites
- Python 3.8+
- `pandas`, `numpy`, `boto3` (AWS credentials required)
- Jupyter for notebook development

### Run E*Trade CSV Processing
```python
from etrade_process_csv import process_etrade_csv_downloads
df_stocks, df_bonds = process_etrade_csv_downloads(
    inpath="/path/to/etrade/csvs",
    outpath="/tmp/accounts"
)
```

### Compute Bollinger Bands
```python
from bollinger import process_tickers, squeeze_alerts

tickers = {"AAPL": df_aapl, "MSFT": df_msft}
processed = process_tickers(tickers, period=20, num_std=2.0)
alerts = squeeze_alerts(processed)
```

### Interactive Development
```bash
jupyter notebook etrade.ipynb
jupyter notebook top10x.ipynb
```

---

## Integration Points

- **E*Trade API**: CSV export for portfolio data
- **AWS S3**: Inbound account data storage
- **AWS Lambda**: DynamoDB ingestion trigger (see `backend/dyndb_load_json/`)
- **DynamoDB**: Portfolio data persistence
- **Obsidian/Knowledge Graph**: Exploratory analysis linking
- **Morningstar PDFs**: ETF research data extraction

---

## Contributing

All data processing scripts follow PEP 8 conventions. Notebooks are for experimentation; production logic should be extracted to the `ramlytics/` package or dedicated `.py` modules.

---

*Last Updated: 2026-11-12*
