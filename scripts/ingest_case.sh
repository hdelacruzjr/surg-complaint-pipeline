#!/bin/bash
# ==============================================================================
# Complaint Investigation Ingestion & Pre-flight Parser
# Role: AI Application Software Developer (Robotic Surgical Systems)
# ==============================================================================
set -eu

# Resolve pipeline root dynamically from the script's location
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PIPELINE_ROOT="$(dirname "$SCRIPT_DIR")"

# Define Paths for Medallion Layers & Code
INCOMING_DIR="$PIPELINE_ROOT/incoming"
BRONZE_DIR="$PIPELINE_ROOT/bronze/raw_vault"
AUDIT_DIR="$PIPELINE_ROOT/bronze/audit_logs"
SILVER_SANITIZED="$PIPELINE_ROOT/silver/sanitized"
SRC_DIR="$PIPELINE_ROOT/src"

# Run Timestamps and Logs
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
AUDIT_LOG="$LOGS_DIR/ingest_${TIMESTAMP}.log"
ERROR_LOG="$LOGS_DIR/ingest_${TIMESTAMP}.err"

# Ensure directories exist
mkdir -p "$INCOMING_DIR" "$BRONZE_DIR" "$AUDIT_DIR" "$SILVER_SANITIZED" "$SRC_DIR"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$AUDIT_LOG"
}

log "=== Starting Ingestion Run ==="

# Check if there are any .log files to process
LOG_COUNT=$(ls "$INCOMING_DIR"/*.log 2>/dev/null | wc -l || true)

if [ "$LOG_COUNT" -eq 0 ]; then
    log "No incoming log files found in $INCOMING_DIR. Exiting cleanly."
    exit 0
fi

log "Found $LOG_COUNT case file(s) for pre-processing."

for file in "$INCOMING_DIR"/*.log; do
    [ -e "$file" ] || continue
    filename=$(basename "$file")
    log "Processing case file: $filename"

    # Extract critical errors using grep
    ERRORS_FOUND=$(grep -E "ERROR|FATAL" "$file" || true)

    if [ -n "$ERRORS_FOUND" ]; then
        log "CRITICAL: Subsystem failure detected in $filename"
        # Extract specific error code using grep & awk
        ERR_CODE=$(grep "Error Code:" "$file" | awk -F'Error Code: ' '{print $2}' || echo "UNKNOWN")
        log "Extracted Failure Mode Code: $ERR_CODE"
    else
        log "Notice: No ERROR/FATAL events detected in $filename"
    fi

    # Archive the raw file to processed
    mv "$file" "$PROCESSED_DIR/"
    log "Archived $filename to $PROCESSED_DIR/"
done

log "=== Ingestion Run Completed Successfully ==="
