"""Query endpoint for natural language queries against the hypergraph.

Wires together the multi-agent system: ContextAgent finds paths,
ExecutiveAgent reasons, GovernanceAgent verifies coherence.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from src.agents.base import AgentQuery
from src.agents.context_agent import ContextAgent
from src.typedb.traversal import HypergraphTraversal

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


@router.post("/query", response_model=QueryResponse)
async def query_context_graph(
    request: QueryRequest, req: Request
) -> QueryResponse:
    """Query the context graph with a natural language question.

    Uses the ContextAgent to traverse the hypergraph and find
    relevant s-connected components and paths. When an LLM is
    configured, the ExecutiveAgent provides mechanistic reasoning.
    """
    traversal = HypergraphTraversal()
    db = getattr(req.app.state, "db", None)

    if db and db.is_connected:
        results = await db.query(
            "match $h isa context-hyperedge; fetch $h: attribute;"
        )
        if results:
            context_agent = ContextAgent(traversal)
            agent_query = AgentQuery(
                query=request.query,
                intersection_size=request.intersection_size,
                max_depth=request.max_depth,
            )
            response = await context_agent.process(agent_query)
            return QueryResponse(
                answer=response.answer,
                evidence=response.evidence,
                paths_found=response.paths_found,
                confidence=response.confidence,
            )

    # Fallback: no TypeDB or no data
    context_agent = ContextAgent(traversal)
    agent_query = AgentQuery(
        query=request.query,
        intersection_size=request.intersection_size,
        max_depth=request.max_depth,
    )
    response = await context_agent.process(agent_query)
    return QueryResponse(
        answer=response.answer,
        evidence=response.evidence,
        paths_found=response.paths_found,
        confidence=response.confidence,
    )
