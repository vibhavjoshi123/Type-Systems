#!/bin/bash
set -e

# ============================================================
#  Hypergraph Context Graph - Quickstart Script
#  Pulls code, installs deps, configures env, sets up TypeDB,
#  and starts the API server.
# ============================================================

# ── Detect python/pip commands (macOS uses python3/pip3) ───────
if command -v python3 &>/dev/null; then
    PY=python3
elif command -v python &>/dev/null; then
    PY=python
else
    echo "ERROR: Python not found. Install Python 3.11+ first."
    exit 1
fi

if command -v pip3 &>/dev/null; then
    PIP=pip3
elif command -v pip &>/dev/null; then
    PIP=pip
else
    echo "ERROR: pip not found. Install pip first."
    exit 1
fi

echo "============================================================"
echo "  Hypergraph Context Graph - Quickstart"
echo "  Using: $PY, $PIP"
echo "============================================================"
echo ""

# ── Step 1: Clone or pull latest code ──────────────────────────
echo "[1/6] Getting latest code..."
if [ -d "Hypergraph-for-Context-Graph" ]; then
    cd Hypergraph-for-Context-Graph
    git pull origin claude/review-docs-start-build-Ceu1x
else
    git clone https://github.com/vibhavjoshi123/Hypergraph-for-Context-Graph.git
    cd Hypergraph-for-Context-Graph
    git checkout claude/review-docs-start-build-Ceu1x
fi
echo "  Done."
echo ""

# ── Step 2: Install dependencies ──────────────────────────────
echo "[2/6] Installing dependencies..."
$PIP install -e ".[dev]" --quiet
echo "  Done."
echo ""

# ── Step 3: Create .env file ──────────────────────────────────
echo "[3/6] Configuring environment..."
if [ -f .env ]; then
    echo "  .env already exists, skipping."
else
    echo "  Creating .env file — you'll need to fill in your keys."
    echo ""

    # Prompt for values
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

# ── Step 4: Run linter ────────────────────────────────────────
echo "[4/6] Running linter..."
ruff check src/ tests/ || { $PIP install ruff --quiet && ruff check src/ tests/; }
echo "  Done."
echo ""

# ── Step 5: Setup TypeDB (create DB, load schema, seed data) ──
echo "[5/6] Setting up TypeDB (schema + seed data)..."
$PY scripts/setup_typedb.py --seed
echo ""

# ── Step 6: Start API server ──────────────────────────────────
echo "[6/6] Starting API server on http://localhost:8000 ..."
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

$PY -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
