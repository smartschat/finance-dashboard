"""Transaction categorization rule engine."""

import re

import pandas as pd

from ..config import load_categories


def categorize_transactions_vectorized(df, is_visa=False, categories_config=None):
    """Categorize transactions using vectorized operations for better performance.

    Args:
        df: DataFrame with transactions
        is_visa: Whether this is Visa data (affects description column used)
        categories_config: Category configuration dict

    Returns:
        Series with category for each transaction
    """
    if categories_config is None:
        categories_config = load_categories()

    # Start with default category
    categories = pd.Series("Sonstiges", index=df.index)

    # Build description column for matching
    if is_visa:
        desc = df["Beschreibung"].fillna("").astype(str).str.lower()
    else:
        emp = df["Zahlungsempfaenger"].fillna("").astype(str)
        zweck = df["Verwendungszweck"].fillna("").astype(str)
        desc = (emp + " " + zweck).str.lower()

    # Apply keyword rules (vectorized string matching)
    rules = categories_config.get("rules", {})
    for category, keywords in rules.items():
        if not keywords:
            continue
        # Build regex pattern for all keywords (escaped, case-insensitive)
        pattern = "|".join(re.escape(k) for k in keywords)
        mask = desc.str.contains(pattern, case=False, na=False, regex=True)
        # Only update rows that are still "Sonstiges" (first match wins)
        categories = categories.where(~mask | (categories != "Sonstiges"), category)

    # Apply IBAN rules last (highest priority, for Girokonto only)
    if not is_visa and "IBAN" in df.columns:
        iban_rules = categories_config.get("iban_rules", {})
        if iban_rules:
            iban_col = df["IBAN"].fillna("").astype(str).str.upper()
            for iban, category in iban_rules.items():
                mask = iban_col == iban.upper()
                categories = categories.where(~mask, category)

    return categories
