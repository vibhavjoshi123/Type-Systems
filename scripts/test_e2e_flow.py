#!/usr/bin/env python3
"""End-to-end flow test: simulates the full hypergraph pipeline.

This test exercises the complete flow without external dependencies:
1. Entity creation (Customer, Employee, Deal, Ticket, Policy)
2. TypeQL query generation for inserts
3. Hyperedge (DecisionEvent) creation connecting entities
4. s-adjacency traversal
5. BFS path finding
6. Yen's K-shortest paths
7. Embedding similarity search
8. 2-morphism (precedent chain) creation
9. Function invocation query generation
10. API request/response simulation

All TypeDB interactions are simulated with an in-memory store.
"""

from __future__ import annotations

import json
import math
import sys
from collections import defaultdict, deque
from datetime import datetime

PASS = 0
FAIL = 0
STEP = 0


def step(name: str) -> None:
    global STEP
    STEP += 1
    print(f"\n{'─'*60}")
    print(f"  Step {STEP}: {name}")
    print(f"{'─'*60}")


def test(name: str, condition: bool, detail: str = "") -> None:
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"    PASS  {name}")
    else:
        FAIL += 1
        print(f"    FAIL  {name} {detail}")


def cosine_similarity(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb) if na and nb else 0.0


# ════════════════════════════════════════════════════════════════════
# In-memory TypeDB simulator
# ════════════════════════════════════════════════════════════════════
class InMemoryTypeDB:
    """Simulates TypeDB 3.x operations in memory."""

    def __init__(self):
        self.entities: dict[str, dict] = {}
        self.relations: list[dict] = []
        self.embeddings: dict[str, list[float]] = {}
        self.queries_executed: list[str] = []

    def insert_entity(self, entity_type, entity_id, name, **attrs):
        self.entities[entity_id] = {
            "entity_id": entity_id,
            "entity_name": name,
            "entity_type": entity_type,
            **attrs,
        }
        # Build TypeQL (validates query generation)
        attr_parts = [
            f'has entity-id "{entity_id}"',
            f'has entity-name "{name}"',
            f'has entity-type-label "{entity_type}"',
        ]
        for k, v in attrs.items():
            attr_name = k.replace("_", "-")
            if isinstance(v, str):
                attr_parts.append(f'has {attr_name} "{v}"')
            elif isinstance(v, (int, float)):
                attr_parts.append(f"has {attr_name} {v}")
        typeql = f"insert $e isa {entity_type}, {', '.join(attr_parts)};"
        self.queries_executed.append(typeql)
        return typeql

    def insert_relation(self, relation_type, participants, **attrs):
        rel = {
            "type": relation_type,
            "participants": participants,
            "entity_ids": {p["entity_id"] for p in participants},
            **attrs,
        }
        self.relations.append(rel)
        # Build TypeQL
        match_parts = []
        role_parts = []
        for i, p in enumerate(participants):
            var = f"$p{i}"
            match_parts.append(
                f'{var} isa enterprise-entity, has entity-id "{p["entity_id"]}";'
            )
            role_parts.append(f"{p['role']}: {var}")
        typeql = (
            f"match\n    {' '.join(match_parts)}\n"
            f"insert\n    ({', '.join(role_parts)}) isa {relation_type};"
        )
        self.queries_executed.append(typeql)
        return typeql

    def get_entity(self, entity_id):
        return self.entities.get(entity_id)

    def get_relations_for_entity(self, entity_id):
        return [r for r in self.relations if entity_id in r["entity_ids"]]

    def delete_entity(self, entity_id):
        if entity_id in self.entities:
            del self.entities[entity_id]
            typeql = (
                f'match\n    $e isa enterprise-entity, has entity-id "{entity_id}";\n'
                f"delete $e;"
            )
            self.queries_executed.append(typeql)
            return True
        return False


# ════════════════════════════════════════════════════════════════════
# BEGIN END-TO-END FLOW
# ════════════════════════════════════════════════════════════════════
print("=" * 60)
print("  END-TO-END FLOW TEST: Hypergraph Context Graph")
print("  Simulating full pipeline with in-memory TypeDB")
print("=" * 60)

db = InMemoryTypeDB()

# ── Step 1: Create Enterprise Entities ─────────────────────────────
step("Create Enterprise Entities")

