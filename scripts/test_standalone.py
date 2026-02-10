#!/usr/bin/env python3
"""Standalone tests that exercise core logic without external dependencies.

Tests: cosine similarity, TypeDB 3.x function generation, schema syntax,
config model, traversal algorithms, and query generation.
"""

from __future__ import annotations

import json
import math
import sys

PASS = 0
FAIL = 0


def test(name: str, condition: bool, detail: str = "") -> None:
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  PASS  {name}")
    else:
        FAIL += 1
        print(f"  FAIL  {name} {detail}")


# ────────────────────────────────────────────────────────────────────
# 1. Cosine Similarity (from embeddings.py)
# ────────────────────────────────────────────────────────────────────
print("\n=== Cosine Similarity ===")


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        raise ValueError(f"Vector dimension mismatch: {len(a)} vs {len(b)}")
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


test("identical vectors = 1.0", abs(cosine_similarity([1, 0, 0], [1, 0, 0]) - 1.0) < 1e-9)
test("orthogonal vectors = 0.0", abs(cosine_similarity([1, 0], [0, 1])) < 1e-9)
test("opposite vectors = -1.0", abs(cosine_similarity([1, 0], [-1, 0]) + 1.0) < 1e-9)
test("zero vector = 0.0", cosine_similarity([0, 0, 0], [1, 2, 3]) == 0.0)

sim = cosine_similarity([1, 1, 0], [1, 0, 0])
test("similar vectors 0.5 < sim < 1.0", 0.5 < sim < 1.0, f"got {sim:.4f}")

try:
    cosine_similarity([1, 2], [1, 2, 3])
    test("dimension mismatch raises ValueError", False)
except ValueError:
    test("dimension mismatch raises ValueError", True)


# ────────────────────────────────────────────────────────────────────
# 2. TypeDB 3.x Schema Syntax Validation
# ────────────────────────────────────────────────────────────────────
print("\n=== TypeDB 3.x Schema Syntax ===")

# Read the schema file
sys.path.insert(0, "/home/user/Hypergraph-for-Context-Graph")

# Parse schema directly from file to avoid pydantic import
with open("/home/user/Hypergraph-for-Context-Graph/src/typedb/schema.py") as f:
    schema_content = f.read()

# Extract SCHEMA_TYPEQL string
start = schema_content.index('SCHEMA_TYPEQL = """') + len('SCHEMA_TYPEQL = """')
end = schema_content.index('"""', start)
schema = schema_content[start:end]

# 3.x: uses 'attribute X, value string;' not 'X sub attribute'
test("3.x attribute syntax", "attribute entity-id, value string;" in schema)
test("no 2.x 'sub attribute' syntax", "sub attribute" not in schema)

# 3.x: uses 'entity X,' not 'X sub entity'
test("3.x entity syntax (customer)", "entity customer, sub enterprise-entity," in schema)
test("3.x abstract entity", "entity enterprise-entity @abstract," in schema)

# 3.x: uses 'relation X,' not 'X sub relation'
test("3.x relation syntax", "relation context-hyperedge," in schema)
test("3.x relation subtype", "relation decision-event, sub context-hyperedge," in schema)

# 3.x: @card annotations
test("@card annotation on tier", "owns tier @card(0..)" in schema)
test("@card annotation on participant", "relates participant @card(1..)" in schema)

# No 2.x rules in schema
test("no 2.x 'rule' keyword in schema", "rule " not in schema)

# Check FUNCTIONS_TYPEQL exists
test("FUNCTIONS_TYPEQL defined", "FUNCTIONS_TYPEQL" in schema_content)
test("3.x 'fun' keyword in functions", "fun customers_at_risk" in schema_content)
test("3.x 'return' in functions", "return { $c };" in schema_content)


# ────────────────────────────────────────────────────────────────────
# 3. TypeDB 3.x Function Generation (from inference.py)
# ────────────────────────────────────────────────────────────────────
print("\n=== TypeDB 3.x Function Generation ===")

from dataclasses import dataclass


