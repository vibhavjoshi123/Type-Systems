"""Hypergraph traversal engine — standalone, no TypeDB dependency.

Implements the same algorithms as the main repo's src/typedb/traversal.py
but operates purely in-memory for benchmarking speed.

Algorithms:
- BFS with IS >= s constraint
- Yen's K-shortest s-paths
- s-connected component discovery
- Hub node identification
- Noise reduction measurement (s=1 vs s=2)
"""

from __future__ import annotations

import heapq
import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field

from core.models import Hyperedge, TwoMorphism

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkResult:
    """Timing and metrics from a benchmark run."""

    name: str
    entity_count: int = 0
    hyperedge_count: int = 0
    two_morphism_count: int = 0
    # s-adjacency metrics
    connections_s1: int = 0
    connections_s2: int = 0
    noise_reduction_pct: float = 0.0
    component_count_s1: int = 0
    component_count_s2: int = 0
    # Hub nodes
    hub_nodes: list[tuple[str, int]] = field(default_factory=list)
    # Timing (seconds)
    ingest_time: float = 0.0
    index_build_time: float = 0.0
    s_adjacency_time: float = 0.0
    component_discovery_time: float = 0.0
    path_finding_time: float = 0.0
    total_time: float = 0.0
    # Path results
    paths_found: list[list[int]] = field(default_factory=list)
    # Largest component
    largest_component_size: int = 0

    def summary(self) -> str:
        """Human-readable summary."""
        lines = [
            f"=== {self.name} ===",
            f"Entities:            {self.entity_count:,}",
            f"Hyperedges:          {self.hyperedge_count:,}",
            f"2-Morphisms:         {self.two_morphism_count:,}",
            "",
            f"Connections (s=1):   {self.connections_s1:,}",
            f"Connections (s=2):   {self.connections_s2:,}",
            f"Noise reduction:     {self.noise_reduction_pct:.1f}%",
            "",
            f"Components (s=1):    {self.component_count_s1}",
            f"Components (s=2):    {self.component_count_s2}",
            f"Largest component:   {self.largest_component_size} hyperedges",
            "",
            f"Hub nodes (top 10):  {self.hub_nodes[:10]}",
            "",
            f"Ingest time:         {self.ingest_time:.3f}s",
            f"Index build time:    {self.index_build_time:.3f}s",
            f"s-Adjacency time:    {self.s_adjacency_time:.3f}s",
            f"Component discovery:  {self.component_discovery_time:.3f}s",
            f"Path finding:        {self.path_finding_time:.3f}s",
            f"TOTAL:               {self.total_time:.3f}s",
        ]
        return "\n".join(lines)


