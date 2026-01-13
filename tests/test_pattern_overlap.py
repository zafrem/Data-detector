"""Tests for pattern overlap issues."""

import pytest

from datadetector import load_registry
from datadetector.engine import Engine


@pytest.fixture
def engine():
    """Create engine with loaded registry."""
    registry = load_registry()
    return Engine(registry=registry)


class TestBankAccountOverlap:
    """Tests to ensure bank accounts don't overlap with other patterns."""

    def test_daegu_bank_not_business_reg(self, engine):
        """Daegu Bank (12 digits) should not match Business Registration (10 digits)."""
        # Daegu Bank: XXX-XX-XXXXXX-X (12 digits)
        test_cases = [
            "123-45-678901-2",
            "999-88-123456-7",
        ]

        for account in test_cases:
            result = engine.find(account)
            matches = result.matches

            # Should match bank account
            bank_matches = [m for m in matches if m.ns_id == "kr/bank_account_10"]
            assert len(bank_matches) > 0, f"{account} should match Daegu Bank"

            # Should NOT match business registration
            biz_matches = [m for m in matches if m.ns_id == "kr/business_registration_01"]
            assert (
                len(biz_matches) == 0
            ), f"{account} should NOT match business registration (has extra digit)"

    def test_gwangju_bank_not_ssn(self, engine):
        """Gwangju Bank (12 digits) should not match US SSN (9 digits)."""
        # Gwangju Bank: XXX-XXX-XXXXXX (12 digits)
        test_cases = [
            "123-456-789012",
            "999-123-456789",
        ]

        for account in test_cases:
            result = engine.find(account)
            matches = result.matches

            # Should match bank account
            bank_matches = [m for m in matches if m.ns_id == "kr/bank_account_11"]
            assert len(bank_matches) > 0, f"{account} should match Gwangju Bank"

            # Should NOT match SSN
            ssn_matches = [m for m in matches if m.ns_id == "us/ssn_01"]
            assert len(ssn_matches) == 0, f"{account} should NOT match US SSN (different format)"

    def test_jeonbuk_bank_not_business_reg(self, engine):
        """Jeonbuk Bank (11 digits) should not match Business Registration (10 digits)."""
        # Jeonbuk Bank: XXX-XX-XXXXXX (11 digits)
        # Note: bank_account_07 (SC First Bank) and bank_account_12 (Jeonbuk Bank)
        # have identical patterns, so either may match. Both are valid 11-digit bank accounts.
        test_cases = [
            "123-45-678901",
            "999-88-123456",
        ]

        for account in test_cases:
            result = engine.find(account)
            matches = result.matches

            # Should match one of the 11-digit bank account patterns
            bank_matches = [
                m for m in matches if m.ns_id in ["kr/bank_account_07", "kr/bank_account_12"]
            ]
            assert len(bank_matches) > 0, f"{account} should match an 11-digit bank account pattern"

            # Should NOT match business registration (only 10 digits)
            biz_matches = [m for m in matches if m.ns_id == "kr/business_registration_01"]
            assert (
                len(biz_matches) == 0
            ), f"{account} should NOT match business registration (has extra digit)"

    def test_jeju_bank_vs_driver_license(self, engine):
        """Jeju Bank and Driver License have same format.

        Should be distinguished by priority/context.
        """
        # Both are XX-XXXXXX-XX (10 digits)
        # This is a genuine ambiguity - we need to rely on priority

        test_case = "89-876543-21"
        result = engine.find(test_case)
        matches = result.matches

        # Should match at least one
        jeju_matches = [m for m in matches if m.ns_id == "kr/bank_account_13"]
        license_matches = [m for m in matches if m.ns_id == "kr/driver_license_01"]

        # Since they're identical formats, both might match - that's acceptable
        # But we should document this ambiguity
        total_matches = len(jeju_matches) + len(license_matches)
        assert total_matches > 0, f"{test_case} should match either Jeju Bank or Driver License"


class TestBusinessRegistrationTight:
    """Tests for tighter business registration pattern."""

    def test_business_reg_exact_length(self, engine):
        """Business registration should match exactly 10 digits with hyphens."""
        # Should match (with hyphens) - use valid numbers that pass checksum verification
        valid = ["123-81-00995", "220-81-04569"]
        for num in valid:
            result = engine.find(num)
            matches = [m for m in result.matches if m.ns_id == "kr/business_registration_01"]
            assert len(matches) > 0, f"Business registration should match {num}"

        # Should NOT match
        invalid = [
            "1234567890",  # No hyphens (ambiguous - could be driver license)
            "123-45-678901",  # 11 digits (bank account)
            "123-45-678901-2",  # 12 digits (bank account)
        ]
        for num in invalid:
            result = engine.find(num)
            matches = [m for m in result.matches if m.ns_id == "kr/business_registration_01"]
            assert len(matches) == 0, f"Business registration should NOT match {num}"


class TestDriverLicenseTight:
    """Tests for tighter driver license pattern."""

    def test_driver_license_exact_length(self, engine):
        """Driver license should match exactly 10 digits with hyphens."""
        # Should match (with hyphens)
        valid = ["12-345678-90"]
        for num in valid:
            result = engine.find(num)
            matches = [m for m in result.matches if m.ns_id == "kr/driver_license_01"]
            assert len(matches) > 0, f"Driver license should match {num}"

        # Should NOT match
        invalid = [
            "1234567890",  # No hyphens (ambiguous - could be business reg)
            "123-456789-01",  # Different format (11 digits - bank account)
        ]
        for num in invalid:
            result = engine.find(num)
            matches = [m for m in result.matches if m.ns_id == "kr/driver_license_01"]
            assert len(matches) == 0, f"Driver license should NOT match {num}"
