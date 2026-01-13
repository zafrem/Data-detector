"""Tests for context-aware pattern filtering."""

import pytest

from datadetector import (
    ContextHint,
    Engine,
    KeywordRegistry,
    create_context_from_field_name,
    load_registry,
)


@pytest.fixture
def engine():
    """Create engine with loaded registry."""
    registry = load_registry()
    return Engine(registry=registry)


@pytest.fixture
def keyword_registry():
    """Create keyword registry."""
    return KeywordRegistry()


class TestContextHint:
    """Tests for ContextHint data class."""

    def test_context_hint_defaults(self):
        """ContextHint should have sensible defaults."""
        hint = ContextHint()

        assert hint.keywords == []
        assert hint.categories == []
        assert hint.pattern_ids == []
        assert hint.exclude_patterns == []
        assert hint.strategy == "loose"

    def test_context_hint_with_keywords(self):
        """ContextHint should normalize keywords to lowercase."""
        hint = ContextHint(keywords=["SSN", "Bank_Account"])

        assert "ssn" in hint.keywords
        assert "bank_account" in hint.keywords

    def test_context_hint_strategies(self):
        """ContextHint should support different strategies."""
        strict = ContextHint(strategy="strict")
        loose = ContextHint(strategy="loose")
        none = ContextHint(strategy="none")

        assert strict.strategy == "strict"
        assert loose.strategy == "loose"
        assert none.strategy == "none"


class TestKeywordRegistry:
    """Tests for KeywordRegistry."""

    def test_load_keywords(self, keyword_registry):
        """Keyword registry should load keywords.yml."""
        assert len(keyword_registry.keyword_map) > 0
        assert len(keyword_registry.category_map) > 0

    def test_get_patterns_for_ssn_keyword(self, keyword_registry):
        """Should find SSN patterns for 'ssn' keyword."""
        patterns = keyword_registry.get_patterns_for_keyword("ssn")

        assert len(patterns) > 0
        assert "us/ssn_01" in patterns or "us/itin_01" in patterns

    def test_get_patterns_for_bank_keyword(self, keyword_registry):
        """Should find bank patterns for 'bank_account' keyword."""
        patterns = keyword_registry.get_patterns_for_keyword("bank_account")

        assert len(patterns) > 0
        # Should include wildcard pattern
        assert any("bank_account" in p for p in patterns)

    def test_get_patterns_partial_match(self, keyword_registry):
        """Should match keywords partially (e.g., 'user_ssn' matches 'ssn')."""
        patterns = keyword_registry.get_patterns_for_keyword("user_ssn")

        assert len(patterns) > 0
        # Should find SSN patterns
        assert any("ssn" in p or "itin" in p for p in patterns)

    def test_get_patterns_for_category(self, keyword_registry):
        """Should get patterns for a category."""
        ssn_patterns = keyword_registry.get_patterns_for_category("ssn")

        assert len(ssn_patterns) > 0
        assert "us/ssn_01" in ssn_patterns

    def test_expand_wildcards(self, keyword_registry):
        """Should expand wildcard patterns."""
        all_patterns = [
            "kr/bank_account_01",
            "kr/bank_account_02",
            "kr/bank_account_03",
            "us/ssn_01",
        ]

        wildcards = {"kr/bank_account_*"}
        expanded = keyword_registry.expand_wildcards(wildcards, all_patterns)

        # Should expand to all kr/bank_account patterns
        assert "kr/bank_account_01" in expanded
        assert "kr/bank_account_02" in expanded
        assert "kr/bank_account_03" in expanded
        # Should not include non-matching patterns
        assert "us/ssn_01" not in expanded

    def test_korean_keywords(self, keyword_registry):
        """Should support Korean keywords."""
        patterns = keyword_registry.get_patterns_for_keyword("주민등록번호")

        assert len(patterns) > 0
        assert any("rrn" in p for p in patterns)


