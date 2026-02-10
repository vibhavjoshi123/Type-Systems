# Enterprise Hypergraph Context Graph - Production Architecture Plan

## Overview

This document outlines the architecture for transforming the prototype Hypergraph-for-Context-Graph into a production-ready system using:
- **TypeDB** as the hypergraph database backend (replacing in-memory storage)
- **Enterprise Data Connectors** for real-time data ingestion
- **LLM Connectors** for intelligent entity extraction and reasoning

---

## Phase 1: TypeDB Integration (Weeks 1-3)

### 1.1 Why TypeDB for Hypergraphs?

TypeDB is ideal for this project because:
- **Native n-ary relations**: TypeDB's PERA model (Polymorphic Entity-Relation-Attribute) natively supports hyperedges where relations can connect 3+ entities
- **Schema enforcement**: TypeQL provides strong typing that matches our DecisionEvent model
- **Inference rules**: Built-in reasoning engine for deriving new relationships
- **Polymorphic queries**: Query across type hierarchies seamlessly

### 1.2 TypeDB Schema Design

```typeql
define

# ============ ATTRIBUTES ============
attribute entity-id, value string;
attribute entity-name, value string;
attribute entity-type, value string;
attribute timestamp, value datetime;
attribute confidence-score, value double;
attribute embedding, value string;  # JSON-serialized vector
attribute source-system, value string;
attribute rationale, value string;
attribute decision-type, value string;
attribute relation-type, value string;

# ============ ENTITIES ============
# Core enterprise entities
entity enterprise-entity,
    abstract,
    owns entity-id @key,
    owns entity-name,
    owns entity-type,
    owns embedding,
    owns source-system,
    plays context-hyperedge:participant,
    plays decision-event:involved-entity;

entity customer, sub enterprise-entity,
    owns health-score value double,
    owns tier value string;

entity employee, sub enterprise-entity,
    owns department value string,
    owns role value string;

entity deal, sub enterprise-entity,
    owns deal-value value double,
    owns stage value string;

entity ticket, sub enterprise-entity,
    owns severity value string,
    owns status value string;

entity policy, sub enterprise-entity,
    owns policy-type value string,
    owns effective-date value datetime;

entity metric, sub enterprise-entity,
    owns metric-value value double,
    owns metric-type value string;

# ============ RELATIONS (HYPEREDGES) ============
# Core hyperedge relation - connects N entities
relation context-hyperedge,
    relates participant,
    owns timestamp,
    owns confidence-score,
    owns source-system;

# Decision event hyperedge - the key structure
relation decision-event, sub context-hyperedge,
    relates involved-entity as participant,
    relates decision-maker,
    relates affected-entity,
    owns decision-type,
    owns relation-type,
    owns rationale;

# Operational context
relation escalation, sub decision-event;
relation approval, sub decision-event;
relation renewal, sub decision-event;
relation incident, sub decision-event;

# ============ INFERENCE RULES ============
rule customer-at-risk:
    when {
        $c isa customer, has health-score $hs;
        $hs < 70.0;
    } then {
        $c has tier "at-risk";
    };

rule high-value-decision-requires-approval:
    when {
        $d isa deal, has deal-value $v;
        $v > 100000.0;
        (involved-entity: $d) isa decision-event;
    } then {
        # Flag for VP approval requirement
    };
```

### 1.3 TypeDB Client Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Python Application                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────────┐    ┌─────────────────┐                 │
│  │  TypeDBClient   │    │  HypergraphOps  │                 │
│  │  (Connection)   │───▶│  (CRUD + Query) │                 │
│  └─────────────────┘    └─────────────────┘                 │
│           │                      │                           │
│           ▼                      ▼                           │
│  ┌─────────────────────────────────────────┐                │
│  │           TypeDB Python Driver           │                │
│  │         (typedb-driver >= 3.0)           │                │
│  └─────────────────────────────────────────┘                │
│                          │                                   │
└──────────────────────────┼───────────────────────────────────┘
                           │ gRPC
                           ▼
              ┌─────────────────────────┐
              │     TypeDB Server       │
              │  (Cloud / CE / Enterprise)│
              └─────────────────────────┘
