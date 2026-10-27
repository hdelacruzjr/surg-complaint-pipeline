#!/usr/bin/env python3
"""
Complaint Investigation Payload Extractor (Silver Layer Pipeline)
Extracts unstructured telemetry and clinical complaint narratives 
into strongly-typed JSON payloads for regulatory reporting.
"""

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class TelemetryMetrics:
    observed_current_amps: Optional[float]
    threshold_limit_amps: Optional[float]
    stalled_joint: Optional[str]
    safety_interlock_engaged: bool


@dataclass(frozen=True)
class CasePayload:
    case_id: str
    device_serial: str
    procedure: str
    subsystem: str
    error_code: str
    patient_harm_reported: bool
    telemetry: TelemetryMetrics
    clinical_summary: str
    metadata: dict = field(default_factory=dict)


class SurgicalCaseParser:
    def __init__(self, case_id: str, silver_sanitized_dir: Path):
        self.case_id = case_id
        self.sanitized_dir = silver_sanitized_dir

    def _read_file_safe(self, file_path: Path) -> str:
        if not file_path.exists():
            return ""
        return file_path.read_text(encoding="utf-8")

    def parse_telemetry(self, log_text: str) -> tuple[str, str, TelemetryMetrics]:
        err_match = re.search(r"Error Code:\s*(ERR_[A-Z_]+[0-9]{3})", log_text)
        error_code = err_match.group(1) if err_match else "UNKNOWN_ERROR"

        subsys_match = re.search(r"\[(SUBSYS_[A-Z]+)\]", log_text)
        subsystem = subsys_match.group(1) if subsys_match else "UNKNOWN_SUBSYS"

        joint_match = re.search(r"Actuator Stall:\s*(Joint\s*\d+)", log_text)
        stalled_joint = joint_match.group(1) if joint_match else None

        current_match = re.search(
            r"motor current exceeded threshold \((\d+\.?\d*)A > (\d+\.?\d*)A limit\)",
            log_text,
        )
        observed_current = float(current_match.group(1)) if current_match else None
        threshold_current = float(current_match.group(2)) if current_match else None
        interlock = "Safety interlock triggered" in log_text

        telemetry = TelemetryMetrics(
            observed_current_amps=observed_current,
            threshold_limit_amps=threshold_current,
            stalled_joint=stalled_joint,
            safety_interlock_engaged=interlock,
        )
        return subsystem, error_code, telemetry

    def parse_narrative(self, narrative_text: str) -> tuple[str, str, bool, str]:
        serial_match = re.search(r"Device Serial:\s*([A-Z0-9-]+)", narrative_text)
        device_serial = serial_match.group(1) if serial_match else "UNKNOWN_SERIAL"

        proc_match = re.search(r"Procedure:\s*(.+)", narrative_text)
        procedure = proc_match.group(1).strip() if proc_match else "Unspecified Procedure"

        harm_pattern = r"(death|serious injury|laceration|hemorrhage|permanent damage)"
        harm_found = bool(re.search(harm_pattern, narrative_text, re.IGNORECASE))
        if re.search(r"no tissue laceration.*patient stable", narrative_text, re.IGNORECASE):
            harm_found = False

        incident_match = re.search(r"Incident Narrative:\s*(.*)", narrative_text, re.DOTALL)
        clinical_summary = incident_match.group(1).strip() if incident_match else narrative_text.strip()

        return device_serial, procedure, harm_found, clinical_summary

    def build_payload(self) -> CasePayload:
        log_file = self.sanitized_dir / f"case_{self.case_id}_device.log"
        narrative_file = self.sanitized_dir / f"complaint_{self.case_id}.txt"

        if not log_file.exists():
            candidates = list(self.sanitized_dir.glob(f"*{self.case_id}*.log"))
            if candidates:
                log_file = candidates[0]

        if not narrative_file.exists():
            candidates = list(self.sanitized_dir.glob(f"*{self.case_id}*.txt"))
            if candidates:
                narrative_file = candidates[0]

        log_content = self._read_file_safe(log_file)
        narrative_content = self._read_file_safe(narrative_file)

        if not log_content and not narrative_content:
            raise FileNotFoundError(
                f"No sanitized logs or narratives found for Case ID {self.case_id} in {self.sanitized_dir}"
            )

        subsystem, error_code, telemetry = self.parse_telemetry(log_content)
        device_serial, procedure, harm_reported, summary = self.parse_narrative(narrative_content)

        return CasePayload(
            case_id=str(self.case_id),
            device_serial=device_serial,
            procedure=procedure,
            subsystem=subsystem,
            error_code=error_code,
            patient_harm_reported=harm_reported,
            telemetry=telemetry,
            clinical_summary=summary,
            metadata={
                "source_log": log_file.name if log_file.exists() else None,
                "source_narrative": narrative_file.name if narrative_file.exists() else None,
            },
        )


def main():
    parser = argparse.ArgumentParser(description="Extract structured case payload from Silver logs.")
    parser.add_argument("--case", required=True, help="Incident Case ID (e.g., 1042)")
    parser.add_argument("--silver-dir", default=None, help="Path to silver directory")
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    pipeline_root = script_dir.parent

    silver_sanitized = Path(args.silver_dir).resolve() / "sanitized" if args.silver_dir else pipeline_root / "silver" / "sanitized"
    silver_payloads = Path(args.silver_dir).resolve() / "payloads" if args.silver_dir else pipeline_root / "silver" / "payloads"

    silver_payloads.mkdir(parents=True, exist_ok=True)

    print(f"[INFO] Parsing Case ID: {args.case}")
    print(f"[INFO] Reading from: {silver_sanitized}")

    case_parser = SurgicalCaseParser(case_id=args.case, silver_sanitized_dir=silver_sanitized)
    
    try:
        payload = case_parser.build_payload()
    except Exception as e:
        print(f"[ERROR] Failed to extract payload: {e}", file=sys.stderr)
        sys.exit(1)

    out_file = silver_payloads / f"case_{args.case}_payload.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(asdict(payload), f, indent=2)

    print(f"[SUCCESS] Payload written to: {out_file}")


if __name__ == "__main__":
    main()
