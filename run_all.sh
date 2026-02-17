#!/usr/bin/env bash
# Run all three benchmarks + comparisons and generate final report.
#
# Usage:
#   ./run_all.sh              # Full run (downloads data first)
#   ./run_all.sh --quick      # Quick run using sample/landmark data only

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

QUICK=false
if [[ "${1:-}" == "--quick" ]]; then
    QUICK=true
fi

# Activate venv if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║         Context Graph Benchmarks — Full Suite                  ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""

if [ "$QUICK" = true ]; then
    echo "Mode: QUICK (sample/landmark data only — no downloads)"
    echo ""
else
    echo "Mode: FULL (downloading public datasets)"
    echo ""

    # ── Download datasets ──────────────────────────────────────────
    echo "━━━ Step 1/6: Downloading datasets ━━━"
    echo ""

    echo "[1/3] ICIJ Offshore Leaks..."
    bash icij_offshore/download.sh || echo "  (ICIJ download failed — will skip this benchmark)"
    echo ""

    echo "[2/3] SCOTUS Cases..."
    bash scotus_citations/download.sh || echo "  (SCOTUS download failed — using landmark data)"
    echo ""

    echo "[3/3] FDA FAERS..."
    bash fda_faers/download.sh || echo "  (FAERS download failed — using sample data)"
    echo ""
fi

# ── Benchmark 1: ICIJ Offshore Leaks ──────────────────────────────
echo "━━━ Step 2/6: Benchmark 1 — ICIJ Offshore Leaks ━━━"
echo ""

if [ "$QUICK" = true ]; then
    echo "  [skip] ICIJ requires downloaded data (run without --quick)"
else
    if [ -d "icij_offshore/data" ] && ls icij_offshore/data/*.csv >/dev/null 2>&1; then
        python3 -m icij_offshore.benchmark --limit 5000
    else
        echo "  [skip] ICIJ data not available"
    fi
fi
echo ""

# ── Benchmark 2: SCOTUS Citations ─────────────────────────────────
echo "━━━ Step 3/6: Benchmark 2 — SCOTUS Citations ━━━"
echo ""

if [ "$QUICK" = true ]; then
    python3 -m scotus_citations.benchmark --use-landmark
else
    python3 -m scotus_citations.benchmark
fi
echo ""

# ── Benchmark 3: FDA FAERS ────────────────────────────────────────
echo "━━━ Step 4/6: Benchmark 3 — FDA FAERS ━━━"
echo ""

if [ "$QUICK" = true ]; then
    python3 -m fda_faers.benchmark --use-sample
else
    python3 -m fda_faers.benchmark
fi
echo ""

# ── Comparisons ───────────────────────────────────────────────────
echo "━━━ Step 5/6: Running comparisons ━━━"
echo ""

echo "[Neo4j baseline — SCOTUS]"
python3 -m compare.neo4j_baseline --benchmark scotus
echo ""

echo "[Neo4j baseline — FAERS]"
python3 -m compare.neo4j_baseline --benchmark faers
echo ""

echo "[Vector baseline — SCOTUS]"
python3 -m compare.vector_baseline --benchmark scotus
echo ""

echo "[Vector baseline — FAERS]"
python3 -m compare.vector_baseline --benchmark faers
echo ""

# ── Generate Report ───────────────────────────────────────────────
echo "━━━ Step 6/6: Generating report ━━━"
echo ""

python3 -m compare.generate_report
echo ""

echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║                    BENCHMARKS COMPLETE                         ║"
echo "╠══════════════════════════════════════════════════════════════════╣"
echo "║  Results: RESULTS.md                                           ║"
echo "║  Details: */results/benchmark_results.json                     ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