class TestContextFiltering:
    """Tests for context filtering in Engine."""

    def test_find_with_ssn_context(self, engine):
        """Should only check SSN patterns when context specifies SSN."""
        text = "SSN: 123-45-6789, Email: user@example.com"

        context = ContextHint(keywords=["ssn"], strategy="strict")
        result = engine.find(text, context=context)

        # Should find SSN
        ssn_matches = [m for m in result.matches if "ssn" in m.ns_id.lower()]
        assert len(ssn_matches) > 0

        # Should NOT find email (not in context)
        email_matches = [m for m in result.matches if "email" in m.ns_id.lower()]
        assert len(email_matches) == 0

    def test_find_with_email_context(self, engine):
        """Should only check email patterns when context specifies email."""
        text = "SSN: 123-45-6789, Email: user@example.com"

        context = ContextHint(keywords=["email"], strategy="strict")
        result = engine.find(text, context=context)

        # Should find email
        email_matches = [m for m in result.matches if "email" in m.ns_id.lower()]
        assert len(email_matches) > 0

        # Should NOT find SSN (not in context)
        ssn_matches = [m for m in result.matches if "ssn" in m.ns_id.lower()]
        assert len(ssn_matches) == 0

    def test_find_with_category_context(self, engine):
        """Should filter by category."""
        text = "Phone: (555) 123-4567, Email: user@example.com"

        context = ContextHint(categories=["phone"], strategy="strict")
        result = engine.find(text, context=context)

        # Should find phone
        phone_matches = [m for m in result.matches if m.category.value == "phone"]
        assert len(phone_matches) > 0

        # Should NOT find email
        email_matches = [m for m in result.matches if m.category.value == "email"]
        assert len(email_matches) == 0

    def test_find_with_pattern_ids(self, engine):
        """Should use explicit pattern IDs."""
        text = "SSN: 123-45-6789, ZIP: 90210"

        context = ContextHint(pattern_ids=["us/ssn_01", "us/zipcode_01"], strategy="strict")
        result = engine.find(text, context=context)

        # Should find both
        assert len(result.matches) >= 2

        # All matches should be from specified patterns
        for match in result.matches:
            assert match.ns_id in ["us/ssn_01", "us/zipcode_01"]

    def test_find_with_exclude_patterns(self, engine):
        """Should exclude specified patterns."""
        text = "SSN: 123-45-6789, ITIN: 900-12-3456"

        context = ContextHint(
            categories=["ssn"], exclude_patterns=["us/itin_01"], strategy="strict"
        )
        result = engine.find(text, context=context)

        # Should NOT find ITIN (excluded)
        itin_matches = [m for m in result.matches if m.ns_id == "us/itin_01"]
        assert len(itin_matches) == 0

    def test_find_loose_strategy_fallback(self, engine):
        """Loose strategy should fall back to all patterns if no matches."""
        text = "Some random text: 123-45-6789"

        # Use non-existent keyword
        context = ContextHint(keywords=["nonexistent_keyword"], strategy="loose")
        result = engine.find(text, context=context)

        # Should still find SSN (fallback to all patterns)
        assert len(result.matches) > 0

    def test_find_strict_strategy_no_fallback(self, engine):
        """Strict strategy should NOT fall back if no keyword matches."""
        text = "SSN: 123-45-6789"

        # Use email keyword but text has SSN
        context = ContextHint(keywords=["email"], strategy="strict")
        result = engine.find(text, context=context)

        # Should NOT find SSN (strict mode, no fallback)
        ssn_matches = [m for m in result.matches if "ssn" in m.ns_id.lower()]
        assert len(ssn_matches) == 0

    def test_find_none_strategy(self, engine):
        """None strategy should check all patterns."""
        text = "SSN: 123-45-6789, Email: user@example.com"

        context = ContextHint(keywords=["ssn"], strategy="none")
        result = engine.find(text, context=context)

        # Should find both SSN and email (strategy='none' means check all)
        assert len(result.matches) >= 2

    def test_redact_with_context(self, engine):
        """Redaction should work with context filtering."""
        text = "SSN: 123-45-6789, Email: user@example.com"

        context = ContextHint(keywords=["ssn"], strategy="strict")
        result = engine.redact(text, context=context)

        # Should redact SSN
        assert "***-**-****" in result.redacted_text or "*" in result.redacted_text
        # Should NOT redact email
        assert "user@example.com" in result.redacted_text

    def test_wildcard_pattern_matching(self, engine):
        """Should expand wildcard patterns."""
        text = "Bank: 123-456789-01234"

        context = ContextHint(pattern_ids=["kr/bank_account_*"], strategy="strict")
        result = engine.find(text, context=context)

        # Should find bank account
        bank_matches = [m for m in result.matches if "bank_account" in m.ns_id]
        assert len(bank_matches) > 0


