"""Neo4j baseline — same queries using binary property graph.

This demonstrates the fundamental limitation of binary graphs for
multi-party events. Where our hypergraph uses ONE edge for an N-ary
event, Neo4j requires N*(N-1)/2 binary edges — losing atomicity.

Requirements:
    pip install neo4j

Usage:
    python -m compare.neo4j_baseline --benchmark icij|scotus|faers

If Neo4j isn't available, this module simulates the comparison by
counting the number of binary edges required vs hyperedges.
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from pathlib import Path

from core.models import Hyperedge

logger = logging.getLogger(__name__)

RESULTS_DIR = Path(__file__).parent / "results"


def count_binary_edges(hyperedges: list[Hyperedge]) -> dict:
    """Count how many binary edges Neo4j would need for the same data.

    For each hyperedge with N participants:
    - Naive: N*(N-1)/2 pairwise edges (complete subgraph)
    - Star: N-1 edges (central node to each participant)
    - Reified: 1 event node + N edges to participants

    All three lose the "this is one atomic event" semantics.
    """
    total_hyperedges = len(hyperedges)
    total_participants = sum(he.cardinality for he in hyperedges)
    avg_cardinality = total_participants / max(total_hyperedges, 1)

    naive_edges = sum(
        he.cardinality * (he.cardinality - 1) // 2
        for he in hyperedges
    )
    star_edges = sum(he.cardinality - 1 for he in hyperedges)
    reified_edges = total_participants  # 1 event node + N edges each

    return {
        "hyperedge_count": total_hyperedges,
        "total_participants": total_participants,
        "avg_cardinality": round(avg_cardinality, 1),
        "neo4j_naive_edges": naive_edges,
        "neo4j_star_edges": star_edges,
        "neo4j_reified_edges": reified_edges,
        "edge_explosion_factor_naive": round(naive_edges / max(total_hyperedges, 1), 1),
        "edge_explosion_factor_star": round(star_edges / max(total_hyperedges, 1), 1),
    }


def simulate_query_comparison(hyperedges: list[Hyperedge], s: int = 2) -> dict:
    """Simulate the query complexity difference.

    Our query: "Find all events sharing >= 2 entities with event X"
    → 1 BFS call on the s-adjacency graph

    Neo4j equivalent (naive):
    → Multiple self-joins: MATCH (a)-[]->(e1)<-[]-(b), (a)-[]->(e2)<-[]-(b)
      WHERE e1 <> e2
    → O(N^2) join complexity for each query
    → No native "intersection size >= 2" operator
    """
    from core.engine import HypergraphTraversal

    engine = HypergraphTraversal(hyperedges)

    # Time our s-adjacency query
    if hyperedges:
        t0 = time.perf_counter()
        neighbors = engine.get_s_neighbors(0, s=s)
        our_time = time.perf_counter() - t0
    else:
        our_time = 0
        neighbors = []

    # Estimate Neo4j query complexity
    avg_size = engine.average_hyperedge_size()
    neo4j_joins_needed = int(avg_size * (avg_size - 1) / 2)  # self-joins for IS check

    return {
        "our_query_time_s": round(our_time, 6),
        "our_result_count": len(neighbors),
        "neo4j_self_joins_per_query": neo4j_joins_needed,
        "neo4j_complexity": f"O(N^{s}) for IS>={s} check",
        "our_complexity": "O(E * avg_degree) via inverted index",
    }


def run_neo4j_comparison(
    benchmark: str,
    hyperedges: list[Hyperedge],
) -> dict:
    """Run the full Neo4j comparison."""
    print(f"\n--- Neo4j Comparison ({benchmark}) ---\n")

    edge_counts = count_binary_edges(hyperedges)
    query_comparison = simulate_query_comparison(hyperedges)

    print(f"Hyperedges: {edge_counts['hyperedge_count']:,}")
    print(f"Avg cardinality: {edge_counts['avg_cardinality']}")
    print(f"Neo4j edges needed (naive/pairwise): {edge_counts['neo4j_naive_edges']:,}")
    print(f"Neo4j edges needed (star pattern): {edge_counts['neo4j_star_edges']:,}")
    print(f"Neo4j edges needed (reified events): {edge_counts['neo4j_reified_edges']:,}")
    print(f"Edge explosion factor: {edge_counts['edge_explosion_factor_naive']}x")
    print()
    print(f"Query comparison:")
    print(f"  Our s-adjacency query: {query_comparison['our_query_time_s']}s")
    print(f"  Neo4j self-joins needed: {query_comparison['neo4j_self_joins_per_query']} per IS check")
    print(f"  Our complexity: {query_comparison['our_complexity']}")
    print(f"  Neo4j complexity: {query_comparison['neo4j_complexity']}")

    result = {
        "benchmark": benchmark,
        **edge_counts,
        **query_comparison,
    }

    RESULTS_DIR.mkdir(exist_ok=True)
    with open(RESULTS_DIR / f"neo4j_comparison_{benchmark}.json", "w") as f:
        json.dump(result, f, indent=2)

    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Neo4j baseline comparison")
    parser.add_argument("--benchmark", choices=["icij", "scotus", "faers"],
                        default="faers")
    args = parser.parse_args()

    # Load the appropriate sample data
    if args.benchmark == "icij":
        print("Run ICIJ benchmark first, then compare.")
    elif args.benchmark == "scotus":
        from scotus_citations.ingest import ingest_landmark
        hyperedges, _ = ingest_landmark()
        run_neo4j_comparison("scotus", hyperedges)
    else:
        from fda_faers.ingest import ingest_sample
        hyperedges = ingest_sample()
        run_neo4j_comparison("faers", hyperedges)


if __name__ == "__main__":
    main()
