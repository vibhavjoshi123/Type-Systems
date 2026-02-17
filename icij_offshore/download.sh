#!/usr/bin/env bash
# Download ICIJ Offshore Leaks data
# Source: https://offshoreleaks.icij.org/pages/database
#
# Files downloaded:
#   - nodes-entities.csv    (~300K offshore companies)
#   - nodes-officers.csv    (~400K directors/shareholders)
#   - nodes-intermediaries.csv (~25K law firms/banks)
#   - nodes-addresses.csv   (~150K registered addresses)
#   - relationships.csv     (~1.3M links between them)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DATA_DIR="${SCRIPT_DIR}/data"

mkdir -p "$DATA_DIR"

BASE_URL="https://offshoreleaks-data.icij.org/offshoreleaks/csv"

FILES=(
    "nodes-entities.csv"
    "nodes-officers.csv"
    "nodes-intermediaries.csv"
    "nodes-addresses.csv"
    "relationships.csv"
)

echo "=== ICIJ Offshore Leaks — Downloading ==="
echo "Target: ${DATA_DIR}"
echo ""

for FILE in "${FILES[@]}"; do
    DEST="${DATA_DIR}/${FILE}"
    if [ -f "$DEST" ]; then
        echo "  [skip] ${FILE} already exists"
    else
        echo "  [download] ${FILE}..."
        curl -fSL "${BASE_URL}/${FILE}.zip" -o "${DEST}.zip"
        unzip -o "${DEST}.zip" -d "$DATA_DIR"
        rm -f "${DEST}.zip"
        echo "  [done] ${FILE} — $(wc -l < "$DEST") rows"
    fi
done

echo ""
echo "=== Download complete ==="
echo "Files in ${DATA_DIR}:"
ls -lh "$DATA_DIR"/*.csv 2>/dev/null || echo "  (no CSV files found)"
