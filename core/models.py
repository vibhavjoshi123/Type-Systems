"""Domain-agnostic Pydantic models for hypergraph benchmarking.

These mirror the models from the main Context Graph repo but are
self-contained — no TypeDB dependency, pure in-memory structures.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class RoleAssignment(BaseModel):
    """An entity's role within a hyperedge."""

    entity_id: str
    entity_type: str = ""
    role: str = Field(..., description="Role this entity plays in the hyperedge")
    attributes: dict[str, str | int | float | bool] = Field(default_factory=dict)


class Hyperedge(BaseModel):
    """An N-ary relation connecting multiple entities.

    Domain-agnostic: works for offshore ownership, court cases,
    drug interactions, or any multi-party event.
    """

    hyperedge_id: str
    relation_type: str = "context-hyperedge"
    participants: list[RoleAssignment] = Field(..., min_length=2)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    attributes: dict[str, str | int | float | bool] = Field(default_factory=dict)

    @property
    def cardinality(self) -> int:
        """Number of entities in this hyperedge."""
        return len(self.participants)

    @property
    def entity_ids(self) -> set[str]:
        """Set of all entity IDs participating in this hyperedge."""
        return {p.entity_id for p in self.participants}

    def intersection_size(self, other: Hyperedge) -> int:
        """Compute intersection size (IS) with another hyperedge."""
        return len(self.entity_ids & other.entity_ids)

    def is_s_adjacent(self, other: Hyperedge, s: int = 2) -> bool:
        """Two hyperedges are s-adjacent iff they share >= s entities."""
        return self.intersection_size(other) >= s


class TwoMorphismType(StrEnum):
    """Types of 2-morphisms (meta-relations between hyperedges)."""

    PRECEDENT = "precedent"
    EXCEPTION = "exception"
    OVERRIDE = "override"
    GENERALIZATION = "generalization"
    SEQUENCE = "sequence"


class TwoMorphism(BaseModel):
    """A 2-morphism: a relation between two hyperedges.

    In legal: Case A sets precedent for Case B.
    In pharma: Drug interaction A overrides safety profile B.
    In finance: Filing A amends/supersedes Filing B.
    """

    morphism_id: str
    morphism_type: TwoMorphismType
    source_hyperedge_id: str
    target_hyperedge_id: str
    rationale: str = ""
    attributes: dict[str, str | int | float | bool] = Field(default_factory=dict)
