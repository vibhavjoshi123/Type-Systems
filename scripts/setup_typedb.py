#!/usr/bin/env python3
"""TypeDB 3.x setup automation script.

Creates the database, loads the schema and functions, and optionally seeds sample data.
Run this once after deploying TypeDB to bootstrap the hypergraph.

Supports both TypeDB Core (local) and TypeDB Cloud connections.

Usage:
    python scripts/setup_typedb.py [--seed]
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("setup_typedb")


async def setup(seed: bool = False) -> None:
    """Run the full TypeDB setup sequence."""
    from src.config import get_settings
    from src.typedb.client import TypeDBClient
    from src.typedb.inference import InferenceManager
    from src.typedb.schema import FUNCTIONS_TYPEQL, SCHEMA_TYPEQL

    settings = get_settings()
    logger.info("Connecting to TypeDB at %s", settings.typedb.address)

    async with TypeDBClient(settings.typedb) as client:
        if not client.is_connected:
            logger.error(
                "Could not connect to TypeDB at %s.",
                settings.typedb.address,
            )
            logger.error(
                "Troubleshooting:\n"
                "  1. Check TYPEDB_ADDRESS in .env "
                "(Cloud format: rv7ii3-0.cluster.typedb.com:443)\n"
                "  2. Ensure TYPEDB_TLS_ENABLED=true for Cloud\n"
                "  3. Verify TYPEDB_USERNAME and TYPEDB_PASSWORD\n"
                "  4. For local: "
                "docker run -d --name typedb -p 1729:1729 "
                "typedb/typedb:latest"
            )
            sys.exit(1)

        # Step 1: Create database (drop first if --seed)
        db_name = settings.typedb.database
        logger.info("Step 1/5: Creating database '%s'...", db_name)
        if seed and client._driver:
            # On seed runs, drop existing DB to avoid stale schema
            try:
                if client._driver.databases.contains(db_name):
                    client._driver.databases.get(db_name).delete()
                    logger.info("Dropped existing database: %s", db_name)
            except Exception:
                logger.debug("Could not drop database (may not exist)")
        created = await client.ensure_database()
        if created:
            logger.info("Database created successfully")
        else:
            logger.info("Database already exists")

        # Step 2: Load schema
        logger.info("Step 2/5: Loading TypeQL 3.x schema...")
        await client.load_schema(SCHEMA_TYPEQL)
        logger.info("Schema loaded successfully")

        # Step 3: Load functions (replaces 2.x inference rules)
        logger.info("Step 3/5: Loading TypeDB functions...")
        try:
            await client.load_schema(FUNCTIONS_TYPEQL)
            logger.info("Functions loaded from schema definition")
        except Exception:
            logger.warning("Schema-level functions not loaded, trying via InferenceManager")

        # Step 4: Load additional functions via manager
        logger.info("Step 4/5: Loading additional functions via InferenceManager...")
        inference = InferenceManager(client)
        loaded = await inference.load_rules()
        logger.info("Loaded %d function(s)", loaded)

        # Step 5: Seed data (optional)
        if seed:
            logger.info("Step 5/5: Seeding sample data...")
            await _seed_data(client)
            logger.info("Sample data seeded successfully")
        else:
            logger.info("Step 5/5: Skipping seed data (use --seed to enable)")

    logger.info("TypeDB setup complete!")


# ═══════════════════════════════════════════════════════════════════════
#  SEED DATA — Rich enterprise scenario with 2-morphisms
# ═══════════════════════════════════════════════════════════════════════
#
#  3 customers, 4 employees, 3 deals, 3 tickets, 3 policies  = 16 entities
#  6 decision-event hyperedges (interconnected via shared entities)
#  4 explicit 2-morphisms (2 precedent-chains + 2 exception-overrides)
#
#  s-adjacency graph (IS >= 2):
#
#    Dec1 ──IS=2── Dec2      Dec3 ──IS=2── Dec6
#      │                                     │
#    IS=3                                  IS=2
#      │                                     │
#    Dec4 ──IS=2── Dec5      Dec1 ──IS=2── Dec6
#
#  2-morphism diagram:
#
#    Dec1 ─precedent─→ Dec6       (incident discount precedent)
#    Dec4 ─precedent─→ Dec5       (SLA credit precedent)
#    Dec2 ─exception─→ Dec1       (VP override of standard process)
#    Dec3 ─exception─→ Dec6       (escalation fast-tracked to discount)
#
# ═══════════════════════════════════════════════════════════════════════


async def _seed_data(client: object) -> None:
    """Seed a rich enterprise scenario for testing."""
    from src.models.entities import Customer, Deal, Employee, Policy, Ticket
    from src.models.hyperedges import DecisionEvent, RoleAssignment
    from src.typedb.operations import HypergraphOperations

    ops = HypergraphOperations(client)  # type: ignore[arg-type]

    # ── Customers ──────────────────────────────────────────────────────
    customers = [
        Customer(
            entity_id="cust_001",
            entity_name="Acme Corp",
            health_score=72.0,
            tier="enterprise",
            arr=500000.0,
            source_system="salesforce",
        ),
        Customer(
            entity_id="cust_002",
            entity_name="Globex Industries",
            health_score=85.0,
            tier="enterprise",
            arr=1200000.0,
            source_system="salesforce",
        ),
        Customer(
            entity_id="cust_003",
            entity_name="Initech Solutions",
            health_score=58.0,
            tier="mid-market",
            arr=180000.0,
            source_system="salesforce",
        ),
    ]

    # ── Employees ──────────────────────────────────────────────────────
    employees = [
        Employee(
            entity_id="emp_001",
            entity_name="Sarah Chen",
            department="Sales",
            job_role="VP",
            title="VP of Sales",
            source_system="workday",
        ),
        Employee(
            entity_id="emp_002",
            entity_name="Marcus Rivera",
            department="Sales",
            job_role="Director",
            title="Account Director",
            source_system="workday",
        ),
        Employee(
            entity_id="emp_003",
            entity_name="Priya Patel",
            department="Support",
            job_role="Lead",
            title="Support Engineering Lead",
            source_system="workday",
        ),
        Employee(
            entity_id="emp_004",
            entity_name="James Wilson",
            department="Finance",
            job_role="CFO",
            title="Chief Financial Officer",
            source_system="workday",
        ),
    ]

    # ── Deals ──────────────────────────────────────────────────────────
    deals = [
        Deal(
            entity_id="deal_001",
            entity_name="Acme Renewal Q1",
            deal_value=500000.0,
            discount_percentage=20.0,
            stage="negotiation",
            source_system="salesforce",
        ),
        Deal(
            entity_id="deal_002",
            entity_name="Globex Platform Expansion",
            deal_value=800000.0,
            discount_percentage=12.0,
            stage="closed-won",
            source_system="salesforce",
        ),
        Deal(
            entity_id="deal_003",
            entity_name="Initech Renewal Q2",
            deal_value=180000.0,
            discount_percentage=18.0,
            stage="negotiation",
            source_system="salesforce",
        ),
    ]

    # ── Tickets ────────────────────────────────────────────────────────
    tickets = [
        Ticket(
            entity_id="tkt_001",
            entity_name="Acme Production Outage - Jan 2026",
            severity="SEV-1",
            status="resolved",
            source_system="zendesk",
        ),
        Ticket(
            entity_id="tkt_002",
            entity_name="Globex Data Migration Failure",
            severity="SEV-2",
            status="resolved",
            source_system="zendesk",
        ),
        Ticket(
            entity_id="tkt_003",
            entity_name="Initech API Latency Degradation",
            severity="SEV-2",
            status="open",
            source_system="zendesk",
        ),
    ]

    # ── Policies ───────────────────────────────────────────────────────
    policies = [
        Policy(
            entity_id="pol_001",
            entity_name="Standard Discount Policy",
            policy_type="discount",
            max_discount=15.0,
            source_system="internal",
        ),
        Policy(
            entity_id="pol_002",
            entity_name="Enterprise SLA Policy",
            policy_type="sla",
            max_discount=20.0,
            source_system="internal",
        ),
        Policy(
            entity_id="pol_003",
            entity_name="Incident Escalation Policy",
            policy_type="escalation",
            max_discount=0.0,
            source_system="internal",
        ),
    ]

    # Insert all entities
    all_entities = [*customers, *employees, *deals, *tickets, *policies]
    for entity in all_entities:
        await ops.insert_entity(entity)
    logger.info("Seeded %d entities", len(all_entities))

    # ── Decision Hyperedges ────────────────────────────────────────────
    #
    # Each decision connects multiple entities through typed roles.
    # Shared entities between decisions create s-adjacency links (IS >= 2).

    decisions = [
        # Dec 1: Acme discount approval — VP override exceeding 15% policy
        # Entities: {cust_001, emp_001, deal_001, tkt_001, pol_001}
        DecisionEvent(
            hyperedge_id="dec_001",
            decision_type="discount-approval",
            rationale=(
                "VP approved 20% discount exceeding 15% policy limit "
                "due to SEV-1 production outage history and $500K ARR "
                "strategic account status. Catalyst: Sarah Chen's executive "
                "authority lowered the approval threshold (catalyst-approver "
                "isomorphism from CRN theory)."
            ),
            participants=[
                RoleAssignment(entity_id="cust_001", role="involved-entity"),
                RoleAssignment(entity_id="emp_001", role="decision-maker"),
                RoleAssignment(entity_id="deal_001", role="involved-entity"),
                RoleAssignment(entity_id="tkt_001", role="involved-entity"),
                RoleAssignment(entity_id="pol_001", role="involved-entity"),
            ],
        ),
        # Dec 2: Globex expansion discount — within policy, standard approval
        # Entities: {cust_002, emp_001, emp_002, deal_002, pol_001}
        # IS=2 with Dec1 via {emp_001, pol_001}
        DecisionEvent(
            hyperedge_id="dec_002",
            decision_type="expansion-discount",
            rationale=(
                "Account Director approved 12% discount on $800K platform "
                "expansion deal for Globex Industries. Within standard 15% "
                "policy limit. VP co-signed as deal exceeded $500K threshold. "
                "Enterprise tier customer with strong health score (85)."
            ),
            participants=[
                RoleAssignment(entity_id="cust_002", role="involved-entity"),
                RoleAssignment(entity_id="emp_001", role="decision-maker"),
                RoleAssignment(entity_id="emp_002", role="decision-maker"),
                RoleAssignment(entity_id="deal_002", role="involved-entity"),
                RoleAssignment(entity_id="pol_001", role="involved-entity"),
            ],
        ),
        # Dec 3: Initech emergency escalation — support-driven
        # Entities: {cust_003, emp_003, tkt_003, pol_003}
        # IS=2 with Dec6 via {cust_003, tkt_003}
        DecisionEvent(
            hyperedge_id="dec_003",
            decision_type="incident-escalation",
            rationale=(
                "Support Lead Priya Patel escalated Initech API latency "
                "degradation (SEV-2) to engineering and executive review. "
                "Customer health score dropped to 58 — churn risk flagged. "
                "Escalation Policy triggered mandatory 48-hour response SLA."
            ),
            participants=[
                RoleAssignment(entity_id="cust_003", role="involved-entity"),
                RoleAssignment(entity_id="emp_003", role="decision-maker"),
                RoleAssignment(entity_id="tkt_003", role="involved-entity"),
                RoleAssignment(entity_id="pol_003", role="involved-entity"),
            ],
        ),
        # Dec 4: Acme SLA credit — CFO approved service credit for outage
        # Entities: {cust_001, emp_004, emp_001, tkt_001, pol_002}
        # IS=3 with Dec1 via {cust_001, emp_001, tkt_001}
        DecisionEvent(
            hyperedge_id="dec_004",
            decision_type="sla-credit-approval",
            rationale=(
                "CFO James Wilson approved 15% SLA service credit for "
                "Acme Corp following the SEV-1 production outage. Enterprise "
                "SLA Policy guarantees 99.9% uptime; outage violated SLA by "
                "4.2 hours. VP Sarah Chen co-approved to align with ongoing "
                "renewal negotiation strategy."
            ),
            participants=[
                RoleAssignment(entity_id="cust_001", role="involved-entity"),
                RoleAssignment(entity_id="emp_004", role="decision-maker"),
                RoleAssignment(entity_id="emp_001", role="decision-maker"),
                RoleAssignment(entity_id="tkt_001", role="involved-entity"),
                RoleAssignment(entity_id="pol_002", role="involved-entity"),
            ],
        ),
        # Dec 5: Globex migration compensation — service credit for migration failure
        # Entities: {cust_002, emp_001, tkt_002, pol_002}
        # IS=2 with Dec4 via {emp_001, pol_002}
        # IS=2 with Dec2 via {cust_002, emp_001}
        DecisionEvent(
            hyperedge_id="dec_005",
            decision_type="migration-compensation",
            rationale=(
                "VP Sarah Chen approved 10% service credit for Globex "
                "Industries following data migration failure (SEV-2). "
                "Applied Enterprise SLA Policy precedent established by "
                "Acme SLA credit (dec_004). $1.2M ARR account retention "
                "justified expedited approval without CFO sign-off."
            ),
            participants=[
                RoleAssignment(entity_id="cust_002", role="involved-entity"),
                RoleAssignment(entity_id="emp_001", role="decision-maker"),
                RoleAssignment(entity_id="tkt_002", role="involved-entity"),
                RoleAssignment(entity_id="pol_002", role="involved-entity"),
            ],
        ),
        # Dec 6: Initech churn prevention — discount to retain at-risk customer
        # Entities: {cust_003, emp_001, emp_002, deal_003, tkt_003, pol_001}
        # IS=2 with Dec1 via {emp_001, pol_001}
        # IS=2 with Dec2 via {emp_001, emp_002, pol_001} = IS=3
        # IS=2 with Dec3 via {cust_003, tkt_003}
        DecisionEvent(
            hyperedge_id="dec_006",
            decision_type="churn-prevention-discount",
            rationale=(
                "VP Sarah Chen and Account Director Marcus Rivera "
                "co-approved 18% renewal discount for Initech Solutions "
                "(exceeding 15% policy limit by 3%). Justification: "
                "ongoing SEV-2 API latency issue, health score at 58 "
                "(churn risk), and precedent set by Acme discount approval "
                "(dec_001). Combined with escalation findings from dec_003."
            ),
            participants=[
                RoleAssignment(entity_id="cust_003", role="involved-entity"),
                RoleAssignment(entity_id="emp_001", role="decision-maker"),
                RoleAssignment(entity_id="emp_002", role="decision-maker"),
                RoleAssignment(entity_id="deal_003", role="involved-entity"),
                RoleAssignment(entity_id="tkt_003", role="involved-entity"),
                RoleAssignment(entity_id="pol_001", role="involved-entity"),
            ],
        ),
    ]

    for decision in decisions:
        await ops.insert_hyperedge(decision)
    logger.info("Seeded %d decision hyperedges", len(decisions))

    # ── 2-Morphisms (meta-relations between decisions) ─────────────────
    #
    # These are the key higher-order structures:
    # - precedent-chain: Decision B cited Decision A as precedent
    # - exception-override: Decision B overrides/bypasses Decision A's pattern
    #
    # In category theory terms: 2-cells in a 2-category
    # In CRN terms: meta-reactions linking reaction pathways

    two_morphism_queries = [
        # 2-Morphism 1: PRECEDENT — Acme discount → Initech churn prevention
        # "The Acme incident-based discount (dec_001) established the precedent
        #  pattern that was later applied to Initech's churn prevention (dec_006)"
        (
            "match"
            ' $d1 isa decision-event, has decision-type "discount-approval";'
            ' $d2 isa decision-event, has decision-type "churn-prevention-discount";'
            " insert"
            " (precedent-decision: $d1, derived-decision: $d2)"
            " isa precedent-chain,"
            ' has precedent-type "precedent",'
            ' has rationale "Acme incident-based discount (20% for SEV-1 outage)'
            " established the pattern for granting above-policy discounts when"
            " service failures affect strategic accounts. Initech churn prevention"
            ' discount (18%) directly cited this as justification.";'
        ),
        # 2-Morphism 2: PRECEDENT — Acme SLA credit → Globex migration compensation
        # "The SLA credit methodology from Acme was reapplied to Globex"
        (
            "match"
            ' $d1 isa decision-event, has decision-type "sla-credit-approval";'
            ' $d2 isa decision-event, has decision-type "migration-compensation";'
            " insert"
            " (precedent-decision: $d1, derived-decision: $d2)"
            " isa precedent-chain,"
            ' has precedent-type "precedent",'
            ' has rationale "Acme SLA credit approval (15% for outage) established'
            " the service-credit methodology under Enterprise SLA Policy. Globex"
            " migration compensation (10%) reused this framework, allowing VP-only"
            ' approval without CFO sign-off for sub-15% credits.";'
        ),
        # 2-Morphism 3: EXCEPTION — Globex standard process → Acme VP override
        # "Acme's approval was an exception to the standard policy-compliant
        #  process demonstrated by the Globex expansion deal"
        (
            "match"
            ' $base isa decision-event, has decision-type "expansion-discount";'
            ' $exc isa decision-event, has decision-type "discount-approval";'
            " insert"
            " (base-decision: $base, exception-decision: $exc)"
            " isa exception-override,"
            ' has override-rationale "The Globex expansion discount (12%) followed'
            " standard policy-compliant approval. The Acme discount (20%) created"
            " an exception: VP executive authority overrode the 15% policy ceiling."
            " This is the catalyst-approver isomorphism from CRN theory — the VP"
            " acts as a catalyst lowering the activation energy (approval threshold)"
            ' for the discount reaction.";'
        ),
        # 2-Morphism 4: EXCEPTION — Initech escalation → Initech churn discount
        # "The standard escalation path was bypassed; escalation findings were
        #  fast-tracked into a discount approval without completing the full
        #  escalation resolution cycle"
        (
            "match"
            ' $base isa decision-event, has decision-type "incident-escalation";'
            ' $exc isa decision-event, has decision-type "churn-prevention-discount";'
            " insert"
            " (base-decision: $base, exception-decision: $exc)"
            " isa exception-override,"
            ' has override-rationale "Standard escalation policy requires full'
            " incident resolution before commercial decisions. The churn prevention"
            " discount was approved while the SEV-2 API latency issue remained open,"
            " bypassing the escalation-then-resolution sequence. VP + Account Director"
            ' co-approval substituted for completed incident resolution.";'
        ),
    ]

    stored = 0
    for typeql in two_morphism_queries:
        try:
            await client.write(typeql)  # type: ignore[union-attr]
            stored += 1
        except Exception as exc:
            logger.warning("Failed to insert 2-morphism: %s", exc)
    logger.info("Seeded %d 2-morphisms (precedent-chains + exception-overrides)", stored)

    # ── Summary ────────────────────────────────────────────────────────
    logger.info(
        "\n"
        "╔══════════════════════════════════════════════════════════════╗\n"
        "║  SEED DATA SUMMARY                                         ║\n"
        "╠══════════════════════════════════════════════════════════════╣\n"
        "║  Entities:    16 (3 customers, 4 employees, 3 deals,       ║\n"
        "║                   3 tickets, 3 policies)                    ║\n"
        "║  Hyperedges:   6 decision-events                           ║\n"
        "║  2-Morphisms:  4 (2 precedent-chains, 2 exception-overrides║\n"
        "║                                                            ║\n"
        "║  s-Adjacency Graph (IS >= 2):                              ║\n"
        "║    Dec1 ─IS=2─ Dec2 ─IS=3─ Dec6 ─IS=2─ Dec3               ║\n"
        "║    Dec1 ─IS=3─ Dec4 ─IS=2─ Dec5                            ║\n"
        "║    Dec1 ─IS=2─ Dec6                                        ║\n"
        "║    Dec2 ─IS=2─ Dec5                                        ║\n"
        "║                                                            ║\n"
        "║  2-Morphism Diagram:                                       ║\n"
        "║    Dec1 ─precedent──→ Dec6  (incident discount pattern)    ║\n"
        "║    Dec4 ─precedent──→ Dec5  (SLA credit methodology)       ║\n"
        "║    Dec2 ─exception──→ Dec1  (VP override of std process)   ║\n"
        "║    Dec3 ─exception──→ Dec6  (escalation fast-tracked)      ║\n"
        "╚══════════════════════════════════════════════════════════════╝"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Set up TypeDB for Hypergraph Context Graph")
    parser.add_argument("--seed", action="store_true", help="Seed sample data")
    args = parser.parse_args()
    asyncio.run(setup(seed=args.seed))


if __name__ == "__main__":
    main()
