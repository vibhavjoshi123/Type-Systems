"""Ingest ICIJ Offshore Leaks CSVs into Hyperedge objects.

Data model:
- Each offshore entity + its connected officers/intermediaries/addresses
  becomes ONE hyperedge (an "offshore-structure").
- When the same officer appears in multiple structures, those structures
  are s-adjacent (they share the officer entity).
- If two structures share >= 2 entities (e.g., same officer AND same
  intermediary), they are 2-adjacent — a strong signal of coordinated
  shell company networks.

This is exactly why hypergraphs beat binary graphs here:
Neo4j would need: entity→officer, entity→intermediary, entity→address
  = 3 separate edges per structure, losing the atomic "this is one structure" fact.
We model it as: 1 hyperedge with N participants.
"""

from __future__ import annotations

import csv
import logging
import time
from pathlib import Path

from core.models import Hyperedge, RoleAssignment

logger = logging.getLogger(__name__)

# Column mappings for ICIJ CSVs
_ENTITY_ID_COL = "node_id"
_ENTITY_NAME_COL = "name"
_ENTITY_JURISDICTION_COL = "jurisdiction"
_ENTITY_COUNTRIES_COL = "country_codes"
_ENTITY_STATUS_COL = "status"
_ENTITY_DATE_COL = "incorporation_date"

_REL_START_COL = "START_ID"
_REL_END_COL = "END_ID"
_REL_TYPE_COL = "TYPE"


def _read_csv(path: Path, limit: int = 0) -> list[dict[str, str]]:
    """Read a CSV file, optionally limiting rows."""
    rows: list[dict[str, str]] = []
    with open(path, newline="", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f, delimiter=",")
        for i, row in enumerate(reader):
            if limit and i >= limit:
                break
            rows.append(row)
    return rows


def _safe_id(prefix: str, node_id: str) -> str:
    """Create a namespaced entity ID."""
    return f"{prefix}:{node_id.strip()}"


