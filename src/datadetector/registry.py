"""Pattern registry for loading and managing regex patterns."""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import jsonschema
import yaml

from datadetector import regex_compat
from datadetector.models import (
    ActionOnMatch,
    Category,
    Examples,
    Pattern,
    Policy,
    Severity,
)
from datadetector.verification import get_verification_function

logger = logging.getLogger(__name__)


class PatternRegistry:
    """Registry for compiled patterns."""

    def __init__(self) -> None:
        """Initialize empty pattern registry."""
        self.patterns: Dict[str, Pattern] = {}  # full_id -> Pattern
        self.namespaces: Dict[str, List[Pattern]] = {}  # namespace -> [Pattern]
        self._version: int = 0

    def add_pattern(self, pattern: Pattern) -> None:
        """Add a pattern to the registry."""
        full_id = pattern.full_id
        if full_id in self.patterns:
            logger.warning(f"Pattern {full_id} already exists, overwriting")

        self.patterns[full_id] = pattern

        # Add to namespace index
        if pattern.namespace not in self.namespaces:
            self.namespaces[pattern.namespace] = []
        if pattern not in self.namespaces[pattern.namespace]:
            self.namespaces[pattern.namespace].append(pattern)

        self._version += 1

    def get_pattern(self, ns_id: str) -> Optional[Pattern]:
        """Get pattern by full namespace/id."""
        return self.patterns.get(ns_id)

    def get_namespace_patterns(self, namespace: str) -> List[Pattern]:
        """Get all patterns for a namespace."""
        return self.namespaces.get(namespace, [])

    def get_all_patterns(self) -> List[Pattern]:
        """Get all patterns in registry."""
        return list(self.patterns.values())

    @property
    def version(self) -> int:
        """Get current registry version (increments on changes)."""
        return self._version

    def __len__(self) -> int:
        """Return number of patterns."""
        return len(self.patterns)

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"PatternRegistry(patterns={len(self.patterns)}, "
            f"namespaces={list(self.namespaces.keys())})"
        )


def _get_project_root() -> Path:
    """Determine project root directory."""
    # 1. Default: relative to source file (dev/editable)
    # src/datadetector/registry.py -> src/datadetector -> src -> root
    root = Path(__file__).parent.parent.parent

    if (root / "pattern-engine").exists():
        return root

    # 2. Docker /app
    if Path("/app/pattern-engine").exists():
        return Path("/app")

    # 3. CWD
    if (Path.cwd() / "pattern-engine").exists():
        return Path.cwd()

    # Fallback to default even if not found
    return root


def load_registry(
    paths: Optional[List[str]] = None,
    validate_schema: bool = True,
    validate_examples: bool = True,
) -> PatternRegistry:
    """
    Load patterns from YAML files into registry.

    Args:
        paths: List of file or directory paths to load. If a directory is provided,
               all .yml and .yaml files in that directory will be loaded.
               If None, loads default patterns.
        validate_schema: Whether to validate against JSON schema
        validate_examples: Whether to validate examples against patterns

    Returns:
        PatternRegistry with loaded patterns

    Raises:
        FileNotFoundError: If pattern file not found
        ValueError: If pattern validation fails
    """
    registry = PatternRegistry()

    if paths is None:
        # Load default patterns from package
        root = _get_project_root()
        config_dir = root / "config"
        pii_patterns_dir = root / "pattern-engine" / "regex" / "pii"
        paths = [
            str(config_dir / "tokens.yml"),  # Load tokens first for faster detection
            str(pii_patterns_dir / "common"),  # Load all common patterns
            str(pii_patterns_dir / "us"),  # Load all US patterns
            str(pii_patterns_dir / "kr"),  # Load all KR patterns
            str(pii_patterns_dir / "cn"),  # Load all CN patterns
            str(pii_patterns_dir / "jp"),  # Load all JP patterns
            str(pii_patterns_dir / "tw"),  # Load all TW patterns
            str(pii_patterns_dir / "in"),  # Load all IN patterns
            str(pii_patterns_dir / "eu"),  # Load all EU patterns (GDPR compliance)
            str(pii_patterns_dir / "iban.yml"),  # IBAN patterns
        ]

    for path_str in paths:
        path = Path(path_str)
        if not path.exists():
            logger.warning(f"Pattern file not found: {path}")
            continue

        # If path is a directory, load all YAML files in it
        if path.is_dir():
            yaml_files = sorted(path.glob("*.yml")) + sorted(path.glob("*.yaml"))
            if not yaml_files:
                logger.warning(f"No YAML files found in directory: {path}")
                continue
            file_paths = yaml_files
        else:
            file_paths = [path]

        for file_path in file_paths:
            logger.info(f"Loading patterns from {file_path}")
            data = _load_yaml_file(file_path)

            if validate_schema:
                _validate_schema(data)

            patterns = _parse_pattern_file(data)

            for pattern in patterns:
                if validate_examples and pattern.examples:
                    _validate_examples(pattern)
                registry.add_pattern(pattern)

    logger.info(f"Loaded {len(registry)} patterns from {len(registry.namespaces)} namespaces")
    return registry


