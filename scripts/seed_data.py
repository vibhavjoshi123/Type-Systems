#!/usr/bin/env python3
"""Seed the TypeDB database with example enterprise data.

Creates sample entities and decision hyperedges demonstrating
the core concepts from the Chemical Reaction Networks PDF.

Usage:
    python scripts/seed_data.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import get_settings
from src.models.entities import Customer, Deal, Employee, Policy, Ticket
from src.models.hyperedges import DecisionEvent, RoleAssignment
from src.typedb.client import TypeDBClient
from src.typedb.operations import HypergraphOperations


async def main() -> None:
    """Seed example data."""
    settings = get_settings()

    async with TypeDBClient(settings.typedb) as client:
        if not client.is_connected:
            print("ERROR: Could not connect to TypeDB.")
            print("Run: docker run -d --name typedb -p 1729:1729 typedb/typedb:latest")
            sys.exit(1)

        ops = HypergraphOperations(client)

        # ── Create Entities ────────────────────────────────────────
        print("Creating entities...")

        acme = Customer(
            entity_id="cust_001",
            entity_name="Acme Corp",
            health_score=65.0,
            tier="enterprise",
            source_system="salesforce",
        )
        await ops.insert_entity(acme)

        vp_sales = Employee(
            entity_id="emp_001",
            entity_name="VP Sales",
            department="Sales",
            role="VP",
            title="Vice President of Sales",
        )
        await ops.insert_entity(vp_sales)

        deal_123 = Deal(
            entity_id="deal_123",
            entity_name="Acme Renewal Q1",
            deal_value=500000.0,
            discount_percentage=20.0,
            stage="negotiation",
            source_system="salesforce",
        )
        await ops.insert_entity(deal_123)

        retention_policy = Policy(
            entity_id="pol_001",
            entity_name="Retention Discount Policy",
            policy_type="discount",
            max_discount=15.0,
        )
        await ops.insert_entity(retention_policy)

        sev1_ticket = Ticket(
            entity_id="tkt_001",
            entity_name="Production Outage - Acme",
            severity="SEV-1",
            status="resolved",
            source_system="pagerduty",
        )
        await ops.insert_entity(sev1_ticket)

        # ── Create Decision Hyperedge ──────────────────────────────
        print("Creating decision hyperedge...")

        # The key hyperedge: 5 entities connected in a single atomic decision
        # This is what RDF/OWL would need reification for, but TypeDB does natively
        discount_decision = DecisionEvent(
            hyperedge_id="dec_001",
            decision_type="discount-approval",
            rationale=(
                "20% discount approved for Acme Corp renewal. Justified by "
                "3 SEV-1 incidents in Q4 and strategic account status. "
                "Exceeds 15% policy limit; VP exception approved."
            ),
            participants=[
                RoleAssignment(entity_id="cust_001", role="involved-entity"),
                RoleAssignment(entity_id="emp_001", role="decision-maker"),
                RoleAssignment(entity_id="deal_123", role="involved-entity"),
                RoleAssignment(entity_id="pol_001", role="involved-entity"),
                RoleAssignment(entity_id="tkt_001", role="involved-entity"),
            ],
            source_system="internal",
        )
        await ops.insert_hyperedge(discount_decision)

        print("Seed data loaded successfully!")
        print("\nCreated:")
        print("  - 5 entities (customer, employee, deal, policy, ticket)")
        print("  - 1 decision hyperedge (5-way n-ary relation)")
        print("\nThis demonstrates the core isomorphism from the Chemical")
        print("Reaction Networks PDF: a single atomic decision event")
        print("connecting all participants, like a chemical reaction.")


if __name__ == "__main__":
    asyncio.run(main())
