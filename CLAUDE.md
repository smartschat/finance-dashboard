# Finance Dashboard

Personal finance dashboard for analyzing DKB (Deutsche Kreditbank) bank exports, built with Streamlit.

## Tech Stack

- Python 3.12+
- Streamlit (web UI)
- Pandas (data processing)
- Plotly (charts)
- uv (package manager)
- Ruff (linting/formatting)

## Commands

```bash
# Install dependencies
uv sync

# Run the dashboard
uv run streamlit run app.py

# Run tests
uv run pytest

# Lint and format
uv run ruff check
uv run ruff format
```

## Project Structure

```
finance-dashboard/
├── app.py                      # Main Streamlit dashboard (monolithic UI)
├── finance_dashboard/          # Core library modules
│   ├── config.py               # Configuration loading (categories.json)
│   ├── data/
│   │   ├── loader.py           # CSV file discovery and loading
│   │   └── parser.py           # DKB CSV parsing (Girokonto + Visa formats)
│   └── categorization/
│       ├── rules.py            # Keyword-based category matching
│       ├── overrides.py        # Manual transaction overrides
│       └── clusters.py         # Group similar transactions
├── .github/workflows/          # CI: tests and linting on push/PR
├── categories.json             # Category rules, overrides, clusters config (gitignored)
├── tests/                      # pytest tests
└── *.csv                       # DKB export files (gitignored)
```

## Data Flow

1. CSV files are discovered by `data/loader.py` (patterns: `*Girokonto*.csv`, `*Visa*.csv`)
2. Parsed by `data/parser.py` which handles both DKB account formats
3. Categorized using rules from `categories.json` via `categorization/rules.py`
4. Manual overrides applied via `categorization/overrides.py`
5. Similar transactions grouped via `categorization/clusters.py`
6. Displayed in Streamlit dashboard (`app.py`)

## Key Conventions

- All transaction amounts are stored as floats (negative = expense, positive = income)
- Categories are defined in `categories.json` with keyword patterns
- Override keys use format: `{date}_{amount}_{description_hash}`
- Non-spending categories (transfers, investments) are excluded from spend calculations
