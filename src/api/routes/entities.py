"""Entity CRUD endpoints.

Wired to TypeDB operations when a database connection is available.
Falls back to echo-only mode when TypeDB is not connected.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from src.models.entities import ENTITY_TYPE_MAP, EntityType
from src.typedb.client import TypeDBClient
from src.typedb.operations import HypergraphOperations

router = APIRouter()


class EntityCreate(BaseModel):
    """Request body for creating an entity."""

    entity_id: str
    entity_name: str
    entity_type: EntityType
    source_system: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)


class EntityResponse(BaseModel):
    """Response for entity operations."""

    entity_id: str
    entity_name: str
    entity_type: EntityType
    source_system: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)


def _get_db(request: Request) -> TypeDBClient | None:
    """Get the TypeDB client from app state, or None."""
    db = getattr(request.app.state, "db", None)
    if db and db.is_connected:
        return db
    return None


@router.post("/entities", response_model=EntityResponse, status_code=201)
async def create_entity(request: EntityCreate, req: Request) -> EntityResponse:
    """Create a new entity in the hypergraph."""
    db = _get_db(req)
    if db:
        model_cls = ENTITY_TYPE_MAP.get(request.entity_type)
        if model_cls:
            entity = model_cls(
                entity_id=request.entity_id,
                entity_name=request.entity_name,
                source_system=request.source_system,
                **request.attributes,
            )
            ops = HypergraphOperations(db)
            await ops.insert_entity(entity)

    return EntityResponse(
        entity_id=request.entity_id,
        entity_name=request.entity_name,
        entity_type=request.entity_type,
        source_system=request.source_system,
        attributes=request.attributes,
    )


@router.get("/entities/{entity_id}", response_model=EntityResponse)
async def get_entity(entity_id: str, req: Request) -> EntityResponse:
    """Get an entity by ID."""
    db = _get_db(req)
    if not db:
        raise HTTPException(
            status_code=503,
            detail="TypeDB not connected. Configure TYPEDB_HOST and TYPEDB_PORT.",
        )

    ops = HypergraphOperations(db)
    result = await ops.get_entity(entity_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Entity not found: {entity_id}")

    attrs = result.get("e", {})
    return EntityResponse(
        entity_id=attrs.get("entity-id", entity_id),
        entity_name=attrs.get("entity-name", ""),
        entity_type=attrs.get("entity-type-label", "customer"),
        source_system=attrs.get("source-system"),
        attributes=attrs,
    )


@router.get("/entities", response_model=list[EntityResponse])
async def list_entities(
    req: Request, entity_type: EntityType | None = None
) -> list[EntityResponse]:
    """List entities, optionally filtered by type."""
    db = _get_db(req)
    if not db:
        raise HTTPException(
            status_code=503,
            detail="TypeDB not connected. Configure TYPEDB_HOST and TYPEDB_PORT.",
        )

    ops = HypergraphOperations(db)
    if entity_type:
        results = await ops.get_entities_by_type(entity_type)
    else:
        results = await db.query(
            "match $e isa enterprise-entity; fetch $e: attribute;"
        )

    entities: list[EntityResponse] = []
    for result in results:
        attrs = result.get("e", {})
        entities.append(
            EntityResponse(
                entity_id=attrs.get("entity-id", ""),
                entity_name=attrs.get("entity-name", ""),
                entity_type=attrs.get("entity-type-label", "customer"),
                source_system=attrs.get("source-system"),
                attributes=attrs,
            )
        )
    return entities


@router.delete("/entities/{entity_id}", status_code=204)
async def delete_entity(entity_id: str, req: Request) -> None:
    """Delete an entity by ID."""
    db = _get_db(req)
    if not db:
        raise HTTPException(
            status_code=503,
            detail="TypeDB not connected. Configure TYPEDB_HOST and TYPEDB_PORT.",
        )

    ops = HypergraphOperations(db)
    await ops.delete_entity(entity_id)