entities_to_create = [
    ("customer", "cust_001", "Acme Corp", {"health_score": 72.0, "tier": "enterprise"}),
    ("customer", "cust_002", "Globex Inc", {"health_score": 45.0, "tier": "mid-market"}),
    ("employee", "emp_001", "Sarah Chen", {"department": "Sales", "role": "VP"}),
    ("employee", "emp_002", "James Lee", {"department": "Support", "role": "Manager"}),
    ("deal", "deal_001", "Acme Renewal Q1", {"deal_value": 500000.0, "stage": "negotiation"}),
    ("ticket", "tkt_001", "Prod Outage Jan 2026", {"severity": "SEV-1", "status": "resolved"}),
    ("ticket", "tkt_002", "API Latency Issue", {"severity": "SEV-2", "status": "open"}),
    ("policy", "pol_001", "Standard Discount Policy", {"policy_type": "discount", "max_discount": 15.0}),
]

for etype, eid, name, attrs in entities_to_create:
    q = db.insert_entity(etype, eid, name, **attrs)

test(f"created {len(db.entities)} entities", len(db.entities) == 8)
test("Acme Corp exists", db.get_entity("cust_001") is not None)
test("Acme health_score=72.0", db.get_entity("cust_001")["health_score"] == 72.0)
test("Globex health_score=45.0 (at-risk)", db.get_entity("cust_002")["health_score"] == 45.0)


# ── Step 2: Create Decision Event Hyperedges ───────────────────────
step("Create Decision Event Hyperedges")

# Decision 1: VP approves 20% discount for Acme (5 entities involved)
dec1 = db.insert_relation(
    "decision-event",
    [
        {"entity_id": "cust_001", "role": "involved-entity"},
        {"entity_id": "emp_001", "role": "decision-maker"},
        {"entity_id": "deal_001", "role": "involved-entity"},
        {"entity_id": "tkt_001", "role": "involved-entity"},
        {"entity_id": "pol_001", "role": "involved-entity"},
    ],
    decision_type="discount-approval",
    rationale="VP approved 20% discount exceeding 15% policy limit",
)

# Decision 2: Escalation for Acme ticket (3 entities)
dec2 = db.insert_relation(
    "escalation",
    [
        {"entity_id": "cust_001", "role": "involved-entity"},
        {"entity_id": "emp_002", "role": "decision-maker"},
        {"entity_id": "tkt_001", "role": "involved-entity"},
    ],
    decision_type="ticket-escalation",
    rationale="Escalated SEV-1 to management",
)

# Decision 3: Support response to API latency (3 entities)
dec3 = db.insert_relation(
    "incident-event",
    [
        {"entity_id": "cust_002", "role": "involved-entity"},
        {"entity_id": "emp_002", "role": "decision-maker"},
        {"entity_id": "tkt_002", "role": "involved-entity"},
    ],
    decision_type="incident-response",
    rationale="Support manager responding to API latency",
)

# Decision 4: New deal assessment (3 entities, shares cust_002 + emp_002 with dec3)
dec4 = db.insert_relation(
    "decision-event",
    [
        {"entity_id": "cust_002", "role": "involved-entity"},
        {"entity_id": "emp_002", "role": "decision-maker"},
        {"entity_id": "deal_001", "role": "involved-entity"},
    ],
    decision_type="deal-assessment",
    rationale="Assessing deal risk given open incidents",
)

test(f"created {len(db.relations)} hyperedges", len(db.relations) == 4)
test("dec1 has 5 participants", len(db.relations[0]["entity_ids"]) == 5)
test("dec2 has 3 participants", len(db.relations[1]["entity_ids"]) == 3)
test("TypeQL uses match/insert", "match" in dec1 and "insert" in dec1)


# ── Step 3: s-Adjacency Analysis ──────────────────────────────────
step("s-Adjacency Analysis (IS >= 2)")


class TestHyperedge:
    def __init__(self, idx, entity_ids):
        self.idx = idx
        self.entity_ids = set(entity_ids)

    def intersection_size(self, other):
        return len(self.entity_ids & other.entity_ids)

    def is_s_adjacent(self, other, s=2):
        return self.intersection_size(other) >= s


hedges = [TestHyperedge(i, r["entity_ids"]) for i, r in enumerate(db.relations)]

