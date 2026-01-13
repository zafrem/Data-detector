"""Context-aware pattern filtering for improved performance and accuracy.

This module provides functionality to filter regex patterns based on contextual
hints such as column names, field labels, or descriptions. This significantly
improves performance by only checking relevant patterns instead of all 61 patterns.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import yaml

from datadetector import regex_compat

# Pre-compile pattern for splitting field names
_FIELD_SPLIT_PATTERN = regex_compat.compile(r"[_\-\s\.]+")


@dataclass
class ContextHint:
    """Contextual information to guide pattern selection.

    Attributes:
        keywords: Keywords from metadata (column names, labels, descriptions).
                  Examples: ["ssn", "bank_account", "email"]
        categories: Category hints to include. Examples: ["ssn", "bank", "phone"]
        pattern_ids: Explicit pattern IDs to include. Examples: ["us/ssn_01"]
        exclude_patterns: Pattern IDs to explicitly exclude. Examples: ["kr/phone_03"]
        strategy: Filtering strategy - 'strict', 'loose', or 'none'
                  - 'strict': Only use keyword-matched patterns
                  - 'loose': Use keyword-matched + fallback to all if no matches (default)
                  - 'none': Use all patterns (disable filtering)
    """

    keywords: List[str] = field(default_factory=list)
    categories: List[str] = field(default_factory=list)
    pattern_ids: List[str] = field(default_factory=list)
    exclude_patterns: List[str] = field(default_factory=list)
    strategy: str = "loose"

    def __post_init__(self) -> None:
        """Normalize keywords to lowercase for matching."""
        self.keywords = [kw.lower() for kw in self.keywords]
        self.categories = [cat.lower() for cat in self.categories]


class KeywordRegistry:
    """Registry mapping keywords to pattern categories/IDs.

    Loads keyword-to-pattern mappings from keywords.yml and provides
    lookup functions to find relevant patterns based on keywords or categories.
    """

    def __init__(self, keywords_file: Optional[Path] = None):
        """Initialize keyword registry.

        Args:
            keywords_file: Path to keywords.yml file. If None, uses default location.
        """
        if keywords_file is None:
            # Default to config/keywords.yml
            keywords_file = Path(__file__).parent.parent.parent / "config" / "keywords.yml"

        self.keywords_file = keywords_file
        self.keyword_map: Dict[str, Dict[str, Any]] = {}
        self.category_map: Dict[str, Dict[str, Any]] = {}
        self._load_keywords()

    def _load_keywords(self) -> None:
        """Load keyword mappings from YAML file."""
        if not self.keywords_file.exists():
            # If keywords file doesn't exist, initialize empty maps
            return

        with open(self.keywords_file, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if data:
            self.keyword_map = data.get("keywords", {})
            self.category_map = data.get("categories", {})

    def get_patterns_for_keyword(self, keyword: str) -> Set[str]:
        """Get pattern IDs for a given keyword.

        Performs both exact and partial matching. For example:
        - "user_ssn" will match keyword "ssn"
        - "bank_account_number" will match keywords "bank_account" and "account_number"

        Args:
            keyword: Keyword to look up (case-insensitive)

        Returns:
            Set of pattern IDs (may include wildcards like 'kr/bank_account_*')
        """
        keyword_normalized = keyword.lower().replace("_", " ").replace("-", " ")

        matched_patterns = set()

        # Check all registered keywords
        for registered_kw, config in self.keyword_map.items():
            registered_normalized = registered_kw.replace("_", " ").replace("-", " ")

            # Exact match or partial match (keyword contains registered keyword)
            if (
                registered_normalized == keyword_normalized
                or registered_normalized in keyword_normalized
                or keyword_normalized in registered_normalized
            ):

                patterns = config.get("patterns", [])
                matched_patterns.update(patterns)

        return matched_patterns

    def get_patterns_for_category(self, category: str) -> Set[str]:
        """Get pattern IDs for a given category.

        Args:
            category: Category name (e.g., 'ssn', 'bank', 'phone')

        Returns:
            Set of pattern IDs belonging to the category
        """
        category_lower = category.lower()
        if category_lower in self.category_map:
            return set(self.category_map[category_lower].get("patterns", []))
        return set()

    def expand_wildcards(self, patterns: Set[str], all_patterns: List[str]) -> Set[str]:
        """Expand wildcard patterns like 'kr/bank_account_*' to actual pattern IDs.

        Args:
            patterns: Set of pattern IDs (may include wildcards)
            all_patterns: List of all available pattern IDs

        Returns:
            Set of expanded pattern IDs (no wildcards)
        """
        expanded = set()

        for pattern in patterns:
            if "*" in pattern:
                # Convert wildcard to regex
                pattern_re = regex_compat.compile(pattern.replace("*", ".*"))
                # Match against all available patterns
                matched = [p for p in all_patterns if pattern_re.match(p)]
                expanded.update(matched)
            else:
                # No wildcard, keep as-is if it exists
                if pattern in all_patterns:
                    expanded.add(pattern)

        return expanded


class ContextFilter:
    """Filter patterns based on contextual hints.

    Uses keyword registry to determine which patterns are relevant for
    the given context, significantly improving performance.
    """

    def __init__(self, registry: Optional[KeywordRegistry] = None):
        """Initialize context filter.

        Args:
            registry: Keyword registry. If None, creates a new one.
        """
        self.registry = registry or KeywordRegistry()

    def filter_patterns(self, hint: ContextHint, all_patterns: List[str]) -> List[str]:
        """Filter pattern list based on context hint.

        Args:
            hint: Context hint with keywords, categories, etc.
            all_patterns: List of all available pattern IDs

        Returns:
            Filtered list of pattern IDs to check (maintains original order)
        """
        # Strategy: none - skip filtering entirely
        if hint.strategy == "none":
            return all_patterns

        # Collect patterns from various sources
        selected_patterns = set()

        # 1. Explicit pattern IDs
        selected_patterns.update(hint.pattern_ids)

        # 2. Keywords
        for keyword in hint.keywords:
            patterns = self.registry.get_patterns_for_keyword(keyword)
            selected_patterns.update(patterns)

        # 3. Categories
        for category in hint.categories:
            patterns = self.registry.get_patterns_for_category(category)
            selected_patterns.update(patterns)

        # Expand wildcards
        expanded_patterns = self.registry.expand_wildcards(selected_patterns, all_patterns)

        # Strategy: loose - if no patterns found, use all patterns as fallback
        if hint.strategy == "loose" and not expanded_patterns:
            return all_patterns

        # Apply exclusions
        expanded_patterns -= set(hint.exclude_patterns)

        # Maintain original order from all_patterns
        filtered = [p for p in all_patterns if p in expanded_patterns]

        return filtered


def create_context_from_field_name(field_name: str, strategy: str = "loose") -> ContextHint:
    """Convenience function to create ContextHint from a field name.

    Automatically extracts keywords from field names like:
    - "user_ssn" -> keywords=["user", "ssn"]
    - "billing_zip_code" -> keywords=["billing", "zip", "code"]
    - "bank_account_number" -> keywords=["bank", "account", "number"]

    Args:
        field_name: Field/column name
        strategy: Filtering strategy ('strict', 'loose', 'none')

    Returns:
        ContextHint with extracted keywords
    """
    # Split by common delimiters
    keywords = _FIELD_SPLIT_PATTERN.split(field_name.lower())
    # Filter out empty strings and single characters
    keywords = [kw for kw in keywords if len(kw) > 1]

    return ContextHint(keywords=keywords, strategy=strategy)