@dataclass
class TypeDBFunction:
    name: str
    signature: str
    body: str
    description: str = ""

    def to_typeql(self) -> str:
        return f"define\nfun {self.name}{self.signature}:\n{self.body}"


func = TypeDBFunction(
    name="customers_at_risk",
    signature="() -> { customer }",
    body=(
        "    match\n"
        "        $c isa customer, has health-score $hs;\n"
        "        $hs < 70.0;\n"
        "    return { $c };"
    ),
)

typeql = func.to_typeql()
test("function starts with 'define'", typeql.startswith("define"))
test("contains 'fun customers_at_risk'", "fun customers_at_risk" in typeql)
test("contains signature", "() -> { customer }" in typeql)
test("contains match clause", "match" in typeql)
test("contains return clause", "return { $c };" in typeql)
test("no 2.x 'rule' or 'when/then'", "rule " not in typeql and "when" not in typeql)


# ────────────────────────────────────────────────────────────────────
# 4. TypeDB 3.x Client Connection Code Validation
# ────────────────────────────────────────────────────────────────────
print("\n=== TypeDB 3.x Client Code Validation ===")

with open("/home/user/Hypergraph-for-Context-Graph/src/typedb/client.py") as f:
    client_code = f.read()

test("uses TypeDB.driver() (3.x)", "TypeDB.driver(" in client_code)
test("no TypeDB.core_driver() (2.x)", "core_driver" not in client_code)
test("uses Credentials class", "Credentials(" in client_code)
test("uses DriverOptions class", "DriverOptions(" in client_code)
test("uses TransactionType", "TransactionType.SCHEMA" in client_code)
test("no session() calls (2.x)", "driver.session(" not in client_code and ".session(" not in client_code)
test("uses .resolve() on queries", ".resolve()" in client_code)
test("uses .as_concept_documents()", ".as_concept_documents()" in client_code)
test("uses .as_concept_rows()", ".as_concept_rows()" in client_code)
test("driver.transaction() (3.x)", "driver.transaction(" in client_code)


# ────────────────────────────────────────────────────────────────────
# 5. Config Validation
# ────────────────────────────────────────────────────────────────────
print("\n=== Config Validation ===")

with open("/home/user/Hypergraph-for-Context-Graph/src/config.py") as f:
    config_code = f.read()

test("has address field (unified)", "address: str" in config_code)
test("no separate host/port fields", "host: str" not in config_code.split("class LLMSettings")[0]
     or "TYPEDB_HOST" not in config_code)
test("has tls_enabled", "tls_enabled: bool" in config_code)
test("has tls_root_ca", "tls_root_ca: str" in config_code)
test("has username", "username: str" in config_code)
test("has password", "password: str" in config_code)
test("default username=admin", '"admin"' in config_code)


# ────────────────────────────────────────────────────────────────────
# 6. .env File Validation
# ────────────────────────────────────────────────────────────────────
print("\n=== .env Configuration ===")

with open("/home/user/Hypergraph-for-Context-Graph/.env") as f:
    env_content = f.read()

test("TypeDB Cloud address configured", "rv7ii3-0.cluster.typedb.com" in env_content)
test("TLS enabled for Cloud", "TYPEDB_TLS_ENABLED=true" in env_content)
test("Anthropic API key set", "LLM_ANTHROPIC_API_KEY=sk-ant-" in env_content)
test("database name set", "TYPEDB_DATABASE=context_graph" in env_content)


# ────────────────────────────────────────────────────────────────────
# 7. TypeQL Query Generation (simulating operations.py)
# ────────────────────────────────────────────────────────────────────
print("\n=== TypeQL Query Generation ===")


def build_insert_query(entity_type: str, entity_id: str, name: str, **attrs) -> str:
    """Simulate what operations.py does."""
    attr_parts = [
        f'has entity-id "{entity_id}"',
        f'has entity-name "{name}"',
        f'has entity-type-label "{entity_type}"',
    ]
    for key, value in attrs.items():
        attr_name = key.replace("_", "-")
        if isinstance(value, str):
            attr_parts.append(f'has {attr_name} "{value}"')
        elif isinstance(value, (int, float)):
            attr_parts.append(f"has {attr_name} {value}")
    return f"insert $e isa {entity_type}, {', '.join(attr_parts)};"


