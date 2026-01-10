"""Tests to verify zip codes correctly reject alphanumeric strings."""

import pytest

from datadetector import load_registry
from datadetector.engine import Engine


@pytest.fixture
def engine():
    """Create engine with loaded registry."""
    registry = load_registry()
    return Engine(registry=registry)


class TestZipcodeAlphanumericRejection:
    """Tests to ensure zip codes don't match when embedded in alphanumeric strings."""

    def test_zipcode_not_in_product_codes(self, engine):
        """Zip codes should not match product codes with alphanumeric characters."""
        product_codes = [
            "MODEL12345",
            "MODEL12345A",
            "ABC12345",
            "SKU90210X",
        ]

        for code in product_codes:
            result = engine.find(code)
            zipcode_matches = [m for m in result.matches if "zipcode" in m.ns_id.lower()]
            assert len(zipcode_matches) == 0, f"Product code '{code}' should NOT match as zipcode"

    def test_zipcode_not_in_serial_numbers(self, engine):
        """Zip codes should not match serial numbers."""
        serial_numbers = [
            "SN12345END",
            "SN90210DEVICE",
            "SERIAL12345A",
        ]

        for serial in serial_numbers:
            result = engine.find(serial)
            zipcode_matches = [m for m in result.matches if "zipcode" in m.ns_id.lower()]
            assert (
                len(zipcode_matches) == 0
            ), f"Serial number '{serial}' should NOT match as zipcode"

    def test_zipcode_not_with_letter_prefix(self, engine):
        """Zip codes should not match when preceded by letters without separator."""
        test_cases = [
            "ABC12345",
            "ZIP12345",  # Even if it says "ZIP", without separator it's not valid
            "POSTAL90210",
        ]

        for text in test_cases:
            result = engine.find(text)
            zipcode_matches = [m for m in result.matches if "zipcode" in m.ns_id.lower()]
            assert (
                len(zipcode_matches) == 0
            ), f"'{text}' should NOT match as zipcode (letter prefix)"

    def test_zipcode_not_with_letter_suffix(self, engine):
        """Zip codes should not match when followed by letters without separator."""
        test_cases = [
            "12345ABC",
            "12345X",
            "90210CITY",
        ]

        for text in test_cases:
            result = engine.find(text)
            zipcode_matches = [m for m in result.matches if "zipcode" in m.ns_id.lower()]
            assert (
                len(zipcode_matches) == 0
            ), f"'{text}' should NOT match as zipcode (letter suffix)"

    def test_zipcode_valid_with_separators(self, engine):
        """Zip codes should match when separated by non-alphanumeric characters."""
        valid_cases = [
            ("Address: 90210", "90210"),
            ("ZIP: 06234", "06234"),  # Not sequential, will pass verification
            ("ZIP-CODE: 48058", "48058"),
            ("Postal: 48058", "48058"),
            ("(90210)", "90210"),
            ("90210-1234", "90210"),  # ZIP+4 format
        ]

        for text, expected_zip in valid_cases:
            result = engine.find(text)
            zipcode_matches = [m for m in result.matches if "zipcode" in m.ns_id.lower()]
            assert len(zipcode_matches) > 0, f"'{text}' should match zipcode '{expected_zip}'"

    def test_zipcode_standalone(self, engine):
        """Standalone zip codes should match."""
        valid_zipcodes = [
            "90210",
            "06234",
            "48058",
            "63309",
        ]

        for zipcode in valid_zipcodes:
            result = engine.find(zipcode)
            zipcode_matches = [m for m in result.matches if "zipcode" in m.ns_id.lower()]
            assert len(zipcode_matches) > 0, f"Standalone zipcode '{zipcode}' should match"

    def test_regex_pattern_correctness(self, engine):
        """Verify the regex pattern uses word boundaries for alphanumeric rejection.

        Note: RE2 doesn't support lookbehind/lookahead assertions, so patterns use
        \\b word boundaries instead of (?<![A-Za-z0-9]) and (?![A-Za-z0-9]).
        """
        from datadetector import load_registry

        registry = load_registry()

        # Check Korean zipcode pattern
        kr_zipcode = registry.get_pattern("kr/zipcode_01")
        assert kr_zipcode is not None
        # RE2-compatible patterns use \b word boundaries instead of lookbehind/lookahead
        assert (
            r"\b" in kr_zipcode.pattern or "(?<![A-Za-z0-9])" in kr_zipcode.pattern
        ), "Korean zipcode should have word boundary or lookbehind for alphanumeric prefix"

        # Check US zipcode pattern
        us_zipcode = registry.get_pattern("us/zipcode_01")
        assert us_zipcode is not None
        assert (
            r"\b" in us_zipcode.pattern or "(?<![A-Za-z0-9])" in us_zipcode.pattern
        ), "US zipcode should have word boundary or lookbehind for alphanumeric prefix"
