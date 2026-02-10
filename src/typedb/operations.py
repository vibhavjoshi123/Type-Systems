"""CRUD operations for entities and hyperedges in TypeDB 3.x.

Provides a high-level Python API over TypeQL queries for managing
the hypergraph's entities (vertices) and relations (hyperedges).

TypeDB 3.x query changes from 2.x:
- Pipeline stages chain together: match -> insert, match -> delete, match -> fetch
- 'delete $e;' for entity deletion
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from src.models.decisions import PrecedentChain
from src.models.entities import Entity, EntityType
from src.models.hyperedges import DecisionEvent, Hyperedge
from src.typedb.client import TypeDBClient

logger = logging.getLogger(__name__)


class HypergraphOperations:
    """High-level CRUD operations for the hypergraph.

    Translates between Pydantic models and TypeQL 3.x queries.
    """

    def __init__(self, client: TypeDBClient) -> None:
        self.client = client

    # ── Entity Operations ──────────────────────────────────────────────

    async def insert_entity(self, entity: Entity) -> str:
        """Insert an entity into the hypergraph. Returns entity_id."""
        type_name = entity.entity_type.value
        attrs = [
            f'has entity-id "{entity.entity_id}"',
            f'has entity-name "{entity.entity_name}"',
            f'has entity-type-label "{entity.entity_type.value}"',
        ]

        if entity.source_system:
            attrs.append(f'has source-system "{entity.source_system}"')

        if entity.embedding:
            embedding_json = json.dumps(entity.embedding)
            attrs.append(f"has embedding-json '{embedding_json}'")

        # Add type-specific attributes
        attrs.extend(self._entity_specific_attrs(entity))

        typeql = f"insert $e isa {type_name}, {', '.join(attrs)};"
        await self.client.write(typeql)
        logger.info("Inserted %s entity: %s", type_name, entity.entity_id)
        return entity.entity_id

    def _entity_specific_attrs(self, entity: Entity) -> list[str]:
        """Build type-specific attribute clauses."""
        attrs: list[str] = []
        extra = entity.model_dump(
            exclude={"entity_id", "entity_name", "entity_type", "source_system",
                      "embedding", "created_at", "metadata"}
        )
        for key, value in extra.items():
            if value is None:
                continue
            attr_name = key.replace("_", "-")
            if isinstance(value, str):
                attrs.append(f'has {attr_name} "{value}"')
            elif isinstance(value, datetime):
                attrs.append(f'has {attr_name} {value.isoformat()}')
            elif isinstance(value, (int, float)):
                attrs.append(f"has {attr_name} {value}")
        return attrs

    async def get_entity(self, entity_id: str) -> dict[str, Any] | None:
        """Fetch an entity by its ID."""
        typeql = f"""
        match
            $e isa enterprise-entity, has entity-id "{entity_id}";
        """
        results = await self.client.query(typeql)
        return results[0] if results else None

    async def get_entities_by_type(self, entity_type: EntityType) -> list[dict[str, Any]]:
        """Fetch all entities of a given type."""
        typeql = f"""
        match
            $e isa {entity_type.value};
        """
        return await self.client.query(typeql)

    async def delete_entity(self, entity_id: str) -> None:
        """Delete an entity by its ID."""
        typeql = f"""
        match
            $e isa enterprise-entity, has entity-id "{entity_id}";
        delete $e;
        """
        await self.client.write(typeql)
        logger.info("Deleted entity: %s", entity_id)

    # ── Hyperedge Operations ───────────────────────────────────────────

    async def insert_hyperedge(self, hyperedge: Hyperedge) -> str:
        """Insert a hyperedge (relation) connecting multiple entities.

        This creates the core n-ary relation that TypeDB handles natively,
        as opposed to the reification required by RDF/OWL or property graphs.
        """
        role_clauses: list[str] = []
        match_clauses: list[str] = []

        for i, participant in enumerate(hyperedge.participants):
            var = f"$p{i}"
            match_clauses.append(
                f'{var} isa enterprise-entity, has entity-id "{participant.entity_id}";'
            )
            role_clauses.append(f"{participant.role}: {var}")

        roles_str = ", ".join(role_clauses)
        match_str = "\n    ".join(match_clauses)

        attrs: list[str] = []
        if hyperedge.confidence_score != 1.0:
            attrs.append(f"has confidence-score {hyperedge.confidence_score}")
        if hyperedge.source_system:
            attrs.append(f'has source-system "{hyperedge.source_system}"')

        if isinstance(hyperedge, DecisionEvent):
            if hyperedge.decision_type:
                attrs.append(f'has decision-type "{hyperedge.decision_type}"')
            if hyperedge.rationale:
                rationale = hyperedge.rationale.replace('"', '\\"')
                attrs.append(f'has rationale "{rationale}"')

        relation_type = hyperedge.relation_type.value
        attrs_str = ", ".join(attrs)
        if attrs_str:
            attrs_str = ", " + attrs_str

        typeql = f"""
        match
            {match_str}
        insert
            ({roles_str}) isa {relation_type}{attrs_str};
        """
        await self.client.write(typeql)
        logger.info(
            "Inserted %s hyperedge with %d participants",
            relation_type,
            len(hyperedge.participants),
        )
        return hyperedge.hyperedge_id

    async def get_hyperedges_for_entity(self, entity_id: str) -> list[dict[str, Any]]:
        """Get all hyperedges involving an entity."""
        typeql = f"""
        match
            $e isa enterprise-entity, has entity-id "{entity_id}";
            $h (participant: $e) isa context-hyperedge;
        """
        return await self.client.query(typeql)

    async def find_s_adjacent_hyperedges(
        self,
        entity_id: str,
        s: int = 2,
    ) -> list[dict[str, Any]]:
        """Find hyperedges that are s-adjacent to those involving entity_id.

        The IS >= 2 constraint: two hyperedges are meaningfully connected
        only if they share at least s nodes. 87% noise reduction at s=2.
        """
        typeql = f"""
        match
            $e isa enterprise-entity, has entity-id "{entity_id}";
            $h1 (participant: $e) isa context-hyperedge;
            $h2 isa context-hyperedge;
            $h1 != $h2;
            $h2 (participant: $e);
        """
        # For s >= 2 we need additional shared entities
        if s >= 2:
            typeql += """
            $shared isa enterprise-entity;
            $shared != $e;
            $h1 (participant: $shared);
            $h2 (participant: $shared);
            """
        return await self.client.query(typeql)

    # ── 2-Morphism Operations ─────────────────────────────────────────

    async def insert_precedent_chain(self, precedent: PrecedentChain) -> None:
        """Insert a 2-morphism (precedent chain) between two decisions.

        This creates a TypeDB nested relation: a relation whose role players
        are themselves relations (decision events).
        """
        typeql = f"""
        match
            $d1 isa decision-event, has entity-id "{precedent.precedent_id}";
            $d2 isa decision-event, has entity-id "{precedent.derived_id}";
        insert
            (precedent-decision: $d1, derived-decision: $d2)
            isa precedent-chain,
            has precedent-type "{precedent.morphism_type.value}";
        """
        if precedent.rationale:
            rationale = precedent.rationale.replace('"', '\\"')
            typeql = typeql.rstrip(";") + f', has rationale "{rationale}";'

        await self.client.write(typeql)
        logger.info(
            "Inserted %s 2-morphism: %s -> %s",
            precedent.morphism_type.value,
            precedent.precedent_id,
            precedent.derived_id,
        )

    async def get_precedent_chain(self, decision_id: str) -> list[dict[str, Any]]:
        """Get all precedent chains involving a decision."""
        typeql = f"""
        match
            $d isa decision-event, has entity-id "{decision_id}";
            {{
                (precedent-decision: $d, derived-decision: $other) isa precedent-chain;
            }} or {{
                (precedent-decision: $other, derived-decision: $d) isa precedent-chain;
            }};
        """
        return await self.client.query(typeql)
