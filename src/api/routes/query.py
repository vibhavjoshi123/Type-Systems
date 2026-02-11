"""Query endpoint for natural language queries against the hypergraph.

Wires together the multi-agent system: ContextAgent finds paths,
ExecutiveAgent reasons over context using Claude.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from src.agents.base import AgentQuery
from src.agents.context_agent import ContextAgent
from src.agents.executive_agent import ExecutiveAgent
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


async def _fetch_graph_context(db: TypeDBClient) -> dict[str, Any]:
    """Fetch entities and hyperedges from TypeDB for agent context."""
    entities = await db.query(
        "match $e isa enterprise-entity,"
        " has entity-id $id,"
        " has entity-name $name,"
        " has entity-type-label $etype;"
    )

    hyperedges = await db.query(
        "match $h isa decision-event,"
        " has decision-type $dt;"
    )

    return {"entities": entities, "hyperedges": hyperedges}


@router.post("/query", response_model=QueryResponse)
async def query_context_graph(
    request: QueryRequest, req: Request
) -> QueryResponse:
    """Query the context graph with a natural language question.

    Pipeline:
    1. Fetch entities and hyperedges from TypeDB
    2. ContextAgent: traverses hypergraph, finds s-connected components
    3. ExecutiveAgent: uses Claude to reason over the graph context
    """
    db = getattr(req.app.state, "db", None)
    llm = getattr(req.app.state, "llm", None)

    # Step 1: Fetch graph data from TypeDB
    graph_context: dict[str, Any] = {"entities": [], "hyperedges": []}
    if db and db.is_connected:
        try:
            graph_context = await _fetch_graph_context(db)
        except Exception as exc:
            logger.warning("Failed to fetch graph context: %s", exc)

    # Step 2: ContextAgent — graph traversal
    traversal = HypergraphTraversal()
    context_agent = ContextAgent(traversal)
    context_query = AgentQuery(
        query=request.query,
        intersection_size=request.intersection_size,
        max_depth=request.max_depth,
    )
    context_response = await context_agent.process(context_query)

    # Step 3: ExecutiveAgent — LLM reasoning over context
    executive_agent = ExecutiveAgent(llm=llm)
    exec_query = AgentQuery(
        query=request.query,
        context={
            "paths": context_response.evidence,
            "entities": graph_context["entities"],
            "hyperedges": graph_context["hyperedges"],
            "graph_summary": context_response.answer,
        },
        intersection_size=request.intersection_size,
        max_depth=request.max_depth,
    )
    exec_response = await executive_agent.process(exec_query)

    return QueryResponse(
        answer=exec_response.answer,
        evidence=exec_response.evidence,
        paths_found=exec_response.paths_found or context_response.paths_found,
        confidence=exec_response.confidence,
    )