# dec1 (cust_001, emp_001, deal_001, tkt_001, pol_001) vs
# dec2 (cust_001, emp_002, tkt_001) -> share {cust_001, tkt_001} = IS=2 ✓
is_01 = hedges[0].intersection_size(hedges[1])
test(f"dec1↔dec2: IS={is_01} (share cust_001, tkt_001)", is_01 == 2)
test("dec1 s=2 adj to dec2", hedges[0].is_s_adjacent(hedges[1], 2))

# dec2 (cust_001, emp_002, tkt_001) vs
# dec3 (cust_002, emp_002, tkt_002) -> share {emp_002} = IS=1 ✗
is_12 = hedges[1].intersection_size(hedges[2])
test(f"dec2↔dec3: IS={is_12} (share emp_002 only)", is_12 == 1)
test("dec2 NOT s=2 adj to dec3", not hedges[1].is_s_adjacent(hedges[2], 2))

# dec3 (cust_002, emp_002, tkt_002) vs
# dec4 (cust_002, emp_002, deal_001) -> share {cust_002, emp_002} = IS=2 ✓
is_23 = hedges[2].intersection_size(hedges[3])
test(f"dec3↔dec4: IS={is_23} (share cust_002, emp_002)", is_23 == 2)
test("dec3 s=2 adj to dec4", hedges[2].is_s_adjacent(hedges[3], 2))

# Noise reduction: at s=1, dec2↔dec3 connected; at s=2, disconnected
test("s=2 filters noisy connection (dec2↔dec3)", not hedges[1].is_s_adjacent(hedges[2], 2))
test(
    "s=1 would keep noisy connection",
    hedges[1].is_s_adjacent(hedges[2], 1),
)
print("    → IS>=2 correctly filters weak (single-entity) connections")


# ── Step 4: BFS Traversal ─────────────────────────────────────────
step("BFS Traversal over s-Adjacency Graph")


def bfs(hedges, start, target=None, s=2, max_depth=10):
    visited = {start}
    parent = {start: None}
    queue = deque([(start, 0)])
    while queue:
        current, depth = queue.popleft()
        if target is not None and current == target:
            path = []
            node = current
            while node is not None:
                path.append(node)
                node = parent[node]
            return list(reversed(path))
        if depth >= max_depth:
            continue
        for i, h in enumerate(hedges):
            if i in visited:
                continue
            if hedges[current].is_s_adjacent(h, s):
                visited.add(i)
                parent[i] = current
                queue.append((i, depth + 1))
    if target is not None:
        return None
    return visited


# BFS from dec1: should reach dec2 (share 2 entities), NOT dec3/dec4
component = bfs(hedges, 0)
test("BFS s=2 from dec1: reaches dec2", 1 in component)
test("BFS s=2 from dec1: cannot reach dec3", 2 not in component)
test("BFS s=2 from dec1: cannot reach dec4", 3 not in component)

# Separate component: dec3 ↔ dec4
component2 = bfs(hedges, 2)
test("BFS s=2 from dec3: reaches dec4", 3 in component2)
test("BFS s=2 from dec3: cannot reach dec1", 0 not in component2)

# Path finding
path = bfs(hedges, 0, target=1, s=2)
test("path dec1→dec2 exists", path is not None)
test("path length = 2 (direct)", path is not None and len(path) == 2)

no_path = bfs(hedges, 0, target=2, s=2)
test("no path dec1→dec3 at s=2", no_path is None)

# At s=1, more paths exist
path_s1 = bfs(hedges, 0, target=3, s=1)
test("path dec1→dec4 at s=1 exists (via dec2→dec3)", path_s1 is not None)
if path_s1:
    test(f"path length = {len(path_s1)}", len(path_s1) >= 2)
    print(f"    → Path: dec{path_s1[0]+1} → " + " → ".join(f"dec{p+1}" for p in path_s1[1:]))


# ── Step 5: s-Connected Components ────────────────────────────────
step("s-Connected Component Discovery")


def find_components(hedges, s=2):
    visited = set()
    components = []
    for i in range(len(hedges)):
        if i in visited:
            continue
        comp = bfs(hedges, i, s=s)
        visited.update(comp)
        components.append(sorted(comp))
    return components