```

### 1.4 Implementation Tasks

| Task | Description | Priority |
|------|-------------|----------|
| `typedb_client.py` | Connection pooling, session management | P0 |
| `typedb_schema.py` | Schema definition and migration | P0 |
| `typedb_operations.py` | CRUD operations for entities/hyperedges | P0 |
| `typedb_traversal.py` | BFS, Yen's K-paths on TypeDB | P1 |
| `typedb_embeddings.py` | Store/retrieve vector embeddings | P1 |
| `typedb_inference.py` | Define and execute inference rules | P2 |

---

## Phase 2: Enterprise Data Connectors (Weeks 4-6)

### 2.1 Connector Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                    CONNECTOR FRAMEWORK                          │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ BaseConnector│  │ RateLimiter  │  │ RetryPolicy  │         │
│  │  (Abstract)  │  │              │  │              │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│         │                                                      │
│         ├──────────────────┬──────────────────┬───────────────┤
│         ▼                  ▼                  ▼               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │  Salesforce  │  │   Zendesk    │  │    Slack     │        │
│  │  Connector   │  │  Connector   │  │  Connector   │        │
│  └──────────────┘  └──────────────┘  └──────────────┘        │
│         │                  │                  │                │
│         ├──────────────────┴──────────────────┘                │
│         ▼                                                      │
│  ┌─────────────────────────────────────────────────┐          │
│  │              Entity Extraction Pipeline          │          │
│  │  (LLM-powered entity resolution & normalization) │          │
│  └─────────────────────────────────────────────────┘          │
│                          │                                     │
│                          ▼                                     │
│  ┌─────────────────────────────────────────────────┐          │
│  │              TypeDB Hypergraph Writer            │          │
│  └─────────────────────────────────────────────────┘          │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

### 2.2 Supported Connectors (Priority Order)

| Connector | Data Type | Use Case | Priority |
|-----------|-----------|----------|----------|
| **Salesforce** | CRM | Customers, Deals, Contacts | P0 |
| **Zendesk** | Support | Tickets, Escalations | P0 |
| **Slack** | Communication | Approvals, Decisions | P0 |
| **PagerDuty** | Incidents | Incidents, On-call | P1 |
| **Snowflake** | Analytics | Usage metrics, KPIs | P1 |
| **JIRA** | Projects | Tasks, Sprints | P2 |
| **Google Workspace** | Docs | Policies, SOPs | P2 |
| **Custom Webhook** | Any | Generic event ingestion | P1 |

### 2.3 Base Connector Interface

```python
from abc import ABC, abstractmethod
from typing import AsyncIterator, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel

class ConnectorConfig(BaseModel):
    """Configuration for a data connector."""
    name: str
    api_key: str | None = None
    api_secret: str | None = None
    base_url: str | None = None
    rate_limit_rpm: int = 60
    retry_attempts: int = 3
    batch_size: int = 100

class RawRecord(BaseModel):
    """Raw record from source system."""
    source_system: str
    record_type: str
    record_id: str
    data: Dict[str, Any]
    timestamp: datetime
    metadata: Dict[str, Any] = {}

class BaseConnector(ABC):
    """Abstract base class for all data connectors."""
    
    def __init__(self, config: ConnectorConfig):
        self.config = config
        self._rate_limiter = RateLimiter(config.rate_limit_rpm)
    
    @abstractmethod
    async def authenticate(self) -> bool:
        """Authenticate with the source system."""
        pass
    
    @abstractmethod
    async def fetch_records(
        self,
        record_type: str,
        since: datetime | None = None,
        until: datetime | None = None,
        filters: Dict[str, Any] | None = None
    ) -> AsyncIterator[RawRecord]:
        """Fetch records from the source system."""
        pass
    
    @abstractmethod
    async def fetch_single(self, record_type: str, record_id: str) -> RawRecord:
        """Fetch a single record by ID."""
        pass
    
    @abstractmethod
    def get_supported_record_types(self) -> List[str]:
        """Return list of supported record types."""
        pass
    
    async def subscribe(
        self,
        record_types: List[str],
        callback: Callable[[RawRecord], Awaitable[None]]
    ) -> None:
        """Subscribe to real-time updates (webhooks/streaming)."""
        raise NotImplementedError("Real-time not supported for this connector")
```

### 2.4 Connector Implementation Example (Salesforce)

```python
class SalesforceConnector(BaseConnector):
    """Salesforce CRM connector."""
    
    SUPPORTED_TYPES = ["Account", "Contact", "Opportunity", "Case", "Task"]
    
    async def authenticate(self) -> bool:
        # OAuth 2.0 flow
        pass
    
    async def fetch_records(
        self,
        record_type: str,
        since: datetime | None = None,
        **kwargs
    ) -> AsyncIterator[RawRecord]:
        soql = self._build_soql(record_type, since)
        async for batch in self._query_all(soql):
            for record in batch:
                yield RawRecord(
                    source_system="salesforce",
                    record_type=record_type,
                    record_id=record["Id"],
                    data=record,
                    timestamp=datetime.fromisoformat(record["LastModifiedDate"])
                )
    
    def _build_soql(self, record_type: str, since: datetime) -> str:
        fields = self._get_fields_for_type(record_type)
        query = f"SELECT {','.join(fields)} FROM {record_type}"
        if since:
            query += f" WHERE LastModifiedDate > {since.isoformat()}"
        return query
