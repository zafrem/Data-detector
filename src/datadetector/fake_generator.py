"""Fake data generator using patterns and Faker.

This module provides functionality to generate fake data that matches
detection patterns, useful for testing, demos, and synthetic data generation.
"""

import json
import logging
import secrets
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional, Union

try:
    from faker import Faker
except ImportError:
    Faker = None  # type: ignore[misc, assignment]

logger = logging.getLogger(__name__)


class FakeDataGenerator:
    """
    Generate fake data matching various patterns and file formats.

    This generator can create:
    - Text data from regex patterns
    - Structured data (JSON, CSV, XML)
    - Office files (Word, Excel, PowerPoint)
    - Database files (SQLite)
    - Log files
    - Images with embedded text
    - And more...

    Example:
        >>> generator = FakeDataGenerator()
        >>> email = generator.from_pattern("comm/email_01")
        >>> print(email)  # user@example.com
        >>>
        >>> # Generate a CSV file with PII
        >>> generator.create_csv_file("output.csv", rows=100, include_pii=True)
    """

    def __init__(self, locale: str = "en_US", seed: Optional[int] = None):
        """
        Initialize the fake data generator.

        Args:
            locale: Locale for Faker (e.g., 'en_US', 'ko_KR')
            seed: Random seed for reproducible generation
        """
        if Faker is None:
            raise ImportError(
                "Faker is required for fake data generation. " "Install it with: pip install faker"
            )

        # Use cryptographically secure random number generator
        self._rng = secrets.SystemRandom()

        if seed is not None:
            Faker.seed(seed)
            # Note: SystemRandom cannot be seeded (uses OS entropy for security)

        self.faker = Faker(locale)
        if seed is not None:
            self.faker.seed_instance(seed)

        # Pattern-to-generator mapping
        self._pattern_generators = self._setup_pattern_generators()

    def _setup_pattern_generators(self) -> Dict[str, Callable[[], str]]:
        """Set up mapping from pattern IDs to generator functions."""
        return {
            # Email
            "comm/email_01": lambda: self.faker.email(),
            # Phone numbers
            "us/phone_01": lambda: self.faker.phone_number()[:14],
            "kr/mobile_01": lambda: (
                f"010-{self._rng.randint(1000, 9999)}-{self._rng.randint(1000, 9999)}"
            ),
            # SSN/National IDs
            "us/ssn_01": lambda: self.faker.ssn(),
            "kr/rrn_01": lambda: self._generate_korean_rrn(),
            # Credit cards
            "comm/credit_card_visa_01": lambda: self.faker.credit_card_number(card_type="visa"),
            "comm/credit_card_mastercard_01": lambda: (
                self.faker.credit_card_number(card_type="mastercard")
            ),
            # Names
            "kr/korean_name_01": lambda: self._generate_korean_name(),
            # Addresses
            "us/zipcode_01": lambda: self.faker.zipcode(),
            "kr/zipcode_01": lambda: f"{self._rng.randint(10000, 99999)}",
            # IPs
            "comm/ipv4_01": lambda: self.faker.ipv4(),
            "comm/ipv6_01": lambda: self.faker.ipv6(),
            # URLs
            "comm/url_01": lambda: self.faker.url(),
            # Tokens - using secrets for cryptographically secure generation
            "comm/aws_access_key_01": lambda: (
                "AKIA"
                + "".join(
                    secrets.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789") for _ in range(16)
                )
            ),
            "comm/github_token_01": lambda: (
                "ghp_"
                + "".join(
                    secrets.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_")
                    for _ in range(36)
                )
            ),
            "comm/google_api_key_01": lambda: (
                "AIza"
                + "".join(
                    secrets.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_")
                    for _ in range(35)
                )
            ),
            # Coordinates
            "comm/latitude_01": lambda: f"{self.faker.latitude()}",
            "comm/longitude_01": lambda: f"{self.faker.longitude()}",
        }

    def _generate_korean_rrn(self) -> str:
        """Generate a fake Korean Resident Registration Number."""
        # YYMMDD-GNNNNNN (G: 1-4 for birth year/gender)
        year = self._rng.randint(50, 99)
        month = self._rng.randint(1, 12)
        day = self._rng.randint(1, 28)
        gender = self._rng.randint(1, 4)
        serial = self._rng.randint(100000, 999999)
        return f"{year:02d}{month:02d}{day:02d}-{gender}{serial:06d}"

    def _generate_korean_name(self) -> str:
        """Generate a fake Korean name."""
        surnames = ["김", "이", "박", "최", "정", "강", "조", "윤", "장", "임"]
        given_chars = [
            "민",
            "서",
            "준",
            "지",
            "하",
            "도",
            "현",
            "수",
            "영",
            "우",
            "진",
            "은",
            "재",
            "윤",
        ]

        surname = self._rng.choice(surnames)
        given_name = self._rng.choice(given_chars) + self._rng.choice(given_chars)
        return surname + given_name

    def from_pattern(self, pattern_id: str) -> str:
        """
        Generate fake data matching a specific pattern.

        Args:
            pattern_id: Pattern ID (e.g., "comm/email_01")

        Returns:
            Generated fake data string

        Raises:
            ValueError: If pattern_id is not supported
        """
        if pattern_id not in self._pattern_generators:
            raise ValueError(f"Pattern '{pattern_id}' is not supported for fake data generation")

        return self._pattern_generators[pattern_id]()

    def generate_text_with_pii(
        self,
        num_records: int = 10,
        include_patterns: Optional[List[str]] = None,
    ) -> str:
        """
        Generate text with embedded PII.

        Args:
            num_records: Number of records to generate
            include_patterns: List of pattern IDs to include (None = all)

        Returns:
            Generated text with PII
        """
        if include_patterns is None:
            include_patterns = list(self._pattern_generators.keys())[:5]

        lines = []
        for i in range(num_records):
            record = f"Record {i+1}:\n"
            record += f"  Name: {self.faker.name()}\n"
            record += f"  Email: {self.from_pattern('comm/email_01')}\n"

            for pattern_id in include_patterns:
                if pattern_id in self._pattern_generators and pattern_id != "comm/email_01":
                    try:
                        value = self.from_pattern(pattern_id)
                        label = pattern_id.split("/")[-1].replace("_", " ").title()
                        record += f"  {label}: {value}\n"
                    except Exception:
                        pass

            lines.append(record)

        return "\n".join(lines)

    def create_csv_file(
        self,
        output_path: Union[str, Path],
        rows: int = 100,
        include_pii: bool = True,
    ) -> None:
        """
        Create a CSV file with fake data.

        Args:
            output_path: Output file path
            rows: Number of rows to generate
            include_pii: Whether to include PII data
        """
        import csv

        output_path = Path(output_path)

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            # Header
            headers = ["id", "name", "email", "phone", "address", "city", "country"]
            if include_pii:
                headers.extend(["ssn", "credit_card", "ip_address"])

            writer.writerow(headers)

            # Data rows
            for i in range(rows):
                row = [
                    i + 1,
                    self.faker.name(),
                    self.faker.email(),
                    self.faker.phone_number(),
                    self.faker.street_address(),
                    self.faker.city(),
                    self.faker.country(),
                ]

                if include_pii:
                    row.extend(
                        [
                            self.faker.ssn(),
                            self.faker.credit_card_number(),
                            self.faker.ipv4(),
                        ]
                    )

                writer.writerow(row)

        logger.info(f"Created CSV file: {output_path} ({rows} rows)")

    def create_json_file(
        self,
        output_path: Union[str, Path],
        records: int = 50,
        include_pii: bool = True,
    ) -> None:
        """
        Create a JSON file with fake data.

        Args:
            output_path: Output file path
            records: Number of records to generate
            include_pii: Whether to include PII data
        """
        output_path = Path(output_path)

        data = []
        for i in range(records):
            record = {
                "id": i + 1,
                "name": self.faker.name(),
                "email": self.faker.email(),
                "phone": self.faker.phone_number(),
                "address": {
                    "street": self.faker.street_address(),
                    "city": self.faker.city(),
                    "country": self.faker.country(),
                },
                "created_at": self.faker.iso8601(),
            }

            if include_pii:
                record.update(
                    {
                        "ssn": self.faker.ssn(),
                        "credit_card": self.faker.credit_card_number(),
                        "ip_address": self.faker.ipv4(),
                    }
                )

            data.append(record)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"Created JSON file: {output_path} ({records} records)")

    def create_sqlite_file(
        self,
        output_path: Union[str, Path],
        records: int = 100,
        include_pii: bool = True,
    ) -> None:
        """
        Create a SQLite database file with fake data.

        Args:
            output_path: Output file path
            records: Number of records to generate
            include_pii: Whether to include PII data
        """
        output_path = Path(output_path)

        # Create database
        conn = sqlite3.connect(output_path)
        cursor = conn.cursor()

        # Create table
        if include_pii:
            cursor.execute(
                """
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY,
                    name TEXT,
                    email TEXT,
                    phone TEXT,
                    address TEXT,
                    ssn TEXT,
                    credit_card TEXT,
                    ip_address TEXT,
                    created_at TEXT
                )
            """
            )
        else:
            cursor.execute(
                """
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY,
                    name TEXT,
                    email TEXT,
                    phone TEXT,
                    address TEXT,
                    created_at TEXT
                )
            """
            )

        # Insert data
        for i in range(records):
            if include_pii:
                cursor.execute(
                    """
                    INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        i + 1,
                        self.faker.name(),
                        self.faker.email(),
                        self.faker.phone_number(),
                        self.faker.address(),
                        self.faker.ssn(),
                        self.faker.credit_card_number(),
                        self.faker.ipv4(),
                        self.faker.iso8601(),
                    ),
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO users VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (
                        i + 1,
                        self.faker.name(),
                        self.faker.email(),
                        self.faker.phone_number(),
                        self.faker.address(),
                        self.faker.iso8601(),
                    ),
                )

        conn.commit()
        conn.close()

        logger.info(f"Created SQLite file: {output_path} ({records} records)")

    def create_log_file(
        self,
        output_path: Union[str, Path],
        lines: int = 1000,
        include_pii: bool = True,
        log_format: str = "apache",
    ) -> None:
        """
        Create a log file with fake data.

        Args:
            output_path: Output file path
            lines: Number of log lines to generate
            include_pii: Whether to include PII in logs
            log_format: Log format ('apache', 'json', 'syslog')
        """
        output_path = Path(output_path)

        with open(output_path, "w", encoding="utf-8") as f:
            for i in range(lines):
                if log_format == "apache":
                    line = self._generate_apache_log(include_pii)
                elif log_format == "json":
                    line = self._generate_json_log(include_pii)
                elif log_format == "syslog":
                    line = self._generate_syslog(include_pii)
                else:
                    line = self._generate_apache_log(include_pii)

                f.write(line + "\n")

        logger.info(f"Created log file: {output_path} ({lines} lines, format={log_format})")

    def _generate_apache_log(self, include_pii: bool) -> str:
        """Generate Apache-style log entry."""
        ip = self.faker.ipv4()
        timestamp = datetime.now().strftime("%d/%b/%Y:%H:%M:%S +0000")
        method = self._rng.choice(["GET", "POST", "PUT", "DELETE"])
        path = f"/{self.faker.uri_path()}"
        status = self._rng.choice([200, 201, 301, 400, 404, 500])
        size = self._rng.randint(100, 50000)

        if include_pii and self._rng.random() > 0.7:
            # Sometimes include email or token in query string
            path += f"?email={self.faker.email()}"

        return f'{ip} - - [{timestamp}] "{method} {path} HTTP/1.1" {status} {size}'

    def _generate_json_log(self, include_pii: bool) -> str:
        """Generate JSON-formatted log entry."""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "level": self._rng.choice(["INFO", "WARNING", "ERROR", "DEBUG"]),
            "message": self.faker.sentence(),
            "ip": self.faker.ipv4(),
            "user_agent": self.faker.user_agent(),
        }

        if include_pii and self._rng.random() > 0.7:
            log_entry["user_email"] = self.faker.email()
            log_entry["user_id"] = str(self.faker.uuid4())

        return json.dumps(log_entry)

    def _generate_syslog(self, include_pii: bool) -> str:
        """Generate syslog-style entry."""
        timestamp = datetime.now().strftime("%b %d %H:%M:%S")
        hostname = self.faker.hostname()
        process = self._rng.choice(["sshd", "kernel", "systemd", "cron"])
        pid = self._rng.randint(1000, 99999)
        message = self.faker.sentence()

        if include_pii and self._rng.random() > 0.8:
            message += f" user={self.faker.user_name()} ip={self.faker.ipv4()}"

        return f"{timestamp} {hostname} {process}[{pid}]: {message}"

    def create_text_file(
        self,
        output_path: Union[str, Path],
        paragraphs: int = 20,
        include_pii: bool = True,
    ) -> None:
        """
        Create a text file with fake content.

        Args:
            output_path: Output file path
            paragraphs: Number of paragraphs to generate
            include_pii: Whether to include PII data
        """
        output_path = Path(output_path)

        with open(output_path, "w", encoding="utf-8") as f:
            for i in range(paragraphs):
                paragraph = self.faker.paragraph(nb_sentences=5)

                if include_pii and self._rng.random() > 0.6:
                    # Inject PII into some paragraphs
                    paragraph += f" Contact: {self.faker.email()} or {self.faker.phone_number()}."

                f.write(paragraph + "\n\n")

        logger.info(f"Created text file: {output_path} ({paragraphs} paragraphs)")

    def supported_patterns(self) -> List[str]:
        """
        Get list of supported pattern IDs for generation.

        Returns:
            List of pattern IDs
        """
        return list(self._pattern_generators.keys())