components_s2 = find_components(hedges, s=2)
test(f"found {len(components_s2)} components at s=2", len(components_s2) == 2)
test("component 1: {dec1, dec2}", [0, 1] in components_s2)
test("component 2: {dec3, dec4}", [2, 3] in components_s2)
print("    → Two distinct decision clusters identified:")
print("      Cluster 1: Acme discount approval + ticket escalation")
print("      Cluster 2: Globex incident + deal assessment")

components_s1 = find_components(hedges, s=1)
test("at s=1: single component (all connected)", len(components_s1) == 1)


# ── Step 6: Embedding Similarity Search ───────────────────────────
step("Embedding Similarity Search")

db.embeddings = {
    "cust_001": [0.9, 0.1, 0.0, 0.0],  # Acme: high-value enterprise
    "cust_002": [0.1, 0.8, 0.1, 0.0],  # Globex: mid-market with issues
    "emp_001": [0.3, 0.0, 0.7, 0.0],   # VP Sales
    "emp_002": [0.0, 0.3, 0.0, 0.7],   # Support Manager
    "deal_001": [0.8, 0.1, 0.1, 0.0],  # Deal: similar to Acme
    "tkt_001": [0.1, 0.7, 0.0, 0.2],   # Ticket: similar to Globex (problems)
    "tkt_002": [0.0, 0.6, 0.0, 0.4],   # Ticket: similar to Globex
    "pol_001": [0.5, 0.0, 0.5, 0.0],   # Policy: between Acme and VP
}

# Query: "find entities similar to Acme Corp"
query_vec = db.embeddings["cust_001"]
scored = []
for eid, emb in db.embeddings.items():
    if eid == "cust_001":
        continue
    scored.append((cosine_similarity(query_vec, emb), eid))
scored.sort(reverse=True)

test("most similar to Acme is deal_001", scored[0][1] == "deal_001")
test(f"deal_001 similarity = {scored[0][0]:.3f}", scored[0][0] > 0.8)
print(f"    → Top 3 entities similar to Acme Corp:")
for sim, eid in scored[:3]:
    name = db.get_entity(eid)["entity_name"]
    print(f"      {eid}: {name} (similarity={sim:.3f})")


# ── Step 7: 2-Morphism (Precedent Chain) ──────────────────────────
step("2-Morphism: Precedent Chain Between Decisions")


def build_precedent_chain_query(precedent_id, derived_id, morphism_type, rationale=None):
    """Build TypeQL for inserting a 2-morphism (meta-relation between decisions)."""
    typeql = (
        f'match\n'
        f'    $d1 isa decision-event, has entity-id "{precedent_id}";\n'
        f'    $d2 isa decision-event, has entity-id "{derived_id}";\n'
        f'insert\n'
        f'    (precedent-decision: $d1, derived-decision: $d2)\n'
        f'    isa precedent-chain,\n'
        f'    has precedent-type "{morphism_type}"'
    )
    if rationale:
        typeql += f',\n    has rationale "{rationale}"'
    typeql += ";"
    return typeql


q = build_precedent_chain_query(
    "dec_001", "dec_002", "precedent",
    "Discount approval set precedent for future escalation handling",
)
test("2-morphism query has precedent-chain", "precedent-chain" in q)
test("2-morphism matches both decisions", "$d1 isa decision-event" in q and "$d2 isa decision-event" in q)
test("2-morphism has roles", "precedent-decision: $d1" in q)
test("2-morphism has morphism type", 'has precedent-type "precedent"' in q)
test("2-morphism has rationale", "has rationale" in q)
print("    → 2-morphism creates meta-relation: dec1 (discount) → dec2 (escalation)")


# ── Step 8: Function Invocation Query ──────────────────────────────
step("TypeDB 3.x Function Invocation")

# In TypeDB 3.x, functions are explicitly called in match clauses
function_query = """
match
    $c in customers_at_risk();
    $c has entity-name $name, has health-score $hs;
"""
test("function invocation uses 'in' keyword", "$c in customers_at_risk()" in function_query)
test("no inference toggle (3.x explicit)", "inference" not in function_query.lower())

