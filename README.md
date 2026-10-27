# Robotic Surgical Complaint Processing Pipeline

A production-grade, Linux-first Medallion data pipeline designed to automate post-market surveillance complaint investigations for robotic surgical systems in compliance with **FDA 21 CFR Part 820** (Quality System Regulation), **21 CFR Part 803** (Medical Device Reporting), and **21 CFR Part 11** (Electronic Records and Signatures).

---

## Architecture Overview

The system implements a decoupled, event-driven Medallion architecture separating Linux shell triage from Python semantic data contracts and downstream LLM inference:

```text
       [ External Hospital SFTP / Device Drop ]
                          │
                          ▼
               incoming/ (Landing Zone)
                          │
         scripts/ingest_case.sh (POSIX Bash)
         ├── Immutability Archive (chmod 444)
         ├── Fast Telemetry Triage (awk / grep -E)
         └── HIPAA Redaction (sed)
                          │
           ┌──────────────┴──────────────┐
           ▼                             ▼
   bronze/raw_vault/             silver/sanitized/
   (Immutable Raw Audit)         (Redacted Logs & Narratives)
                                         │
                             src/extract_case_payload.py
                             (Python Dataclasses & Regex)
                                         │
                                         ▼
                                 silver/payloads/
                             (Validated JSON Schemas)
                                         │
                         src/generate_complaint_summary.py
                         (Ollama Local GPU / AWS Bedrock)
                                         │
                                         ▼
                                   gold/reports/
                        (FDA Investigation Report Drafts)
cat << 'EOF' > README.md
# Robotic Surgical Complaint Processing Pipeline

A production-grade, Linux-first Medallion data pipeline designed to automate post-market surveillance complaint investigations for robotic surgical systems in compliance with **FDA 21 CFR Part 820** (Quality System Regulation), **21 CFR Part 803** (Medical Device Reporting), and **21 CFR Part 11** (Electronic Records and Signatures).

---

## Architecture Overview

The system implements a decoupled, event-driven Medallion architecture separating Linux shell triage from Python semantic data contracts and downstream LLM inference:

```text
       [ External Hospital SFTP / Device Drop ]
                          │
                          ▼
               incoming/ (Landing Zone)
                          │
         scripts/ingest_case.sh (POSIX Bash)
         ├── Immutability Archive (chmod 444)
         ├── Fast Telemetry Triage (awk / grep -E)
         └── HIPAA Redaction (sed)
                          │
           ┌──────────────┴──────────────┐
           ▼                             ▼
   bronze/raw_vault/             silver/sanitized/
   (Immutable Raw Audit)         (Redacted Logs & Narratives)
                                         │
                             src/extract_case_payload.py
                             (Python Dataclasses & Regex)
                                         │
                                         ▼
                                 silver/payloads/
                             (Validated JSON Schemas)
                                         │
                         src/generate_complaint_summary.py
                         (Ollama Local GPU / AWS Bedrock)
                                         │
                                         ▼
                                   gold/reports/
                        (FDA Investigation Report Drafts)

clear
