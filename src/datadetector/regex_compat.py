"""RE2-based regex compatibility layer.

This module provides a unified interface for regex operations using google-re2
when available, with automatic fallback to Python's standard re module.

RE2 guarantees linear-time matching, preventing ReDoS attacks. When RE2 is not
available, the standard re module is used (which may be vulnerable to ReDoS
with certain patterns).

Note: RE2's \\b (word boundary) only works with ASCII word characters. For Unicode
patterns (Korean, Chinese, Japanese, etc.), \\b is automatically removed as these
languages use whitespace boundaries naturally.
"""

from __future__ import annotations

import logging
import re as std_re
from enum import Enum
from typing import Iterator, List, Optional, Union

logger = logging.getLogger(__name__)


class RegexEngine(Enum):
    """Regex engine selection mode."""

    AUTO = "auto"  # Use RE2 if available, fallback to standard re
    RE2 = "re2"  # Force RE2 (error if unavailable)
    STANDARD = "standard"  # Force standard re module

# Try to import google-re2, fall back to standard re if unavailable
try:
    import re2

    HAS_RE2 = True
    logger.debug("Using google-re2 for regex operations (ReDoS-safe)")
except ImportError:
    re2 = None
    HAS_RE2 = False
    logger.info(
        "google-re2 not available, using standard re module. "
        "Install google-re2 for ReDoS protection: pip install google-re2"
    )

# Module-level engine preference (default: AUTO)
_engine_preference: RegexEngine = RegexEngine.AUTO


def set_engine(engine: RegexEngine) -> None:
    """
    Set the preferred regex engine.

    Args:
        engine: RegexEngine.AUTO (default), RegexEngine.RE2, or RegexEngine.STANDARD

    Raises:
        ValueError: If RE2 is requested but not available

    Example:
        >>> from datadetector.regex_compat import set_engine, RegexEngine
        >>> set_engine(RegexEngine.STANDARD)  # Force standard re for small texts
        >>> set_engine(RegexEngine.RE2)       # Force RE2 for large texts
        >>> set_engine(RegexEngine.AUTO)      # Use RE2 if available (default)
    """
    global _engine_preference
    if engine == RegexEngine.RE2 and not HAS_RE2:
        raise ValueError(
            "RE2 engine requested but google-re2 is not installed. "
            "Install it with: pip install google-re2"
        )
    _engine_preference = engine
    logger.info(f"Regex engine preference set to: {engine.value}")


def get_engine() -> RegexEngine:
    """
    Get the current regex engine preference.

    Returns:
        Current RegexEngine setting
    """
    return _engine_preference


def _should_use_re2() -> bool:
    """Determine if RE2 should be used based on preference and availability."""
    if _engine_preference == RegexEngine.STANDARD:
        return False
    if _engine_preference == RegexEngine.RE2:
        return True  # Already validated in set_engine
    # AUTO mode
    return HAS_RE2

# Flag constants (same values as standard re module for compatibility)
IGNORECASE = 2  # re.IGNORECASE
MULTILINE = 8  # re.MULTILINE
DOTALL = 16  # re.DOTALL

# Unicode ranges for CJK characters (used to detect when \b needs transformation)
_CJK_RANGES = [
    (0x4E00, 0x9FFF),  # CJK Unified Ideographs
    (0x3400, 0x4DBF),  # CJK Unified Ideographs Extension A
    (0xAC00, 0xD7AF),  # Hangul Syllables (Korean)
    (0x3040, 0x309F),  # Hiragana (Japanese)
    (0x30A0, 0x30FF),  # Katakana (Japanese)
    (0x1100, 0x11FF),  # Hangul Jamo
    (0x3130, 0x318F),  # Hangul Compatibility Jamo
]


def _convert_unicode_escapes(pattern: str) -> str:
    """
    Convert Python-style Unicode escapes to actual characters.

    RE2 doesn't support \\uXXXX syntax. Convert to actual Unicode characters
    or RE2's \\x{XXXX} syntax.

    Args:
        pattern: Pattern potentially containing \\uXXXX escapes

    Returns:
        Pattern with Unicode escapes converted
    """
    # Convert \uXXXX to actual Unicode characters
    # Use regex to find all \uXXXX patterns and replace them
    result = []
    i = 0
    while i < len(pattern):
        # Check if we have enough characters for \uXXXX (need at least 6 more including current)
        if i + 6 <= len(pattern) and pattern[i : i + 2] == "\\u":
            # Check if next 4 chars are hex
            hex_part = pattern[i + 2 : i + 6]
            if len(hex_part) == 4 and all(c in "0123456789abcdefABCDEF" for c in hex_part):
                # Convert to actual character
                char = chr(int(hex_part, 16))
                result.append(char)
                i += 6
                continue
        result.append(pattern[i])
        i += 1

    return "".join(result)


