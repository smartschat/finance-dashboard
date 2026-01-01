"""CSV data loading for DKB bank exports."""

import json
import re
from pathlib import Path

import pandas as pd
import streamlit as st

from .parser import parse_german_number, parse_german_date
from ..config import load_categories
from ..categorization.rules import categorize_transactions_vectorized


def load_girokonto(filepath):
    """Load Girokonto (checking account) CSV file.

    Args:
        filepath: Path to the CSV file

    Returns:
        tuple: (DataFrame, int) - the loaded data and count of rows dropped due to parse failures
    """
    df = pd.read_csv(filepath, sep=";", encoding="utf-8-sig", skiprows=4)

    df.columns = [
        "Buchungsdatum",
        "Wertstellung",
        "Status",
        "Zahlungspflichtiger",
        "Zahlungsempfaenger",
        "Verwendungszweck",
        "Umsatztyp",
        "IBAN",
        "Betrag",
        "Glaeubiger_ID",
        "Mandatsreferenz",
        "Kundenreferenz",
    ]

    df["Betrag"] = df["Betrag"].apply(parse_german_number)
    df["Datum"] = df["Buchungsdatum"].apply(parse_german_date)

    # Track rows that failed to parse
    rows_before = len(df)
    df = df.dropna(subset=["Datum"])
    parse_failures = rows_before - len(df)

    df["Monat"] = df["Datum"].dt.to_period("M")
    df["Woche"] = df["Datum"].dt.isocalendar().week
    df["Wochentag"] = df["Datum"].dt.day_name()

    return df, parse_failures


def load_visa(filepath):
    """Load Visa credit card CSV file.

    Args:
        filepath: Path to the CSV file

    Returns:
        tuple: (DataFrame, int) - the loaded data and count of rows dropped due to parse failures
    """
    df = pd.read_csv(filepath, sep=";", encoding="utf-8-sig", skiprows=4)

    df.columns = [
        "Belegdatum",
        "Wertstellung",
        "Status",
        "Beschreibung",
        "Umsatztyp",
        "Betrag",
        "Fremdwaehrung",
    ]

    df["Betrag"] = df["Betrag"].apply(parse_german_number)
    df["Datum"] = df["Belegdatum"].apply(parse_german_date)

    # Track rows that failed to parse
    rows_before = len(df)
    df = df.dropna(subset=["Datum"])
    parse_failures = rows_before - len(df)

    df["Monat"] = df["Datum"].dt.to_period("M")
    df["Woche"] = df["Datum"].dt.isocalendar().week
    df["Wochentag"] = df["Datum"].dt.day_name()

    return df, parse_failures


def get_csv_file_manifest(data_dir="."):
    """Get a manifest of CSV files with their modification times for cache invalidation.

    Args:
        data_dir: Directory to search for CSV files

    Returns:
        str: JSON string of file paths and mtimes
    """
    data_dir = Path(data_dir)
    files = list(data_dir.glob("*Girokonto*.csv")) + list(data_dir.glob("*Visa*.csv"))
    # Return sorted list of (filename, mtime) tuples as a hashable string
    manifest = sorted((str(f), f.stat().st_mtime) for f in files)
    return json.dumps(manifest)


@st.cache_data
def load_all_data(_file_manifest, data_dir="."):
    """Load all CSV files from the specified directory.

    Args:
        _file_manifest: JSON string of file paths and mtimes for cache invalidation
        data_dir: Directory to search for CSV files

    Returns:
        tuple: (giro_dfs, visa_dfs, parse_failures) where parse_failures is total count
    """
    data_dir = Path(data_dir)

    girokonto_files = list(data_dir.glob("*Girokonto*.csv"))
    visa_files = list(data_dir.glob("*Visa*.csv"))

    # Load categories once for all transactions
    cats_config = load_categories()

    total_parse_failures = 0

    giro_dfs = []
    for f in girokonto_files:
        df, failures = load_girokonto(f)
        total_parse_failures += failures
        # Extract account number from filename
        match = re.search(r"DE\d+", f.name)
        df["Konto"] = match.group() if match else f.stem
        df["Kategorie"] = categorize_transactions_vectorized(
            df, is_visa=False, categories_config=cats_config
        )
        giro_dfs.append(df)

    visa_dfs = []
    for f in visa_files:
        df, failures = load_visa(f)
        total_parse_failures += failures
        df["Konto"] = "Visa Kreditkarte"
        df["Kategorie"] = categorize_transactions_vectorized(
            df, is_visa=True, categories_config=cats_config
        )
        visa_dfs.append(df)

    return giro_dfs, visa_dfs, total_parse_failures
