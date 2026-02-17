"""Benchmark 1: ICIJ Offshore Leaks — Shell company cluster detection.

Demonstrates:
- s-Adjacency finds coordinated shell company networks
- IS >= 2 noise reduction on real ownership data
- Hub node detection reveals key officers controlling many entities
- Component discovery finds isolated clusters

Run:
    python -m icij_offshore.benchmark [--limit N] [--data-dir PATH]
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

from core.engine import BenchmarkResult, HypergraphTraversal
from icij_offshore.ingest import ingest

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

RESULTS_DIR = Path(__file__).parent / "results"


def run_benchmark(
    data_dir: Path,
    entity_limit: int = 0,
    relationship_limit: int = 0,
) -> BenchmarkResult:
    """Run the full ICIJ Offshore Leaks benchmark."""

    print("=" * 70)
    print("BENCHMARK 1: ICIJ Offshore Leaks — Shell Company Clusters")
    print("=" * 70)
    print()

    # ── Ingest ─────────────────────────────────────────────────────────
    t0 = time.perf_counter()
    hyperedges = ingest(data_dir, entity_limit, relationship_limit)
    ingest_time = time.perf_counter() - t0

    if not hyperedges:
        print("ERROR: No hyperedges built. Did you run download.sh first?")
        sys.exit(1)

    # ── Load into engine ───────────────────────────────────────────────
    t0 = time.perf_counter()
    engine = HypergraphTraversal(hyperedges)
    index_time = time.perf_counter() - t0

    print(f"Loaded {len(hyperedges):,} hyperedges ({engine.entity_count:,} unique entities)")
    print(f"  Ingest time:  {ingest_time:.3f}s")
    print(f"  Index build:  {index_time:.3f}s")
    print(f"  Avg edge size: {engine.average_hyperedge_size():.1f} participants")
    print()

    # ── Run benchmark ──────────────────────────────────────────────────
    result = engine.run_benchmark("ICIJ Offshore Leaks")
    result.ingest_time = ingest_time
    result.index_build_time = index_time

    # ── Additional ICIJ-specific analysis ──────────────────────────────
    print()
    print("--- ICIJ-Specific Analysis ---")
    print()

    # Top hub officers (people controlling the most entities)
    hubs = engine.hub_nodes(min_degree=5)
    print(f"Officers controlling >= 5 entities: {len(hubs)}")
    for entity_id, degree in hubs[:20]:
        print(f"  {entity_id}: {degree} entities")

    # Find the largest s=2 component (coordinated network)
    components_s2 = engine.find_s_connected_components(s=2)
    if components_s2:
        largest = max(components_s2, key=len)
        print(f"\nLargest coordinated network (s=2): {len(largest)} entities")
        print(f"Total s=2 clusters: {len(components_s2)}")

        # Show what entities are in the largest cluster
        print(f"\nSample from largest cluster (first 10 hyperedges):")
        for idx in largest[:10]:
            he = hyperedges[idx]
            names = [
                p.attributes.get("name", p.entity_id)[:40]
                for p in he.participants
            ]
            print(f"  {he.hyperedge_id}: {', '.join(names)}")

    # ── Path finding demo ──────────────────────────────────────────────
    if len(hyperedges) >= 2 and components_s2:
        largest = max(components_s2, key=len)
        if len(largest) >= 2:
            print(f"\nPath finding: {largest[0]} → {largest[-1]} (s=2)")
            t0 = time.perf_counter()
            paths = engine.yen_k_shortest_paths(
                largest[0], largest[-1], k=3, s=2,
            )
            result.path_finding_time = time.perf_counter() - t0
            result.paths_found = paths
            print(f"  Found {len(paths)} paths in {result.path_finding_time:.3f}s")
            for i, path in enumerate(paths):
                print(f"  Path {i + 1}: {' → '.join(str(p) for p in path)} (length {len(path)})")

    print()
    print(result.summary())

    # ── Save results ───────────────────────────────────────────────────
    RESULTS_DIR.mkdir(exist_ok=True)

    results_file = RESULTS_DIR / "benchmark_results.json"
    results_data = {
        "benchmark": result.name,
        "entity_count": result.entity_count,
        "hyperedge_count": result.hyperedge_count,
        "connections_s1": result.connections_s1,
        "connections_s2": result.connections_s2,
        "noise_reduction_pct": round(result.noise_reduction_pct, 2),
        "component_count_s1": result.component_count_s1,
        "component_count_s2": result.component_count_s2,
        "largest_component_size": result.largest_component_size,
        "hub_nodes_top10": result.hub_nodes[:10],
        "ingest_time_s": round(result.ingest_time, 3),
        "index_build_time_s": round(result.index_build_time, 3),
        "s_adjacency_time_s": round(result.s_adjacency_time, 3),
        "component_discovery_time_s": round(result.component_discovery_time, 3),
        "path_finding_time_s": round(result.path_finding_time, 3),
        "total_time_s": round(result.total_time, 3),
    }

    with open(results_file, "w") as f:
        json.dump(results_data, f, indent=2, default=str)

    summary_file = RESULTS_DIR / "benchmark_summary.txt"
    with open(summary_file, "w") as f:
        f.write(result.summary())

    print(f"\nResults saved to {RESULTS_DIR}/")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="ICIJ Offshore Leaks benchmark",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path(__file__).parent / "data",
        help="Path to downloaded ICIJ CSV files",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limit entities per type (0 = all, use 1000-10000 for quick test)",
    )
    parser.add_argument(
        "--rel-limit",
        type=int,
        default=0,
        help="Limit relationships (0 = all)",
    )
    args = parser.parse_args()

    run_benchmark(args.data_dir, args.limit, args.rel_limit)


if __name__ == "__main__":
    main()
