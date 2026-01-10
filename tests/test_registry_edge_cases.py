"""Tests for registry.py edge cases to improve coverage."""

import logging
import re

import pytest

from datadetector.models import ActionOnMatch, Category, Pattern, Policy, Severity
from datadetector.registry import (
    PatternRegistry,
    _compile_pattern,
    _load_yaml_file,
    load_registry,
)


class TestPatternRegistryEdgeCases:
    """Test edge cases in PatternRegistry."""

    def test_add_duplicate_pattern_warning(self, caplog):
        """Test warning when adding duplicate pattern."""
        registry = PatternRegistry()

        pattern1 = Pattern(
            id="test_01",
            namespace="test",
            location="test",
            category=Category.EMAIL,
            pattern=r"test",
            compiled=re.compile(r"test"),
            description="Test",
            flags=[],
            mask="***",
            examples=None,
            policy=Policy(
                store_raw=False,
                action_on_match=ActionOnMatch.REDACT,
                severity=Severity.MEDIUM,
            ),
            metadata={},
            verification=None,
            verification_func=None,
            priority=100,
        )

        pattern2 = Pattern(
            id="test_01",
            namespace="test",
            location="test",
            category=Category.EMAIL,
            pattern=r"test2",
            compiled=re.compile(r"test2"),
            description="Test2",
            flags=[],
            mask="***",
            examples=None,
            policy=Policy(
                store_raw=False,
                action_on_match=ActionOnMatch.REDACT,
                severity=Severity.MEDIUM,
            ),
            metadata={},
            verification=None,
            verification_func=None,
            priority=100,
        )

        with caplog.at_level(logging.WARNING):
            registry.add_pattern(pattern1)
            registry.add_pattern(pattern2)

        assert "already exists, overwriting" in caplog.text

    def test_pattern_not_found_warning(self, caplog, tmp_path):
        """Test warning when pattern file not found."""
        non_existent = tmp_path / "nonexistent.yml"

        with caplog.at_level(logging.WARNING):
            load_registry(paths=[str(non_existent)])

        assert "Pattern file not found" in caplog.text

    def test_directory_no_yaml_files_warning(self, caplog, tmp_path):
        """Test warning when directory has no YAML files."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        with caplog.at_level(logging.WARNING):
            load_registry(paths=[str(empty_dir)])

        assert "No YAML files found in directory" in caplog.text

    def test_load_directory_with_yaml_files(self, tmp_path):
        """Test loading YAML files from a directory."""
        patterns_dir = tmp_path / "patterns"
        patterns_dir.mkdir()

        # Create two pattern files
        file1 = patterns_dir / "patterns1.yml"
        file1.write_text(
            """
namespace: test1
patterns:
  - id: email_01
    location: test1
    category: email
    description: Test
    pattern: '[a-z]+'
    mask: "***"
    policy:
      store_raw: false
      action_on_match: redact
      severity: medium
"""
        )

        file2 = patterns_dir / "patterns2.yaml"
        file2.write_text(
            """
namespace: test2
patterns:
  - id: phone_01
    location: test2
    category: phone
    description: Test
    pattern: '[0-9]+'
    mask: "***"
    policy:
      store_raw: false
      action_on_match: redact
      severity: medium
