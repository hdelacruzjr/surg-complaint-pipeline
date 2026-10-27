#!/bin/bash
# ==============================================================================
# Complaint Investigation Ingestion & Pre-flight Parser (Medallion Pattern)
# ==============================================================================
set -euo pipefail

# 1. Resolve pipeline root dynamically
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PIPELINE_ROOT="$(dirname "$SCRIPT_DIR")"

# 2. Medallion Directory Paths
INCOMING_DIR="$PIPELINE_ROOT/incoming"
BRONZE_RAW="$PIPELINE_ROOT/bronze/raw_vault"
BRONZE_AUDIT="$PIPELINE_ROOT/bronze/audit_logs"
SILVER_SANITIZED="$PIPELINE_ROOT/silver/sanitized"
SILVER_PAYLOADS="$PIPELINE_ROOT/silver/payloads"
GOLD_REPORTS="$PIPELINE_ROOT/gold/reports"
SRC_DIR="$PIPELINE_ROOT/src"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
AUDIT_LOG="$BRONZE_AUDIT/ingest_${TIMESTAMP}.log"

# Ensure directories exist
mkdir -p "$INCOMING_DIR" "$BRONZE_RAW" "$BRONZE_AUDIT" "$SILVER_SANITIZED" "$SILVER_PAYLOADS" "$GOLD_REPORTS" "$SRC_DIR"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" \vert{} tee -a "$AUDIT_LOG"
}

log "=== Starting Ingestion Run (Medallion Flow) ==="

FILE_COUNT=$(ls "$INCOMING_DIR"/* 2>/dev/null | wc -l || true)

if [ "$FILE_COUNT" -eq 0 ]; then
    log "No incoming files found in $INCOMING_DIR. Exiting cleanly."
    exit 0
fi

log "Found $FILE_COUNT file(s) in incoming landing zone."

for file in "$INCOMING_DIR"/*; do
    [ -e "$file" ] || continue
    filename=$(basename "$file")
    log "Processing incoming file: $filename"

    # Step A: Bronze Archive (Locked read-only)
    BRONZE_TARGET="$BRONZE_RAW/${filename}"
    cp -f "$file" "$BRONZE_TARGET"
    chmod 444 "$BRONZE_TARGET"
    log "Archived to Bronze (chmod 444): $BRONZE_TARGET"

    # Step B: Parsing and Triage
    case "$filename" in
        *.log)
            ERRORS_FOUND=$(grep -E "ERROR\vert{}FATAL" "$file" || true)
            if [ -n "$ERRORS_FOUND" ]; then
                log "CRITICAL: Faults detected in $filename"
                ERR_CODE=$(grep "Error Code:" "$file" | awk -F'Error Code: ' '{print $2}' || echo "UNKNOWN")
                log "Extracted Failure Code (awk/grep): $ERR_CODE"
                STALLED_JOINT=$(grep "Actuator Stall" "$file" | awk '{print $6, $7}' || echo "UNKNOWN")
                log "Extracted Joint Telemetry (awk): $STALLED_JOINT"
            fi
            mv "$file" "$SILVER_SANITIZED/$filename"
            ;;

        *.txt)
            log "Sanitizing clinical narrative for PHI (sed)..."
            sed -e 's/Patient Name: .*/Patient Name: [REDACTED_PATIENT_PHI]/' \
                -e 's/Operating Surgeon: .*/Operating Surgeon: [REDACTED_CLINICAL_STAFF]/' \
                "$file" > "$SILVER_SANITIZED/$filename"
            rm "$file"
            log "Saved sanitized narrative to Silver: $SILVER_SANITIZED/$filename"
            ;;

        *)
            log "Unknown file type: $filename. Moving to Silver as-is."
            mv "$file" "$SILVER_SANITIZED/$filename"
            ;;
    esac
done

log "=== Ingestion Run Completed Successfully ==="
