"""Tests for transaction categorization logic."""

import pandas as pd

from finance_dashboard.categorization.rules import categorize_transactions_vectorized


class TestCategorizeTransactionsVectorized:
    """Tests for vectorized categorization function."""

    def test_keyword_matching_basic(self, sample_categories_config):
        """Test basic keyword matching."""
        df = pd.DataFrame(
            {
                "Zahlungsempfaenger": ["REWE SAGT DANKE"],
                "Verwendungszweck": ["Einkauf"],
                "IBAN": ["DE12345"],
            }
        )
        result = categorize_transactions_vectorized(
            df, is_visa=False, categories_config=sample_categories_config
        )
        assert result.iloc[0] == "Lebensmittel"

    def test_keyword_matching_case_insensitive(self, sample_categories_config):
        """Test that keyword matching is case-insensitive."""
        df = pd.DataFrame(
            {
                "Zahlungsempfaenger": ["rewe", "REWE", "Rewe", "RewE"],
                "Verwendungszweck": ["", "", "", ""],
                "IBAN": ["DE1", "DE2", "DE3", "DE4"],
            }
        )
        result = categorize_transactions_vectorized(
            df, is_visa=False, categories_config=sample_categories_config
        )
        assert all(result == "Lebensmittel")

    def test_keyword_in_verwendungszweck(self, sample_categories_config):
        """Test keyword matching in Verwendungszweck field."""
        df = pd.DataFrame(
            {
                "Zahlungsempfaenger": ["Unknown Merchant"],
                "Verwendungszweck": ["EDEKA Filiale 123"],
                "IBAN": ["DE12345"],
            }
        )
        result = categorize_transactions_vectorized(
            df, is_visa=False, categories_config=sample_categories_config
        )
        assert result.iloc[0] == "Lebensmittel"

    def test_iban_rule_priority(self, sample_categories_config):
        """Test that IBAN rules have highest priority."""
        df = pd.DataFrame(
            {
                "Zahlungsempfaenger": ["REWE SAGT DANKE"],  # Would match Lebensmittel
                "Verwendungszweck": ["Einkauf"],
                "IBAN": ["DE89370400440532013000"],  # IBAN rule: Gehalt
            }
        )
        result = categorize_transactions_vectorized(
            df, is_visa=False, categories_config=sample_categories_config
        )
        assert result.iloc[0] == "Gehalt"

    def test_visa_description_matching(self, sample_categories_config):
        """Test Visa transactions use Beschreibung field."""
        df = pd.DataFrame(
            {
                "Beschreibung": ["SPOTIFY STOCKHOLM", "NETFLIX.COM"],
            }
        )
        result = categorize_transactions_vectorized(
            df, is_visa=True, categories_config=sample_categories_config
        )
        assert result.iloc[0] == "Abonnements"
        assert result.iloc[1] == "Abonnements"

    def test_no_match_returns_sonstiges(self, sample_categories_config):
        """Test that unmatched transactions get 'Sonstiges' category."""
        df = pd.DataFrame(
            {
                "Zahlungsempfaenger": ["Unknown Random Merchant"],
                "Verwendungszweck": ["Random purchase"],
                "IBAN": ["DE99999"],
            }
        )
        result = categorize_transactions_vectorized(
            df, is_visa=False, categories_config=sample_categories_config
        )
        assert result.iloc[0] == "Sonstiges"

    def test_multiple_transactions(self, sample_categories_config):
        """Test categorizing multiple transactions at once."""
        df = pd.DataFrame(
            {
                "Zahlungsempfaenger": [
                    "REWE SAGT DANKE",
                    "SHELL TANKSTELLE",
                    "RESTAURANT BELLA",
                    "UNKNOWN MERCHANT",
                ],
                "Verwendungszweck": ["Einkauf", "Tanken", "Dinner", "Something"],
                "IBAN": ["DE1", "DE2", "DE3", "DE4"],
            }
        )
        result = categorize_transactions_vectorized(
            df, is_visa=False, categories_config=sample_categories_config
        )
        assert result.iloc[0] == "Lebensmittel"
        assert result.iloc[1] == "Mobilität"
        assert result.iloc[2] == "Restaurants"
        assert result.iloc[3] == "Sonstiges"

    def test_empty_dataframe(self, sample_categories_config):
        """Test handling of empty DataFrame."""
        df = pd.DataFrame(
            {
                "Zahlungsempfaenger": [],
                "Verwendungszweck": [],
                "IBAN": [],
            }
        )
        result = categorize_transactions_vectorized(
            df, is_visa=False, categories_config=sample_categories_config
        )
        assert len(result) == 0

    def test_missing_columns_handled(self, sample_categories_config):
        """Test handling when optional columns are missing."""
        df = pd.DataFrame(
            {
                "Beschreibung": ["SPOTIFY AB"],
            }
        )
        # Should not raise error for Visa (no IBAN column needed)
        result = categorize_transactions_vectorized(
            df, is_visa=True, categories_config=sample_categories_config
        )
        assert result.iloc[0] == "Abonnements"

    def test_null_values_handled(self, sample_categories_config):
        """Test handling of null/NaN values in fields."""
        df = pd.DataFrame(
            {
                "Zahlungsempfaenger": [None, "REWE"],
                "Verwendungszweck": ["EDEKA Einkauf", None],
                "IBAN": [None, "DE123"],
            }
        )
        result = categorize_transactions_vectorized(
            df, is_visa=False, categories_config=sample_categories_config
        )
        # First row: None + "EDEKA Einkauf" should match Lebensmittel
        assert result.iloc[0] == "Lebensmittel"
        # Second row: "REWE" + None should match Lebensmittel
        assert result.iloc[1] == "Lebensmittel"

    def test_first_matching_rule_wins(self, sample_categories_config):
        """Test that first matching rule wins (rules are applied in order)."""
        # Add a config where description could match multiple rules
        config = {
            "rules": {
                "CategoryA": ["test"],
                "CategoryB": ["test keyword"],
            },
            "iban_rules": {},
        }
        df = pd.DataFrame(
            {
                "Zahlungsempfaenger": ["test keyword here"],
                "Verwendungszweck": [""],
                "IBAN": ["DE123"],
            }
        )
        result = categorize_transactions_vectorized(df, is_visa=False, categories_config=config)
        # "test" matches first, so CategoryA should win
        assert result.iloc[0] == "CategoryA"

    def test_special_regex_characters_escaped(self, sample_categories_config):
        """Test that special regex characters in keywords are properly escaped."""
        config = {
            "rules": {
                "Special": ["h&m", "c&a", "r+v"],
            },
            "iban_rules": {},
        }
        df = pd.DataFrame(
            {
                "Zahlungsempfaenger": ["H&M STORE", "C&A Fashion", "R+V Versicherung"],
                "Verwendungszweck": ["", "", ""],
                "IBAN": ["DE1", "DE2", "DE3"],
            }
        )
        result = categorize_transactions_vectorized(df, is_visa=False, categories_config=config)
        assert all(result == "Special")
