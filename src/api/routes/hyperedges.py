"""Hyperedge CRUD endpoints.

Wired to TypeDB operations when a database connection is available.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from src.models.hyperedges import DecisionEvent, Hyperedge, RelationType, RoleAssignment
from src.typedb.client import TypeDBClient
from src.typedb.operations import HypergraphOperations

router = APIRouter()


class RoleAssignmentCreate(BaseModel):
    """Role assignment in a hyperedge creation request."""

    entity_id: str
    role: str


class HyperedgeCreate(BaseModel):
    """Request body for creating a hyperedge."""

    hyperedge_id: str
    relation_type: RelationType = RelationType.DECISION
    participants: list[RoleAssignmentCreate] = Field(..., min_length=2)
    decision_type: str | None = None
    rationale: str | None = None
    source_system: str | None = None


class HyperedgeResponse(BaseModel):
    """Response for hyperedge operations."""

    hyperedge_id: str
    relation_type: RelationType
    participants: list[RoleAssignmentCreate]
    decision_type: str | None = None
    rationale: str | None = None


def _get_db(request: Request) -> TypeDBClient | None:
    """Get the TypeDB client from app state, or None."""
    db = getattr(request.app.state, "db", None)
    if db and db.is_connected:
        return db
    return None


@router.post("/hyperedges", response_model=HyperedgeResponse, status_code=201)
async def create_hyperedge(
    request: HyperedgeCreate, req: Request
) -> HyperedgeResponse:
    """Create a new hyperedge connecting multiple entities."""
    db = _get_db(req)
    if db:
        roles = [
            RoleAssignment(entity_id=p.entity_id, role=p.role)
            for p in request.participants
        ]
        if request.decision_type or request.rationale:
            hyperedge: Hyperedge = DecisionEvent(
                hyperedge_id=request.hyperedge_id,
                relation_type=request.relation_type,
                participants=roles,
                decision_type=request.decision_type,
                rationale=request.rationale,
                source_system=request.source_system,
            )
        else:
            hyperedge = Hyperedge(
                hyperedge_id=request.hyperedge_id,
                relation_type=request.relation_type,
                participants=roles,
                source_system=request.source_system,
            )
        ops = HypergraphOperations(db)
        await ops.insert_hyperedge(hyperedge)

    return HyperedgeResponse(
        hyperedge_id=request.hyperedge_id,
        relation_type=request.relation_type,
        participants=request.participants,
        decision_type=request.decision_type,
        rationale=request.rationale,
    )


@router.get("/hyperedges/{entity_id}", response_model=list[HyperedgeResponse])
async def get_hyperedges_for_entity(
    entity_id: str, req: Request
) -> list[HyperedgeResponse]:
    """Get all hyperedges involving an entity."""
    db = _get_db(req)
    if not db:
        raise HTTPException(
            status_code=503,
            detail="TypeDB not connected. Configure TYPEDB_HOST and TYPEDB_PORT.",
        )

    ops = HypergraphOperations(db)
    results = await ops.get_hyperedges_for_entity(entity_id)

    hyperedges: list[HyperedgeResponse] = []
    for result in results:
        attrs = result.get("h", {})
        hyperedges.append(
            HyperedgeResponse(
                hyperedge_id=attrs.get("hyperedge-id", ""),
                relation_type=attrs.get("relation-type", RelationType.CONTEXT),
                participants=[],
            )
        )
    return hyperedges


class SAdjacencyRequest(BaseModel):
    """Request for finding s-adjacent hyperedges."""

    entity_id: str
    s: int = Field(default=2, ge=1, description="Minimum intersection size")


@router.post("/hyperedges/s-adjacent", response_model=list[dict[str, Any]])
async def find_s_adjacent(
    request: SAdjacencyRequest, req: Request
) -> list[dict[str, Any]]:
    """Find hyperedges that are s-adjacent (share >= s entities).

    IS >= 2 reduces noise by 87%.
    """
    db = _get_db(req)
    if not db:
        raise HTTPException(
            status_code=503,
            detail="TypeDB not connected. Configure TYPEDB_HOST and TYPEDB_PORT.",
        )

    ops = HypergraphOperations(db)
    return await ops.find_s_adjacent_hyperedges(request.entity_id, request.s)
