"""Tests for regex_compat module."""

import pytest

from datadetector import regex_compat


class TestCompile:
    """Tests for compile function."""

    def test_compile_simple_pattern(self) -> None:
        """Test compiling a simple pattern."""
        pattern = regex_compat.compile(r"\d{3}-\d{4}")
        assert pattern is not None
        assert pattern.pattern == r"\d{3}-\d{4}"

    def test_compile_with_pattern_id(self) -> None:
        """Test compiling with pattern_id."""
        pattern = regex_compat.compile(r"\d+", pattern_id="test/digits")
        assert pattern.pattern_id == "test/digits"

    def test_compile_invalid_pattern_raises(self) -> None:
        """Test that invalid patterns raise error."""
        with pytest.raises(regex_compat.error):
            regex_compat.compile(r"[")

    def test_compile_lookahead_raises(self) -> None:
        """Test that lookaheads are not supported."""
        with pytest.raises(regex_compat.error):
            regex_compat.compile(r"(?=\d)\d+")

    def test_compile_lookbehind_raises(self) -> None:
        """Test that lookbehinds are not supported."""
        with pytest.raises(regex_compat.error):
            regex_compat.compile(r"(?<=\d)\d+")


class TestFullmatch:
    """Tests for fullmatch emulation."""

    def test_fullmatch_exact(self) -> None:
        """Test fullmatch with exact match."""
        pattern = regex_compat.compile(r"\d{5}")
        assert pattern.fullmatch("12345") is not None

    def test_fullmatch_no_match_shorter(self) -> None:
        """Test fullmatch with shorter input."""
        pattern = regex_compat.compile(r"\d{5}")
        assert pattern.fullmatch("1234") is None

    def test_fullmatch_no_match_longer(self) -> None:
        """Test fullmatch with longer input."""
        pattern = regex_compat.compile(r"\d{5}")
        assert pattern.fullmatch("123456") is None

    def test_fullmatch_no_match_with_prefix(self) -> None:
        """Test fullmatch with prefix."""
        pattern = regex_compat.compile(r"\d{5}")
        assert pattern.fullmatch("a12345") is None

    def test_fullmatch_no_match_with_suffix(self) -> None:
        """Test fullmatch with suffix."""
        pattern = regex_compat.compile(r"\d{5}")
        assert pattern.fullmatch("12345a") is None

    def test_fullmatch_with_alternation(self) -> None:
        """Test fullmatch with alternation pattern."""
        pattern = regex_compat.compile(r"a|b")
        assert pattern.fullmatch("a") is not None
        assert pattern.fullmatch("b") is not None
        assert pattern.fullmatch("ab") is None


class TestSearch:
    """Tests for search method."""

    def test_search_finds_match(self) -> None:
        """Test search finds match in string."""
        pattern = regex_compat.compile(r"\d{3}")
        match = pattern.search("abc123def")
        assert match is not None
        assert match.group() == "123"

    def test_search_no_match(self) -> None:
        """Test search returns None when no match."""
        pattern = regex_compat.compile(r"\d{3}")
        assert pattern.search("abcdef") is None


class TestMatch:
    """Tests for match method."""

    def test_match_at_start(self) -> None:
        """Test match at start of string."""
        pattern = regex_compat.compile(r"\d{3}")
        match = pattern.match("123abc")
        assert match is not None
        assert match.group() == "123"

    def test_match_not_at_start(self) -> None:
        """Test match fails when pattern not at start."""
        pattern = regex_compat.compile(r"\d{3}")
        assert pattern.match("abc123") is None


class TestFinditer:
    """Tests for finditer method."""

    def test_finditer_multiple_matches(self) -> None:
        """Test finditer finds all matches."""
        pattern = regex_compat.compile(r"\d+")
        matches = list(pattern.finditer("a1b23c456"))
        assert len(matches) == 3
        assert [m.group() for m in matches] == ["1", "23", "456"]

    def test_finditer_no_matches(self) -> None:
        """Test finditer with no matches."""
        pattern = regex_compat.compile(r"\d+")
        matches = list(pattern.finditer("abcdef"))
        assert matches == []


class TestFindall:
    """Tests for findall method."""

    def test_findall_multiple_matches(self) -> None:
        """Test findall returns all matches."""
        pattern = regex_compat.compile(r"\d+")
        matches = pattern.findall("a1b23c456")
        assert matches == ["1", "23", "456"]


class TestSub:
    """Tests for sub method."""

    def test_sub_replaces_all(self) -> None:
        """Test sub replaces all matches."""
        pattern = regex_compat.compile(r"\d+")
        result = pattern.sub("X", "a1b23c456")
        assert result == "aXbXcX"

    def test_sub_with_count(self) -> None:
        """Test sub with count limit."""
        pattern = regex_compat.compile(r"\d+")
        result = pattern.sub("X", "a1b23c456", count=2)
        assert result == "aXbXc456"


class TestSplit:
    """Tests for split method."""

    def test_split_by_pattern(self) -> None:
        """Test split by pattern."""
        pattern = regex_compat.compile(r"[,;]+")
        result = pattern.split("a,b;c,,d")
        assert result == ["a", "b", "c", "d"]


class TestFlags:
    """Tests for flag handling."""

    def test_ignorecase_flag(self) -> None:
        """Test IGNORECASE flag."""
        pattern = regex_compat.compile(r"test", flags=regex_compat.IGNORECASE)
        assert pattern.search("TEST") is not None
        assert pattern.search("TeSt") is not None

    def test_multiline_flag(self) -> None:
        """Test MULTILINE flag."""
        pattern = regex_compat.compile(r"^test", flags=regex_compat.MULTILINE)
        assert pattern.search("line1\ntest") is not None

    def test_dotall_flag(self) -> None:
        """Test DOTALL flag."""
        pattern = regex_compat.compile(r"a.b", flags=regex_compat.DOTALL)
        assert pattern.search("a\nb") is not None


class TestConvertFlags:
    """Tests for convert_flags function."""

    def test_convert_ignorecase(self) -> None:
        """Test converting IGNORECASE flag."""
        flags = regex_compat.convert_flags(["IGNORECASE"])
        assert flags == regex_compat.IGNORECASE

    def test_convert_multiline(self) -> None:
        """Test converting MULTILINE flag."""
        flags = regex_compat.convert_flags(["MULTILINE"])
        assert flags == regex_compat.MULTILINE

    def test_convert_dotall(self) -> None:
        """Test converting DOTALL flag."""
        flags = regex_compat.convert_flags(["DOTALL"])
        assert flags == regex_compat.DOTALL

    def test_convert_unicode_is_noop(self) -> None:
        """Test UNICODE flag is ignored (RE2 is always Unicode)."""
        flags = regex_compat.convert_flags(["UNICODE"])
        assert flags == 0

    def test_convert_multiple_flags(self) -> None:
        """Test converting multiple flags."""
        flags = regex_compat.convert_flags(["IGNORECASE", "MULTILINE"])
        assert flags == (regex_compat.IGNORECASE | regex_compat.MULTILINE)

    def test_convert_empty_list(self) -> None:
        """Test converting empty flag list."""
        flags = regex_compat.convert_flags([])
        assert flags == 0


class TestCompiledPatternRepr:
    """Tests for CompiledPattern __repr__."""

    def test_repr(self) -> None:
        """Test string representation."""
        pattern = regex_compat.compile(r"\d+", flags=regex_compat.IGNORECASE)
        repr_str = repr(pattern)
        assert "CompiledPattern" in repr_str
        assert r"\d+" in repr_str
