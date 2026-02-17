#!/usr/bin/env bash
# Download FDA FAERS (Adverse Event Reporting System) data.
#
# Source: https://fis.fda.gov/extensions/FPD-QDE-FAERS/FPD-QDE-FAERS.html
#
# FAERS data is published quarterly as ASCII pipe-delimited files.
# We download the most recent quarter for benchmarking.
#
# Files:
#   - DRUG*.txt   — drugs involved in each report
#   - REAC*.txt   — reactions (adverse events)
#   - OUTC*.txt   — patient outcomes
#   - INDI*.txt   — indications (why drug was prescribed)
#   - DEMO*.txt   — demographics (case identifiers)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DATA_DIR="${SCRIPT_DIR}/data"

mkdir -p "$DATA_DIR"

# Use 2024 Q3 data (most recent stable release)
QUARTER="2024q3"
BASE_URL="https://fis.fda.gov/content/Exports/faers_ascii_${QUARTER}.zip"

echo "=== FDA FAERS — Downloading ${QUARTER} ==="
echo "Target: ${DATA_DIR}"
echo ""

ZIP_FILE="${DATA_DIR}/faers_${QUARTER}.zip"

if [ -f "${DATA_DIR}/DRUG${QUARTER}.txt" ] || [ -f "${DATA_DIR}/DRUG24Q3.txt" ]; then
    echo "  [skip] FAERS ${QUARTER} data already exists"
else
    echo "  [download] FAERS ${QUARTER} (this may take a few minutes)..."
    curl -fSL "$BASE_URL" -o "$ZIP_FILE" || {
        echo ""
        echo "  [fallback] Direct download failed."
        echo "  Please download manually from:"
        echo "    https://fis.fda.gov/extensions/FPD-QDE-FAERS/FPD-QDE-FAERS.html"
        echo "  Select '${QUARTER}' and download the ASCII zip."
        echo "  Extract to: ${DATA_DIR}/"
        exit 1
    }
    echo "  [extract] Unzipping..."
    unzip -o "$ZIP_FILE" -d "$DATA_DIR"
    rm -f "$ZIP_FILE"

    # FAERS zips contain a subdirectory; flatten if needed
    if [ -d "${DATA_DIR}/ASCII" ] || [ -d "${DATA_DIR}/ascii" ]; then
        mv "${DATA_DIR}"/[Aa][Ss][Cc][Ii][Ii]/* "$DATA_DIR"/ 2>/dev/null || true
        rmdir "${DATA_DIR}"/[Aa][Ss][Cc][Ii][Ii] 2>/dev/null || true
    fi

    echo "  [done]"
fi

echo ""
echo "=== Download complete ==="
echo "Files in ${DATA_DIR}:"
ls -lh "$DATA_DIR"/*.txt 2>/dev/null || ls -lh "$DATA_DIR"/*.TXT 2>/dev/null || echo "  (no data files found)"

# Show row counts
echo ""
echo "Row counts:"
for f in "$DATA_DIR"/DRUG*.txt "$DATA_DIR"/DRUG*.TXT "$DATA_DIR"/REAC*.txt "$DATA_DIR"/REAC*.TXT 2>/dev/null; do
    if [ -f "$f" ]; then
        echo "  $(basename "$f"): $(wc -l < "$f") rows"
    fi
done