def _has_unicode_char_class(pattern: str) -> bool:
    """Check if pattern contains Unicode character classes that need \b transformation."""
    # Look for character ranges that include CJK characters
    # Pattern like [가-힣] or [一-龯] or Unicode property escapes

    # Check for Hangul range (as literal strings)
    if "가-힣" in pattern or "ㄱ-ㅎ" in pattern or "ㅏ-ㅣ" in pattern:
        return True

    # Check for CJK Ideographs range (as literal strings)
    if "一-龯" in pattern or "一-龥" in pattern:
        return True

    # Check for Japanese Hiragana/Katakana (as literal strings)
    if "ぁ-ん" in pattern or "ァ-ン" in pattern:
        return True

    # Check for Unicode property escapes for CJK
    if r"\p{Han}" in pattern or r"\p{Hangul}" in pattern:
        return True
    if r"\p{Hiragana}" in pattern or r"\p{Katakana}" in pattern:
        return True

    # Check for \uXXXX escapes in CJK ranges
    # Common CJK ranges: 4e00-9fff (Han), ac00-d7af (Hangul), 3040-30ff (Japanese)
    if r"\u" in pattern:
        # If pattern contains \u escapes, likely Unicode - check for CJK
        return True

    # Check for actual CJK characters in the pattern (after \uXXXX conversion)
    for char in pattern:
        code = ord(char)
        # Check CJK ranges
        for start, end in _CJK_RANGES:
            if start <= code <= end:
                return True

    return False


def _transform_word_boundaries(pattern: str) -> str:
    """
    Transform \\b word boundaries for Unicode compatibility.

    RE2's \\b only works with ASCII word characters. For patterns containing
    CJK character classes, we remove \\b since CJK languages use whitespace
    as natural word boundaries.

    Args:
        pattern: Original regex pattern

    Returns:
        Transformed pattern with \\b handled appropriately
    """
    if r"\b" not in pattern:
        return pattern

    if not _has_unicode_char_class(pattern):
        # Pattern only uses ASCII, \b works fine
        return pattern

    # For Unicode patterns, remove \b as CJK uses whitespace boundaries
    # This is safe because:
    # 1. CJK text naturally has spaces between semantic units
    # 2. The character class ranges already limit what can match
    transformed = pattern.replace(r"\b", "")

    logger.debug(f"Transformed pattern for Unicode compatibility: {pattern!r} -> {transformed!r}")

    return transformed


def _create_options(flags: int = 0, using_re2: bool = True) -> "Optional[re2.Options]":
    """Create re2.Options from flag bitmask (RE2 only)."""
    if not using_re2 or not HAS_RE2:
        return None
    options = re2.Options()
    if flags & IGNORECASE:
        options.case_sensitive = False
    if flags & DOTALL:
        options.dot_nl = True
    # Note: MULTILINE is handled by adding (?m) prefix to pattern
    # (see _apply_multiline_flag function)
    return options


def _convert_flags_to_std_re(flags: int) -> int:
    """Convert internal flag values to standard re module flags."""
    std_flags = 0
    if flags & IGNORECASE:
        std_flags |= std_re.IGNORECASE
    if flags & MULTILINE:
        std_flags |= std_re.MULTILINE
    if flags & DOTALL:
        std_flags |= std_re.DOTALL
    return std_flags


def _apply_multiline_flag(pattern: str, flags: int) -> str:
    """Apply MULTILINE flag by adding (?m) prefix if needed."""
    if flags & MULTILINE:
        # RE2 supports (?m) inline flag for multiline mode
        # This makes ^ and $ match at line boundaries
        return f"(?m){pattern}"
    return pattern


