"""Ingest SCOTUS case data into Hyperedge + TwoMorphism objects.

Data model:
- Each case becomes a Hyperedge (decision-event) connecting:
  majority author + concurring justices + dissenting justices + legal topics
- Citations between cases become TwoMorphisms:
  precedent, overruled, distinguished, affirmed

Why this proves 2-morphisms:
  Legal citation IS the canonical example of a meta-relation.
  "Case A → Case B" isn't just a link — it has a TYPE
  (precedent vs overruled vs distinguished) and a RATIONALE
  (why the court cited it). That's exactly a 2-morphism:
  a typed, annotated relation between two decision-events.
"""

from __future__ import annotations

import csv
import logging
import time
from pathlib import Path

from core.models import Hyperedge, RoleAssignment, TwoMorphism, TwoMorphismType

logger = logging.getLogger(__name__)


def _citation_type_to_morphism(cite_type: str) -> TwoMorphismType:
    """Map citation type strings to TwoMorphismType."""
    ct = cite_type.lower().strip()
    if "overrul" in ct:
        return TwoMorphismType.OVERRIDE
    if "distinguish" in ct:
        return TwoMorphismType.EXCEPTION
    if "affirm" in ct:
        return TwoMorphismType.PRECEDENT
    return TwoMorphismType.PRECEDENT


def ingest_landmark(
) -> tuple[list[Hyperedge], list[TwoMorphism]]:
    """Build hyperedges and 2-morphisms from the curated landmark dataset.

    Returns:
        (hyperedges, two_morphisms)
    """
    from scotus_citations.landmark_data import LANDMARK_CASES, LANDMARK_CITATIONS

    t0 = time.perf_counter()
    hyperedges: list[Hyperedge] = []

    for case in LANDMARK_CASES:
        participants: list[RoleAssignment] = []

        # Majority author
        author = case.get("majority_author", "")
        if author:
            participants.append(RoleAssignment(
                entity_id=f"justice:{author.lower().replace(' ', '-')}",
                entity_type="justice",
                role="majority-author",
                attributes={"name": author},
            ))

        # Dissenters
        for dissenter in case.get("dissenters", []):
            participants.append(RoleAssignment(
                entity_id=f"justice:{dissenter.lower().replace(' ', '-')}",
                entity_type="justice",
                role="dissenting-justice",
                attributes={"name": dissenter},
            ))

        # Legal topics
        for topic in case.get("topics", []):
            participants.append(RoleAssignment(
                entity_id=f"topic:{topic}",
                entity_type="topic",
                role="legal-topic",
                attributes={"name": topic},
            ))

        if len(participants) >= 2:
            hyperedges.append(Hyperedge(
                hyperedge_id=case["case_id"],
                relation_type="case-decision",
                participants=participants,
                attributes={
                    "name": case["name"],
                    "year": case["year"],
                    "direction": case.get("decision_direction", ""),
                },
            ))

    # Build 2-morphisms from citations
    morphisms: list[TwoMorphism] = []
    case_ids = {case["case_id"] for case in LANDMARK_CASES}

    for cite in LANDMARK_CITATIONS:
        source = cite["source"]
        target = cite["target"]
        if source not in case_ids or target not in case_ids:
            continue

        morphisms.append(TwoMorphism(
            morphism_id=f"{source}-->{target}",
            morphism_type=_citation_type_to_morphism(cite["type"]),
            source_hyperedge_id=source,
            target_hyperedge_id=target,
            rationale=cite.get("rationale", ""),
        ))

    elapsed = time.perf_counter() - t0
    logger.info(
        "Built %d case hyperedges + %d citation 2-morphisms in %.3fs",
        len(hyperedges), len(morphisms), elapsed,
    )

    return hyperedges, morphisms


def ingest_scdb(
    data_dir: str | Path,
    limit: int = 0,
) -> tuple[list[Hyperedge], list[TwoMorphism]]:
    """Ingest from the Supreme Court Database CSV (bulk data).

    Falls back to landmark data if SCDB files not found.
    """
    data_dir = Path(data_dir)
    scdb_file = data_dir / "scdb_cases.csv"
    citations_file = data_dir / "citations.csv"

    if not scdb_file.exists():
        logger.warning("SCDB file not found at %s, using landmark data", scdb_file)
        return ingest_landmark()

    t0 = time.perf_counter()
    hyperedges: list[Hyperedge] = []

    # Parse SCDB case-centered data
    with open(scdb_file, newline="", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if limit and i >= limit:
                break

            case_id = row.get("caseId", row.get("usCite", f"case-{i}")).strip()
            case_name = row.get("caseName", "").strip()
            year = row.get("term", "").strip()
            chief = row.get("chief", "").strip()
            majority_votes = row.get("majVotes", "").strip()
            minority_votes = row.get("minVotes", "").strip()
            issue = row.get("issue", "").strip()
            issue_area = row.get("issueArea", "").strip()
            direction = row.get("decisionDirection", "").strip()

            participants: list[RoleAssignment] = []

            if chief:
                participants.append(RoleAssignment(
                    entity_id=f"justice:{chief.lower().replace(' ', '-')}",
                    entity_type="justice",
                    role="chief-justice",
                    attributes={"name": chief},
                ))

            if issue_area:
                participants.append(RoleAssignment(
                    entity_id=f"topic:area-{issue_area}",
                    entity_type="topic",
                    role="legal-topic",
                    attributes={"name": f"Issue Area {issue_area}"},
                ))

            if issue:
                participants.append(RoleAssignment(
                    entity_id=f"topic:issue-{issue}",
                    entity_type="topic",
                    role="legal-topic",
                    attributes={"name": f"Issue {issue}"},
                ))

            if len(participants) >= 2:
                hyperedges.append(Hyperedge(
                    hyperedge_id=case_id,
                    relation_type="case-decision",
                    participants=participants,
                    attributes={
                        "name": case_name,
                        "year": year,
                        "direction": direction,
                        "majority_votes": majority_votes,
                        "minority_votes": minority_votes,
                    },
                ))

    # Parse citations if available
    morphisms: list[TwoMorphism] = []
    if citations_file.exists():
        with open(citations_file, newline="", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                if limit and i >= limit:
                    break
                source = row.get("citing_opinion_id", row.get("source", "")).strip()
                target = row.get("cited_opinion_id", row.get("target", "")).strip()
                if source and target:
                    morphisms.append(TwoMorphism(
                        morphism_id=f"cite-{i}",
                        morphism_type=TwoMorphismType.PRECEDENT,
                        source_hyperedge_id=source,
                        target_hyperedge_id=target,
                    ))

    elapsed = time.perf_counter() - t0
    logger.info(
        "Built %d case hyperedges + %d citation 2-morphisms from SCDB in %.3fs",
        len(hyperedges), len(morphisms), elapsed,
    )

    return hyperedges, morphisms
