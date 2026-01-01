"""Tests for date and number parsing functions."""

import pytest
from datetime import datetime

from finance_dashboard.data.parser import parse_german_number, parse_german_date


class TestParseGermanNumber:
    """Tests for parse_german_number function."""

    def test_simple_positive(self):
        """Test parsing simple positive number."""
        assert parse_german_number("123,45") == 123.45

    def test_simple_negative(self):
        """Test parsing simple negative number."""
        assert parse_german_number("-123,45") == -123.45

    def test_with_thousand_separator(self):
        """Test parsing number with thousand separator."""
        assert parse_german_number("1.234,56") == 1234.56

    def test_large_number(self):
        """Test parsing large number with multiple thousand separators."""
        assert parse_german_number("1.234.567,89") == 1234567.89

    def test_negative_with_thousand_separator(self):
        """Test parsing negative number with thousand separator."""
        assert parse_german_number("-1.234,56") == -1234.56

    def test_small_decimal(self):
        """Test parsing small decimal."""
        assert parse_german_number("0,01") == 0.01

    def test_zero(self):
        """Test parsing zero."""
        assert parse_german_number("0,00") == 0.0

    def test_integer(self):
        """Test parsing integer (no decimal)."""
        assert parse_german_number("100") == 100.0

    def test_with_euro_symbol(self):
        """Test parsing number with euro symbol."""
        assert parse_german_number("€ 123,45") == 123.45
        assert parse_german_number("123,45€") == 123.45

    def test_with_spaces(self):
        """Test parsing number with spaces."""
        assert parse_german_number("  123,45  ") == 123.45
        assert parse_german_number("1 234,56") == 1234.56

    def test_empty_string(self):
        """Test parsing empty string returns 0."""
        assert parse_german_number("") == 0.0

    def test_none_value(self):
        """Test parsing None returns 0."""
        assert parse_german_number(None) == 0.0

    def test_invalid_string(self):
        """Test parsing invalid string returns 0."""
        assert parse_german_number("abc") == 0.0
        assert parse_german_number("not a number") == 0.0


class TestParseGermanDate:
    """Tests for parse_german_date function."""

    def test_short_year_format(self):
        """Test parsing date with 2-digit year."""
        result = parse_german_date("15.01.24")
        assert result == datetime(2024, 1, 15)

    def test_long_year_format(self):
        """Test parsing date with 4-digit year."""
        result = parse_german_date("15.01.2024")
        assert result == datetime(2024, 1, 15)

    def test_end_of_month(self):
        """Test parsing end of month date."""
        result = parse_german_date("31.12.24")
        assert result == datetime(2024, 12, 31)

    def test_beginning_of_year(self):
        """Test parsing beginning of year date."""
        result = parse_german_date("01.01.24")
        assert result == datetime(2024, 1, 1)

    def test_with_leading_spaces(self):
        """Test parsing date with leading/trailing spaces."""
        result = parse_german_date("  15.01.24  ")
        assert result == datetime(2024, 1, 15)

    def test_none_value(self):
        """Test parsing None returns None."""
        assert parse_german_date(None) is None

    def test_empty_string(self):
        """Test parsing empty string returns None."""
        assert parse_german_date("") is None

    def test_invalid_format(self):
        """Test parsing invalid format returns None."""
        assert parse_german_date("2024-01-15") is None
        assert parse_german_date("01/15/2024") is None
        assert parse_german_date("invalid") is None

    def test_invalid_date(self):
        """Test parsing invalid date values returns None."""
        assert parse_german_date("32.01.24") is None
        assert parse_german_date("15.13.24") is None

    def test_previous_century(self):
        """Test parsing date from previous century (2-digit year)."""
        # Note: strptime interprets 2-digit years 00-68 as 2000-2068, 69-99 as 1969-1999
        result = parse_german_date("15.01.99")
        assert result == datetime(1999, 1, 15)