"""
        )

        registry = load_registry(paths=[str(patterns_dir)], validate_schema=False)
        assert len(registry) == 2
        assert "test1" in registry.namespaces
        assert "test2" in registry.namespaces

    def test_load_yaml_file_not_dict_error(self, tmp_path):
        """Test error when YAML file contains non-dict."""
        bad_file = tmp_path / "bad.yml"
        bad_file.write_text("- item1\n- item2\n")  # List, not dict

        with pytest.raises(ValueError, match="Expected YAML file to contain a dict"):
            _load_yaml_file(bad_file)

    def test_compile_pattern_with_priority(self):
        """Test pattern with custom priority."""
        pattern_data = {
            "id": "test_01",
            "location": "test",
            "category": "email",
            "pattern": r"test",
            "mask": "***",
            "priority": 200,
            "policy": {
                "store_raw": False,
                "action_on_match": "redact",
                "severity": "medium",
            },
        }

        pattern = _compile_pattern("test", pattern_data)
        assert pattern.priority == 200

    def test_compile_pattern_with_all_flags(self):
        """Test compiling pattern with all regex flags."""
        from datadetector import regex_compat

        pattern_data = {
            "id": "test_01",
            "location": "test",
            "category": "email",
            "pattern": r"test",
            "flags": ["IGNORECASE", "MULTILINE", "DOTALL", "UNICODE", "VERBOSE"],
            "mask": "***",
            "policy": {
                "store_raw": False,
                "action_on_match": "redact",
                "severity": "medium",
            },
        }

        pattern = _compile_pattern("test", pattern_data)
        # Check flags using regex_compat constants (RE2)
        # Note: UNICODE is implicit in RE2 (always enabled), VERBOSE is not supported
        assert pattern.compiled.flags & regex_compat.IGNORECASE
        assert pattern.compiled.flags & regex_compat.MULTILINE
        assert pattern.compiled.flags & regex_compat.DOTALL

    def test_compile_pattern_regex_error(self):
        """Test error when regex fails to compile."""
        pattern_data = {
            "id": "bad_01",
            "location": "test",
            "category": "email",
            "pattern": r"[invalid(regex",  # Invalid regex
            "mask": "***",
            "policy": {
                "store_raw": False,
                "action_on_match": "redact",
                "severity": "medium",
            },
        }

        with pytest.raises(ValueError, match="Failed to compile pattern"):
            _compile_pattern("test", pattern_data)

    def test_verification_function_not_found_warning(self, caplog, tmp_path):
        """Test warning when verification function not found."""
        pattern_file = tmp_path / "pattern.yml"
        pattern_file.write_text(
            """
namespace: test
patterns:
  - id: test_01
    location: test
    category: other
    pattern: '[0-9]+'
    verification: nonexistent_function
    mask: "***"
    policy:
      store_raw: false
      action_on_match: redact
      severity: medium
"""
        )

        with caplog.at_level(logging.WARNING):
            load_registry(paths=[str(pattern_file)], validate_schema=False)

        assert "Verification function 'nonexistent_function' not found" in caplog.text


class TestPatternRegistryMethods:
    """Test PatternRegistry methods for better coverage."""

    def test_registry_repr(self):
        """Test __repr__ method."""
        registry = PatternRegistry()
        pattern = Pattern(
            id="test_01",
            namespace="test",
            location="test",
            category=Category.EMAIL,
            pattern=r"test",
            compiled=re.compile(r"test"),
            description="Test",
            flags=[],
            mask="***",
            examples=None,
            policy=Policy(
                store_raw=False,
                action_on_match=ActionOnMatch.REDACT,
                severity=Severity.MEDIUM,
            ),
            metadata={},
            verification=None,
            verification_func=None,
            priority=100,
        )
        registry.add_pattern(pattern)

        repr_str = repr(registry)
        assert "PatternRegistry" in repr_str
        assert "patterns=1" in repr_str
        assert "test" in repr_str

    def test_registry_version_increments(self):
        """Test that version increments on pattern add."""
        registry = PatternRegistry()
        initial_version = registry.version

        pattern = Pattern(
            id="test_01",
            namespace="test",
            location="test",
            category=Category.EMAIL,
            pattern=r"test",
            compiled=re.compile(r"test"),
            description="Test",
            flags=[],
            mask="***",
            examples=None,
            policy=Policy(
                store_raw=False,
                action_on_match=ActionOnMatch.REDACT,
                severity=Severity.MEDIUM,
            ),
            metadata={},
            verification=None,
            verification_func=None,
            priority=100,
        )

        registry.add_pattern(pattern)
        assert registry.version == initial_version + 1

    def test_get_nonexistent_pattern(self):
        """Test getting non-existent pattern returns None."""
        registry = PatternRegistry()
        assert registry.get_pattern("nonexistent/pattern") is None

    def test_get_nonexistent_namespace(self):
        """Test getting non-existent namespace returns empty list."""
        registry = PatternRegistry()
        assert registry.get_namespace_patterns("nonexistent") == []

    def test_load_registry_with_validation_disabled(self, tmp_path):
        """Test loading registry with validation disabled."""
        pattern_file = tmp_path / "pattern.yml"
        pattern_file.write_text(
            """
namespace: test
patterns:
  - id: test_01
    location: test
    category: email
    pattern: '[a-z]+'
    mask: "***"
    policy:
      store_raw: false
      action_on_match: redact
      severity: medium
    examples:
      match:
        - "abc"
      nomatch:
        - "123"
"""
        )

        # Load without validation
        registry = load_registry(
            paths=[str(pattern_file)], validate_schema=False, validate_examples=False
        )
        assert len(registry) == 1
