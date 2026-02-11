"""Tests for Pydantic data models."""


import pytest

from src.models.decisions import (
    DecisionTrace,
    ExceptionOverride,
    PrecedentChain,
    TwoMorphismType,
)
from src.models.entities import (
    ENTITY_TYPE_MAP,
    Customer,
    Deal,
    Employee,
    EntityType,
    Metric,
    Policy,
    Ticket,
)
from src.models.hyperedges import (
    DecisionEvent,
    Hyperedge,
    HypergraphPath,
    RelationType,
    RoleAssignment,
)

# ── Entity Tests ───────────────────────────────────────────────────────


class TestEntity:
    def test_customer_creation(self):
        c = Customer(
            entity_id="cust_001",
            entity_name="Acme Corp",
            health_score=72.0,
            tier="enterprise",
        )
        assert c.entity_id == "cust_001"
        assert c.entity_type == EntityType.CUSTOMER
        assert c.health_score == 72.0
        assert c.tier == "enterprise"

    def test_employee_creation(self):
        e = Employee(
            entity_id="emp_001",
            entity_name="VP Sales",
            department="Sales",
            job_role="VP",
        )
        assert e.entity_type == EntityType.EMPLOYEE
        assert e.department == "Sales"

    def test_deal_creation(self):
        d = Deal(
            entity_id="deal_001",
            entity_name="Acme Renewal",
            deal_value=500000.0,
            discount_percentage=20.0,
            stage="negotiation",
        )
        assert d.deal_value == 500000.0
        assert d.discount_percentage == 20.0

    def test_ticket_creation(self):
        t = Ticket(
            entity_id="tkt_001",
            entity_name="Outage",
            severity="SEV-1",
            status="resolved",
        )
        assert t.severity == "SEV-1"

    def test_policy_creation(self):
        p = Policy(
            entity_id="pol_001",
            entity_name="Discount Policy",
            policy_type="discount",
            max_discount=15.0,
        )
        assert p.max_discount == 15.0

    def test_metric_creation(self):
        m = Metric(
            entity_id="met_001",
            entity_name="NPS Score",
            metric_value=42.0,
            metric_type="NPS",
        )
        assert m.metric_value == 42.0

    def test_entity_type_map(self):
        assert ENTITY_TYPE_MAP[EntityType.CUSTOMER] is Customer
        assert ENTITY_TYPE_MAP[EntityType.DEAL] is Deal
        assert len(ENTITY_TYPE_MAP) == 6

    def test_health_score_validation(self):
        with pytest.raises(ValueError):
            Customer(
                entity_id="c1",
                entity_name="Bad",
                health_score=150.0,  # > 100
            )


# ── Hyperedge Tests ────────────────────────────────────────────────────


class TestHyperedge:
    @pytest.fixture
    def sample_hyperedge_a(self):
        return Hyperedge(
            hyperedge_id="he_001",
            participants=[
                RoleAssignment(entity_id="cust_001", role="participant"),
                RoleAssignment(entity_id="deal_001", role="participant"),
                RoleAssignment(entity_id="pol_001", role="participant"),
            ],
        )

    @pytest.fixture
    def sample_hyperedge_b(self):
        return Hyperedge(
            hyperedge_id="he_002",
            participants=[
                RoleAssignment(entity_id="cust_001", role="participant"),
                RoleAssignment(entity_id="deal_001", role="participant"),
                RoleAssignment(entity_id="emp_001", role="participant"),
            ],
        )

    @pytest.fixture
    def sample_hyperedge_c(self):
        return Hyperedge(
            hyperedge_id="he_003",
            participants=[
                RoleAssignment(entity_id="tkt_001", role="participant"),
                RoleAssignment(entity_id="met_001", role="participant"),
            ],
        )

    def test_cardinality(self, sample_hyperedge_a):
        assert sample_hyperedge_a.cardinality == 3

    def test_entity_ids(self, sample_hyperedge_a):
        assert sample_hyperedge_a.entity_ids == {"cust_001", "deal_001", "pol_001"}

    def test_intersection_size(self, sample_hyperedge_a, sample_hyperedge_b):
        # share cust_001 and deal_001
        assert sample_hyperedge_a.intersection_size(sample_hyperedge_b) == 2

    def test_s_adjacent_true(self, sample_hyperedge_a, sample_hyperedge_b):
        assert sample_hyperedge_a.is_s_adjacent(sample_hyperedge_b, s=2)

    def test_s_adjacent_false(self, sample_hyperedge_a, sample_hyperedge_c):
        # no shared entities
        assert not sample_hyperedge_a.is_s_adjacent(sample_hyperedge_c, s=2)

    def test_s_adjacent_s1(self, sample_hyperedge_a, sample_hyperedge_b):
        assert sample_hyperedge_a.is_s_adjacent(sample_hyperedge_b, s=1)

    def test_decision_event(self):
        de = DecisionEvent(
            hyperedge_id="dec_001",
            decision_type="discount-approval",
            rationale="VP approved exception",
            participants=[
                RoleAssignment(entity_id="cust_001", role="involved-entity"),
                RoleAssignment(entity_id="emp_001", role="decision-maker"),
            ],
        )
        assert de.relation_type == RelationType.DECISION
        assert de.rationale == "VP approved exception"


