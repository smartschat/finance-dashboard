"""Pytest fixtures for finance-dashboard tests."""

import pytest
import pandas as pd
from datetime import datetime


@pytest.fixture
def sample_categories_config():
    """Sample categories configuration for testing."""
    return {
        "config": {
            "non_spending_categories": ["Umbuchungen", "Kreditkarte", "Investitionen"],
            "cc_settlement_patterns": ["kreditkartenabrechnung", "ausgleich kreditkarte"],
        },
        "rules": {
            "Lebensmittel": ["rewe", "edeka", "aldi", "lidl"],
            "Restaurants": ["restaurant", "cafe", "mcdonald"],
            "Abonnements": ["spotify", "netflix", "chatgpt"],
            "Mobilität": ["db vertrieb", "shell", "tankstelle"],
        },
        "iban_rules": {
            "DE89370400440532013000": "Gehalt",
            "DE91100000000123456789": "Umbuchungen",
        },
        "overrides": {},
        "clusters": {
            "Spotify": ["*spotify*"],
            "Netflix": ["Netflix*"],
        },
    }


@pytest.fixture
def sample_girokonto_row():
    """Sample Girokonto transaction row."""
    return {
        "Buchungsdatum": "15.01.24",
        "Wertstellung": "15.01.24",
        "Status": "Gebucht",
        "Zahlungspflichtiger": "",
        "Zahlungsempfaenger": "REWE SAGT DANKE",
        "Verwendungszweck": "Einkauf 12345",
        "Umsatztyp": "Lastschrift",
        "IBAN": "DE12345678901234567890",
        "Betrag": "-45,99",
        "Glaeubiger_ID": "",
        "Mandatsreferenz": "",
        "Kundenreferenz": "",
    }


@pytest.fixture
def sample_visa_row():
    """Sample Visa transaction row."""
    return {
        "Belegdatum": "15.01.24",
        "Wertstellung": "17.01.24",
        "Status": "Gebucht",
        "Beschreibung": "SPOTIFY STOCKHOLM",
        "Umsatztyp": "Lastschrift",
        "Betrag": "-9,99",
        "Fremdwaehrung": "",
    }


@pytest.fixture
def sample_girokonto_df():
    """Sample Girokonto DataFrame for testing."""
    data = {
        "Datum": [datetime(2024, 1, 15), datetime(2024, 1, 16), datetime(2024, 1, 17)],
        "Betrag": [-45.99, -12.50, 2500.00],
        "Zahlungsempfaenger": ["REWE SAGT DANKE", "SHELL TANKSTELLE", "ARBEITGEBER GMBH"],
        "Verwendungszweck": ["Einkauf", "Tanken", "Gehalt Januar"],
        "IBAN": ["DE111", "DE222", "DE89370400440532013000"],
        "Konto": "DE123456",
        "Monat": pd.Series([datetime(2024, 1, 15), datetime(2024, 1, 16), datetime(2024, 1, 17)]).dt.to_period("M"),
    }
    return pd.DataFrame(data)


@pytest.fixture
def sample_visa_df():
    """Sample Visa DataFrame for testing."""
    data = {
        "Datum": [datetime(2024, 1, 15), datetime(2024, 1, 20)],
        "Betrag": [-9.99, -15.99],
        "Beschreibung": ["SPOTIFY STOCKHOLM", "NETFLIX.COM"],
        "Konto": "Visa Kreditkarte",
        "Monat": pd.Series([datetime(2024, 1, 15), datetime(2024, 1, 20)]).dt.to_period("M"),
    }
    return pd.DataFrame(data)