```

---

## Phase 3: LLM Connectors (Weeks 7-9)

### 3.1 LLM Provider Abstraction

```
┌─────────────────────────────────────────────────────────────┐
│                    LLM CONNECTOR LAYER                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                  LLMRouter                           │    │
│  │  (Model selection, fallback, load balancing)         │    │
│  └─────────────────────────────────────────────────────┘    │
│                          │                                   │
│         ┌────────────────┼────────────────┐                 │
│         ▼                ▼                ▼                 │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐            │
│  │  Anthropic │  │   OpenAI   │  │  Together  │            │
│  │   Claude   │  │   GPT-4    │  │   Llama    │            │
│  └────────────┘  └────────────┘  └────────────┘            │
│         │                │                │                  │
│         └────────────────┴────────────────┘                 │
│                          │                                   │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Structured Output Parser                │    │
│  │  (Pydantic models, JSON schema, retry on failure)    │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 LLM Use Cases in the System

| Use Case | Model Recommendation | Description |
|----------|---------------------|-------------|
| **Entity Extraction** | Claude 3.5 Sonnet / GPT-4o | Extract entities from unstructured text |
| **Relation Identification** | Claude 3.5 Sonnet | Identify n-ary relationships |
| **Entity Resolution** | Embedding + LLM | Match entities across systems |
| **Hyperedge Generation** | Claude Opus / GPT-4 | Construct DecisionEvent hyperedges |
| **Reasoning/Interpretation** | Claude Opus | Mechanistic interpretation |
| **Embeddings** | text-embedding-3-large / nomic-embed | Vector representations |

### 3.3 LLM Connector Interface

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Type, TypeVar
from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)

class LLMConfig(BaseModel):
    """Configuration for LLM connector."""
    provider: str  # "anthropic", "openai", "together", "local"
    model: str
    api_key: str | None = None
    base_url: str | None = None
    max_tokens: int = 4096
    temperature: float = 0.0
    timeout: int = 60

