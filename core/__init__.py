"""Core hypergraph engine for benchmarking — domain-agnostic."""

from core.engine import HypergraphTraversal
from core.loader import DomainConfig, load_config
from core.models import Hyperedge, RoleAssignment, TwoMorphism

__all__ = [
    "DomainConfig",
    "Hyperedge",
    "HypergraphTraversal",
    "RoleAssignment",
    "TwoMorphism",
    "load_config",
]
