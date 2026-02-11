"""TypeDB 3.x schema definitions for the hypergraph context graph.

The schema maps directly to the PERA model:
- Entities are first-class with typed attributes
- Relations (hyperedges) natively connect N entities through typed roles
- Nested relations implement 2-morphisms (meta-relations between decisions)
- Closed World Assumption enforces policy compliance

TypeDB 3.x syntax changes from 2.x:
- 'entity X' keyword instead of 'X sub entity'
- 'attribute X, value string' instead of 'X sub attribute, value string'
- 'relation X' instead of 'X sub relation'
- Explicit @card annotations (default owns is 0..1 in 3.x)
- Rules replaced by functions (explicit invocation)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Complete TypeQL 3.x schema for the enterprise hypergraph context graph
SCHEMA_TYPEQL = """
define

# ============ ATTRIBUTES ============
attribute entity-id, value string;
attribute entity-name, value string;
attribute entity-type-label, value string;
attribute timestamp, value datetime;
attribute confidence-score, value double;
attribute embedding-json, value string;
attribute source-system, value string;
attribute rationale, value string;
attribute decision-type, value string;
attribute relation-type-label, value string;
attribute precedent-type, value string;
attribute override-rationale, value string;
attribute trace-id, value string;

# Domain-specific attributes
attribute health-score, value double;
attribute tier, value string;
attribute arr, value double;
attribute department, value string;
attribute job-role, value string;
attribute title, value string;
attribute deal-value, value double;
attribute discount-percentage, value double;
attribute stage, value string;
attribute severity, value string;
attribute status, value string;
attribute priority, value string;
attribute policy-type, value string;
attribute max-discount, value double;
attribute effective-date, value datetime;
attribute metric-value, value double;
attribute metric-type, value string;
attribute unit, value string;

# ============ ENTITIES ============
entity enterprise-entity @abstract,
    owns entity-id @key,
    owns entity-name,
    owns entity-type-label,
    owns embedding-json,
    owns source-system,
    owns timestamp,
    plays context-hyperedge:participant,
    plays decision-event:involved-entity,
    plays decision-event:decision-maker,
    plays decision-event:affected-entity;

entity customer, sub enterprise-entity,
    owns health-score,
    owns tier @card(0..),
    owns arr;

entity employee, sub enterprise-entity,
    owns department,
    owns job-role,
    owns title;

entity deal, sub enterprise-entity,
    owns deal-value,
    owns discount-percentage,
    owns stage;

entity ticket, sub enterprise-entity,
    owns severity,
    owns status,
    owns priority;

entity policy, sub enterprise-entity,
    owns policy-type,
    owns max-discount,
    owns effective-date;

entity metric, sub enterprise-entity,
    owns metric-value,
    owns metric-type,
    owns unit;

# ============ RELATIONS (HYPEREDGES) ============
# Core hyperedge relation - connects N entities
relation context-hyperedge,
    relates participant @card(1..),
    owns timestamp,
    owns confidence-score,
    owns source-system;

# Decision event hyperedge - the key structure
relation decision-event, sub context-hyperedge,
    relates involved-entity as participant @card(0..),
    relates decision-maker as participant @card(0..),
    relates affected-entity as participant @card(0..),
    owns decision-type,
    owns relation-type-label,
    owns rationale,
    plays precedent-chain:precedent-decision,
    plays precedent-chain:derived-decision,
    plays exception-override:base-decision,
    plays exception-override:exception-decision;

# Specialized decision subtypes
relation escalation, sub decision-event;
relation approval, sub decision-event;
relation renewal, sub decision-event;
relation incident-event, sub decision-event;

# ============ 2-MORPHISMS (META-RELATIONS) ============
# Relationship between decisions (nested relations)
relation precedent-chain,
    relates precedent-decision,
    relates derived-decision,
    owns precedent-type,
    owns rationale,
    owns timestamp;

# Exception override: catalyst-approver isomorphism
relation exception-override,
    relates base-decision,
    relates exception-decision,
    owns override-rationale,
    owns timestamp;
"""

# TypeDB 3.x functions replacing old inference rules.
# Functions are explicitly invoked in queries (unlike 2.x rules which were implicit).
FUNCTIONS_TYPEQL = """
define
fun customers_at_risk() -> { customer }:
    match
        $c isa customer, has health-score $hs;
        $hs < 70.0;
    return { $c };
"""


class SchemaManager:
    """Manages TypeDB schema operations."""

    def __init__(self, schema: str = SCHEMA_TYPEQL) -> None:
        self.schema = schema

    def get_schema(self) -> str:
        """Return the full TypeQL schema definition."""
        return self.schema

    def get_entity_types(self) -> list[str]:
        """Return list of concrete entity type names."""
        return ["customer", "employee", "deal", "ticket", "policy", "metric"]

    def get_relation_types(self) -> list[str]:
        """Return list of relation type names (hyperedge types)."""
        return [
            "context-hyperedge",
            "decision-event",
            "escalation",
            "approval",
            "renewal",
            "incident-event",
            "precedent-chain",
            "exception-override",
        ]