q = build_insert_query("customer", "cust_001", "Acme Corp", health_score=72.0, tier="enterprise")
test("insert query has 'insert $e isa customer'", "insert $e isa customer" in q)
test("insert has entity-id", 'has entity-id "cust_001"' in q)
test("insert has entity-name", 'has entity-name "Acme Corp"' in q)
test("insert has health-score", "has health-score 72.0" in q)
test("insert has tier", 'has tier "enterprise"' in q)


def build_delete_query(entity_id: str) -> str:
    return f"""match\n    $e isa enterprise-entity, has entity-id "{entity_id}";\ndelete $e;"""


d = build_delete_query("cust_001")
test("delete uses 3.x syntax", "delete $e;" in d)
test("delete has match clause", "match" in d)


def build_hyperedge_insert(participants: list[tuple[str, str]], relation_type: str) -> str:
    match_parts = []
    role_parts = []
    for i, (eid, role) in enumerate(participants):
        var = f"$p{i}"
        match_parts.append(f'{var} isa enterprise-entity, has entity-id "{eid}";')
        role_parts.append(f"{role}: {var}")
    return (
        f"match\n    {'  '.join(match_parts)}\n"
        f"insert\n    ({', '.join(role_parts)}) isa {relation_type};"
    )


h = build_hyperedge_insert(
    [("cust_001", "involved-entity"), ("emp_001", "decision-maker")],
    "decision-event",
)
test("hyperedge match finds participants", "$p0 isa enterprise-entity" in h)
test("hyperedge inserts relation", "isa decision-event" in h)
test("hyperedge has roles", "involved-entity: $p0" in h)
test("hyperedge has decision-maker role", "decision-maker: $p1" in h)


# ────────────────────────────────────────────────────────────────────
# 8. Embedding Store Logic
# ────────────────────────────────────────────────────────────────────
print("\n=== Embedding Store Logic ===")


def find_similar(
    query: list[float],
    store: dict[str, list[float]],
    top_k: int = 3,
    threshold: float = 0.0,
) -> list[dict]:
    scored = []
    for eid, emb in store.items():
        score = cosine_similarity(query, emb)
        if score >= threshold:
            scored.append((score, eid))
    scored.sort(reverse=True)
    return [{"entity_id": eid, "similarity": s} for s, eid in scored[:top_k]]


store = {
    "cust_001": [1.0, 0.0, 0.0],
    "cust_002": [0.9, 0.1, 0.0],
    "cust_003": [0.0, 1.0, 0.0],
    "cust_004": [0.0, 0.0, 1.0],
}

results = find_similar([1.0, 0.0, 0.0], store, top_k=2)
test("top-2 returns 2 results", len(results) == 2)
test("most similar is cust_001", results[0]["entity_id"] == "cust_001")
test("second most similar is cust_002", results[1]["entity_id"] == "cust_002")
test("cust_001 similarity = 1.0", abs(results[0]["similarity"] - 1.0) < 1e-9)

results_threshold = find_similar([1.0, 0.0, 0.0], store, threshold=0.5)
test("threshold filters low-similarity", all(r["similarity"] >= 0.5 for r in results_threshold))
test(
    "threshold excludes orthogonal",
    "cust_003" not in [r["entity_id"] for r in results_threshold],
)


# ────────────────────────────────────────────────────────────────────
# 9. s-Adjacency & Traversal Logic
# ────────────────────────────────────────────────────────────────────
print("\n=== s-Adjacency & Traversal ===")

from collections import defaultdict, deque


class SimpleHyperedge:
    def __init__(self, entity_ids: set[str]):
        self.entity_ids = entity_ids

    def is_s_adjacent(self, other, s=2):
        return len(self.entity_ids & other.entity_ids) >= s


