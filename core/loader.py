"""Domain config loader — reads YAML and provides typed schema info.

Each benchmark vertical defines a config.yaml that specifies:
- Entity types and their attributes
- Hyperedge (relation) types and their roles
- 2-Morphism types applicable to this domain

The loader parses this into a DomainConfig that the ingest scripts use
to build properly-typed Hyperedge objects from raw data.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class EntityTypeConfig(BaseModel):
    """Schema for an entity type in a domain."""

    name: str
    description: str = ""
    attributes: list[str] = Field(default_factory=list)


class RoleConfig(BaseModel):
    """A role within a relation type."""

    name: str
    entity_types: list[str] = Field(
        default_factory=list,
        description="Which entity types can play this role",
    )
    required: bool = True


class RelationTypeConfig(BaseModel):
    """Schema for a hyperedge/relation type."""

    name: str
    description: str = ""
    roles: list[RoleConfig] = Field(default_factory=list)
    min_participants: int = 2


class MorphismTypeConfig(BaseModel):
    """Schema for a 2-morphism type in this domain."""

    name: str
    description: str = ""
    source_relation: str = ""
    target_relation: str = ""


class DomainConfig(BaseModel):
    """Full domain configuration for a benchmark vertical."""

    domain: str
    description: str = ""
    entity_types: list[EntityTypeConfig] = Field(default_factory=list)
    relation_types: list[RelationTypeConfig] = Field(default_factory=list)
    morphism_types: list[MorphismTypeConfig] = Field(default_factory=list)

    def entity_type_names(self) -> list[str]:
        return [e.name for e in self.entity_types]

    def relation_type_names(self) -> list[str]:
        return [r.name for r in self.relation_types]


def load_config(path: str | Path) -> DomainConfig:
    """Load a domain config from a YAML file."""
    path = Path(path)
    with open(path) as f:
        data = yaml.safe_load(f)
    return DomainConfig(**data)