def ingest(
    data_dir: str | Path,
    entity_limit: int = 0,
    relationship_limit: int = 0,
) -> list[Hyperedge]:
    """Parse ICIJ CSVs and build hyperedges.

    Args:
        data_dir: Path to directory containing the downloaded CSVs.
        entity_limit: Max entities to load per type (0 = all).
        relationship_limit: Max relationships to load (0 = all).

    Returns:
        List of Hyperedge objects representing offshore structures.
    """
    data_dir = Path(data_dir)
    t0 = time.perf_counter()

    # ── Load node files ────────────────────────────────────────────────
    logger.info("Loading ICIJ node files...")

    entities_raw = _read_csv(data_dir / "nodes-entities.csv", entity_limit)
    officers_raw = _read_csv(data_dir / "nodes-officers.csv", entity_limit)
    intermediaries_raw = _read_csv(data_dir / "nodes-intermediaries.csv", entity_limit)
    addresses_raw = _read_csv(data_dir / "nodes-addresses.csv", entity_limit)

    logger.info(
        "Loaded: %d entities, %d officers, %d intermediaries, %d addresses",
        len(entities_raw), len(officers_raw),
        len(intermediaries_raw), len(addresses_raw),
    )

    # Build lookup: node_id → (type, name)
    node_type: dict[str, str] = {}
    node_name: dict[str, str] = {}

    for row in entities_raw:
        nid = row.get(_ENTITY_ID_COL, "").strip()
        node_type[nid] = "entity"
        node_name[nid] = row.get(_ENTITY_NAME_COL, "").strip()

    for row in officers_raw:
        nid = row.get(_ENTITY_ID_COL, "").strip()
        node_type[nid] = "officer"
        node_name[nid] = row.get(_ENTITY_NAME_COL, row.get("name", "")).strip()

    for row in intermediaries_raw:
        nid = row.get(_ENTITY_ID_COL, "").strip()
        node_type[nid] = "intermediary"
        node_name[nid] = row.get(_ENTITY_NAME_COL, row.get("name", "")).strip()

    for row in addresses_raw:
        nid = row.get(_ENTITY_ID_COL, "").strip()
        node_type[nid] = "address"
        node_name[nid] = row.get("address", row.get(_ENTITY_NAME_COL, "")).strip()

    # ── Load relationships ─────────────────────────────────────────────
    logger.info("Loading relationships...")
    rels_raw = _read_csv(data_dir / "relationships.csv", relationship_limit)
    logger.info("Loaded: %d relationships", len(rels_raw))

    # Group relationships by source entity (offshore entity → its connections)
    # This builds the N-ary hyperedge: one entity + all its connected nodes
    entity_connections: dict[str, list[tuple[str, str, str]]] = {}

    for row in rels_raw:
        start_id = row.get(_REL_START_COL, "").strip()
        end_id = row.get(_REL_END_COL, "").strip()
        rel_type = row.get(_REL_TYPE_COL, "").strip()

        if not start_id or not end_id:
            continue

        # Determine which side is the offshore entity
        start_type = node_type.get(start_id, "")
        end_type = node_type.get(end_id, "")

        if start_type == "entity":
            entity_connections.setdefault(start_id, []).append(
                (end_id, end_type or "unknown", rel_type)
            )
        elif end_type == "entity":
            entity_connections.setdefault(end_id, []).append(
                (start_id, start_type or "unknown", rel_type)
            )

    # ── Build hyperedges ───────────────────────────────────────────────
    logger.info("Building hyperedges from %d entities with connections...",
                len(entity_connections))

    hyperedges: list[Hyperedge] = []

    for entity_id, connections in entity_connections.items():
        participants: list[RoleAssignment] = []

        # The offshore entity itself
        participants.append(RoleAssignment(
            entity_id=_safe_id("entity", entity_id),
            entity_type="entity",
            role="offshore-entity",
            attributes={"name": node_name.get(entity_id, "")},
        ))

        # All connected nodes become participants in the same hyperedge
        seen: set[str] = set()
        for conn_id, conn_type, rel_type in connections:
            safe_conn_id = _safe_id(conn_type, conn_id)
            if safe_conn_id in seen:
                continue
            seen.add(safe_conn_id)

            role = _rel_type_to_role(rel_type, conn_type)
            participants.append(RoleAssignment(
                entity_id=safe_conn_id,
                entity_type=conn_type,
                role=role,
                attributes={"name": node_name.get(conn_id, "")},
            ))

        if len(participants) >= 2:
            hyperedges.append(Hyperedge(
                hyperedge_id=f"offshore-{entity_id}",
                relation_type="offshore-structure",
                participants=participants,
                attributes={"source": "icij-offshore-leaks"},
            ))

    elapsed = time.perf_counter() - t0
    logger.info(
        "Built %d hyperedges in %.2fs (avg %.1f participants/edge)",
        len(hyperedges),
        elapsed,
        sum(he.cardinality for he in hyperedges) / max(len(hyperedges), 1),
    )

    return hyperedges


def _rel_type_to_role(rel_type: str, node_type: str) -> str:
    """Map ICIJ relationship types to hyperedge roles."""
    rel_lower = rel_type.lower()
    if "director" in rel_lower:
        return "director"
    if "shareholder" in rel_lower:
        return "shareholder"
    if "beneficiary" in rel_lower or "beneficial" in rel_lower:
        return "beneficiary"
    if "secretary" in rel_lower:
        return "secretary"
    if "nominee" in rel_lower:
        return "nominee"
    if "intermediary" in rel_lower:
        return "intermediary"
    if "registered" in rel_lower or "address" in rel_lower:
        return "registered-address"
    if node_type == "officer":
        return "officer"
    if node_type == "intermediary":
        return "intermediary"
    if node_type == "address":
        return "registered-address"
    return "connected-party"
