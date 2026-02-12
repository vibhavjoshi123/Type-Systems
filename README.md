# Hypergraph Context Graph

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![TypeDB](https://img.shields.io/badge/TypeDB-3.x-green.svg)](https://typedb.com/)


**Production-ready Enterprise Context Graph using Hypergraphs and TypeDB**

This project implements a hypergraph-based context graph system for enterprise decision-making, 

## Why Context Graphs?

> *"The last generation of enterprise software became trillion-dollar companies by owning **what happened**. The next trillion-dollar opportunity? Owning **why it happened**."*
> — [Foundation Capital](https://foundationcapital.com/context-graphs-ais-trillion-dollar-opportunity/)

Traditional systems of record store **what** — a deal closed, a ticket resolved. Context graphs capture **why** — the decision traces showing how rules were applied, where exceptions were granted, and why actions were allowed.

Traditional knowledge graphs use pairwise edges (2 nodes). But enterprise decisions are **n-ary** — they involve multiple entities simultaneously:

> "When a renewal agent proposes a 20% discount, it doesn't just pull from the CRM. It pulls from PagerDuty for incident history, Zendesk for escalation threads, Slack for VP approval from last quarter, Salesforce for the deal record, Snowflake for usage data, and the semantic layer for the definition of 'healthy customer'."

**Hypergraphs** solve this by allowing edges (hyperedges) to connect 3+ nodes. **2-morphisms** go further — they capture relationships *between* decisions (precedent chains, exception overrides), so the graph gets smarter with each query.

See **[EXAMPLES.md](EXAMPLES.md)** for a full walkthrough with seed data, 2-morphism diagrams, and example queries.

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

### Agent Pipeline: Decision Traces + 2-Morphisms

The `/api/v1/query` endpoint executes the full multi-agent pipeline:

1. **TypeDB Cloud** — Fetches 16 entities with full attributes and 6 decision hyperedges with rationale, role players, and existing 2-morphisms
2. **ContextAgent** — Runs s-adjacency traversal (IS >= 2) over real hyperedge objects, finds s-connected components
3. **ExecutiveAgent** — Sends the full graph context to Claude for mechanistic reasoning
4. **2-Morphism Extraction** — Claude identifies precedent/exception patterns between decisions
5. **TypeDB Writeback** — New 2-morphisms stored back to TypeDB (with deduplication)

**Seed data:** 16 entities (3 customers, 4 employees, 3 deals, 3 tickets, 3 policies), 6 interconnected decisions, 4 explicit 2-morphisms (2 precedent-chains + 2 exception-overrides).

```
2-MORPHISM DIAGRAM:

  Dec1: Acme Discount ──precedent──→ Dec6: Initech Churn Prevention
       ↑ exception                         ↑ exception
  Dec2: Globex Expansion              Dec3: Initech Escalation

  Dec4: Acme SLA Credit ──precedent──→ Dec5: Globex Migration Compensation
```

**Example:** `"Why was the Acme discount approved?"` — Claude traces the full causal chain through the hypergraph: SEV-1 outage → renewal negotiation → policy exception → VP override → 20% discount approved. It identifies this decision as the **precedent** that later justified Initech's 18% churn prevention discount.

**Graph growth from feedback loop:** Started with 6 seed hyperedges → after 5 queries, the graph grew to **23 hyperedges** as Claude extracted and stored new 2-morphism relationships.

| Query | Confidence | 2-Morphisms Proposed | Stored |
|---|---|---|---|
| "Why was the Acme discount approved?" | 0.8 | 6 | 6 |
| "What precedents exist for above-policy discounts?" | 0.8 | 7 | 1 |
| "How are Acme, Globex and Initech connected?" | 0.8 | 6 | 2 |
| "What is Sarah Chen's role across all decisions?" | 0.8 | 7 | 0 |
| "Risk of more above-policy discounts?" | 0.8 | 8 | 8 |

For full Claude reasoning output from all 5 queries, see **[EXAMPLE_RESULTS.md](EXAMPLE_RESULTS.md)**.

For seed data walkthrough, 2-morphism diagrams, and query explanations, see **[EXAMPLES.md](EXAMPLES.md)**.

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

See [REQUIREMENTS_COVERAGE.md](REQUIREMENTS_COVERAGE.md) for a detailed comparison of all three research PDFs against the codebase. **30/35 requirements implemented (86%)**, with the 3 missing items explicitly marked as "open research" in the source documents.

## Roadmap

- [x] Phase 1: TypeDB 3.x Integration (schema, client, CRUD, traversal)
- [x] Phase 2: Enterprise Connectors (BaseConnector ABC, WebhookConnector)
- [x] Phase 3: LLM Connectors (Anthropic Claude, OpenAI, Together AI)
- [x] Phase 4: Multi-Agent System (Context, Executive, Governance agents)
- [x] Phase 5: End-to-End Pipeline (TypeDB Cloud + Claude API + FastAPI)
- [x] Phase 6a: LLM-to-2-morphism translation (feedback loop)
- [ ] Phase 6b: Rich-club analysis, scale-free topology
- [ ] Phase 7: Production Deployment (K8s, monitoring, load testing)

## References

1. [Context Graphs: AI's Trillion-Dollar Opportunity](https://foundationcapital.com/context-graphs-ais-trillion-dollar-opportunity/) — Foundation Capital (Jaya Gupta & Ashu Garg)
2. [Context Graphs: Who Actually Captures It?](https://www.linkedin.com/pulse/context-graphs-trillion-dollar-opportunity-who-actually-prukalpa--kxadc/) — Prukalpa, Metadata Weekly
3. [Chemical Reaction Networks as Context Graphs](Chemical_Reaction_Networks_Context_Graphs_Visual.pdf) — CRN-to-enterprise isomorphism, s-adjacency, IS >= 2
4. [Higher-Order Categorical Reasoning](higher_order_categorical_reasoning.pdf) — 2-morphisms, agent architecture, coherence verification
5. [TypeDB vs RDF/OWL Analysis](TypeDB_vs_RDF_OWL_Full_Analysis.pdf) — Why TypeDB PERA model for native n-ary relations
6. [TypeDB Documentation](https://typedb.com/docs)


## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please read our contributing guidelines and submit PRs.
