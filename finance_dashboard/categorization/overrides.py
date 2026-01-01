"""Transaction override key generation."""

import hashlib
import pandas as pd


def get_override_key(row):
    """Generate a unique key for a transaction to use in overrides.

    Uses a hash of the full description to avoid collisions from truncation.

    Args:
        row: DataFrame row or Series with Datum, Beschreibung, Betrag

    Returns:
        str: Unique key in format "date_hash_amount"
    """
    date_str = row["Datum"].strftime("%Y-%m-%d") if pd.notna(row["Datum"]) else "unknown"
    desc = str(row.get("Beschreibung", ""))
    amount = f"{row.get('Betrag', 0):.2f}"
    # Use hash of full description to avoid collisions
    desc_hash = hashlib.md5(desc.encode()).hexdigest()[:12]
    return f"{date_str}_{desc_hash}_{amount}"


def get_legacy_override_key(row):
    """Generate the old-format override key for migration purposes.

    Args:
        row: DataFrame row or Series with Datum, Beschreibung, Betrag

    Returns:
        str: Legacy key in format "date_truncated-desc_amount"
    """
    date_str = row["Datum"].strftime("%Y-%m-%d") if pd.notna(row["Datum"]) else "unknown"
    desc = str(row.get("Beschreibung", ""))[:30].replace("/", "-")
    amount = f"{row.get('Betrag', 0):.2f}"
    return f"{date_str}_{desc}_{amount}"
