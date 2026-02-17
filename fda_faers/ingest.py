"""Ingest FDA FAERS data into Hyperedge objects.

Data model:
- Each adverse event report is ONE hyperedge connecting:
  Drug A + Drug B + ... + Reaction + Outcome = one atomic event

Why this can't be binary edges:
  Patient on warfarin + aspirin + metformin → GI bleeding.
  In Neo4j: warfarin→GI-bleeding, aspirin→GI-bleeding, metformin→GI-bleeding (3 edges)
  Problem: you lose "all three TOGETHER caused this". Maybe warfarin alone is fine.
  In our hypergraph: ONE hyperedge with all 4 entities.
  s-Adjacency then finds: other events with warfarin + aspirin (IS=2) are connected.
  Events with only warfarin (IS=1) are NOT connected at s=2 — noise filtered.
"""

from __future__ import annotations

import csv
import logging
import time
from pathlib import Path

from core.models import Hyperedge, RoleAssignment

logger = logging.getLogger(__name__)

# FAERS file column names
_CASE_ID = "primaryid"
_DRUG_NAME = "drugname"
_DRUG_ROLE = "role_cod"
_DRUG_ROUTE = "route"
_DRUG_DOSE = "dose_amt"
_REACTION_NAME = "pt"  # MedDRA preferred term
_OUTCOME_CODE = "outc_cod"
_INDICATION = "indi_pt"


def _read_pipe_delimited(path: Path, limit: int = 0) -> list[dict[str, str]]:
    """Read FAERS pipe-delimited file (or CSV fallback)."""
    rows: list[dict[str, str]] = []

    # Try pipe delimiter first (FAERS format), fall back to comma
    for delimiter in ["$", "|", ","]:
        try:
            with open(path, newline="", encoding="utf-8", errors="replace") as f:
                reader = csv.DictReader(f, delimiter=delimiter)
                for i, row in enumerate(reader):
                    if limit and i >= limit:
                        break
                    rows.append(row)
                if rows:
                    return rows
        except Exception:
            rows = []

    return rows


def ingest_sample() -> list[Hyperedge]:
    """Build hyperedges from the curated sample dataset."""
    from fda_faers.sample_data import SAMPLE_EVENTS

    t0 = time.perf_counter()
    hyperedges: list[Hyperedge] = []

    for event in SAMPLE_EVENTS:
        participants: list[RoleAssignment] = []

        for drug in event["drugs"]:
            participants.append(RoleAssignment(
                entity_id=f"drug:{drug['name'].lower()}",
                entity_type="drug",
                role=f"{'suspect-drug' if drug['role'] in ('PS', 'SS') else 'concomitant-drug'}",
                attributes={
                    "name": drug["name"],
                    "role_code": drug["role"],
                    "indication": drug.get("indication", ""),
                },
            ))

        for reaction in event["reactions"]:
            participants.append(RoleAssignment(
                entity_id=f"reaction:{reaction.lower().replace(' ', '-')}",
                entity_type="reaction",
                role="reaction",
                attributes={"name": reaction},
            ))

        for outcome in event.get("outcomes", []):
            participants.append(RoleAssignment(
                entity_id=f"outcome:{outcome}",
                entity_type="outcome",
                role="outcome",
                attributes={"code": outcome},
            ))

        if len(participants) >= 2:
            hyperedges.append(Hyperedge(
                hyperedge_id=event["case_id"],
                relation_type="adverse-event",
                participants=participants,
                attributes={"source": "fda-faers-sample"},
            ))

    elapsed = time.perf_counter() - t0
    logger.info("Built %d sample hyperedges in %.3fs", len(hyperedges), elapsed)
    return hyperedges


