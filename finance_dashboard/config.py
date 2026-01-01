"""Configuration loading and management."""

import json
from pathlib import Path

# Default configuration file location
CATEGORIES_FILE = Path(__file__).parent.parent / "categories.json"

# Default values (can be overridden in categories.json config section)
DEFAULT_NON_SPEND_CATEGORIES = ["Umbuchungen", "Kreditkarte", "Investitionen"]
DEFAULT_CC_SETTLEMENT_PATTERNS = ["kreditkartenabrechnung", "ausgleich kreditkarte"]


def load_categories(filepath=None):
    """Load category rules from JSON file.

    Args:
        filepath: Path to categories file (defaults to CATEGORIES_FILE)

    Returns:
        dict: Categories configuration with rules, iban_rules, overrides, clusters
    """
    if filepath is None:
        filepath = CATEGORIES_FILE

    if Path(filepath).exists():
        with open(filepath, encoding="utf-8") as f:
            return json.load(f)
    return {"config": {}, "rules": {}, "iban_rules": {}, "overrides": {}, "clusters": {}}


def save_categories(categories, filepath=None):
    """Save category rules to JSON file.

    Args:
        categories: Categories configuration dict
        filepath: Path to categories file (defaults to CATEGORIES_FILE)
    """
    if filepath is None:
        filepath = CATEGORIES_FILE

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(categories, f, ensure_ascii=False, indent=2)


def get_non_spend_categories(categories_config=None):
    """Get non-spending categories from config, with fallback to defaults.

    Args:
        categories_config: Categories configuration dict (loads if None)

    Returns:
        list: Category names to exclude from spending calculations
    """
    if categories_config is None:
        categories_config = load_categories()
    config = categories_config.get("config", {})
    return config.get("non_spending_categories", DEFAULT_NON_SPEND_CATEGORIES)


def get_cc_settlement_patterns(categories_config=None):
    """Get credit card settlement patterns from config, with fallback to defaults.

    Args:
        categories_config: Categories configuration dict (loads if None)

    Returns:
        list: Patterns to identify credit card settlement transactions
    """
    if categories_config is None:
        categories_config = load_categories()
    config = categories_config.get("config", {})
    return config.get("cc_settlement_patterns", DEFAULT_CC_SETTLEMENT_PATTERNS)


def hashable_config(config):
    """Convert config dict to hashable string for caching.

    Args:
        config: Configuration dict

    Returns:
        str: JSON string representation
    """
    return json.dumps(config, sort_keys=True)
