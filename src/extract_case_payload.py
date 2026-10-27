"""
Telemetry Extraction Service for Surgical Robotics.
Extracts structured error payloads from telemetry logs for regulatory reporting.
"""

import argparse
from dataclasses import dataclass, asdict
import json
import logging
from pathlib import Path
import re
import sys
from typing import List

# Module 6: Structured logging for auditable medical records
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("TelemetryExtractor")

# Module 5: Pre-compiled regex with named capture groups (?P<name>...)[cite: 3]
LOG_PATTERN = re.compile(
    r"^\[(?P<timestamp>[^\]]+)\]\s+"
    r"\[(?P<level>[^\]]+)\]\s+"
    r"\[(?P<device>[^\]]+)\]\s+"
    r".*?Code:\s*(?P<error_code>[A-Z0-9_]+)\.\s*"
    r"Temp:\s*(?P<temperature>[\d\.]+)C"
)


# Module 6: Custom domain exception[cite: 3]
class TelemetryParseError(Exception):
    """Raised when a log line fails format validation."""
    pass


# Module 3: Typed data modeling with @dataclass[cite: 3]
@dataclass(frozen=True)
class TelemetryPayload:
    timestamp: str
    severity: str
    subsystem: str
    error_code: str
    temperature_celsius: float

    @classmethod
    def from_log_line(cls, line: str) -> "TelemetryPayload":
        """Parse, validate, and convert a raw log line into a typed payload[cite: 3]."""
        match = LOG_PATTERN.search(line)
        if not match:
            raise TelemetryParseError(f"Line did not match telemetry schema: {line.strip()}")

        data = match.groupdict()
        return cls(
            timestamp=data["timestamp"],
            severity=data["level"],
            subsystem=data["device"],
            error_code=data["error_code"],
            temperature_celsius=float(data["temperature"]),
        )


# Module 1: CLI Design via argparse[cite: 3]
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract structured surgical telemetry into compliant JSON payloads."
    )
    parser.add_argument(
        "-i", "--input",
        type=Path,
        required=True,
        help="Path to the raw input telemetry .log file"
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=Path("output/telemetry_payload.json"),
        help="Destination path for structured JSON (default: output/telemetry_payload.json)"
    )
    return parser.parse_args()


def extract_telemetry(input_path: Path) -> List[TelemetryPayload]:
    """Read a log file and return all successfully parsed telemetry records."""
    # Module 2: Defensive pathlib operations[cite: 3]
    if not input_path.is_file():
        raise FileNotFoundError(f"Source file not found: {input_path.resolve()}")

    records: List[TelemetryPayload] = []
    # Module 2: UTF-8 read_text() context[cite: 3]
    lines = input_path.read_text(encoding="utf-8").splitlines()

    for line_num, raw_line in enumerate(lines, start=1):
        clean_line = raw_line.strip()
        if not clean_line:
            continue

        try:
            record = TelemetryPayload.from_log_line(clean_line)
            records.append(record)
        except TelemetryParseError as err:
            logger.warning("Skipping invalid record at line %d: %s", line_num, err)

    return records


def main():
    args = parse_args()
    input_file: Path = args.input
    output_file: Path = args.output

    logger.info("Initiating ingestion from: %s", input_file.resolve())

    try:
        telemetry_records = extract_telemetry(input_file)
    except FileNotFoundError as err:
        logger.error("IO Failure: %s", err)
        sys.exit(1)

    if not telemetry_records:
        logger.warning("No valid telemetry events extracted. No payload written.")
        sys.exit(0)

    # Module 2: Ensure destination parent directories exist[cite: 3]
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Module 3: Convert dataclasses to dicts for JSON serialization[cite: 3]
    serialized = [asdict(rec) for rec in telemetry_records]
    output_file.write_text(json.dumps(serialized, indent=2), encoding="utf-8")

    logger.info("Extraction complete. %d records serialized to: %s", len(serialized), output_file.resolve())


if __name__ == "__main__":
    main()
