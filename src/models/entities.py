"""Entity models for the hypergraph context graph.

Entities are the vertices (nodes) in the hypergraph. Each entity type corresponds
to a TypeDB entity type with typed attributes and role-playing capabilities.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class EntityType(StrEnum):
    """Supported entity types in the hypergraph."""

    CUSTOMER = "customer"
    EMPLOYEE = "employee"
    DEAL = "deal"
    TICKET = "ticket"
    POLICY = "policy"
    METRIC = "metric"


class Entity(BaseModel):
    """Base entity in the hypergraph (vertex/node).

    Maps to TypeDB's `enterprise-entity` abstract entity type.
    """

    entity_id: str = Field(..., description="Unique identifier for the entity")
    entity_name: str = Field(..., description="Human-readable name")
    entity_type: EntityType = Field(..., description="Type discriminator")
    source_system: str | None = Field(default=None, description="Originating data source")
    embedding: list[float] | None = Field(default=None, description="Vector embedding")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, str | int | float | bool] = Field(default_factory=dict)


class Customer(Entity):
    """Customer entity with CRM-specific attributes."""

    entity_type: EntityType = EntityType.CUSTOMER
    health_score: float | None = Field(default=None, ge=0, le=100)
    tier: str | None = Field(default=None, description="e.g., enterprise, mid-market, SMB")
    arr: float | None = Field(default=None, description="Annual recurring revenue")


class Employee(Entity):
    """Employee entity with organizational attributes."""

    entity_type: EntityType = EntityType.EMPLOYEE
    department: str | None = None
    job_role: str | None = None
    title: str | None = None


class Deal(Entity):
    """Deal/opportunity entity."""

    entity_type: EntityType = EntityType.DEAL
    deal_value: float | None = Field(default=None, ge=0)
    discount_percentage: float | None = Field(default=None, ge=0, le=100)
    stage: str | None = None


class Ticket(Entity):
    """Support ticket entity."""

    entity_type: EntityType = EntityType.TICKET
    severity: str | None = Field(default=None, description="e.g., SEV-1, SEV-2")
    status: str | None = Field(default=None, description="e.g., open, resolved")
    priority: str | None = None


class Policy(Entity):
    """Business policy entity."""

    entity_type: EntityType = EntityType.POLICY
    policy_type: str | None = None
    max_discount: float | None = Field(default=None, ge=0, le=100)
    effective_date: datetime | None = None


class Metric(Entity):
    """Usage/business metric entity."""

    entity_type: EntityType = EntityType.METRIC
    metric_value: float | None = None
    metric_type: str | None = Field(default=None, description="e.g., usage, NPS, churn_risk")
    unit: str | None = None


ENTITY_TYPE_MAP: dict[EntityType, type[Entity]] = {
    EntityType.CUSTOMER: Customer,
    EntityType.EMPLOYEE: Employee,
    EntityType.DEAL: Deal,
    EntityType.TICKET: Ticket,
    EntityType.POLICY: Policy,
    EntityType.METRIC: Metric,
}
