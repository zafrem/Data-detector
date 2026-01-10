import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List

import yaml

from datadetector import regex_compat

# ANSI colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"


def load_yaml(path: Path) -> Dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def check_regex_compilation(pattern: str, pattern_id: str) -> bool:
    try:
        regex_compat.compile(pattern, pattern_id=pattern_id)
        return True
    except regex_compat.error as e:
        print(f"{RED}[FAIL] {pattern_id}: Invalid Regex (RE2) - {e}{RESET}")
        return False


def check_re2_compatibility(pattern: str, pattern_id: str) -> List[str]:
    """Check for RE2 compatibility issues (informational only, compilation will fail anyway)."""
    issues = []
    # Check for lookarounds which RE2 doesn't support
    if "(?=" in pattern or "(?!" in pattern or "(?<=" in pattern or "(?<!" in pattern:
        issues.append("Contains lookarounds (unsupported in RE2)")
    # Check for backreferences using regex_compat
    backref_pattern = regex_compat.compile(r"\\[1-9]")
    if backref_pattern.search(pattern):
        issues.append("Contains backreferences (unsupported in RE2)")
    return issues


def validate_examples(item: Dict[str, Any]) -> int:
    failures = 0
    pattern_id = item.get("id", "unknown")
    regex_str = item.get("pattern")

    if not regex_str:
        return 0

    # 1. Compile Regex
    try:
        flags = regex_compat.convert_flags(item.get("flags", []))
        regex = regex_compat.compile(regex_str, flags, pattern_id=pattern_id)
    except regex_compat.error:
        # Already handled in compilation check
        return 1

    examples = item.get("examples", {})

    # 2. Check Positive Matches
    for ex in examples.get("match", []):
        if not regex.search(
            ex
        ):  # Using search to be permissive, usually fullmatch is preferred for strict types
            # For strict patterns, we might expect fullmatch, but patterns usually have \b
            # Let's try fullmatch if it's anchored, otherwise search
            print(f"{RED}[FAIL] {pattern_id}: Example '{ex}' did not match pattern.{RESET}")
            failures += 1

    # 3. Check Negative Matches
    for ex in examples.get("nomatch", []):
        match = regex.search(ex)
        if match:
            # If it matches, we must check if verification would have saved it.
            # Since this is a pure regex repo, we warn but might not fail if
            # verification is required.
            verification = item.get("verification")
            if verification:
                msg = (
                    f"{YELLOW}[WARN] {pattern_id}: Nomatch example '{ex}' "
                    f"matched regex, but has verification '{verification}'. "
                    f"Skipping failure.{RESET}"
                )
                print(msg)
            else:
                msg = (
                    f"{RED}[FAIL] {pattern_id}: Nomatch example '{ex}' "
                    "MATCHED pattern (no verification function)."
                    f"{RESET}"
                )
                print(msg)
                failures += 1

    return failures


def main():
    parser = argparse.ArgumentParser(description="Pattern Regression Runner")
    parser.add_argument(
        "--patterns-dir", type=str, default="patterns", help="Directory containing YAML patterns"
    )
    args = parser.parse_args()

    base_dir = Path(args.patterns_dir)
    if not base_dir.exists():
        print(f"Directory {base_dir} does not exist.")
        sys.exit(1)

    total_patterns = 0
    total_failures = 0

    print(f"Scanning patterns in {base_dir}...")

    for yaml_file in base_dir.rglob("*.yml"):
        try:
            data = load_yaml(yaml_file)
        except Exception as e:
            print(f"{RED}[ERROR] Failed to parse YAML {yaml_file}: {e}{RESET}")
            total_failures += 1
            continue

        if not data or "patterns" not in data:
            continue

        namespace = data.get("namespace", "unknown")

        for item in data["patterns"]:
            total_patterns += 1
            pid = f"{namespace}/{item.get('id')}"
            pattern_str = item.get("pattern", "")

            # Check Compilation
            if not check_regex_compilation(pattern_str, pid):
                total_failures += 1
                continue

            # Check RE2 Compatibility (informational, compilation will fail anyway)
            re2_issues = check_re2_compatibility(pattern_str, pid)
            for issue in re2_issues:
                print(f"{YELLOW}[WARN] {pid}: RE2 Compatibility - {issue}{RESET}")

            # Check Examples
            fails = validate_examples(item)
            if fails > 0:
                total_failures += fails

    print("-" * 40)
    print(f"Processed {total_patterns} patterns.")

    if total_failures > 0:
        print(f"{RED}Regression Failed with {total_failures} errors.{RESET}")
        sys.exit(1)
    else:
        print(f"{GREEN}All regression tests passed.{RESET}")
        sys.exit(0)


if __name__ == "__main__":
    main()