class HypergraphTraversal:
    """In-memory hypergraph traversal engine.

    Identical algorithms to the main repo, optimized for benchmarking
    with timing instrumentation at every step.
    """

    def __init__(self, hyperedges: list[Hyperedge] | None = None) -> None:
        self._hyperedges: list[Hyperedge] = []
        self._two_morphisms: list[TwoMorphism] = []
        # Inverted index: entity_id → [hyperedge indices]
        self._entity_index: dict[str, list[int]] = defaultdict(list)
        # Morphism index: hyperedge_id → [TwoMorphism]
        self._morphism_index: dict[str, list[TwoMorphism]] = defaultdict(list)

        if hyperedges:
            self.add_hyperedges(hyperedges)

    # ── Loading ─────────────────────────────────────────────────────────

    def add_hyperedge(self, he: Hyperedge) -> None:
        idx = len(self._hyperedges)
        self._hyperedges.append(he)
        for eid in he.entity_ids:
            self._entity_index[eid].append(idx)

    def add_hyperedges(self, hyperedges: list[Hyperedge]) -> None:
        for he in hyperedges:
            self.add_hyperedge(he)

    def add_two_morphism(self, m: TwoMorphism) -> None:
        self._two_morphisms.append(m)
        self._morphism_index[m.source_hyperedge_id].append(m)
        self._morphism_index[m.target_hyperedge_id].append(m)

    def add_two_morphisms(self, morphisms: list[TwoMorphism]) -> None:
        for m in morphisms:
            self.add_two_morphism(m)

    @property
    def hyperedges(self) -> list[Hyperedge]:
        return list(self._hyperedges)

    @property
    def two_morphisms(self) -> list[TwoMorphism]:
        return list(self._two_morphisms)

    @property
    def entity_count(self) -> int:
        return len(self._entity_index)

    # ── s-Adjacency ────────────────────────────────────────────────────

    def get_s_neighbors(self, idx: int, s: int = 2) -> list[int]:
        """Find all hyperedges s-adjacent to the given one (share >= s entities)."""
        target = self._hyperedges[idx]
        neighbors: list[int] = []
        seen: set[int] = {idx}

        for eid in target.entity_ids:
            for other_idx in self._entity_index[eid]:
                if other_idx in seen:
                    continue
                seen.add(other_idx)
                if target.is_s_adjacent(self._hyperedges[other_idx], s):
                    neighbors.append(other_idx)
        return neighbors

    def count_total_connections(self, s: int = 2) -> int:
        """Count total s-adjacent pairs (undirected)."""
        total = 0
        for idx in range(len(self._hyperedges)):
            total += len(self.get_s_neighbors(idx, s))
        return total // 2  # undirected

    # ── BFS ────────────────────────────────────────────────────────────

    def bfs(
        self,
        start_idx: int,
        target_idx: int | None = None,
        s: int = 2,
        max_depth: int = 50,
    ) -> list[int] | None:
        """BFS over s-adjacent hyperedges.

        If target given: returns shortest s-path.
        If target None: returns all reachable indices (component).
        """
        visited: set[int] = {start_idx}
        parent: dict[int, int | None] = {start_idx: None}
        queue: deque[tuple[int, int]] = deque([(start_idx, 0)])

        while queue:
            current, depth = queue.popleft()

            if target_idx is not None and current == target_idx:
                path: list[int] = []
                node: int | None = current
                while node is not None:
                    path.append(node)
                    node = parent[node]
                return list(reversed(path))

            if depth >= max_depth:
                continue

            for neighbor in self.get_s_neighbors(current, s):
                if neighbor not in visited:
                    visited.add(neighbor)
                    parent[neighbor] = current
                    queue.append((neighbor, depth + 1))

        if target_idx is not None:
            return None
        return list(visited)

    # ── s-Connected Components ─────────────────────────────────────────

    def find_s_connected_components(self, s: int = 2) -> list[list[int]]:
        """Find all s-connected components (maximal clusters)."""
        visited: set[int] = set()
        components: list[list[int]] = []

        for idx in range(len(self._hyperedges)):
            if idx in visited:
                continue
            component = self.bfs(idx, target_idx=None, s=s)
            if component:
                visited.update(component)
                components.append(sorted(component))

        return components

    # ── Yen's K-Shortest Paths ─────────────────────────────────────────

    def yen_k_shortest_paths(
        self,
        start_idx: int,
        target_idx: int,
        k: int = 3,
        s: int = 2,
        max_depth: int = 50,
    ) -> list[list[int]]:
        """Find K shortest s-paths using Yen's algorithm."""
        shortest = self.bfs(start_idx, target_idx, s, max_depth)
        if shortest is None:
            return []

        a_paths: list[list[int]] = [shortest]
        b_candidates: list[tuple[int, list[int]]] = []

        for k_i in range(1, k):
            if not a_paths:
                break
            prev_path = a_paths[k_i - 1]

            for spur_idx in range(len(prev_path) - 1):
                spur_node = prev_path[spur_idx]
                root_path = prev_path[: spur_idx + 1]

                excluded_edges: set[tuple[int, int]] = set()
                for path in a_paths:
                    if path[: spur_idx + 1] == root_path and spur_idx + 1 < len(path):
                        excluded_edges.add((path[spur_idx], path[spur_idx + 1]))

                excluded_nodes: set[int] = set(root_path[:-1])
                spur_path = self._restricted_bfs(
                    spur_node, target_idx, s, max_depth - spur_idx,
                    excluded_edges, excluded_nodes,
                )

                if spur_path is not None:
                    total_path = root_path[:-1] + spur_path
                    cost = len(total_path)
                    if (cost, total_path) not in b_candidates:
                        heapq.heappush(b_candidates, (cost, total_path))

            if not b_candidates:
                break
            _, next_path = heapq.heappop(b_candidates)
            a_paths.append(next_path)

        return a_paths

    def _restricted_bfs(
        self,
        start_idx: int,
        target_idx: int,
        s: int,
        max_depth: int,
        excluded_edges: set[tuple[int, int]],
        excluded_nodes: set[int],
    ) -> list[int] | None:
        """BFS with exclusions (for Yen's algorithm)."""
        visited: set[int] = {start_idx} | excluded_nodes
        parent: dict[int, int | None] = {start_idx: None}
        queue: deque[tuple[int, int]] = deque([(start_idx, 0)])

        while queue:
            current, depth = queue.popleft()
            if current == target_idx:
                path: list[int] = []
                node: int | None = current
                while node is not None:
                    path.append(node)
                    node = parent[node]
                return list(reversed(path))
            if depth >= max_depth:
                continue
            for neighbor in self.get_s_neighbors(current, s):
                if neighbor in visited:
                    continue
                if (current, neighbor) in excluded_edges:
                    continue
                visited.add(neighbor)
                parent[neighbor] = current
                queue.append((neighbor, depth + 1))
        return None

    # ── Hub Nodes ──────────────────────────────────────────────────────

    def hub_nodes(self, min_degree: int = 3) -> list[tuple[str, int]]:
        """Find hub nodes (entities appearing in >= min_degree hyperedges)."""
        hubs = [
            (eid, len(indices))
            for eid, indices in self._entity_index.items()
            if len(indices) >= min_degree
        ]
        return sorted(hubs, key=lambda x: x[1], reverse=True)

    def average_hyperedge_size(self) -> float:
        if not self._hyperedges:
            return 0.0
        return sum(he.cardinality for he in self._hyperedges) / len(self._hyperedges)

    # ── 2-Morphism Chains ──────────────────────────────────────────────

    def find_morphism_chain(
        self,
        start_he_id: str,
        max_depth: int = 20,
    ) -> list[TwoMorphism]:
        """Follow 2-morphism links from a starting hyperedge.

        Returns the chain of morphisms: A → B → C → ...
        Used for: legal precedent chains, drug interaction cascades,
        filing amendment histories.
        """
        chain: list[TwoMorphism] = []
        visited: set[str] = {start_he_id}
        current_id = start_he_id

        for _ in range(max_depth):
            morphisms = self._morphism_index.get(current_id, [])
            # Follow outgoing morphisms (source = current)
            outgoing = [m for m in morphisms if m.source_hyperedge_id == current_id]
            if not outgoing:
                break
            # Take the first unvisited target
            found = False
            for m in outgoing:
                if m.target_hyperedge_id not in visited:
                    chain.append(m)
                    visited.add(m.target_hyperedge_id)
                    current_id = m.target_hyperedge_id
                    found = True
                    break
            if not found:
                break

        return chain

    # ── Full Benchmark ─────────────────────────────────────────────────

    def run_benchmark(self, name: str) -> BenchmarkResult:
        """Run the full benchmark suite and return structured results."""
        result = BenchmarkResult(name=name)
        total_start = time.perf_counter()

        result.entity_count = self.entity_count
        result.hyperedge_count = len(self._hyperedges)
        result.two_morphism_count = len(self._two_morphisms)

        # Noise reduction: s=1 vs s=2
        t0 = time.perf_counter()
        result.connections_s1 = self.count_total_connections(s=1)
        result.connections_s2 = self.count_total_connections(s=2)
        result.s_adjacency_time = time.perf_counter() - t0

        if result.connections_s1 > 0:
            result.noise_reduction_pct = (
                (1 - result.connections_s2 / result.connections_s1) * 100
            )

        # Component discovery
        t0 = time.perf_counter()
        result.component_count_s1 = len(self.find_s_connected_components(s=1))
        result.component_count_s2 = len(self.find_s_connected_components(s=2))
        result.component_discovery_time = time.perf_counter() - t0

        components_s2 = self.find_s_connected_components(s=2)
        if components_s2:
            result.largest_component_size = max(len(c) for c in components_s2)

        # Hub nodes
        result.hub_nodes = self.hub_nodes(min_degree=3)

        result.total_time = time.perf_counter() - total_start

        logger.info("\n%s", result.summary())
        return result
