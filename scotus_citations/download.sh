#!/usr/bin/env bash
# Download SCOTUS case data from public sources.
#
# Sources:
#   1. Supreme Court Database (SCDB) — case-level data with justice votes
#      http://supremecourtdatabase.org/
#   2. CourtListener — citation network via bulk API
#      https://www.courtlistener.com/api/bulk-info/
#
# For benchmarking, we use the SCDB case-centered data (CSV)
# and CourtListener citation edges.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DATA_DIR="${SCRIPT_DIR}/data"

mkdir -p "$DATA_DIR"

echo "=== SCOTUS Citations — Downloading ==="
echo "Target: ${DATA_DIR}"
echo ""

# ── 1. Supreme Court Database (case-level with justice votes) ──────
SCDB_URL="http://supremecourtdatabase.org/_media/01_case_centered_citation.csv.zip"
SCDB_FILE="${DATA_DIR}/scdb_cases.csv"

if [ -f "$SCDB_FILE" ]; then
    echo "  [skip] SCDB cases already exists"
else
    echo "  [download] SCDB case-centered data..."
    curl -fSL "$SCDB_URL" -o "${SCDB_FILE}.zip" || {
        echo "  [fallback] Direct SCDB download failed."
        echo "  Please download manually from: http://supremecourtdatabase.org/data.php"
        echo "  Save as: ${SCDB_FILE}"
    }
    if [ -f "${SCDB_FILE}.zip" ]; then
        unzip -o "${SCDB_FILE}.zip" -d "$DATA_DIR"
        # Rename to standard name
        mv "$DATA_DIR"/*case_centered*.csv "$SCDB_FILE" 2>/dev/null || true
        rm -f "${SCDB_FILE}.zip"
        echo "  [done] $(wc -l < "$SCDB_FILE") rows"
    fi
fi

# ── 2. CourtListener citation edges ───────────────────────────────
CL_URL="https://www.courtlistener.com/api/bulk-data/citations/scotus.csv.gz"
CL_FILE="${DATA_DIR}/citations.csv"

if [ -f "$CL_FILE" ]; then
    echo "  [skip] Citation edges already exists"
else
    echo "  [download] CourtListener citation edges..."
    curl -fSL "$CL_URL" -o "${CL_FILE}.gz" || {
        echo "  [fallback] CourtListener bulk download failed."
        echo "  Alternative: use the API at https://www.courtlistener.com/api/rest/v4/citations/"
        echo "  Or download from: https://www.courtlistener.com/api/bulk-info/"
    }
    if [ -f "${CL_FILE}.gz" ]; then
        gunzip "${CL_FILE}.gz"
        echo "  [done] $(wc -l < "$CL_FILE") rows"
    fi
fi

# ── 3. Landmark cases (curated for demo) ──────────────────────────
# If bulk downloads fail, we provide a curated dataset of ~200 landmark
# cases with known citation chains for the benchmark demo.
LANDMARK_FILE="${DATA_DIR}/landmark_cases.csv"

if [ ! -f "$SCDB_FILE" ] && [ ! -f "$LANDMARK_FILE" ]; then
    echo ""
    echo "  [info] Bulk data not available. Creating landmark cases dataset..."
    echo "  This curated dataset includes ~200 key SCOTUS cases with citation links."
    echo "  Run: python -m scotus_citations.create_landmark_data"
fi

echo ""
echo "=== Download complete ==="
echo "Files in ${DATA_DIR}:"
ls -lh "$DATA_DIR"/* 2>/dev/null || echo "  (no files found)"
