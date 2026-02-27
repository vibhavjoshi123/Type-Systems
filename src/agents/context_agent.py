"""Context Agent - hypergraph traversal and path finding.

Operates on 1-morphisms: computes compositions in the 1-category.
The IS constraint is a composition rule that defines when composition
is valid. Finding a path means computing e1 o e2 o e3.

From Higher-Order Reasoning PDF Section 3 and MIT paper.
"""

from __future__ import annotations

from src.agents.base import AgentQuery, AgentResponse, BaseAgent
from src.typedb.traversal import HypergraphTraversal


class ContextAgent(BaseAgent):
    """Agent for hypergraph traversal and context gathering.

    Capabilities:
    - BFS over s-adjacent hyperedges
    - Yen's K-shortest paths with IS constraints
    - s-connected component discovery
    - Hub node identification
    """

    def __init__(self, traversal: HypergraphTraversal) -> None:
        super().__init__()
        self._traversal = traversal

    @property
    def name(self) -> str:
        return "context_agent"

    async def process(self, query: AgentQuery) -> AgentResponse:
        """Find relevant context by traversing the hypergraph.

        Uses BFS with IS >= s constraint to find connected decisions
        and build context for reasoning.
        """
        s = query.intersection_size
        max_depth = query.max_depth

        # Find s-connected components
        components = self._traversal.find_s_connected_components(s)

        # Identify hub nodes
        hubs = self._traversal.hub_nodes(min_degree=3)

        # Build evidence from components
        evidence: list[dict[str, object]] = []
        for i, component in enumerate(components):
            evidence.append({
                "component_id": i,
                "hyperedge_count": len(component),
                "hyperedge_indices": component,
            })

        return AgentResponse(
            answer=f"Found {len(components)} s-connected component(s) "
                   f"with IS>={s}, {len(hubs)} hub node(s), "
                   f"across {len(self._traversal.hyperedges)} hyperedges.",
            evidence=evidence,
            paths_found=len(components),
            confidence=min(1.0, len(components) * 0.2),
            metadata={
                "hub_nodes": hubs[:10],
                "intersection_size": s,
                "max_depth": max_depth,
                "total_hyperedges": len(self._traversal.hyperedges),
                "avg_hyperedge_size": self._traversal.average_hyperedge_size(),
            },
        )

    async def find_paths(
        self,
        start_idx: int,
        target_idx: int,
        k: int = 3,
        s: int = 2,
    ) -> list[list[int]]:
        """Find K shortest s-paths between two hyperedges."""
        return self._traversal.yen_k_shortest_paths(
            start_idx, target_idx, k=k, s=s
        )
