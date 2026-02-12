# Context Graph Examples: Decision Traces & 2-Morphisms

> *"The last generation of enterprise software became trillion-dollar companies by owning **what happened**. The next trillion-dollar opportunity? Owning **why it happened**."*
> — Jaya Gupta & Ashu Garg, [Foundation Capital](https://foundationcapital.com/context-graphs-ais-trillion-dollar-opportunity/)

This document demonstrates the Hypergraph Context Graph system with real queries against seed data. It shows how **decision traces**, **s-adjacency traversal**, and **2-morphisms** capture the reasoning behind enterprise decisions — not just the outcomes.

---

## Why Context Graphs?

Traditional systems of record (Salesforce, Zendesk, Workday) store **what happened**: a deal closed, a ticket resolved, a discount applied. But they don't store **why** — the chain of reasoning, the exceptions granted, the precedents cited.

A **Context Graph** captures these **decision traces**: the multi-entity relationships that explain how rules were applied, where exceptions were granted, and why actions were allowed to happen.

### What makes this different from a knowledge graph?

| Feature | Knowledge Graph | Context Graph (Hypergraph) |
|---|---|---|
| Edge type | Pairwise (2 nodes) | N-ary (3+ nodes per hyperedge) |
| Stores | Facts ("Acme is a customer") | Decision traces ("VP approved 20% discount involving Acme, the deal, the outage, and the policy") |
| Relationships | Entity-to-entity | **Decision-to-decision** (2-morphisms) |
| Learns from | Static data | Feedback loops — graph compounds with each query |
| Key insight | What happened | **Why it happened** |

---

## Seed Data: Enterprise Decision Scenario

The seed data models a realistic enterprise scenario across 3 companies with interconnected decision traces:

### Entities (16 total)

| Type | ID | Name | Key Attributes |
|---|---|---|---|
| Customer | cust_001 | Acme Corp | health=72, enterprise, $500K ARR |
| Customer | cust_002 | Globex Industries | health=85, enterprise, $1.2M ARR |
| Customer | cust_003 | Initech Solutions | health=58, mid-market, $180K ARR |
| Employee | emp_001 | Sarah Chen | VP of Sales |
| Employee | emp_002 | Marcus Rivera | Account Director |
| Employee | emp_003 | Priya Patel | Support Engineering Lead |
| Employee | emp_004 | James Wilson | CFO |
| Deal | deal_001 | Acme Renewal Q1 | $500K, 20% discount, negotiation |
| Deal | deal_002 | Globex Platform Expansion | $800K, 12% discount, closed-won |
| Deal | deal_003 | Initech Renewal Q2 | $180K, 18% discount, negotiation |
| Ticket | tkt_001 | Acme Production Outage | SEV-1, resolved |
| Ticket | tkt_002 | Globex Data Migration Failure | SEV-2, resolved |
| Ticket | tkt_003 | Initech API Latency Degradation | SEV-2, open |
| Policy | pol_001 | Standard Discount Policy | max 15% |
| Policy | pol_002 | Enterprise SLA Policy | max 20% |
| Policy | pol_003 | Incident Escalation Policy | escalation |

### Decision Hyperedges (6 total)

Each decision is an **n-ary hyperedge** connecting all participating entities in a single atomic event:

```
Dec 1: Acme Discount Approval (VP Override)
       ├── involved: Acme Corp, Acme Renewal Q1, Production Outage, Discount Policy
       └── decision-maker: Sarah Chen
       Rationale: "VP approved 20% discount exceeding 15% policy limit due to
                   SEV-1 outage history and $500K ARR strategic account status"

Dec 2: Globex Expansion Discount (Within Policy)
       ├── involved: Globex Industries, Globex Expansion, Discount Policy
       └── decision-maker: Sarah Chen, Marcus Rivera
       Rationale: "12% discount on $800K expansion, within 15% policy limit"

Dec 3: Initech Emergency Escalation
       ├── involved: Initech Solutions, API Latency Ticket, Escalation Policy
       └── decision-maker: Priya Patel
       Rationale: "SEV-2 escalated to engineering; health score 58, churn risk"

Dec 4: Acme SLA Credit
       ├── involved: Acme Corp, Production Outage, SLA Policy
       └── decision-maker: James Wilson (CFO), Sarah Chen
       Rationale: "15% SLA credit for SEV-1 outage violating 99.9% uptime"

Dec 5: Globex Migration Compensation
       ├── involved: Globex Industries, Migration Failure Ticket, SLA Policy
       └── decision-maker: Sarah Chen
       Rationale: "10% credit applying SLA precedent from Acme (dec_004)"

Dec 6: Initech Churn Prevention Discount
       ├── involved: Initech Solutions, Initech Renewal, API Ticket, Discount Policy
       └── decision-maker: Sarah Chen, Marcus Rivera
       Rationale: "18% discount exceeding 15% limit; cited Acme precedent (dec_001)"
```

### s-Adjacency Graph (IS >= 2)

Two hyperedges are **s-adjacent** when they share 2 or more entities (intersection size >= 2). This filters out noise — sharing just 1 entity is too weak a connection. At IS >= 2, noise is reduced by **87%**.

```
         Dec1 ──IS=2── Dec2 ──IS=3── Dec6 ──IS=2── Dec3
          │                            │
        IS=3                         IS=2
          │                            │
         Dec4 ──IS=2── Dec5          Dec1
```

**Shared entities creating s-adjacency:**
- Dec1 ↔ Dec2: `{Sarah Chen, Discount Policy}` (IS=2)
- Dec1 ↔ Dec4: `{Acme Corp, Sarah Chen, Production Outage}` (IS=3)
- Dec1 ↔ Dec6: `{Sarah Chen, Discount Policy}` (IS=2)
- Dec2 ↔ Dec5: `{Globex Industries, Sarah Chen}` (IS=2)
- Dec2 ↔ Dec6: `{Sarah Chen, Marcus Rivera, Discount Policy}` (IS=3)
- Dec3 ↔ Dec6: `{Initech Solutions, API Latency Ticket}` (IS=2)
- Dec4 ↔ Dec5: `{Sarah Chen, SLA Policy}` (IS=2)

All 6 decisions form a **single s-connected component** — the entire decision history is reachable through shared context.

---

## 2-Morphisms: Relations Between Relations

This is the key innovation. A **2-morphism** is a relationship between two decision hyperedges — a meta-relation that captures how decisions influence each other:

```
╔══════════════════════════════════════════════════════════════════╗
║  2-MORPHISM DIAGRAM                                             ║
║                                                                  ║
║  ┌─────────────────┐  precedent   ┌──────────────────────────┐  ║
║  │ Dec1: Acme      │─────────────→│ Dec6: Initech Churn      │  ║
║  │ Discount (20%)  │              │ Prevention (18%)          │  ║
║  └─────────────────┘              └──────────────────────────┘  ║
║         ↑                                    ↑                   ║
║         │ exception                          │ exception         ║
║         │                                    │                   ║
║  ┌─────────────────┐              ┌──────────────────────────┐  ║
║  │ Dec2: Globex    │              │ Dec3: Initech            │  ║
║  │ Expansion (12%) │              │ Escalation               │  ║
║  └─────────────────┘              └──────────────────────────┘  ║
║                                                                  ║
║  ┌─────────────────┐  precedent   ┌──────────────────────────┐  ║
║  │ Dec4: Acme SLA  │─────────────→│ Dec5: Globex Migration   │  ║
║  │ Credit (15%)    │              │ Compensation (10%)        │  ║
║  └─────────────────┘              └──────────────────────────┘  ║
╚══════════════════════════════════════════════════════════════════╝
```

### The 4 Seed 2-Morphisms Explained

**1. Precedent: Dec1 → Dec6** (Incident Discount Pattern)
> Acme's incident-based discount (20% for SEV-1 outage) established the pattern for granting above-policy discounts when service failures affect strategic accounts. Initech's churn prevention discount (18%) directly cited this as justification.

*In CRN terms: Reaction pathway A established the mechanism that pathway B follows.*

**2. Precedent: Dec4 → Dec5** (SLA Credit Methodology)
> Acme's SLA credit approval (15% for outage) established the service-credit methodology under Enterprise SLA Policy. Globex migration compensation (10%) reused this framework, allowing VP-only approval without CFO sign-off for sub-15% credits.

*In category theory terms: Morphism composition — the methodology arrow composes through the SLA policy object.*

**3. Exception Override: Dec2 → Dec1** (VP Override of Standard Process)
> Globex's expansion discount (12%) followed the standard policy-compliant process. Acme's discount (20%) created an exception: VP executive authority overrode the 15% policy ceiling. This is the **catalyst-approver isomorphism** from CRN theory — the VP acts as a catalyst lowering the activation energy (approval threshold).

*In chemistry: A catalyst lowers the activation energy barrier. In enterprise: The VP's authority lowers the policy threshold.*

**4. Exception Override: Dec3 → Dec6** (Escalation Fast-Tracked)
> Standard escalation policy requires full incident resolution before commercial decisions. The churn prevention discount was approved while the SEV-2 API latency issue remained open, bypassing the escalation-then-resolution sequence. VP + Account Director co-approval substituted for completed incident resolution.

*In CRN terms: A competing reaction pathway dominated, consuming the intermediate without completing the expected sequence.*

---

## Example Queries

### Query 1: "Why was the Acme discount approved?"

This is the simplest query — asks about a single decision trace.

```bash
curl -s -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query":"Why was the Acme discount approved?"}' | python3 -m json.tool
```

**What the system does:**
1. Fetches all 16 entities with full attributes from TypeDB
2. Fetches all 6 decision hyperedges with rationale and role players
3. ContextAgent runs s-adjacency traversal → finds 1 connected component with 6 hyperedges
4. ExecutiveAgent sends full context to Claude → reasons over the causal chain
5. LLM extracts 2-morphism proposals → stores new ones to TypeDB (with dedup)

**Expected answer highlights:**
- VP Sarah Chen exercised executive override authority
- 20% discount exceeds 15% policy limit
- Justified by SEV-1 production outage + $500K ARR strategic account
- Causal chain: Outage → Renewal Negotiation → Policy Exception → VP Override → Approval
- Precedent and exception patterns identified

---

### Query 2: "What precedents exist for giving discounts above policy limits?"

This query specifically targets 2-morphisms — it asks about meta-relationships.

```bash
curl -s -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query":"What precedents exist for giving discounts above policy limits?"}' | python3 -m json.tool
```

**What the system finds:**
- Dec1 (Acme 20%) and Dec6 (Initech 18%) both exceed the 15% Standard Discount Policy
- Precedent chain links them: Dec1 → Dec6
- Exception override: Dec2 (Globex 12%, within policy) is the "normal" baseline that Dec1 overrode
- Pattern: SEV incidents + strategic account status = justification for policy exceptions
- Sarah Chen is the common decision-maker across all above-policy approvals

---

### Query 3: "How are Acme, Globex, and Initech decisions connected?"

This query tests s-adjacency traversal across the full graph.

```bash
curl -s -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query":"How are Acme, Globex and Initech decisions connected?"}' | python3 -m json.tool
```

**What the system reveals:**
- All 6 decisions form a single s-connected component
- Sarah Chen (emp_001) is the **hub node** — she participates in 5 of 6 decisions
- Standard Discount Policy (pol_001) appears in 3 decisions (Dec1, Dec2, Dec6)
- The connection chain: Acme outage → Acme discount → Initech churn prevention → Initech escalation
- Parallel chain: Acme SLA credit → Globex migration compensation
- Cross-chain link: Globex expansion (standard process) ↔ Acme discount (exception)

---

### Query 4: "What is the risk of approving more above-policy discounts?"

This query demonstrates the **compounding feedback loop**. Each query adds new 2-morphism insights.

```bash
curl -s -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query":"What is the risk of approving more above-policy discounts?"}' | python3 -m json.tool
```

**What the feedback loop captures:**
- On the first run, Claude identifies risk patterns and proposes new 2-morphisms
- On subsequent runs, the graph is richer — Claude now sees the previously stored 2-morphisms
- The system gets smarter over time: **accuracy → trust → adoption → feedback → accuracy**

---

## The Feedback Loop: Why This Compounds

```
     ┌──────────────────────────────────────────────┐
     │                                              │
     ▼                                              │
  Query ──→ TypeDB ──→ ContextAgent ──→ ExecutiveAgent
  (NL)     (fetch)    (s-adjacency)    (Claude LLM)
                                            │
                                            ▼
                                     2-Morphism Extraction
                                            │
                                            ▼
                              ┌─────────────────────────┐
                              │  Store in TypeDB         │
                              │  (with deduplication)    │
                              └─────────────┬───────────┘
                                            │
                              ┌─────────────▼───────────┐
                              │  Next query sees richer  │
                              │  graph with more         │──┘
                              │  2-morphism connections   │
                              └─────────────────────────┘
```

This is the core insight from [Foundation Capital's thesis](https://foundationcapital.com/context-graphs-ais-trillion-dollar-opportunity/): the system that wins isn't the one that captures the most context on day one — it's the one that **gets better at capturing and delivering context over time**.

Every query:
1. Reads the current graph (entities + decisions + existing 2-morphisms)
2. Claude reasons over the full context
3. New 2-morphisms are extracted and stored (if not duplicates)
4. The next query has a richer graph to reason over

**LLMs commoditize. Decision intelligence compounds.**

---

## Running the Examples

```bash
# 1. Reseed with fresh data (drops old DB)
python scripts/setup_typedb.py --seed

# 2. Start the API server
python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# 3. Verify entities and hyperedges loaded
curl -s http://localhost:8000/api/v1/entities | python3 -m json.tool | head -20
curl -s http://localhost:8000/api/v1/hyperedges | python3 -m json.tool | head -20

# 4. Run the showcase queries
curl -s -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query":"Why was the Acme discount approved?"}' | python3 -m json.tool

curl -s -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query":"What precedents exist for giving discounts above policy limits?"}' | python3 -m json.tool

curl -s -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query":"How are Acme, Globex and Initech decisions connected?"}' | python3 -m json.tool
```

---

## References

- [Context Graphs: AI's Trillion-Dollar Opportunity](https://foundationcapital.com/context-graphs-ais-trillion-dollar-opportunity/) — Foundation Capital (Jaya Gupta & Ashu Garg)
- [Context Graphs: Who Actually Captures It?](https://www.linkedin.com/pulse/context-graphs-trillion-dollar-opportunity-who-actually-prukalpa--kxadc/) — Prukalpa, Metadata Weekly
- [Chemical Reaction Networks as Context Graphs](Chemical_Reaction_Networks_Context_Graphs_Visual.pdf) — CRN-to-enterprise isomorphism
- [Higher-Order Categorical Reasoning](higher_order_categorical_reasoning.pdf) — 2-morphisms and agent architecture
- [TypeDB vs RDF/OWL Analysis](TypeDB_vs_RDF_OWL_Full_Analysis.pdf) — Why TypeDB for n-ary relations