def _load_yaml_file(path: Path) -> Dict[str, Any]:
    """Load YAML file."""
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
        if not isinstance(data, dict):
            raise ValueError(f"Expected YAML file to contain a dict, got {type(data)}")
        return data


def _validate_schema(data: Dict[str, Any]) -> None:
    """Validate pattern data against JSON schema."""
    schema_path = _get_project_root() / "schemas" / "pattern-schema.json"

    if not schema_path.exists():
        logger.warning("Pattern schema not found, skipping validation")
        return

    with open(schema_path, encoding="utf-8") as f:
        schema = yaml.safe_load(f)

    try:
        jsonschema.validate(data, schema)
    except jsonschema.ValidationError as e:
        raise ValueError(f"Pattern schema validation failed: {e.message}") from e


def _parse_pattern_file(data: Dict[str, Any]) -> List[Pattern]:
    """Parse pattern file data into Pattern objects."""
    namespace = data["namespace"]
    patterns = []

    for pattern_data in data.get("patterns", []):
        pattern = _compile_pattern(namespace, pattern_data)
        patterns.append(pattern)

    return patterns


def _compile_pattern(namespace: str, data: Dict[str, Any]) -> Pattern:
    """Compile a single pattern definition."""
    pattern_id = data["id"]
    location = data["location"]
    category = Category(data["category"])
    pattern_str = data["pattern"]

    # Parse regex flags and compile pattern
    flag_names = data.get("flags", [])
    flags = regex_compat.convert_flags(flag_names)

    try:
        compiled = regex_compat.compile(
            pattern_str,
            flags,
            pattern_id=f"{namespace}/{pattern_id}",
        )
    except regex_compat.error as e:
        raise ValueError(f"Failed to compile pattern {namespace}/{pattern_id}: {e}") from e

    # Parse policy
    policy_data = data.get("policy", {})
    policy = Policy(
        store_raw=policy_data.get("store_raw", False),
        action_on_match=ActionOnMatch(policy_data.get("action_on_match", "redact")),
        severity=Severity(policy_data.get("severity", "medium")),
    )

    # Parse examples
    examples = None
    if "examples" in data:
        examples = Examples(
            match=data["examples"].get("match", []),
            nomatch=data["examples"].get("nomatch", []),
        )

    # Parse verification function
    verification = data.get("verification")
    verification_func = None
    if verification:
        verification_func = get_verification_function(verification)
        if verification_func is None:
            logger.warning(
                f"Verification function '{verification}' not found "
                f"for pattern {namespace}/{pattern_id}"
            )

    # Parse priority (default: 100)
    priority = data.get("priority", 100)

    return Pattern(
        id=pattern_id,
        namespace=namespace,
        location=location,
        category=category,
        pattern=pattern_str,
        compiled=compiled,
        description=data.get("description", ""),
        flags=data.get("flags", []),
        mask=data.get("mask"),
        examples=examples,
        policy=policy,
        metadata=data.get("metadata", {}),
        verification=verification,
        verification_func=verification_func,
        priority=priority,
    )


def _validate_examples(pattern: Pattern) -> None:
    """Validate pattern examples match/nomatch expectations."""
    if not pattern.examples:
        return

    errors = []

    # Check that match examples match
    for example in pattern.examples.match:
        regex_matches = pattern.compiled.fullmatch(example) is not None
        if not regex_matches:
            errors.append(f"Example should match but doesn't: '{example}'")
        elif pattern.verification_func is not None:
            # Also check verification if present
            if not pattern.verification_func(example):
                errors.append(f"Example matches regex but fails verification: '{example}'")

    # Check that nomatch examples don't match
    for example in pattern.examples.nomatch:
        regex_matches = pattern.compiled.fullmatch(example) is not None
        if regex_matches:
            # If regex matches, check if verification fails (which is acceptable)
            if pattern.verification_func is not None:
                if pattern.verification_func(example):
                    # Both regex and verification passed - this is wrong
                    errors.append(f"Example should NOT match but does: '{example}'")
                # else: regex matched but verification failed - this is OK
            else:
                # No verification function, so regex match means it matched
                errors.append(f"Example should NOT match but does: '{example}'")

    if errors:
        error_msg = f"Pattern {pattern.full_id} example validation failed:\n" + "\n".join(errors)
        raise ValueError(error_msg)

    logger.debug(f"Pattern {pattern.full_id} examples validated successfully")
