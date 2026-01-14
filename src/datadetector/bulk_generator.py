"""Bulk data generator for creating large training datasets with metadata.

This module provides functionality to generate large volumes of fake data
along with metadata about what patterns were used, perfect for training
machine learning models or testing at scale.
"""

import csv
import json
import logging
import secrets
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from datadetector.fake_generator import FakeDataGenerator

logger = logging.getLogger(__name__)


class BulkDataGenerator:
    """Generate bulk training data with pattern metadata.

    This generator creates large datasets containing fake PII along with
    metadata about which patterns were used to generate each piece of data.
    This is useful for:
    - Training ML models for PII detection
    - Testing detection systems at scale
    - Creating labeled datasets
    - Benchmarking performance
    """

    def __init__(
        self, faker_generator: Optional[FakeDataGenerator] = None, seed: Optional[int] = None
    ):
        """
        Initialize bulk data generator.

        Args:
            faker_generator: Existing FakeDataGenerator instance (will create one if None)
            seed: Random seed for reproducibility
        """
        if faker_generator is None:
            self.gen = FakeDataGenerator(seed=seed)
        else:
            self.gen = faker_generator

        self.faker = self.gen.faker
        # Use cryptographically secure random number generator
        self._rng = secrets.SystemRandom()

    def generate_labeled_record(
        self,
        include_patterns: Optional[List[str]] = None,
        num_pii_items: int = 5,
    ) -> Dict[str, Any]:
        """
        Generate a single labeled record with PII and metadata.

        Args:
            include_patterns: List of pattern IDs to use (None = random selection)
            num_pii_items: Number of PII items to include

        Returns:
            Dictionary with 'text', 'pii_items', and 'metadata'
        """
        if include_patterns is None:
            # Select random patterns
            available_patterns = self.gen.supported_patterns()
            include_patterns = self._rng.sample(
                available_patterns, min(num_pii_items, len(available_patterns))
            )

        pii_items = []
        text_parts = []

        # Generate context text
        context = self.faker.paragraph(nb_sentences=self._rng.randint(2, 4))
        text_parts.append(context)

        # Generate PII items with metadata
        for pattern_id in include_patterns:
            try:
                value = self.gen.from_pattern(pattern_id)

                # Create context for this PII item
                templates = [
                    f"Contact information: {value}",
                    f"Please use {value} for identification",
                    f"Their {pattern_id.split('/')[-1].replace('_', ' ')} is {value}",
                    f"You can reach them at {value}",
                    f"Use this: {value}",
                    value,  # Sometimes just the value alone
                ]

                text_with_pii = self._rng.choice(templates)
                text_parts.append(text_with_pii)

                # Extract category from pattern_id
                namespace, pattern_name = pattern_id.split("/")

                pii_items.append(
                    {
                        "pattern_id": pattern_id,
                        "namespace": namespace,
                        "pattern_name": pattern_name,
                        "value": value,
                        "start_hint": (
                            len(" ".join(text_parts[:-1])) + 1 if len(text_parts) > 1 else 0
                        ),
                    }
                )

            except Exception as e:
                logger.warning(f"Failed to generate pattern {pattern_id}: {e}")
                continue

        # Combine all text parts
        full_text = " ".join(text_parts)

        return {
            "text": full_text,
            "pii_items": pii_items,
            "metadata": {
                "num_pii_items": len(pii_items),
                "patterns_used": include_patterns,
                "text_length": len(full_text),
            },
        }

    def generate_bulk_labeled_data(
        self,
        num_records: int = 1000,
        patterns_per_record: Tuple[int, int] = (3, 8),
        include_patterns: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Generate bulk labeled training data.

        Args:
            num_records: Number of records to generate
            patterns_per_record: (min, max) number of PII items per record
            include_patterns: List of pattern IDs to use (None = use all)

        Returns:
            List of labeled records
        """
        logger.info(f"Generating {num_records} labeled records...")

        records = []
        for i in range(num_records):
            num_pii = self._rng.randint(patterns_per_record[0], patterns_per_record[1])
            record = self.generate_labeled_record(
                include_patterns=include_patterns,
                num_pii_items=num_pii,
            )
            record["record_id"] = i + 1
            records.append(record)

            if (i + 1) % 100 == 0:
                logger.info(f"  Generated {i + 1}/{num_records} records...")

        logger.info(f"✓ Generated {num_records} labeled records")
        return records

    def save_bulk_data_jsonl(
        self,
        output_path: Union[str, Path],
        num_records: int = 1000,
        patterns_per_record: Tuple[int, int] = (3, 8),
        include_patterns: Optional[List[str]] = None,
    ) -> None:
        """
        Save bulk labeled data in JSONL format (one JSON object per line).

        This format is ideal for:
        - Streaming large datasets
        - Machine learning training pipelines
        - Line-by-line processing

        Args:
            output_path: Output file path
            num_records: Number of records to generate
            patterns_per_record: (min, max) number of PII items per record
            include_patterns: List of pattern IDs to use (None = use all)
        """
        output_path = Path(output_path)

        records = self.generate_bulk_labeled_data(
            num_records=num_records,
            patterns_per_record=patterns_per_record,
            include_patterns=include_patterns,
        )

        with open(output_path, "w", encoding="utf-8") as f:
            for record in records:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

        logger.info(f"✓ Saved {num_records} records to {output_path}")
        logger.info(f"  File size: {output_path.stat().st_size:,} bytes")

    def save_bulk_data_json(
        self,
        output_path: Union[str, Path],
        num_records: int = 1000,
        patterns_per_record: Tuple[int, int] = (3, 8),
        include_patterns: Optional[List[str]] = None,
    ) -> None:
        """
        Save bulk labeled data as a single JSON file.

        Args:
            output_path: Output file path
            num_records: Number of records to generate
            patterns_per_record: (min, max) number of PII items per record
            include_patterns: List of pattern IDs to use (None = use all)
        """
        output_path = Path(output_path)

        records = self.generate_bulk_labeled_data(
            num_records=num_records,
            patterns_per_record=patterns_per_record,
            include_patterns=include_patterns,
        )

        # Create dataset with metadata
        dataset = {
            "metadata": {
                "num_records": len(records),
                "generator": "BulkDataGenerator",
                "patterns_per_record_range": patterns_per_record,
                "total_pii_items": sum(r["metadata"]["num_pii_items"] for r in records),
                "supported_patterns": (
                    self.gen.supported_patterns() if include_patterns is None else include_patterns
                ),
            },
            "records": records,
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(dataset, f, indent=2, ensure_ascii=False)

        logger.info(f"✓ Saved {num_records} records to {output_path}")
        logger.info(f"  File size: {output_path.stat().st_size:,} bytes")

    def save_bulk_data_csv(
        self,
        output_path: Union[str, Path],
        num_records: int = 1000,
        patterns_per_record: Tuple[int, int] = (3, 8),
        include_patterns: Optional[List[str]] = None,
    ) -> None:
        """
        Save bulk labeled data as CSV (text + metadata columns).

        Args:
            output_path: Output file path
            num_records: Number of records to generate
            patterns_per_record: (min, max) number of PII items per record
            include_patterns: List of pattern IDs to use (None = use all)
        """
        output_path = Path(output_path)

        records = self.generate_bulk_labeled_data(
            num_records=num_records,
            patterns_per_record=patterns_per_record,
            include_patterns=include_patterns,
        )

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            # Header
            writer.writerow(
                [
                    "record_id",
                    "text",
                    "num_pii_items",
                    "text_length",
                    "patterns_used",
                    "pii_items_json",
                ]
            )

            # Data rows
            for record in records:
                writer.writerow(
                    [
                        record["record_id"],
                        record["text"],
                        record["metadata"]["num_pii_items"],
                        record["metadata"]["text_length"],
                        ",".join(record["metadata"]["patterns_used"]),
                        json.dumps(record["pii_items"]),
                    ]
                )

        logger.info(f"✓ Saved {num_records} records to {output_path}")
        logger.info(f"  File size: {output_path.stat().st_size:,} bytes")

    def generate_detection_pairs(
        self,
        num_pairs: int = 1000,
        positive_ratio: float = 0.7,
    ) -> List[Dict[str, Any]]:
        """
        Generate text pairs for binary classification (has PII / no PII).

        Useful for training binary classifiers or testing detection systems.

        Args:
            num_pairs: Number of pairs to generate
            positive_ratio: Ratio of positive (has PII) examples

        Returns:
            List of dicts with 'text', 'has_pii', 'label' (0/1)
        """
        logger.info(f"Generating {num_pairs} detection pairs (positive ratio: {positive_ratio})...")

        num_positive = int(num_pairs * positive_ratio)
        num_negative = num_pairs - num_positive

        pairs = []

        # Generate positive examples (with PII)
        for i in range(num_positive):
            record = self.generate_labeled_record(num_pii_items=self._rng.randint(1, 5))
            pairs.append(
                {
                    "pair_id": i + 1,
                    "text": record["text"],
                    "has_pii": True,
                    "label": 1,
                    "pii_count": len(record["pii_items"]),
                    "patterns": [item["pattern_id"] for item in record["pii_items"]],
                }
            )

        # Generate negative examples (no PII)
        for i in range(num_negative):
            text = " ".join(
                [
                    self.faker.paragraph(nb_sentences=self._rng.randint(2, 5))
                    for _ in range(self._rng.randint(1, 3))
                ]
            )
            pairs.append(
                {
                    "pair_id": num_positive + i + 1,
                    "text": text,
                    "has_pii": False,
                    "label": 0,
                    "pii_count": 0,
                    "patterns": [],
                }
            )

        # Shuffle pairs
        self._rng.shuffle(pairs)

        logger.info(
            f"✓ Generated {num_pairs} pairs ({num_positive} positive, {num_negative} negative)"
        )
        return pairs

    def save_detection_pairs(
        self,
        output_path: Union[str, Path],
        num_pairs: int = 1000,
        positive_ratio: float = 0.7,
        format: str = "jsonl",
    ) -> None:
        """
        Save detection pairs to file.

        Args:
            output_path: Output file path
            num_pairs: Number of pairs to generate
            positive_ratio: Ratio of positive examples
            format: Output format ('jsonl', 'json', or 'csv')
        """
        output_path = Path(output_path)
        pairs = self.generate_detection_pairs(num_pairs, positive_ratio)

        if format == "jsonl":
            with open(output_path, "w", encoding="utf-8") as f:
                for pair in pairs:
                    f.write(json.dumps(pair, ensure_ascii=False) + "\n")
        elif format == "json":
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(pairs, f, indent=2, ensure_ascii=False)
        elif format == "csv":
            with open(output_path, "w", newline="", encoding="utf-8") as f:
                fieldnames = ["pair_id", "text", "has_pii", "label", "pii_count", "patterns"]
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for pair in pairs:
                    row = pair.copy()
                    row["patterns"] = ",".join(row["patterns"])
                    writer.writerow(row)
        else:
            raise ValueError(f"Unsupported format: {format}")

        logger.info(f"✓ Saved {num_pairs} detection pairs to {output_path}")
        logger.info(f"  File size: {output_path.stat().st_size:,} bytes")

    def generate_statistics(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate statistics about a dataset.

        Args:
            records: List of labeled records

        Returns:
            Dictionary with dataset statistics
        """
        total_pii = sum(r["metadata"]["num_pii_items"] for r in records)
        pattern_counts: Dict[str, int] = {}

        for record in records:
            for pii_item in record["pii_items"]:
                pattern_id = pii_item["pattern_id"]
                pattern_counts[pattern_id] = pattern_counts.get(pattern_id, 0) + 1

        return {
            "total_records": len(records),
            "total_pii_items": total_pii,
            "avg_pii_per_record": total_pii / len(records) if records else 0,
            "avg_text_length": (
                sum(r["metadata"]["text_length"] for r in records) / len(records) if records else 0
            ),
            "pattern_distribution": pattern_counts,
            "unique_patterns_used": len(pattern_counts),
        }