class CompiledPattern:
    """Wrapper for compiled regex pattern with fullmatch support.

    Uses RE2 when available for ReDoS protection, otherwise falls back
    to Python's standard re module.
    """

    def __init__(
        self,
        pattern: str,
        flags: int = 0,
        pattern_id: str = "",
    ) -> None:
        """
        Compile a regex pattern.

        Args:
            pattern: Regex pattern string
            flags: Regex flags (IGNORECASE, MULTILINE, DOTALL)
            pattern_id: Optional identifier for logging
        """
        self.pattern_str = pattern
        self.flags = flags
        self.pattern_id = pattern_id
        self._using_re2 = _should_use_re2()

        # Transform pattern for Unicode compatibility
        # First convert \uXXXX escapes to actual characters
        transformed_pattern = _convert_unicode_escapes(pattern)
        # Then handle \b word boundaries for Unicode patterns
        transformed_pattern = _transform_word_boundaries(transformed_pattern)
        self._transformed_pattern_str = transformed_pattern

        if self._using_re2:
            # Apply MULTILINE flag via (?m) prefix for RE2
            re2_pattern = _apply_multiline_flag(transformed_pattern, flags)

            # Create options from flags
            options = _create_options(flags, using_re2=True)

            # Compile the main pattern with RE2
            self._pattern: Union[re2._Pattern, std_re.Pattern[str]] = re2.compile(
                re2_pattern, options=options
            )

            # Pre-compile anchored version for fullmatch emulation
            # Wrap in non-capturing group to preserve alternation behavior
            self._anchored_pattern_str = f"^(?:{re2_pattern})$"
            self._anchored_pattern: Union[re2._Pattern, std_re.Pattern[str]] = re2.compile(
                self._anchored_pattern_str, options=options
            )
        else:
            # Use standard re module
            std_flags = _convert_flags_to_std_re(flags)
            self._pattern = std_re.compile(transformed_pattern, std_flags)
            self._anchored_pattern_str = f"^(?:{transformed_pattern})$"
            self._anchored_pattern = std_re.compile(self._anchored_pattern_str, std_flags)

    def finditer(self, text: str) -> Iterator[Union["re2._Match", std_re.Match[str]]]:
        """Find all matches in text."""
        return self._pattern.finditer(text)

    def findall(self, text: str) -> List[str]:
        """Find all matches and return as list."""
        return self._pattern.findall(text)

    def search(self, text: str) -> Optional[Union["re2._Match", std_re.Match[str]]]:
        """Search for pattern in text."""
        return self._pattern.search(text)

    def match(self, text: str) -> Optional[Union["re2._Match", std_re.Match[str]]]:
        """Match pattern at start of text."""
        return self._pattern.match(text)

    def fullmatch(self, text: str) -> Optional[Union["re2._Match", std_re.Match[str]]]:
        """
        Match pattern against entire text.

        RE2 doesn't have native fullmatch, so we emulate it using
        an anchored pattern: ^(?:pattern)$

        For standard re, we use the same approach for consistency.
        """
        return self._anchored_pattern.match(text)

    def sub(self, repl: str, text: str, count: int = 0) -> str:
        """Replace matches in text."""
        return self._pattern.sub(repl, text, count)

    def split(self, text: str, maxsplit: int = 0) -> List[str]:
        """Split text by pattern."""
        return self._pattern.split(text, maxsplit)

    @property
    def pattern(self) -> str:
        """Return the original pattern string."""
        return self.pattern_str

    def __repr__(self) -> str:
        """String representation."""
        backend = "re2" if self._using_re2 else "re"
        return f"CompiledPattern({self.pattern_str!r}, flags={self.flags}, backend={backend})"


def compile(
    pattern: str,
    flags: int = 0,
    pattern_id: str = "",
) -> CompiledPattern:
    """
    Compile a regex pattern using RE2.

    Args:
        pattern: Regex pattern string
        flags: Regex flags (IGNORECASE, MULTILINE, DOTALL)
        pattern_id: Optional identifier for error messages

    Returns:
        CompiledPattern wrapper

    Raises:
        re2.error: If pattern is invalid or uses unsupported features
    """
    return CompiledPattern(pattern, flags, pattern_id)


def convert_flags(flag_names: List[str]) -> int:
    """
    Convert flag names to combined flag value.

    Args:
        flag_names: List of flag names (e.g., ["IGNORECASE", "MULTILINE"])

    Returns:
        Combined integer flag value

    Note:
        UNICODE flag is ignored (RE2 is always Unicode)
        VERBOSE flag is not supported by RE2 and will log a warning
    """
    flags = 0
    for name in flag_names:
        if name == "IGNORECASE":
            flags |= IGNORECASE
        elif name == "MULTILINE":
            flags |= MULTILINE
        elif name == "DOTALL":
            flags |= DOTALL
        elif name == "UNICODE":
            # RE2 is always Unicode, ignore this flag
            pass
        elif name == "VERBOSE":
            logger.warning(
                "VERBOSE flag is not supported by RE2. "
                "Pattern comments and whitespace will not be ignored."
            )
    return flags


# Expose error type for catching compilation errors
# Use re2.error when available, otherwise use re.error
error = re2.error if HAS_RE2 else std_re.error
