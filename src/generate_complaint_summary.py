"""
FDA Complaint Summarization Bridge for Surgical Robotics.
Consumes structured case payloads and generates local zero-egress summaries via Ollama.
"""

import argparse
import json
import logging
from pathlib import Path
import sys
import urllib.error
import urllib.request

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("ComplaintSummarizer")

OLLAMA_ENDPOINT = "http://localhost:11434/api/generate"

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate FDA 21 CFR 820 compliant summary from telemetry JSON."
    )
    parser.add_argument(
        "-i", "--input",
        type=Path,
        required=True,
        help="Path to structured telemetry JSON"
    )
    parser.add_argument(
        "-m", "--model",
        type=str,
        default="llama3.2:latest",
        help="Local Ollama model name"
    )
    return parser.parse_args()

def generate_summary(payload_path: Path, model_name: str) -> str:
    if not payload_path.is_file():
        raise FileNotFoundError(f"Input payload missing: {payload_path.resolve()}")

    telemetry_data = json.loads(payload_path.read_text(encoding="utf-8"))

    prompt_text = (
        "You are a regulatory complaint investigator for surgical robotics under FDA 21 CFR 820. "
        "Summarize these telemetry anomalies in 3 concise bullet points identifying the affected subsystems "
        f"and immediate safety risks:\n\n{json.dumps(telemetry_data, indent=2)}"
    )

    request_body = json.dumps({
        "model": model_name,
        "prompt": prompt_text,
        "stream": False
    }).encode("utf-8")

    req = urllib.request.Request(
        OLLAMA_ENDPOINT,
        data=request_body,
        headers={"Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            return res_data.get("response", "No response text found.")
    except urllib.error.URLError as err:
        logger.error("Failed to connect to local Ollama inference service: %s", err)
        sys.exit(1)

def main():
    args = parse_args()
    logger.info("Generating summary for: %s using [%s]", args.input.name, args.model)
    
    summary = generate_summary(args.input, args.model)
    print("\n" + "=" * 60)
    print("REGULATORY TELEMETRY SUMMARY REPORT (ZERO EGRESS)")
    print("=" * 60)
    print(summary)
    print("=" * 60 + "\n")

if __name__ == "__main__":
    main()