class BaseLLMConnector(ABC):
    """Abstract base class for LLM connectors."""
    
    def __init__(self, config: LLMConfig):
        self.config = config
    
    @abstractmethod
    async def complete(
        self,
        prompt: str,
        system_prompt: str | None = None,
        **kwargs
    ) -> str:
        """Generate a completion."""
        pass
    
    @abstractmethod
    async def complete_structured(
        self,
        prompt: str,
        output_schema: Type[T],
        system_prompt: str | None = None,
        **kwargs
    ) -> T:
        """Generate a structured output matching the schema."""
        pass
    
    @abstractmethod
    async def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for texts."""
        pass

class LLMRouter:
    """Routes requests to appropriate LLM based on task."""
    
    def __init__(self, connectors: Dict[str, BaseLLMConnector]):
        self.connectors = connectors
        self.task_routing = {
            "extraction": "anthropic",
            "reasoning": "anthropic",
            "embedding": "openai",
            "fast_classification": "together"
        }
    
    async def route(
        self,
        task: str,
        prompt: str,
        **kwargs
    ) -> str:
        provider = self.task_routing.get(task, "anthropic")
        connector = self.connectors[provider]
        return await connector.complete(prompt, **kwargs)
```

### 3.4 Entity Extraction Pipeline

```python
class EntityExtractionPipeline:
    """LLM-powered entity extraction from raw records."""
    
    EXTRACTION_PROMPT = """
    Extract all entities and their relationships from the following record.
    
    Source System: {source_system}
    Record Type: {record_type}
    Data: {data}
    
    Return a JSON object with:
    1. "entities": List of entities with {id, name, type, attributes}
    2. "relationships": List of relationships with {type, participants: [entity_ids], attributes}
    
    Focus on extracting:
    - People (employees, customers, contacts)
    - Organizations (companies, departments)
    - Objects (deals, tickets, incidents)
    - Events (approvals, escalations, decisions)
    - Policies/Rules referenced
    """
    
    async def extract(self, record: RawRecord) -> ExtractionResult:
        prompt = self.EXTRACTION_PROMPT.format(
            source_system=record.source_system,
            record_type=record.record_type,
            data=json.dumps(record.data)
        )
        
        result = await self.llm.complete_structured(
            prompt=prompt,
            output_schema=ExtractionResult,
            system_prompt="You are an expert at entity extraction..."
        )
        
        return result
```

---

## Phase 4: Multi-Agent Reasoning System (Weeks 10-12)

### 4.1 Agent Architecture (from MIT Paper)

```
┌─────────────────────────────────────────────────────────────┐
│                    AGENTIC REASONING SYSTEM                  │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  User Query: "Why was Acme given a 20% discount?"           │
│                          │                                   │
│                          ▼                                   │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                   ContextAgent                       │    │
│  │  - Hypergraph traversal (BFS, Yen's K-paths)        │    │
│  │  - Path intersection constraints (IS ≥ 2)           │    │
│  │  - Embedding-based semantic search                   │    │
│  └─────────────────────────────────────────────────────┘    │
│                          │                                   │
│                          ▼                                   │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                  ExecutiveAgent                      │    │
│  │  - Mechanistic interpretation                        │    │
│  │  - Causal chain construction                         │    │
│  │  - Decision rationale synthesis                      │    │
│  └─────────────────────────────────────────────────────┘    │
│                          │                                   │
│                          ▼                                   │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                 GovernanceAgent                      │    │
│  │  - Compliance verification                           │    │
│  │  - Policy matching                                   │    │
│  │  - Recommendation generation                         │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 Agent Tools (TypeDB-Powered)

```python
class HypergraphTools:
    """Tools for agents to interact with the hypergraph."""
    
    def __init__(self, typedb_client: TypeDBClient):
        self.db = typedb_client
    
    async def find_entity(self, query: str) -> List[Entity]:
        """Semantic search for entities."""
        # Uses embedding similarity + TypeQL
        pass
    
    async def get_hyperedges(self, entity_id: str) -> List[Hyperedge]:
        """Get all hyperedges involving an entity."""
        query = """
        match
            $e isa enterprise-entity, has entity-id "%s";
            $h (participant: $e) isa context-hyperedge;
        fetch $h: attribute;
        """ % entity_id
        return await self.db.query(query)
    
    async def find_paths(
        self,
        start_id: str,
        end_id: str,
        intersection_size: int = 1,
        k_paths: int = 3
    ) -> List[HypergraphPath]:
        """Find K shortest paths with intersection constraints."""
        # Implements Algorithm from MIT paper
        pass
    
    async def get_s_connected_components(self, s: int) -> List[Component]:
        """Find s-connected components for stability analysis."""
        pass
```

---

## Phase 5: Production Deployment (Weeks 13-16)

### 5.1 System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         PRODUCTION ARCHITECTURE                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │   API Gateway │  │  Auth (OAuth) │  │  Rate Limiter│              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
│           │                                                          │
│           ▼                                                          │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                     FastAPI Application                      │    │
│  │  /api/v1/query     - Natural language queries                │    │
│  │  /api/v1/entities  - Entity CRUD                             │    │
│  │  /api/v1/hyperedges - Hyperedge CRUD                         │    │
│  │  /api/v1/connectors - Connector management                   │    │
│  │  /api/v1/agents    - Agent reasoning endpoints               │    │
│  └─────────────────────────────────────────────────────────────┘    │
│           │                                                          │
│           ├──────────────────┬──────────────────┐                   │
│           ▼                  ▼                  ▼                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │    TypeDB    │  │    Redis     │  │   Temporal   │              │
│  │   Cluster    │  │   (Cache)    │  │  (Workflows) │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                     Background Workers                       │    │
│  │  - Connector sync jobs (Celery/Temporal)                     │    │
│  │  - Entity resolution batch processing                        │    │
│  │  - Embedding generation                                      │    │
│  │  - Inference rule execution                                  │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 5.2 Technology Stack

| Component | Technology | Justification |
|-----------|------------|---------------|
| Database | TypeDB Cloud/CE 3.x | Native hypergraph, inference |
| API Framework | FastAPI | Async, OpenAPI, type hints |
| Task Queue | Temporal | Complex workflows, durability |
| Cache | Redis | Session, embedding cache |
| LLM | Anthropic Claude API | Best reasoning capability |
| Embeddings | OpenAI / Nomic | High quality vectors |
| Observability | OpenTelemetry + Grafana | Distributed tracing |
| Container | Docker + K8s | Scalability |

---

## Project Structure

```
hypergraph-context-graph/
├── src/
│   ├── __init__.py
│   ├── config.py                 # Configuration management
│   │
│   ├── typedb/                   # TypeDB integration
│   │   ├── __init__.py
│   │   ├── client.py             # Connection management
│   │   ├── schema.py             # Schema definitions
│   │   ├── operations.py         # CRUD operations
│   │   ├── traversal.py          # Graph algorithms
│   │   └── embeddings.py         # Vector storage
│   │
│   ├── connectors/               # Data connectors
│   │   ├── __init__.py
│   │   ├── base.py               # Abstract base connector
│   │   ├── salesforce.py
│   │   ├── zendesk.py
│   │   ├── slack.py
│   │   ├── pagerduty.py
│   │   ├── snowflake.py
│   │   └── webhook.py            # Generic webhook connector
│   │
│   ├── llm/                      # LLM connectors
│   │   ├── __init__.py
│   │   ├── base.py               # Abstract LLM connector
│   │   ├── anthropic.py
│   │   ├── openai.py
│   │   ├── together.py
│   │   ├── router.py             # LLM routing logic
│   │   └── prompts/              # Prompt templates
│   │       ├── extraction.py
│   │       ├── reasoning.py
│   │       └── resolution.py
│   │
│   ├── extraction/               # Entity extraction pipeline
│   │   ├── __init__.py
│   │   ├── pipeline.py
│   │   ├── entity_resolver.py
│   │   └── hyperedge_builder.py
│   │
│   ├── agents/                   # Multi-agent system
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── context_agent.py
│   │   ├── executive_agent.py
│   │   ├── governance_agent.py
│   │   └── tools.py              # Agent tools
│   │
│   ├── api/                      # FastAPI application
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── routes/
│   │   │   ├── query.py
│   │   │   ├── entities.py
│   │   │   ├── hyperedges.py
│   │   │   └── connectors.py
│   │   └── middleware/
│   │
│   └── models/                   # Pydantic models
│       ├── __init__.py
│       ├── entities.py
│       ├── hyperedges.py
│       └── decisions.py
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
├── scripts/
│   ├── setup_typedb.py
│   ├── load_schema.py
│   └── seed_data.py
│
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
│
├── docs/
│   ├── api.md
│   ├── connectors.md
│   └── deployment.md
│
├── pyproject.toml
├── requirements.txt
└── README.md
```

---

## Implementation Roadmap

### Sprint 1-2: TypeDB Foundation
- [x] Set up TypeDB (Cloud or CE)
- [x] Implement TypeDB Python client wrapper
- [x] Define and load schema
- [x] Basic CRUD operations
- [x] Unit tests for TypeDB layer

### Sprint 3-4: Data Connectors
- [x] Implement BaseConnector
- [x] Salesforce connector
- [x] Zendesk connector
- [x] Webhook connector
- [ ] Integration tests

### Sprint 5-6: LLM Integration
- [x] Implement LLM connector abstraction
- [x] Anthropic Claude connector
- [x] OpenAI connector
- [x] Entity extraction pipeline
- [x] Prompt engineering & testing

### Sprint 7-8: Agent System
- [x] Implement ContextAgent
- [x] Implement ExecutiveAgent
- [x] Implement GovernanceAgent
- [x] Hypergraph traversal algorithms
- [ ] End-to-end agent tests

### Sprint 9-10: API & Production
- [x] FastAPI application
- [x] Authentication/Authorization
- [x] Rate limiting
- [x] Observability setup
- [ ] Load testing

### Sprint 11-12: Polish & Deploy
- [ ] Documentation
- [x] CI/CD pipeline
- [ ] Kubernetes manifests
- [ ] Production deployment
- [ ] Monitoring dashboards

---

## Getting Started (Next Steps)

1. **Set up TypeDB locally**:
   ```bash
   # Using Docker
   docker run -d --name typedb -p 1729:1729 typedb/typedb:latest
   
   # Or download CE from https://typedb.com/docs/home/install/ce
   ```

2. **Install Python dependencies**:
   ```bash
   pip install typedb-driver anthropic openai pydantic fastapi
   ```

3. **Load the schema**:
   ```bash
   python scripts/load_schema.py
   ```

4. **Run the first connector**:
   ```bash
   python -m src.connectors.webhook --port 8080
   ```

---

## References

1. TypeDB Documentation: https://typedb.com/docs
2. TypeDB Python Driver: https://github.com/typedb/typedb-driver
3. HyperGraphReasoning: https://github.com/lamm-mit/HyperGraphReasoning
