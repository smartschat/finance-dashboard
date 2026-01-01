"""Date and number parsing functions for German bank export formats."""

from datetime import datetime

import pandas as pd


def parse_german_number(value):
    """Parse German number format (1.234,56 -> 1234.56).

    Args:
        value: String value in German number format, or None/empty

    Returns:
        float: Parsed number, or 0.0 if parsing fails
    """
    if pd.isna(value) or value == "":
        return 0.0
    value = str(value).strip()
    value = value.replace("€", "").replace(" ", "").strip()
    value = value.replace(".", "")  # Remove thousand separator
    value = value.replace(",", ".")  # Convert decimal separator
    try:
        return float(value)
    except ValueError:
        return 0.0


def parse_german_date(date_str):
    """Parse German date format (DD.MM.YY or DD.MM.YYYY).

    Args:
        date_str: String in German date format

    Returns:
        datetime: Parsed date, or None if parsing fails
    """
    if pd.isna(date_str):
        return None
    date_str = str(date_str).strip()
    try:
        if len(date_str.split(".")[-1]) == 2:
            return datetime.strptime(date_str, "%d.%m.%y")
        else:
            return datetime.strptime(date_str, "%d.%m.%Y")
    except ValueError:
        return None