class TestCreateContextFromFieldName:
    """Tests for create_context_from_field_name helper."""

    def test_create_from_ssn_field(self):
        """Should extract 'ssn' from 'user_ssn'."""
        context = create_context_from_field_name("user_ssn")

        assert "ssn" in context.keywords
        assert context.strategy == "loose"

    def test_create_from_complex_field_name(self):
        """Should extract multiple keywords from complex field name."""
        context = create_context_from_field_name("billing_address_zip_code")

        assert "billing" in context.keywords
        assert "address" in context.keywords
        assert "zip" in context.keywords
        assert "code" in context.keywords

    def test_create_with_strategy(self):
        """Should respect strategy parameter."""
        context = create_context_from_field_name("user_ssn", strategy="strict")

        assert context.strategy == "strict"

    def test_create_filters_short_keywords(self):
        """Should filter out single-character keywords."""
        context = create_context_from_field_name("a_ssn_b")

        # Should only include 'ssn', not 'a' or 'b'
        assert "ssn" in context.keywords
        assert "a" not in context.keywords
        assert "b" not in context.keywords


class TestPerformanceWithContext:
    """Tests to verify performance improvements with context filtering."""

    def test_fewer_patterns_checked(self, engine):
        """Context filtering should reduce number of patterns checked."""
        text = "SSN: 123-45-6789"

        # Without context - checks all patterns
        result_no_context = engine.find(text)

        # With context - checks only SSN patterns
        context = ContextHint(keywords=["ssn"], strategy="strict")
        result_with_context = engine.find(text, context=context)

        # Both should find the SSN
        assert len(result_no_context.matches) > 0
        assert len(result_with_context.matches) > 0

        # Same result, but context filtering checked fewer patterns
        # (We can't directly verify this without instrumenting the code,
        # but we can verify the results are correct)
        assert result_no_context.matches[0].ns_id == result_with_context.matches[0].ns_id


class TestKoreanContextFiltering:
    """Tests for Korean patterns with context filtering."""

    def test_korean_rrn_with_context(self, engine):
        """Should find Korean RRN with Korean keyword."""
        # Use valid RRN from pattern examples (990101-1234567 fails verification)
        text = "주민등록번호: 900101-1234568"

        context = ContextHint(keywords=["주민등록번호"], strategy="strict")
        result = engine.find(text, context=context)

        rrn_matches = [m for m in result.matches if "rrn" in m.ns_id or "corporate" in m.ns_id]
        assert len(rrn_matches) > 0

    def test_korean_bank_account_with_context(self, engine):
        """Should find Korean bank account with Korean keyword."""
        text = "계좌번호: 123-456789-01234"

        context = ContextHint(keywords=["계좌번호"], strategy="strict")
        result = engine.find(text, context=context)

        bank_matches = [m for m in result.matches if "bank_account" in m.ns_id]
        assert len(bank_matches) > 0

    def test_korean_zipcode_with_context(self, engine):
        """Should find Korean zipcode with Korean keyword."""
        text = "우편번호: 06234"

        context = ContextHint(keywords=["우편번호"], strategy="strict")
        result = engine.find(text, context=context)

        zip_matches = [m for m in result.matches if "zipcode" in m.ns_id.lower()]
        assert len(zip_matches) > 0


class TestDisableContextFiltering:
    """Tests for disabling context filtering."""

    def test_engine_with_context_filtering_disabled(self):
        """Engine should work with context filtering disabled."""
        registry = load_registry()
        engine = Engine(registry=registry, enable_context_filtering=False)

        text = "SSN: 123-45-6789"

        # Context should be ignored when feature is disabled
        context = ContextHint(keywords=["email"], strategy="strict")
        result = engine.find(text, context=context)

        # Should still find SSN (context filtering disabled)
        ssn_matches = [m for m in result.matches if "ssn" in m.ns_id.lower()]
        assert len(ssn_matches) > 0