class TestHypergraphPath:
    def test_valid_path(self):
        he1 = Hyperedge(
            hyperedge_id="he_1",
            participants=[
                RoleAssignment(entity_id="a", role="p"),
                RoleAssignment(entity_id="b", role="p"),
                RoleAssignment(entity_id="c", role="p"),
            ],
        )
        he2 = Hyperedge(
            hyperedge_id="he_2",
            participants=[
                RoleAssignment(entity_id="b", role="p"),
                RoleAssignment(entity_id="c", role="p"),
                RoleAssignment(entity_id="d", role="p"),
            ],
        )
        path = HypergraphPath(hyperedges=[he1, he2], intersection_size=2)
        assert path.is_valid()
        assert path.length == 2
        assert path.all_entity_ids == {"a", "b", "c", "d"}

    def test_invalid_path(self):
        he1 = Hyperedge(
            hyperedge_id="he_1",
            participants=[
                RoleAssignment(entity_id="a", role="p"),
                RoleAssignment(entity_id="b", role="p"),
            ],
        )
        he2 = Hyperedge(
            hyperedge_id="he_2",
            participants=[
                RoleAssignment(entity_id="c", role="p"),
                RoleAssignment(entity_id="d", role="p"),
            ],
        )
        path = HypergraphPath(hyperedges=[he1, he2], intersection_size=2)
        assert not path.is_valid()

    def test_single_hyperedge_path(self):
        he = Hyperedge(
            hyperedge_id="he_1",
            participants=[
                RoleAssignment(entity_id="a", role="p"),
                RoleAssignment(entity_id="b", role="p"),
            ],
        )
        path = HypergraphPath(hyperedges=[he])
        assert path.is_valid()
        assert path.length == 1


# ── Decision / 2-Morphism Tests ────────────────────────────────────────


class TestDecisions:
    def test_precedent_chain(self):
        pc = PrecedentChain(
            precedent_id="dec_001",
            derived_id="dec_002",
            morphism_type=TwoMorphismType.PRECEDENT,
            rationale="Similar customer profile and deal structure",
        )
        assert pc.morphism_type == TwoMorphismType.PRECEDENT

    def test_exception_override(self):
        eo = ExceptionOverride(
            base_decision_id="dec_001",
            exception_decision_id="dec_002",
            override_rationale="VP exception for strategic account",
            approver_id="emp_001",
        )
        assert eo.approver_id == "emp_001"

    def test_decision_trace(self):
        trace = DecisionTrace(
            trace_id="trace_001",
            decisions=["dec_001", "dec_002", "dec_003"],
            two_morphisms=[
                PrecedentChain(
                    precedent_id="dec_001",
                    derived_id="dec_002",
                ),
            ],
            is_coherent=True,
        )
        assert trace.is_coherent
        assert len(trace.decisions) == 3
        assert len(trace.two_morphisms) == 1
