"""Benchmark 3: FDA FAERS — Multi-drug adverse event detection.

Demonstrates:
- Hyperedges capture multi-drug interactions as atomic events
- s-Adjacency finds related adverse events sharing >= 2 drugs/reactions
- Hub nodes reveal the most dangerous drugs (appear in most events)
- Binary graphs CANNOT model 3-drug interactions without information loss

The killer demo query:
  "Patient on warfarin + aspirin + metformin — what adverse events are
   structurally connected?"
  → s=2 traversal finds all events sharing any 2 of these entities
  → reveals GI bleeding risk from warfarin+aspirin combo
  → reveals hypoglycemia risk from metformin in bleeding context

Run:
    python -m fda_faers.benchmark [--data-dir PATH] [--use-sample] [--limit N]
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from pathlib import Path

from core.engine import BenchmarkResult, HypergraphTraversal
from fda_faers.ingest import ingest_faers, ingest_sample

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

RESULTS_DIR = Path(__file__).parent / "results"


def run_benchmark(
    data_dir: Path | None = None,
    use_sample: bool = False,
    limit: int = 0,
) -> BenchmarkResult:
    """Run the full FDA FAERS benchmark."""

    print("=" * 70)
    print("BENCHMARK 3: FDA FAERS — Multi-Drug Adverse Event Detection")
    print("=" * 70)
    print()

    # ── Ingest ─────────────────────────────────────────────────────────
    t0 = time.perf_counter()
    if use_sample or data_dir is None:
        hyperedges = ingest_sample()
        source = "sample (curated 20 events)"
    else:
        hyperedges = ingest_faers(data_dir, limit)
        source = f"FAERS bulk (limit={limit})" if limit else "FAERS bulk (all)"
    ingest_time = time.perf_counter() - t0

    print(f"Source: {source}")
    print(f"Adverse events (hyperedges): {len(hyperedges)}")
    print(f"Ingest time: {ingest_time:.3f}s")
    print()

    # ── Load into engine ───────────────────────────────────────────────
    t0 = time.perf_counter()
    engine = HypergraphTraversal(hyperedges)
    index_time = time.perf_counter() - t0

    print(f"Unique entities: {engine.entity_count:,}")
    print(f"Avg participants per event: {engine.average_hyperedge_size():.1f}")
    print()

    # ── Run standard benchmark ─────────────────────────────────────────
    result = engine.run_benchmark("FDA FAERS Adverse Events")
    result.ingest_time = ingest_time
    result.index_build_time = index_time

    # ── FAERS-specific: Drug interaction analysis ──────────────────────
    print()
    print("--- Drug Interaction Analysis ---")
    print()

    # Hub drugs (appear in most events)
    hub_drugs = [
        (eid, deg) for eid, deg in engine.hub_nodes(min_degree=2)
        if eid.startswith("drug:")
    ]
    print(f"Most dangerous drugs (appear in >= 2 events):")
    for eid, degree in hub_drugs[:15]:
        drug_name = eid.replace("drug:", "").upper()
        print(f"  {drug_name}: {degree} adverse events")

    # Hub reactions
    print()
    hub_reactions = [
        (eid, deg) for eid, deg in engine.hub_nodes(min_degree=2)
        if eid.startswith("reaction:")
    ]
    print(f"Most common adverse reactions:")
    for eid, degree in hub_reactions[:10]:
        reaction_name = eid.replace("reaction:", "").replace("-", " ").upper()
        print(f"  {reaction_name}: {degree} events")

    # ── The killer query: warfarin + aspirin + metformin ───────────────
    print()
    print("--- Killer Query: Warfarin + Aspirin + Metformin Interactions ---")
    print()

    # Find events containing warfarin
    warfarin_events = []
    for i, he in enumerate(hyperedges):
        eids = he.entity_ids
        if "drug:warfarin" in eids:
            warfarin_events.append(i)

    if warfarin_events:
        print(f"Events involving warfarin: {len(warfarin_events)}")

        # From the first warfarin event, find s=2 neighbors
        start_idx = warfarin_events[0]
        start_he = hyperedges[start_idx]
        print(f"Starting from: {start_he.hyperedge_id}")
        print(f"  Participants: {', '.join(p.attributes.get('name', p.entity_id) for p in start_he.participants)}")

        neighbors = engine.get_s_neighbors(start_idx, s=2)
        print(f"\ns=2 connected events (share >= 2 entities with this event): {len(neighbors)}")
        for n_idx in neighbors:
            n_he = hyperedges[n_idx]
            shared = start_he.entity_ids & n_he.entity_ids
            drugs_in_common = [e for e in shared if e.startswith("drug:")]
            reactions_in_common = [e for e in shared if e.startswith("reaction:")]
            print(f"  {n_he.hyperedge_id}:")
            print(f"    Shared drugs: {', '.join(d.replace('drug:', '').upper() for d in drugs_in_common)}")
            print(f"    Shared reactions: {', '.join(r.replace('reaction:', '').replace('-', ' ').upper() for r in reactions_in_common)}")
            print(f"    All participants: {', '.join(p.attributes.get('name', p.entity_id) for p in n_he.participants)}")

        # s=1 comparison (noisy)
        neighbors_s1 = engine.get_s_neighbors(start_idx, s=1)
        print(f"\ns=1 connected events (share >= 1 entity): {len(neighbors_s1)}")
        print(f"s=2 connected events (share >= 2 entities): {len(neighbors)}")
        if neighbors_s1:
            noise = (1 - len(neighbors) / len(neighbors_s1)) * 100 if neighbors_s1 else 0
            print(f"Noise reduction: {noise:.0f}% fewer false connections")

    # ── Component analysis ─────────────────────────────────────────────
    print()
    print("--- Interaction Clusters ---")
    components_s2 = engine.find_s_connected_components(s=2)
    print(f"Distinct drug interaction clusters (s=2): {len(components_s2)}")
    for i, comp in enumerate(components_s2):
        # Collect unique drugs in this cluster
        cluster_drugs: set[str] = set()
        cluster_reactions: set[str] = set()
        for idx in comp:
            for p in hyperedges[idx].participants:
                if p.entity_type == "drug":
                    cluster_drugs.add(p.attributes.get("name", p.entity_id))
                elif p.entity_type == "reaction":
                    cluster_reactions.add(p.attributes.get("name", p.entity_id))

        print(f"\n  Cluster {i + 1} ({len(comp)} events):")
        print(f"    Drugs: {', '.join(sorted(cluster_drugs))}")
        print(f"    Reactions: {', '.join(sorted(cluster_reactions)[:5])}"
              + ("..." if len(cluster_reactions) > 5 else ""))

    # ── Save results ───────────────────────────────────────────────────
    RESULTS_DIR.mkdir(exist_ok=True)

    results_data = {
        "benchmark": result.name,
        "source": source,
        "event_count": len(hyperedges),
        "entity_count": result.entity_count,
        "connections_s1": result.connections_s1,
        "connections_s2": result.connections_s2,
        "noise_reduction_pct": round(result.noise_reduction_pct, 2),
        "component_count_s2": result.component_count_s2,
        "hub_drugs": hub_drugs[:10],
        "hub_reactions": hub_reactions[:10],
        "warfarin_events": len(warfarin_events) if warfarin_events else 0,
        "total_time_s": round(result.total_time, 3),
    }

    with open(RESULTS_DIR / "benchmark_results.json", "w") as f:
        json.dump(results_data, f, indent=2, default=str)

    with open(RESULTS_DIR / "benchmark_summary.txt", "w") as f:
        f.write(result.summary())

    print(f"\nResults saved to {RESULTS_DIR}/")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="FDA FAERS benchmark")
    parser.add_argument("--data-dir", type=Path, default=Path(__file__).parent / "data")
    parser.add_argument("--use-sample", action="store_true",
                        help="Use curated sample dataset instead of FAERS bulk")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    run_benchmark(args.data_dir, args.use_sample, args.limit)


if __name__ == "__main__":
    main()
