# Hypergraph Context Graph

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![TypeDB](https://img.shields.io/badge/TypeDB-3.x-green.svg)](https://typedb.com/)


**Production-ready Enterprise Context Graph using Hypergraphs and TypeDB**

This project implements a hypergraph-based context graph system for enterprise decision-making, 

## Why Hypergraphs?

Traditional knowledge graphs use pairwise edges (connecting exactly 2 nodes). But enterprise decisions are **n-ary** – they involve multiple entities simultaneously:

> "When a renewal agent proposes a 20% discount, it doesn't just pull from the CRM. It pulls from PagerDuty for incident history, Zendesk for escalation threads, Slack for VP approval from last quarter, Salesforce for the deal record, Snowflake for usage data, and the semantic layer for the definition of 'healthy customer'."

**Hypergraphs** solve this by allowing edges (hyperedges) to connect 3+ nodes, preserving the full context of enterprise decisions.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    ENTERPRISE DATA SOURCES                   │
├─────────┬─────────┬─────────┬─────────┬─────────┬──────────┤
│Salesforce│ Zendesk │  Slack  │PagerDuty│Snowflake│  Custom  │
└────┬────┴────┬────┴────┬────┴────┬────┴────┬────┴────┬─────┘
     │         │         │         │         │         │
     └─────────┴─────────┴────┬────┴─────────┴─────────┘
                              │
                    ┌─────────▼─────────┐
                    │   LLM-Powered     │
                    │   Entity          │  ◄── Claude / GPT-4
                    │   Extraction      │
                    └─────────┬─────────┘
                              │
                    ┌─────────▼─────────┐
                    │     TypeDB        │
                    │   Hypergraph      │  ◄── Native n-ary relations
                    │   Database        │
                    └─────────┬─────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
┌───────▼───────┐    ┌───────▼───────┐    ┌───────▼───────┐
│ ContextAgent  │    │ExecutiveAgent │    │GovernanceAgent│
│ (Traversal)   │    │ (Reasoning)   │    │ (Compliance)  │
└───────────────┘    └───────────────┘    └───────────────┘
```

## Features

- **TypeDB Backend**: Native hypergraph storage with inference rules
- **Enterprise Connectors**: Salesforce, Zendesk, Slack, PagerDuty, Snowflake
- **LLM Integration**: Anthropic Claude, OpenAI GPT-4, Together AI
- **Entity Extraction**: LLM-powered extraction pipeline
- **Multi-Agent Reasoning**: Context, Executive, and Governance agents
- **Path Finding**: BFS and Yen's K-shortest paths with intersection constraints

## Quick Start

### One-Command Setup

```bash
git clone https://github.com/vibhavjoshi123/Hypergraph-for-Context-Graph.git
cd Hypergraph-for-Context-Graph
bash scripts/quickstart.sh
```

The quickstart script handles everything: virtual environment, dependencies, `.env` configuration (prompts for TypeDB Cloud address, credentials, and Anthropic API key), schema loading, seed data, and starts the API server.

### Prerequisites

- Python 3.11+
- [TypeDB Cloud](https://cloud.typedb.com) account (or TypeDB Core for local)
- [Anthropic API key](https://console.anthropic.com) for LLM-powered reasoning

### Manual Setup

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e ".[dev]"

# Configure environment
cp .env.example .env
# Edit .env with your TypeDB and Anthropic credentials

# Load schema and seed data
python scripts/setup_typedb.py --seed

# Start the API server
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

### Configuration

Create a `.env` file (or let `quickstart.sh` generate one):

```env
# TypeDB Cloud
TYPEDB_ADDRESS=your-cluster.cluster.typedb.com:443
TYPEDB_DATABASE=context_graph
TYPEDB_USERNAME=admin
TYPEDB_PASSWORD=your-password
TYPEDB_TLS_ENABLED=true

# Anthropic LLM (required for agent reasoning)
LLM_ANTHROPIC_API_KEY=sk-ant-...
LLM_DEFAULT_MODEL=claude-sonnet-4-20250514

# API
API_HOST=0.0.0.0
API_PORT=8000
```

## End-to-End Test Results

Tested against TypeDB Cloud with the full agent pipeline hitting Anthropic's Claude API.

### API Endpoints

```bash
# Health check
curl http://localhost:8000/health
# => {"status":"healthy","version":"0.1.0","typedb_connected":true}

# List all entities
curl http://localhost:8000/api/v1/entities
# => [{"entity_id":"cust_001","entity_name":"Acme Corp","entity_type":"customer",...}, ...]

# Get entity by ID
curl http://localhost:8000/api/v1/entities/cust_001
# => {"entity_id":"cust_001","entity_name":"Acme Corp","entity_type":"customer",...}

# Create entity
curl -X POST http://localhost:8000/api/v1/entities \
  -H "Content-Type: application/json" \
  -d '{"entity_id":"test_001","entity_name":"Test Corp","entity_type":"customer"}'

# List hyperedges
curl http://localhost:8000/api/v1/hyperedges
# => [{"dt":"discount-approval","h":"0x1f..."}]

# Query with Claude reasoning (hits Anthropic API)
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query":"Why was the Acme discount approved?"}'
```

### Agent Pipeline Test

The `/api/v1/query` endpoint executes the full multi-agent pipeline:

1. **TypeDB Cloud** - Fetches all entities with full attributes (health_score, ARR, discount_percentage, severity, etc.) and decision hyperedges with rationale and role players
2. **ContextAgent** - Runs s-adjacency traversal (IS >= 2) over real hyperedge objects, finds s-connected components
3. **ExecutiveAgent** - Sends the full graph context to Claude via Anthropic API for mechanistic reasoning

**Example query:** `"Why was the Acme discount approved?"`

**Claude's response (verified correct against seed data):**
> The Acme discount was approved because VP of Sales Sarah Chen exercised executive override authority to grant a 20% discount (exceeding the standard 15% policy limit) based on two factors: Acme Corp's strategic account status as an enterprise customer with $500K ARR and their history of experiencing a SEV-1 production outage.

**Causal chain identified:**
```
Acme Corp (Enterprise, $500K ARR)
    -> Production Outage (SEV-1, Jan 2026)
    -> Q1 Renewal Deal ($500K, 20% discount)
    -> Standard Discount Policy (15% limit) <- constraint
    -> VP Sarah Chen -> Executive Override
    -> Discount Approved (20%)
```

**Evidence returned includes:**
- 5 entities with full domain attributes (health_score=72, arr=500K, discount=20%, max_discount=15%, severity=SEV-1)
- 1 decision hyperedge with rationale and 5 role players (4 involved-entity + 1 decision-maker)
- 1 s-connected component found via IS >= 2 traversal

## Project Structure

```
hypergraph-context-graph/
├── src/
│   ├── typedb/           # TypeDB client and schema
│   ├── connectors/       # Enterprise data connectors
│   ├── llm/              # LLM provider integrations
│   ├── extraction/       # Entity extraction pipeline
│   ├── agents/           # Multi-agent reasoning system
│   ├── api/              # FastAPI application
│   └── models/           # Pydantic data models
├── tests/
├── scripts/
├── docs/
└── docker/
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run linter
ruff check src/

# Type checking
mypy src/
```

## Requirements Coverage

See [REQUIREMENTS_COVERAGE.md](REQUIREMENTS_COVERAGE.md) for a detailed comparison of all three research PDFs against the codebase. **29/35 requirements implemented (83%)**, with the 3 missing items explicitly marked as "open research" in the source documents.

## Roadmap

- [x] Phase 1: TypeDB 3.x Integration (schema, client, CRUD, traversal)
- [x] Phase 2: Enterprise Connectors (BaseConnector ABC, WebhookConnector)
- [x] Phase 3: LLM Connectors (Anthropic Claude, OpenAI, Together AI)
- [x] Phase 4: Multi-Agent System (Context, Executive, Governance agents)
- [x] Phase 5: End-to-End Pipeline (TypeDB Cloud + Claude API + FastAPI)
- [ ] Phase 6: Rich-club analysis, LLM-to-2-morphism translation
- [ ] Phase 7: Production Deployment (K8s, monitoring, load testing)

## References

1. [Chemical Reaction Networks as Context Graphs](Chemical_Reaction_Networks_Context_Graphs_Visual.pdf) - Core isomorphism between chemical and enterprise hypergraphs
2. [Higher-Order Categorical Reasoning](higher_order_categorical_reasoning.pdf) - 2-morphisms, agent architecture, coherence verification
3. [TypeDB vs RDF/OWL Analysis](TypeDB_vs_RDF_OWL_Full_Analysis.pdf) - Why TypeDB PERA model for native n-ary relations
4. [TypeDB Documentation](https://typedb.com/docs)


## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please read our contributing guidelines and submit PRs.
