"""Tests for override key generation functions."""

from datetime import datetime

import pandas as pd

from finance_dashboard.categorization.overrides import get_legacy_override_key, get_override_key


class TestGetOverrideKey:
    """Tests for the new hash-based override key function."""

    def test_basic_key_generation(self):
        """Test basic key generation."""
        row = pd.Series(
            {
                "Datum": datetime(2024, 1, 15),
                "Beschreibung": "REWE SAGT DANKE",
                "Betrag": -45.99,
            }
        )
        key = get_override_key(row)
        # Should be format: date_hash_amount
        assert key.startswith("2024-01-15_")
        assert key.endswith("_-45.99")
        # Hash should be 12 characters
        parts = key.split("_")
        assert len(parts) == 3
        assert len(parts[1]) == 12

    def test_same_input_same_key(self):
        """Test that same input produces same key (deterministic)."""
        row = pd.Series(
            {
                "Datum": datetime(2024, 1, 15),
                "Beschreibung": "Test Description",
                "Betrag": 100.00,
            }
        )
        key1 = get_override_key(row)
        key2 = get_override_key(row)
        assert key1 == key2

    def test_different_descriptions_different_keys(self):
        """Test that different descriptions produce different keys."""
        row1 = pd.Series(
            {
                "Datum": datetime(2024, 1, 15),
                "Beschreibung": "Description A",
                "Betrag": 100.00,
            }
        )
        row2 = pd.Series(
            {
                "Datum": datetime(2024, 1, 15),
                "Beschreibung": "Description B",
                "Betrag": 100.00,
            }
        )
        assert get_override_key(row1) != get_override_key(row2)

    def test_long_description_handled(self):
        """Test that long descriptions are handled (hashed, not truncated)."""
        short_desc = "Short"
        long_desc = "A" * 1000  # Very long description

        row_short = pd.Series(
            {
                "Datum": datetime(2024, 1, 15),
                "Beschreibung": short_desc,
                "Betrag": 100.00,
            }
        )
        row_long = pd.Series(
            {
                "Datum": datetime(2024, 1, 15),
                "Beschreibung": long_desc,
                "Betrag": 100.00,
            }
        )

        key_short = get_override_key(row_short)
        key_long = get_override_key(row_long)

        # Both should have same format length (hash is fixed size)
        assert len(key_short.split("_")[1]) == len(key_long.split("_")[1]) == 12

    def test_null_date_handled(self):
        """Test handling of null date."""
        row = pd.Series(
            {
                "Datum": None,
                "Beschreibung": "Test",
                "Betrag": 100.00,
            }
        )
        key = get_override_key(row)
        assert key.startswith("unknown_")

    def test_missing_description_handled(self):
        """Test handling of missing description."""
        row = pd.Series(
            {
                "Datum": datetime(2024, 1, 15),
                "Betrag": 100.00,
            }
        )
        # Should not raise error
        key = get_override_key(row)
        assert "2024-01-15" in key

    def test_missing_betrag_handled(self):
        """Test handling of missing Betrag."""
        row = pd.Series(
            {
                "Datum": datetime(2024, 1, 15),
                "Beschreibung": "Test",
            }
        )
        key = get_override_key(row)
        assert key.endswith("_0.00")

    def test_amount_formatting(self):
        """Test that amounts are formatted consistently."""
        row = pd.Series(
            {
                "Datum": datetime(2024, 1, 15),
                "Beschreibung": "Test",
                "Betrag": 100,  # Integer
            }
        )
        key = get_override_key(row)
        assert key.endswith("_100.00")


class TestGetLegacyOverrideKey:
    """Tests for the legacy (truncated) override key function."""

    def test_basic_key_generation(self):
        """Test basic legacy key generation."""
        row = pd.Series(
            {
                "Datum": datetime(2024, 1, 15),
                "Beschreibung": "REWE SAGT DANKE",
                "Betrag": -45.99,
            }
        )
        key = get_legacy_override_key(row)
        assert key == "2024-01-15_REWE SAGT DANKE_-45.99"

    def test_description_truncated_to_30_chars(self):
        """Test that description is truncated to 30 characters."""
        long_desc = "A" * 50
        row = pd.Series(
            {
                "Datum": datetime(2024, 1, 15),
                "Beschreibung": long_desc,
                "Betrag": 100.00,
            }
        )
        key = get_legacy_override_key(row)
        # Description part should be 30 chars
        parts = key.split("_")
        assert len(parts[1]) == 30

    def test_slashes_replaced(self):
        """Test that slashes are replaced with dashes."""
        row = pd.Series(
            {
                "Datum": datetime(2024, 1, 15),
                "Beschreibung": "Test/With/Slashes",
                "Betrag": 100.00,
            }
        )
        key = get_legacy_override_key(row)
        assert "/" not in key
        assert "Test-With-Slashes" in key

    def test_null_date_handled(self):
        """Test handling of null date."""
        row = pd.Series(
            {
                "Datum": None,
                "Beschreibung": "Test",
                "Betrag": 100.00,
            }
        )
        key = get_legacy_override_key(row)
        assert key.startswith("unknown_")


class TestKeyCompatibility:
    """Tests for compatibility between new and legacy keys."""

    def test_new_key_different_from_legacy(self):
        """Test that new keys are different from legacy keys."""
        row = pd.Series(
            {
                "Datum": datetime(2024, 1, 15),
                "Beschreibung": "REWE SAGT DANKE",
                "Betrag": -45.99,
            }
        )
        new_key = get_override_key(row)
        legacy_key = get_legacy_override_key(row)
        assert new_key != legacy_key

    def test_both_keys_stable(self):
        """Test that both key functions produce stable results."""
        row = pd.Series(
            {
                "Datum": datetime(2024, 1, 15),
                "Beschreibung": "Test Transaction",
                "Betrag": 50.00,
            }
        )

        # Generate keys multiple times
        new_keys = [get_override_key(row) for _ in range(5)]
        legacy_keys = [get_legacy_override_key(row) for _ in range(5)]

        # All should be identical
        assert len(set(new_keys)) == 1
        assert len(set(legacy_keys)) == 1

    def test_collision_scenario_avoided(self):
        """Test that the new key avoids collisions that legacy key would have."""
        # Two transactions with same first 30 chars but different full descriptions
        desc1 = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAX"  # 31 chars, ends with X
        desc2 = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAY"  # 31 chars, ends with Y

        row1 = pd.Series(
            {
                "Datum": datetime(2024, 1, 15),
                "Beschreibung": desc1,
                "Betrag": 100.00,
            }
        )
        row2 = pd.Series(
            {
                "Datum": datetime(2024, 1, 15),
                "Beschreibung": desc2,
                "Betrag": 100.00,
            }
        )

        # Legacy keys would be the same (truncated to 30 chars)
        legacy_key1 = get_legacy_override_key(row1)
        legacy_key2 = get_legacy_override_key(row2)
        assert legacy_key1 == legacy_key2  # Collision!

        # New keys should be different (uses hash of full description)
        new_key1 = get_override_key(row1)
        new_key2 = get_override_key(row2)
        assert new_key1 != new_key2  # No collision!
