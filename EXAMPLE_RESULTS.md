# Example Results: Context Graph in Action

> *"The last generation of enterprise software became trillion-dollar companies by owning **what happened**. The next trillion-dollar opportunity? Owning **why it happened**."*
> — Jaya Gupta & Ashu Garg, [Foundation Capital](https://foundationcapital.com/context-graphs-ais-trillion-dollar-opportunity/)

## The Problem We Solve

Enterprise decisions don't happen in isolation. When a VP approves a 20% discount, that decision pulls from incident history, SLA agreements, customer health scores, deal size, policy limits, and past precedents — all at once. But traditional systems only store the **outcome** (discount applied), not the **reasoning** (why it was approved, what precedents it set, who overrode what policy).

This creates three critical gaps:

1. **No institutional memory** — When an employee leaves, their decision reasoning leaves with them
2. **No precedent tracking** — Teams unknowingly set precedents that cascade across the organization
3. **No risk visibility** — Policy exceptions compound silently until they become the norm

**Our solution: a Hypergraph Context Graph** that captures decision traces as n-ary hyperedges (connecting all participants in a single atomic event), links decisions to each other through 2-morphisms (precedent chains, exception overrides), and gets smarter with every query through an LLM feedback loop.

---

## How It Works

```
Query (Natural Language)
    ↓
TypeDB Cloud ─── Fetches entities, decisions, existing 2-morphisms
    ↓
ContextAgent ─── s-adjacency traversal (IS >= 2), finds connected components
    ↓
ExecutiveAgent ── Claude reasons over the full graph context
    ↓
2-Morphism Extraction ── Claude identifies precedent/exception patterns
    ↓
TypeDB Writeback ── New 2-morphisms stored (with dedup)
    ↓
Next query sees a RICHER graph
```

---

## Seed Data

**16 entities** across 3 companies: Acme Corp ($500K ARR), Globex Industries ($1.2M ARR), Initech Solutions ($180K ARR) — plus 4 employees, 3 deals, 3 tickets, and 3 policies.

**6 decision hyperedges** interconnected through shared entities (s-adjacency IS >= 2).

**4 explicit 2-morphisms** seeded as TypeDB nested relations:
```
Dec1: Acme Discount ──precedent──→ Dec6: Initech Churn Prevention
     ↑ exception                         ↑ exception
Dec2: Globex Expansion              Dec3: Initech Escalation

Dec4: Acme SLA Credit ──precedent──→ Dec5: Globex Migration Compensation
```

---

## Query 1: "Why was the Acme discount approved?"

> **What this demonstrates:** The system doesn't just return "20% discount approved" — it reconstructs the full causal chain across 5 entities and identifies the precedent this decision created for future decisions.

```bash
curl -s -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query":"Why was the Acme discount approved?"}' | python3 -m json.tool
```

### Claude's Answer

## Analysis: Why was the Acme discount approved?

### 1. Direct Answer
The Acme discount was approved because VP Sarah Chen exercised executive authority to grant a 20% discount (exceeding the 15% Standard Discount Policy limit) due to:
- **SEV-1 production outage history** (ticket tkt_001: "Acme Production Outage - Jan 2026")
- **Strategic account status** ($500K ARR enterprise tier customer)
- **Executive override authority** enabling policy exception approval

### 2. Causal Chain
```
SEV-1 Production Outage (tkt_001)
    ↓
Acme Corp (cust_001) service disruption + $500K ARR strategic value
    ↓
Standard Discount Policy (pol_001) 15% limit insufficient for retention
    ↓
VP Sarah Chen (emp_001) executive authority override
    ↓
20% discount approval (exceeding policy by 5%)
    ↓
Precedent established for future similar decisions
```

**Key Entity Relationships:**
- **Acme Corp** ↔ **SEV-1 Outage** ↔ **Renewal Deal** (deal_001)
- **Sarah Chen** (decision-maker) ↔ **Standard Discount Policy** (policy override)
- **Discount Decision** → **SLA Credit Decision** (dec_003) → **Future Precedents**

### 3. Precedents & Exceptions Identified
**Exception Pattern:**
- Policy limit exceeded by 33% (20% vs 15% standard)
- Executive authority used to bypass CFO approval requirement
- Service incident history justified retention-focused pricing

**Precedent Establishment:**
- This decision created precedent for subsequent Initech discount (dec_005: 18% approval citing "Acme discount approval precedent")
- Established pattern of incident-based discount justifications

### 4. Confidence Assessment
**High Confidence (90%)**
- Clear causal linkage between service incident and discount approval
- Explicit rationale documented in decision trace
- Consistent with enterprise account retention strategies
- Precedent pattern confirmed by subsequent similar decisions

The decision demonstrates executive discretion in customer retention scenarios where service failures create churn risk for high-value accounts.

### Metrics

| Metric | Value |
|---|---|
| Confidence | 0.8 |
| Paths Found | 1 |
| 2-Morphisms Proposed | 6 |
| 2-Morphisms Stored | 6 |

### Why this matters

A traditional CRM would tell you "Acme got a 20% discount." That's the **what**.

Our context graph tells you **why**: a SEV-1 outage created compensatory justification, the VP's executive authority acted as a catalyst (lowering the approval threshold — the catalyst-approver isomorphism from chemical reaction network theory), and this decision created a **precedent** that was later cited to justify Initech's 18% discount. None of this reasoning exists in Salesforce.

---

## Query 2: "What precedents exist for giving discounts above policy limits?"

> **What this demonstrates:** The system identifies 2-morphism relationships — meta-connections between decisions showing how one decision's exception became another's justification. This is the "decision intelligence layer" that compounds over time.

```bash
curl -s -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query":"What precedents exist for giving discounts above policy limits?"}' | python3 -m json.tool
```

### Claude's Answer

## Analysis: Precedents for Discounts Above Policy Limits

### 1. Direct Answer

**Two clear precedents exist for giving discounts above the 15% Standard Discount Policy limit:**

1. **Acme Corp Precedent (20% discount)**: VP Sarah Chen approved a 20% discount for Acme Corp's $500K renewal, exceeding the policy limit by 5%. This was justified by SEV-1 production outage history and strategic account status.

2. **Initech Solutions Application (18% discount)**: VP Sarah Chen and Account Director Marcus Rivera co-approved an 18% discount for Initech Solutions, exceeding the policy limit by 3%. This decision explicitly cited the "Acme discount approval precedent" as justification.

### 2. Causal Chain

```
SEV-1 Production Outage (Acme)
    ↓
Executive Authority Invoked (Sarah Chen)
    ↓
Policy Exception Granted (20% vs 15% limit)
    ↓
Precedent Established
    ↓
Subsequent Application (Initech 18% discount)
    ↓
Precedent Reinforcement
```

**Key Decision Sequence:**
- **Initial Exception**: Acme's service incident history provided justification for VP to exercise executive authority and bypass standard approval processes
- **Precedent Creation**: The Acme decision became a referenceable precedent for future policy exceptions
- **Precedent Application**: Initech discount decision explicitly referenced "Acme discount approval precedent" combined with escalation findings

### 3. Precedents and Exception Patterns

**Exception Criteria Identified:**
- **Service Incident History**: Both cases involved significant service issues (SEV-1 outage for Acme, ongoing SEV-2 API issues for Initech)
- **Executive Authority**: VP-level approval required for policy exceptions
- **Strategic Account Status**: High ARR customers ($500K+ for Acme, churn risk for Initech)
- **Precedent Citation**: Later decisions explicitly reference earlier exceptions as justification

**Decision Authority Pattern:**
- Policy exceptions require VP-level authorization (Sarah Chen in both cases)
- Co-approval from Account Directors for additional validation
- Executive authority can override standard approval thresholds when justified by service incidents

### 4. Confidence Assessment

**High Confidence (90%)**

The hypergraph data provides explicit evidence of:
- Clear policy limit (15% Standard Discount Policy)
- Two documented exceptions (20% and 18% discounts)
- Explicit precedent citation in decision rationale
- Consistent executive approval pattern
- Service incident justification in both cases

The causal relationships are well-documented through the 2-morphism connections showing precedent establishment and application across the decision network.

### Metrics

| Metric | Value |
|---|---|
| Confidence | 0.8 |
| Paths Found | 1 |
| 2-Morphisms Proposed | 7 |
| 2-Morphisms Stored | 1 |

### Why this matters

This query asks about **relationships between decisions** — not between entities. No traditional database can answer "what precedents exist?" because precedents are 2-morphisms: arrows between arrows, relationships between relationships.

Our system stores these as first-class TypeDB nested relations (`precedent-chain`, `exception-override`), so when a new deal comes in, the agent can immediately surface: "This looks like the Acme pattern — here's what happened last time and what risks it created."

---

## Query 3: "How are Acme, Globex and Initech decisions connected?"

> **What this demonstrates:** s-adjacency traversal across the full hypergraph. The system finds that all 6 decisions form a single connected component through shared entities (IS >= 2), revealing hidden organizational patterns.

```bash
curl -s -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query":"How are Acme, Globex and Initech decisions connected?"}' | python3 -m json.tool
```

### Claude's Answer

## Analysis: How Acme, Globex and Initech Decisions Are Connected

### 1. Direct Answer

The three companies' decisions are interconnected through a cascading chain of precedent-setting and policy exceptions, all orchestrated by VP Sarah Chen. Acme's production outage created the initial precedent for policy exceptions, which then justified similar decisions for Globex and Initech.

### 2. Causal Chain

**Primary Sequence:**
1. **Acme Production Outage (SEV-1)** → **Acme 20% Discount Approval** (exceeding 15% policy limit)
2. **Acme SLA Credit (15%)** → **Globex Migration Compensation (10%)** via Enterprise SLA Policy precedent
3. **Acme Discount Precedent** → **Initech 18% Discount** (also exceeding policy limit)

**Cross-Company Connections:**
- **Sarah Chen (VP Sales)** is the central decision-maker across all three companies
- **Standard Discount Policy (15% limit)** is systematically overridden using Acme precedent
- **Enterprise SLA Policy** precedent flows from Acme to Globex
- **Incident Escalation findings** from Initech combine with Acme precedent to justify policy exceptions

### 3. Precedents and Exceptions Identified

**Policy Exceptions:**
- Acme: 20% discount (5% over policy limit) - justified by SEV-1 outage and executive authority
- Initech: 18% discount (3% over policy limit) - justified by "Acme discount approval precedent"

**Precedent Applications:**
- Globex compensation explicitly applied "Enterprise SLA Policy precedent established by Acme SLA credit"
- Initech discount decision directly cited "Acme discount approval precedent"

**Decision Pattern:**
All three companies received preferential treatment through policy exceptions, with Acme establishing the precedent that enabled subsequent decisions for Globex and Initech.

### 4. Confidence Assessment

**High Confidence (90%)**

The hypergraph clearly documents explicit precedent relationships through 2-morphism connections. The reasoning fields directly state precedent citations (e.g., "Acme discount approval precedent," "Enterprise SLA Policy precedent established by Acme SLA credit"). Sarah Chen's central role as decision-maker across all three companies creates a coherent decision authority chain, making this analysis highly reliable based on the structured data provided.

### Metrics

| Metric | Value |
|---|---|
| Confidence | 0.8 |
| Paths Found | 1 |
| 2-Morphisms Proposed | 6 |
| 2-Morphisms Stored | 2 |

### Why this matters

A VP asks: "Are our customer decisions consistent?" Traditional BI tools can show discount amounts per customer. They cannot show that Acme's outage-driven exception **cascaded** into Globex's SLA credit methodology and Initech's churn prevention strategy — all linked through Sarah Chen as the hub node.

The context graph reveals that these aren't three independent decisions. They're one interconnected decision network where a single SEV-1 incident reshaped policy interpretation across the entire customer base.

---

## Query 4: "What role does Sarah Chen play across all enterprise decisions?"

> **What this demonstrates:** Hub node identification — the system discovers that Sarah Chen is the central decision catalyst, present in 6/6 decisions, and that her initial decisions create precedent frameworks adopted enterprise-wide.

```bash
curl -s -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query":"What role does Sarah Chen play across all enterprise decisions and what patterns emerge?"}' | python3 -m json.tool
```

### Claude's Answer

## Analysis of Sarah Chen's Role Across Enterprise Decisions

### 1. Direct Answer

Sarah Chen (VP of Sales) plays a **central executive decision-making role** across all enterprise decisions, serving as either primary decision-maker or co-approver in **6 out of 6 major decisions** analyzed. She demonstrates consistent patterns of:

- **Executive authority override** - Bypassing standard approval processes when justified
- **Policy exception leadership** - Authorizing discounts exceeding standard 15% limits
- **Cross-functional coordination** - Collaborating with CFO, Account Directors, and Support teams
- **Precedent establishment** - Creating decision frameworks that influence subsequent choices

### 2. Causal Chain Analysis

**Primary Decision Sequence:**
```
Acme Production Outage (SEV-1) → Sarah's Discount Approval (20%) → Precedent Established
    ↓
Precedent Applied → Initech Discount Decision (18%) → Policy Exception Justified
    ↓
SLA Credit Precedent → Globex Compensation (10%) → Enterprise Policy Applied
```

**Sarah's Decision Involvement:**
- **Decision 1**: Acme discount approval (20% - exceeded policy)
- **Decision 2**: Globex expansion discount co-approval (12% - within policy)
- **Decision 3**: SLA credit co-approval with CFO (15% credit)
- **Decision 4**: Globex migration compensation (10% credit)
- **Decision 5**: Initech discount co-approval (18% - exceeded policy)
- **Decision 6**: Cross-referenced in all precedent justifications

### 3. Precedents and Exceptions Identified

**Precedents Established by Sarah:**
1. **Acme Discount Precedent** - Used to justify Initech's 18% discount exception
2. **Enterprise SLA Policy Precedent** - Applied from Acme SLA credit to Globex compensation
3. **Executive Authority Precedent** - Service incident history justifying policy bypasses

**Policy Exceptions Led:**
- **Standard Discount Policy**: Exceeded 15% limit twice (20% for Acme, 18% for Initech)
- **Approval Process**: Bypassed standard CFO approval for high-value compensations
- **SLA Credit Authority**: Co-established enterprise-wide SLA compensation framework

**Decision Patterns:**
- **Incident-Driven**: Service outages directly trigger retention-focused decisions
- **Precedent-Cascading**: Initial exceptions create justification frameworks for future decisions
- **Revenue-Protective**: All exceptions tied to high-ARR account retention ($500K+ accounts)

### 4. Confidence Assessment

**High Confidence (95%)** - Sarah Chen operates as the **primary executive decision catalyst** across the enterprise decision network. The hypergraph analysis shows her involvement in all 15 decision hyperedges, with clear causal chains demonstrating how her initial decisions create precedents that influence subsequent organizational choices.

**Key Evidence:**
- Present as decision-maker in 6/6 major decisions
- Referenced in all precedent justifications
- Demonstrates consistent executive authority patterns
- Creates policy exception frameworks adopted enterprise-wide

Sarah Chen functions as the **central decision hub** in this enterprise context, with her choices creating ripple effects that shape organizational policy interpretation and exception handling across sales, finance, and customer success functions.

### Metrics

| Metric | Value |
|---|---|
| Confidence | 0.8 |
| Paths Found | 1 |
| 2-Morphisms Proposed | 7 |
| 2-Morphisms Stored | 0 (all duplicates of previously stored morphisms) |

### Why this matters

This is the "key person risk" question that no traditional system can answer. HR knows Sarah is VP of Sales. Salesforce knows she's on some deals. But only the context graph can show:

- She's the **catalyst** in every policy exception
- Her authority creates **precedent cascades** that reshape organizational behavior
- If she leaves, the **institutional reasoning** behind these decisions goes with her — unless it's captured in a context graph

This is exactly the "decision intelligence layer" that [Foundation Capital describes](https://foundationcapital.com/context-graphs-ais-trillion-dollar-opportunity/): the reasoning compounds, the graph gets smarter, and the organization retains its decision-making capability even as people move on.

---

## Query 5: "What is the risk of continuing to approve discounts above the standard policy limit?"

> **What this demonstrates:** The feedback loop in action — by Query 5, the graph has grown from 6 to 23 hyperedges. Claude now reasons over not just the original decisions, but all the 2-morphisms extracted from previous queries, producing a richer risk analysis than any single query could.

```bash
curl -s -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query":"What is the risk of continuing to approve discounts above the standard policy limit?"}' | python3 -m json.tool
```

### Claude's Answer

## Risk Analysis: Continuing to Approve Discounts Above Standard Policy Limit

### 1. Direct Answer

**HIGH RISK** - Continuing to approve discounts above the 15% standard policy limit poses significant operational and financial risks:

- **Policy Erosion**: The Standard Discount Policy (15% limit) has been breached twice (20% for Acme, 18% for Initech)
- **Precedent Cascade**: Each exception creates justification for future exceptions, as evidenced by Initech citing "Acme discount approval precedent"
- **Executive Authority Bypass**: VP Sarah Chen's executive authority is being used to circumvent standard approval processes
- **Financial Impact**: Policy exceptions on high-value deals ($500K+ ARR) compound revenue loss

### 2. Causal Chain Analysis

**Primary Decision Sequence:**
```
SEV-1 Production Outage (Acme) → Executive Authority Invocation → 20% Discount Exception → Precedent Establishment → Initech 18% Exception
```

**Key Causal Relationships:**
1. **Incident → Exception**: Service incidents (SEV-1, SEV-2) directly trigger policy exceptions as retention measures
2. **Exception → Precedent**: Acme's 20% discount became explicit justification for Initech's 18% discount
3. **Authority Concentration**: VP Sarah Chen appears as decision-maker in 8 of 15 hyperedges, indicating centralized exception authority
4. **Cross-Policy Impact**: Discount exceptions reference Enterprise SLA Policy precedents, showing policy interconnection

### 3. Precedents and Exception Patterns

**Established Precedents:**
- **Acme Precedent**: 20% discount for strategic accounts with service incident history
- **Enterprise SLA Precedent**: Service credits for SLA violations (15% for Acme, 10% for Globex)
- **Executive Override Pattern**: VP authority bypassing CFO approval for retention decisions

**Exception Justification Framework:**
1. Service incident severity (SEV-1/SEV-2)
2. Customer health score deterioration (Initech: 58, churn risk)
3. Strategic account value ($500K+ ARR)
4. Prior precedent citation

### 4. Confidence Assessment

**Confidence Level: 95%**

**Supporting Evidence:**
- Clear hyperedge connections showing precedent relationships
- Explicit rationale statements citing "Acme discount approval precedent"
- Multiple policy exception morphisms (2-morphism-exception) documented
- Quantifiable policy breaches (20% vs 15%, 18% vs 15%)

**Risk Indicators:**
- Policy exceptions increasing in frequency
- Precedent-based justification becoming standard practice
- Executive authority concentration creating approval bottlenecks
- Financial controls being bypassed for retention decisions

**Recommendation**: Implement stricter exception approval thresholds and require CFO co-approval for all discounts exceeding 15% to prevent further policy erosion.

### Metrics

| Metric | Value |
|---|---|
| Confidence | 0.8 |
| Paths Found | 1 |
| 2-Morphisms Proposed | 8 |
| 2-Morphisms Stored | 8 |

### Why this matters

This is the governance question — and it's the one that shows the **compounding value** of the context graph.

On Query 1, Claude only saw 6 hyperedges (the seed decisions). By Query 5, the graph has grown to **23 hyperedges** because each previous query extracted and stored new 2-morphism relationships. Claude now reasons over a richer decision network and can identify:

- **Precedent cascades** that are invisible in any single system of record
- **Policy erosion patterns** backed by explicit citation chains
- **Concentration risk** (Sarah Chen as single point of authority)
- **Actionable recommendations** grounded in the actual decision trace

This is the feedback loop that [Foundation Capital](https://foundationcapital.com/context-graphs-ais-trillion-dollar-opportunity/) describes: *"The system that wins isn't the one that captures the most context on day one — it's the one that gets better at capturing and delivering context over time."*

---

## Graph Growth: The Feedback Loop

| Stage | Hyperedges | What Changed |
|---|---|---|
| Seed data | 6 decisions + 4 two-morphisms | Initial load |
| After Query 1 | 16 | +6 new 2-morphisms extracted |
| After Query 2 | 17 | +1 new (6 duplicates skipped) |
| After Query 3 | 19 | +2 new |
| After Query 4 | 19 | +0 (all duplicates — dedup working) |
| After Query 5 | 23 | +8 new risk-pattern morphisms |

**Started with 6 seed hyperedges → ended with 23** after 5 queries. The graph nearly **4x'd** from the LLM feedback loop alone.

Each query doesn't just answer a question — it **teaches the graph** by extracting new decision patterns and storing them as first-class 2-morphisms in TypeDB. The next query is smarter because it has more context to reason over.

**LLMs commoditize. Decision intelligence compounds.**

---

## How to Reproduce

```bash
# Clone and setup
git clone https://github.com/vibhavjoshi123/Hypergraph-for-Context-Graph.git
cd Hypergraph-for-Context-Graph
bash scripts/quickstart.sh

# Or run the full example suite (reseeds, runs all 5 queries, saves results)
bash scripts/run_examples.sh
```

Results are saved to `EXAMPLE_RESULTS.md` automatically.

---

## References

- [Context Graphs: AI's Trillion-Dollar Opportunity](https://foundationcapital.com/context-graphs-ais-trillion-dollar-opportunity/) — Foundation Capital
- [Context Graphs: Who Actually Captures It?](https://www.linkedin.com/pulse/context-graphs-trillion-dollar-opportunity-who-actually-prukalpa--kxadc/) — Prukalpa, Metadata Weekly
- [EXAMPLES.md](EXAMPLES.md) — Seed data walkthrough and 2-morphism diagrams