# Simulate function: customers with health_score < 70
at_risk = [
    (eid, e) for eid, e in db.entities.items()
    if e["entity_type"] == "customer" and e.get("health_score", 100) < 70
]
test(f"found {len(at_risk)} at-risk customer(s)", len(at_risk) == 1)
test("Globex Inc is at-risk", at_risk[0][0] == "cust_002")
print(f"    → At-risk: {at_risk[0][1]['entity_name']} (health={at_risk[0][1]['health_score']})")


# ── Step 9: API Flow Simulation ────────────────────────────────────
step("API Request/Response Flow Simulation")


def simulate_api_health(db_connected):
    return {"status": "healthy", "version": "0.1.0", "typedb_connected": db_connected}


def simulate_api_create_entity(entity_data, db_connected):
    if not db_connected:
        return 503, {"detail": "TypeDB not connected"}
    return 201, entity_data


def simulate_api_query(query_text, db_connected):
    if not db_connected:
        return 503, {"detail": "TypeDB not connected"}
    return 200, {"query": query_text, "results": [], "context": {}}


health = simulate_api_health(True)
test("health check returns healthy", health["status"] == "healthy")
test("health shows typedb connected", health["typedb_connected"] is True)

status, body = simulate_api_create_entity({"entity_id": "test"}, True)
test("create entity returns 201", status == 201)

status, body = simulate_api_create_entity({"entity_id": "test"}, False)
test("create without DB returns 503", status == 503)

status, body = simulate_api_query("What decisions involve Acme?", True)
test("query returns 200", status == 200)


# ── Step 10: Full Pipeline Integration ─────────────────────────────
step("Full Pipeline: Ingest → Store → Query → Traverse → Reason")

print("    Simulating: 'Why was Acme given a 20% discount?'")
print()

# 1. Find entity
target = db.get_entity("cust_001")
test("found target entity: Acme Corp", target is not None)

# 2. Get all relations involving this entity
related = db.get_relations_for_entity("cust_001")
test(f"found {len(related)} related hyperedges", len(related) == 2)

# 3. Identify the discount decision
discount_decision = None
for r in related:
    if r.get("decision_type") == "discount-approval":
        discount_decision = r
        break
test("found discount-approval decision", discount_decision is not None)

# 4. Get all entities in this decision
participants = discount_decision["entity_ids"]
test("decision involves 5 entities", len(participants) == 5)

# 5. Build context: gather entity details
context_entities = []
for eid in sorted(participants):
    e = db.get_entity(eid)
    context_entities.append(e)

print("    Decision context:")
for e in context_entities:
    etype = e["entity_type"]
    name = e["entity_name"]
    extra = {k: v for k, v in e.items() if k not in ("entity_id", "entity_name", "entity_type")}
    print(f"      [{etype}] {name}: {extra}")

# 6. Check for s-adjacent decisions
escalation = db.relations[1]
shared = discount_decision["entity_ids"] & escalation["entity_ids"]
test(f"found s-adjacent escalation (shared: {shared})", len(shared) >= 2)

# 7. Simulate LLM reasoning output
reasoning = (
    "The 20% discount for Acme Corp was approved by VP Sarah Chen because:\n"
    "1. Acme is an enterprise-tier customer (health_score=72.0)\n"
    "2. They experienced a SEV-1 production outage (tkt_001)\n"
    "3. The deal value is $500K (deal_001)\n"
    "4. Although the standard discount policy limits to 15% (pol_001),\n"
    "   the VP exercised exception authority given the incident history.\n"
    "5. An s-adjacent escalation decision confirms the severity context."
)
print()
print("    LLM Reasoning Output:")
for line in reasoning.split("\n"):
    print(f"      {line}")

test("reasoning references all 5 entities", all(
    term in reasoning for term in ["Acme", "Sarah Chen", "SEV-1", "$500K", "15%"]
))
test("reasoning explains exception", "exception" in reasoning.lower())


# ════════════════════════════════════════════════════════════════════
# Summary
# ════════════════════════════════════════════════════════════════════
print(f"\n{'═'*60}")
print(f"  RESULTS: {PASS} passed, {FAIL} failed out of {PASS + FAIL} tests")
print(f"  TypeQL queries generated: {len(db.queries_executed)}")
print(f"  Entities in graph: {len(db.entities)}")
print(f"  Relations in graph: {len(db.relations)}")
print(f"  s-Connected components (s=2): {len(components_s2)}")
print(f"{'═'*60}")

sys.exit(1 if FAIL > 0 else 0)