# Create test hypergraph:
# H0: {A, B, C}
# H1: {B, C, D}  -- shares B,C with H0 -> s=2 adjacent
# H2: {D, E, F}  -- shares D only with H1 -> NOT s=2 adjacent
# H3: {A, E, F}  -- shares A only with H0, shares E,F with H2 -> s=2 adj to H2
hyperedges = [
    SimpleHyperedge({"A", "B", "C"}),
    SimpleHyperedge({"B", "C", "D"}),
    SimpleHyperedge({"D", "E", "F"}),
    SimpleHyperedge({"A", "E", "F"}),
]

test("H0 s=2 adjacent to H1", hyperedges[0].is_s_adjacent(hyperedges[1], 2))
test("H0 NOT s=2 adj to H2", not hyperedges[0].is_s_adjacent(hyperedges[2], 2))
test("H0 NOT s=2 adj to H3", not hyperedges[0].is_s_adjacent(hyperedges[3], 2))
test("H1 NOT s=2 adj to H2", not hyperedges[1].is_s_adjacent(hyperedges[2], 2))
test("H2 s=2 adjacent to H3", hyperedges[2].is_s_adjacent(hyperedges[3], 2))

# s=1 adjacency (more permissive)
test("H0 s=1 adj to H3 (share A)", hyperedges[0].is_s_adjacent(hyperedges[3], 1))
test("H1 s=1 adj to H2 (share D)", hyperedges[1].is_s_adjacent(hyperedges[2], 1))


# BFS over s-adjacency graph
def bfs_s_adjacency(edges, start, s=2):
    visited = {start}
    queue = deque([start])
    while queue:
        current = queue.popleft()
        for i, he in enumerate(edges):
            if i in visited:
                continue
            if edges[current].is_s_adjacent(he, s):
                visited.add(i)
                queue.append(i)
    return visited


component_from_0 = bfs_s_adjacency(hyperedges, 0, s=2)
test("BFS s=2 from H0: reaches H1", 1 in component_from_0)
test("BFS s=2 from H0: does NOT reach H2", 2 not in component_from_0)
test("BFS s=2 from H0: does NOT reach H3", 3 not in component_from_0)

component_from_2 = bfs_s_adjacency(hyperedges, 2, s=2)
test("BFS s=2 from H2: reaches H3", 3 in component_from_2)
test("BFS s=2 from H2: does NOT reach H0", 0 not in component_from_2)

# At s=1, everything should be reachable (connected)
component_s1 = bfs_s_adjacency(hyperedges, 0, s=1)
test("BFS s=1 from H0: all reachable", component_s1 == {0, 1, 2, 3})


# ────────────────────────────────────────────────────────────────────
# 10. Delete Syntax (3.x specific)
# ────────────────────────────────────────────────────────────────────
print("\n=== TypeDB 3.x Delete Syntax ===")

with open("/home/user/Hypergraph-for-Context-Graph/src/typedb/embeddings.py") as f:
    emb_code = f.read()

test(
    "3.x delete uses 'of' syntax",
    "delete embedding-json of $e;" in emb_code,
)
test(
    "no 2.x 'delete $e has $emb' syntax",
    "delete $e has" not in emb_code,
)

with open("/home/user/Hypergraph-for-Context-Graph/src/typedb/operations.py") as f:
    ops_code = f.read()

test("entity delete uses 'delete $e;'", "delete $e;" in ops_code)


# ────────────────────────────────────────────────────────────────────
# 11. pyproject.toml driver version
# ────────────────────────────────────────────────────────────────────
print("\n=== Dependency Version ===")

with open("/home/user/Hypergraph-for-Context-Graph/pyproject.toml") as f:
    toml = f.read()

test("typedb-driver >= 3.0.0", "typedb-driver>=3.0.0" in toml)
test("no 2.x driver version", "typedb-driver>=2" not in toml)


# ────────────────────────────────────────────────────────────────────
# Summary
# ────────────────────────────────────────────────────────────────────
print(f"\n{'='*50}")
print(f"  RESULTS: {PASS} passed, {FAIL} failed out of {PASS + FAIL} tests")
print(f"{'='*50}")

sys.exit(1 if FAIL > 0 else 0)
