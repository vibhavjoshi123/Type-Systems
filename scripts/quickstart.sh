#!/bin/bash
set -e

# ============================================================
#  Hypergraph Context Graph - Quickstart Script
#  Pulls code, creates venv, installs deps, configures env,
#  sets up TypeDB, and starts the API server.
#
#  Run from inside the repo:
#    bash scripts/quickstart.sh
# ============================================================

# ── Detect Python 3.11+ (try versioned commands first for macOS) ──
PY=""
for candidate in python3.13 python3.12 python3.11 python3 python; do
    if command -v "$candidate" &>/dev/null; then
        ver=$("$candidate" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null)
        major=$(echo "$ver" | cut -d. -f1)
        minor=$(echo "$ver" | cut -d. -f2)
        if [ "$major" -ge 3 ] && [ "$minor" -ge 11 ]; then
            PY="$candidate"
            break
        fi
    fi
done

if [ -z "$PY" ]; then
    echo "ERROR: Python 3.11+ is required but not found."
    echo ""
    echo "  Install a newer version:"
    echo "  macOS (Homebrew):  brew install python@3.12"
    echo "  Ubuntu/Debian:     sudo apt install python3.12"
    echo "  Or use pyenv:      pyenv install 3.12.0"
    echo ""
    exit 1
fi

echo "============================================================"
echo "  Hypergraph Context Graph - Quickstart"
echo "  Using: $PY ($($PY --version 2>&1))"
echo "============================================================"
echo ""

# ── Step 1: Get into the repo directory ────────────────────────
echo "[1/7] Getting latest code..."
if [ -f "pyproject.toml" ] && grep -q "hypergraph-context-graph" pyproject.toml 2>/dev/null; then
    echo "  Already in repo directory, pulling latest..."
    git pull origin claude/review-docs-start-build-Ceu1x || true
elif [ -d "Hypergraph-for-Context-Graph" ]; then
    cd Hypergraph-for-Context-Graph
    git pull origin claude/review-docs-start-build-Ceu1x
else
    git clone https://github.com/vibhavjoshi123/Hypergraph-for-Context-Graph.git
    cd Hypergraph-for-Context-Graph
    git checkout claude/review-docs-start-build-Ceu1x
fi
echo "  Done."
echo ""

# ── Step 2: Create virtual environment ─────────────────────────
echo "[2/7] Setting up virtual environment..."
if [ -d ".venv" ] && [ -f ".venv/bin/python" ]; then
    echo "  .venv already exists, activating..."
else
    echo "  Creating .venv with $PY..."
    $PY -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
echo "  Activated: $(python --version) at $(which python)"
echo ""

# ── Step 3: Install dependencies ──────────────────────────────
echo "[3/7] Installing dependencies..."
pip install --upgrade pip --quiet
pip install -e ".[dev]" --quiet
echo "  Done."
echo ""

# ── Step 4: Create .env file ──────────────────────────────────
echo "[4/7] Configuring environment..."
if [ -f .env ]; then
    echo "  .env already exists, skipping."
else
    echo "  Creating .env file — fill in your keys below."
    echo ""

    read -rp "  TypeDB Cloud address [https://rv7ii3-0.cluster.typedb.com:80]: " TYPEDB_ADDR
    TYPEDB_ADDR=${TYPEDB_ADDR:-https://rv7ii3-0.cluster.typedb.com:80}

    read -rp "  TypeDB username [admin]: " TYPEDB_USER
    TYPEDB_USER=${TYPEDB_USER:-admin}

    read -rp "  TypeDB password [password]: " TYPEDB_PASS
    TYPEDB_PASS=${TYPEDB_PASS:-password}

    read -rp "  Anthropic API key (sk-ant-...): " ANTHROPIC_KEY

    if [ -z "$ANTHROPIC_KEY" ]; then
        echo "  WARNING: No Anthropic API key provided. LLM features won't work."
        ANTHROPIC_KEY="sk-ant-REPLACE-ME"
    fi

    cat > .env << ENVEOF
# TypeDB Cloud
TYPEDB_ADDRESS=${TYPEDB_ADDR}
TYPEDB_DATABASE=context_graph
TYPEDB_USERNAME=${TYPEDB_USER}
TYPEDB_PASSWORD=${TYPEDB_PASS}
TYPEDB_TLS_ENABLED=true

# Anthropic LLM
LLM_ANTHROPIC_API_KEY=${ANTHROPIC_KEY}
LLM_DEFAULT_PROVIDER=anthropic
LLM_DEFAULT_MODEL=claude-sonnet-4-20250514

# API
API_HOST=0.0.0.0
API_PORT=8000
API_DEBUG=false
LOG_FORMAT=text
LOG_LEVEL=INFO
ENVEOF
    echo "  .env created."
fi
echo ""

# ── Step 5: Run linter ────────────────────────────────────────
echo "[5/7] Running linter..."
ruff check src/ tests/
echo "  Done."
echo ""

# ── Step 6: Setup TypeDB (create DB, load schema, seed data) ──
echo "[6/7] Setting up TypeDB (schema + seed data)..."
python scripts/setup_typedb.py --seed
echo ""

# ── Step 7: Start API server ──────────────────────────────────
echo "[7/7] Starting API server on http://localhost:8000 ..."
echo ""
echo "  Try these endpoints:"
echo "    curl http://localhost:8000/health"
echo "    curl http://localhost:8000/api/v1/entities"
echo "    curl -X POST http://localhost:8000/api/v1/entities \\"
echo '      -H "Content-Type: application/json" \'
echo '      -d '"'"'{"entity_id":"test_001","entity_name":"Test Corp","entity_type":"customer"}'"'"''
echo ""
echo "  Press Ctrl+C to stop the server."
echo "============================================================"
echo ""

python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