def ingest_faers(
    data_dir: str | Path,
    limit: int = 0,
) -> list[Hyperedge]:
    """Parse FAERS ASCII files and build hyperedges.

    Groups drug, reaction, outcome, and indication records by case ID,
    then builds one hyperedge per case.
    """
    data_dir = Path(data_dir)

    # Find FAERS files (case-insensitive, different naming conventions)
    drug_file = _find_file(data_dir, "DRUG")
    reac_file = _find_file(data_dir, "REAC")
    outc_file = _find_file(data_dir, "OUTC")
    indi_file = _find_file(data_dir, "INDI")

    if not drug_file or not reac_file:
        logger.warning("FAERS files not found in %s, using sample data", data_dir)
        return ingest_sample()

    t0 = time.perf_counter()

    # Group by case ID
    case_drugs: dict[str, list[dict[str, str]]] = {}
    case_reactions: dict[str, list[str]] = {}
    case_outcomes: dict[str, list[str]] = {}
    case_indications: dict[str, list[str]] = {}

    # Parse drugs
    logger.info("Parsing %s...", drug_file.name)
    for row in _read_pipe_delimited(drug_file, limit):
        cid = row.get(_CASE_ID, "").strip()
        name = row.get(_DRUG_NAME, "").strip()
        if cid and name:
            case_drugs.setdefault(cid, []).append(row)

    # Parse reactions
    logger.info("Parsing %s...", reac_file.name)
    for row in _read_pipe_delimited(reac_file, limit):
        cid = row.get(_CASE_ID, "").strip()
        reaction = row.get(_REACTION_NAME, "").strip()
        if cid and reaction:
            case_reactions.setdefault(cid, []).append(reaction)

    # Parse outcomes
    if outc_file:
        logger.info("Parsing %s...", outc_file.name)
        for row in _read_pipe_delimited(outc_file, limit):
            cid = row.get(_CASE_ID, "").strip()
            outcome = row.get(_OUTCOME_CODE, row.get("outc_code", "")).strip()
            if cid and outcome:
                case_outcomes.setdefault(cid, []).append(outcome)

    # Parse indications
    if indi_file:
        logger.info("Parsing %s...", indi_file.name)
        for row in _read_pipe_delimited(indi_file, limit):
            cid = row.get(_CASE_ID, "").strip()
            indication = row.get(_INDICATION, row.get("indi_pt", "")).strip()
            if cid and indication:
                case_indications.setdefault(cid, []).append(indication)

    # Build hyperedges
    logger.info("Building hyperedges from %d cases...", len(case_drugs))
    hyperedges: list[Hyperedge] = []
    case_limit = limit if limit else len(case_drugs)

    for i, (cid, drugs) in enumerate(case_drugs.items()):
        if i >= case_limit:
            break

        participants: list[RoleAssignment] = []
        seen_ids: set[str] = set()

        for drug_row in drugs:
            name = drug_row.get(_DRUG_NAME, "").strip().upper()
            role_code = drug_row.get(_DRUG_ROLE, "").strip()
            eid = f"drug:{name.lower()}"

            if eid not in seen_ids:
                seen_ids.add(eid)
                role = "suspect-drug" if role_code in ("PS", "SS") else "concomitant-drug"
                participants.append(RoleAssignment(
                    entity_id=eid,
                    entity_type="drug",
                    role=role,
                    attributes={"name": name, "role_code": role_code},
                ))

        for reaction in case_reactions.get(cid, []):
            eid = f"reaction:{reaction.lower().replace(' ', '-')}"
            if eid not in seen_ids:
                seen_ids.add(eid)
                participants.append(RoleAssignment(
                    entity_id=eid,
                    entity_type="reaction",
                    role="reaction",
                    attributes={"name": reaction},
                ))

        for outcome in case_outcomes.get(cid, []):
            eid = f"outcome:{outcome}"
            if eid not in seen_ids:
                seen_ids.add(eid)
                participants.append(RoleAssignment(
                    entity_id=eid,
                    entity_type="outcome",
                    role="outcome",
                    attributes={"code": outcome},
                ))

        if len(participants) >= 2:
            hyperedges.append(Hyperedge(
                hyperedge_id=f"faers-{cid}",
                relation_type="adverse-event",
                participants=participants,
                attributes={"source": "fda-faers"},
            ))

    elapsed = time.perf_counter() - t0
    logger.info(
        "Built %d hyperedges in %.2fs (avg %.1f participants/edge)",
        len(hyperedges), elapsed,
        sum(he.cardinality for he in hyperedges) / max(len(hyperedges), 1),
    )

    return hyperedges


def _find_file(data_dir: Path, prefix: str) -> Path | None:
    """Find a FAERS file by prefix (case-insensitive)."""
    for ext in ("*.txt", "*.TXT", "*.csv"):
        for f in data_dir.glob(ext):
            if f.stem.upper().startswith(prefix.upper()):
                return f
    return None
