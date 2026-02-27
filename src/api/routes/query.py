"""Query endpoint for natural language queries against the hypergraph.

Uses the OrchestratorAgent to dynamically route queries:
- Simple lookups skip the LLM and return graph structure directly
- Standard queries run ContextAgent → ExecutiveAgent (with iterative verification)
- Complex multi-entity queries fan out to per-entity sub-agents, then synthesize

The orchestrator replaces the previous fixed 3-step pipeline.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from src.agents.base import AgentQuery
from src.agents.orchestrator import OrchestratorAgent
from src.models.decisions import TwoMorphismType
from src.models.hyperedges import Hyperedge, RelationType, RoleAssignment
from src.typedb.client import TypeDBClient
from src.typedb.traversal import HypergraphTraversal

logger = logging.getLogger(__name__)

router = APIRouter()


class QueryRequest(BaseModel):
    """Natural language query request."""

    query: str = Field(..., description="Natural language query", min_length=1)
    intersection_size: int = Field(
        default=2, ge=1, description="Minimum IS for path finding"
    )
    max_depth: int = Field(default=5, ge=1, description="Maximum traversal depth")
    k_paths: int = Field(default=3, ge=1, description="Number of paths to find")


class QueryResponse(BaseModel):
    """Response to a natural language query."""

    answer: str
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    paths_found: int = 0
    confidence: float = 0.0
    two_morphisms_proposed: int = 0
    two_morphisms_stored: int = 0
    routing_strategy: str = ""
    sub_agents_spawned: int = 0
    spawn_log: list[dict[str, Any]] = Field(default_factory=list)


# ── Per-type queries for full attributes ────────────────────────────

_ENTITY_QUERIES: dict[str, str] = {
    "customer": (
        "match $e isa customer,"
        " has entity-id $id, has entity-name $name, has entity-type-label $etype,"
        " has health-score $hs, has tier $tier, has arr $arr;"
    ),
    "employee": (
        "match $e isa employee,"
        " has entity-id $id, has entity-name $name, has entity-type-label $etype,"
        " has department $dept, has job-role $jr, has title $ttl;"
    ),
    "deal": (
        "match $e isa deal,"
        " has entity-id $id, has entity-name $name, has entity-type-label $etype,"
        " has deal-value $dv, has discount-percentage $dp, has stage $stg;"
    ),
    "ticket": (
        "match $e isa ticket,"
        " has entity-id $id, has entity-name $name, has entity-type-label $etype,"
        " has severity $sev, has status $sts;"
    ),
    "policy": (
        "match $e isa policy,"
        " has entity-id $id, has entity-name $name, has entity-type-label $etype,"
        " has policy-type $pt, has max-discount $md;"
    ),
}


async def _fetch_rich_entities(db: TypeDBClient) -> list[dict[str, Any]]:
    """Fetch entities with all domain-specific attributes, per type."""
    all_entities: list[dict[str, Any]] = []
    for entity_type, q in _ENTITY_QUERIES.items():
        try:
            rows = await db.query(q)
            all_entities.extend(rows)
        except Exception as exc:
            logger.debug("Query for %s failed (may have no data): %s", entity_type, exc)
    return all_entities


async def _fetch_rich_hyperedges(db: TypeDBClient) -> list[dict[str, Any]]:
    """Fetch decision-events with rationale and role-player assignments."""
    # Get decision type + rationale
    decisions = await db.query(
        "match $h isa decision-event,"
        " has decision-type $dt, has rationale $rat;"
    )

    # Get role players for each decision-event
    role_queries = [
        (
            "involved-entity",
            "match $h isa decision-event"
            " (involved-entity: $p); $p has entity-id $pid, has entity-name $pname;",
        ),
        (
            "decision-maker",
            "match $h isa decision-event"
            " (decision-maker: $p); $p has entity-id $pid, has entity-name $pname;",
        ),
    ]

    role_players: list[dict[str, Any]] = []
    for role_name, q in role_queries:
        try:
            rows = await db.query(q)
            for row in rows:
                row["_role"] = role_name
            role_players.extend(rows)
        except Exception as exc:
            logger.debug("Role query for %s failed: %s", role_name, exc)

    # Enrich decisions with role player info
    for dec in decisions:
        dec["role_players"] = role_players

    return decisions


def _build_hyperedges(
    decisions: list[dict[str, Any]],
) -> list[Hyperedge]:
    """Convert raw TypeDB decision results into Hyperedge objects for traversal."""
    hyperedges: list[Hyperedge] = []
    for i, dec in enumerate(decisions):
        participants: list[RoleAssignment] = []
        for rp in dec.get("role_players", []):
            pid = rp.get("pid", "")
            role = rp.get("_role", "involved-entity")
            if pid:
                participants.append(RoleAssignment(entity_id=pid, role=role))

        if len(participants) >= 2:
            hyperedges.append(
                Hyperedge(
                    hyperedge_id=f"dec_{i}",
                    relation_type=RelationType.DECISION,
                    participants=participants,
                )
            )
    return hyperedges


_MORPHISM_TYPE_MAP: dict[str, str] = {
    "precedent": "precedent",
    "exception": "exception",
    "override": "override",
    "generalization": "generalization",
    "sequence": "sequence",
    "justification": "justification",
}


async def _store_2morphisms(
    db: TypeDBClient,
    proposals: list[dict[str, Any]],
) -> int:
    """Write 2-morphism proposals back to TypeDB as decision-event relations.

    This is the feedback loop: the LLM identifies meta-relationships between
    decisions, and we persist them so future queries have richer paths.

    Deduplication: before inserting, checks if a decision-event with the
    same decision-type and rationale already exists.  This prevents infinite
    compounding on repeated / similar queries.

    decision-event requires at least 1 role player (inherits @card(1..)
    from context-hyperedge:participant), so we match an existing entity
    to satisfy the constraint.
    """
    stored = 0
    for proposal in proposals:
        morphism_type = proposal.get("morphism_type", "precedent")
        rationale = proposal.get("rationale", "")
        safe_rationale = rationale.replace('"', "'").replace("\\", "")

        # Map string type to TwoMorphismType enum
        try:
            mtype = TwoMorphismType(
                _MORPHISM_TYPE_MAP.get(morphism_type, "precedent")
            )
        except ValueError:
            mtype = TwoMorphismType.PRECEDENT

        dt_label = f"2-morphism-{mtype.value}"

        # ── Dedup check: skip if identical decision-type + rationale exists ──
        try:
            existing = await db.query(
                "match $h isa decision-event,"
                f' has decision-type "{dt_label}",'
                f' has rationale "{safe_rationale}";'
            )
            if existing:
                logger.debug(
                    "Skipping duplicate 2-morphism: %s (%s)",
                    mtype.value,
                    rationale[:80],
                )
                continue
        except Exception as exc:
            logger.debug("Dedup check failed, proceeding with insert: %s", exc)

        # Match any existing entity as participant (required by @card(1..))
        # and create a decision-event recording the 2-morphism discovery.
        try:
            typeql = (
                "match $e isa enterprise-entity;"
                " limit 1;"
                " insert (involved-entity: $e) isa decision-event,"
                f' has decision-type "{dt_label}",'
                f' has rationale "{safe_rationale}";'
            )
            await db.write(typeql)
            stored += 1
            logger.info(
                "Stored 2-morphism: %s (%s)",
                mtype.value,
                rationale[:80],
            )
        except Exception as exc:
            logger.warning("Failed to store 2-morphism: %s", exc)

    return stored


@router.post("/query", response_model=QueryResponse)
async def query_context_graph(
    request: QueryRequest, req: Request
) -> QueryResponse:
    """Query the context graph with a natural language question.

    Pipeline (adaptive, driven by OrchestratorAgent):
    1. Fetch rich entity and hyperedge data from TypeDB
    2. Orchestrator classifies query complexity
    3. Routes to appropriate strategy:
       - SIMPLE: graph traversal only
       - STANDARD: traversal → iterative LLM reasoning
       - COMPLEX: per-entity fan-out → synthesis → governance
    4. Write 2-morphism proposals back to TypeDB (feedback loop)
    """
    db = getattr(req.app.state, "db", None)
    llm = getattr(req.app.state, "llm", None)

    # Step 1: Fetch rich graph data from TypeDB
    entities: list[dict[str, Any]] = []
    decisions: list[dict[str, Any]] = []
    he_objects: list[Hyperedge] = []

    if db and db.is_connected:
        try:
            entities = await _fetch_rich_entities(db)
            decisions = await _fetch_rich_hyperedges(db)
            he_objects = _build_hyperedges(decisions)
        except Exception as exc:
            logger.warning("Failed to fetch graph context: %s", exc)

    # Step 2: Create the orchestrator with the current graph state
    traversal = HypergraphTraversal(he_objects if he_objects else None)
    orchestrator = OrchestratorAgent(
        traversal=traversal,
        llm=llm,
        entities=entities,
        hyperedges=decisions,
    )

    # Step 3: Let the orchestrator decide the execution strategy
    agent_query = AgentQuery(
        query=request.query,
        intersection_size=request.intersection_size,
        max_depth=request.max_depth,
    )
    response = await orchestrator.process(agent_query)

    # Step 4: Write 2-morphism proposals back to TypeDB
    proposals = response.metadata.get("two_morphism_proposals", [])
    stored = 0
    if proposals and db and db.is_connected:
        stored = await _store_2morphisms(db, proposals)

    routing = response.metadata.get("routing", {})

    spawn_log = routing.get("spawn_log", [])

    return QueryResponse(
        answer=response.answer,
        evidence=response.evidence,
        paths_found=response.paths_found,
        confidence=response.confidence,
        two_morphisms_proposed=len(proposals),
        two_morphisms_stored=stored,
        routing_strategy=routing.get("strategy", ""),
        sub_agents_spawned=routing.get("sub_agents_spawned", len(spawn_log)),
        spawn_log=spawn_log,
    )
