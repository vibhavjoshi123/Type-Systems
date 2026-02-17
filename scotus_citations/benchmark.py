"""Benchmark 2: SCOTUS Citations — Legal precedent chains via 2-morphisms.

Demonstrates:
- 2-Morphisms map real legal citation relationships
- Precedent chains are traversable paths through the hypergraph
- Overrulings and distinctions are typed meta-relations
- s-Adjacency connects cases sharing justices + legal topics

Run:
    python -m scotus_citations.benchmark [--data-dir PATH] [--use-landmark]
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from pathlib import Path

from core.engine import BenchmarkResult, HypergraphTraversal
from scotus_citations.ingest import ingest_landmark, ingest_scdb

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

RESULTS_DIR = Path(__file__).parent / "results"


def run_benchmark(
    data_dir: Path | None = None,
    use_landmark: bool = False,
    limit: int = 0,
) -> BenchmarkResult:
    """Run the full SCOTUS Citations benchmark."""

    print("=" * 70)
    print("BENCHMARK 2: SCOTUS Citations — Legal Precedent Chains")
    print("=" * 70)
    print()

    # ── Ingest ─────────────────────────────────────────────────────────
    t0 = time.perf_counter()
    if use_landmark or data_dir is None:
        hyperedges, morphisms = ingest_landmark()
        source = "landmark (curated)"
    else:
        hyperedges, morphisms = ingest_scdb(data_dir, limit)
        source = "SCDB (bulk)"
    ingest_time = time.perf_counter() - t0

    print(f"Source: {source}")
    print(f"Cases (hyperedges): {len(hyperedges)}")
    print(f"Citations (2-morphisms): {len(morphisms)}")
    print(f"Ingest time: {ingest_time:.3f}s")
    print()

    # ── Load into engine ───────────────────────────────────────────────
    t0 = time.perf_counter()
    engine = HypergraphTraversal(hyperedges)
    engine.add_two_morphisms(morphisms)
    index_time = time.perf_counter() - t0

    # ── Run standard benchmark ─────────────────────────────────────────
    result = engine.run_benchmark("SCOTUS Citations")
    result.ingest_time = ingest_time
    result.index_build_time = index_time
    result.two_morphism_count = len(morphisms)

    # ── SCOTUS-specific: 2-Morphism chain analysis ─────────────────────
    print()
    print("--- 2-Morphism Chain Analysis ---")
    print()

    # Find the longest precedent chains
    he_id_to_idx = {he.hyperedge_id: i for i, he in enumerate(hyperedges)}

    # Trace from Marbury v. Madison (the root of judicial review)
    marbury_chain = engine.find_morphism_chain("marbury-v-madison-1803")
    if marbury_chain:
        print(f"Precedent chain from Marbury v. Madison: {len(marbury_chain)} links")
        current = "marbury-v-madison-1803"
        print(f"  {current}")
        for m in marbury_chain:
            arrow = "OVERRULED BY" if m.morphism_type == "override" else "→"
            print(f"    {arrow} {m.target_hyperedge_id}")
            if m.rationale:
                print(f"       '{m.rationale[:80]}...'")
            current = m.target_hyperedge_id

    # Trace the privacy/abortion chain: Griswold → Roe → Casey → Dobbs
    privacy_chain = engine.find_morphism_chain("griswold-v-connecticut-1965")
    if privacy_chain:
        print(f"\nPrivacy rights chain from Griswold: {len(privacy_chain)} links")
        current = "griswold-v-connecticut-1965"
        print(f"  {current}")
        for m in privacy_chain:
            arrow = "OVERRULED BY" if m.morphism_type == "override" else "→"
            print(f"    {arrow} {m.target_hyperedge_id}")
            if m.rationale:
                print(f"       '{m.rationale[:80]}...'")

    # Trace Chevron deference → Loper Bright
    chevron_chain = engine.find_morphism_chain("chevron-v-nrdc-1984")
    if chevron_chain:
        print(f"\nAdmin law chain from Chevron: {len(chevron_chain)} links")
        current = "chevron-v-nrdc-1984"
        print(f"  {current}")
        for m in chevron_chain:
            arrow = "OVERRULED BY" if m.morphism_type == "override" else "→"
            print(f"    {arrow} {m.target_hyperedge_id}")
            if m.rationale:
                print(f"       '{m.rationale[:80]}...'")

    # ── s-Adjacency analysis (cases sharing justices + topics) ─────────
    print()
    print("--- s-Adjacency Analysis (shared justices + topics) ---")
    print()

    components_s2 = engine.find_s_connected_components(s=2)
    print(f"s=2 connected components: {len(components_s2)}")
    for i, comp in enumerate(components_s2):
        case_names = []
        for idx in comp:
            name = hyperedges[idx].attributes.get("name", hyperedges[idx].hyperedge_id)
            case_names.append(str(name))
        print(f"  Component {i + 1} ({len(comp)} cases): {', '.join(case_names[:5])}"
              + ("..." if len(case_names) > 5 else ""))

    # Hub justices (appear in most cases)
    print()
    hubs = engine.hub_nodes(min_degree=2)
    print(f"Hub entities (appear in >= 2 cases): {len(hubs)}")
    for eid, degree in hubs[:15]:
        print(f"  {eid}: {degree} cases")

    # ── Overruling analysis ────────────────────────────────────────────
    print()
    print("--- Overruling Analysis ---")
    overrulings = [m for m in morphisms if m.morphism_type == "override"]
    precedents = [m for m in morphisms if m.morphism_type == "precedent"]
    exceptions = [m for m in morphisms if m.morphism_type == "exception"]

    print(f"  Precedent citations: {len(precedents)}")
    print(f"  Overrulings: {len(overrulings)}")
    print(f"  Distinctions: {len(exceptions)}")

    for m in overrulings:
        print(f"  {m.source_hyperedge_id} → OVERRULED BY → {m.target_hyperedge_id}")
        if m.rationale:
            print(f"    '{m.rationale[:100]}'")

    # ── Save results ───────────────────────────────────────────────────
    RESULTS_DIR.mkdir(exist_ok=True)

    results_data = {
        "benchmark": result.name,
        "source": source,
        "case_count": len(hyperedges),
        "citation_count": len(morphisms),
        "precedents": len(precedents),
        "overrulings": len(overrulings),
        "distinctions": len(exceptions),
        "entity_count": result.entity_count,
        "connections_s1": result.connections_s1,
        "connections_s2": result.connections_s2,
        "noise_reduction_pct": round(result.noise_reduction_pct, 2),
        "component_count_s2": result.component_count_s2,
        "hub_nodes_top10": result.hub_nodes[:10],
        "marbury_chain_length": len(marbury_chain) if marbury_chain else 0,
        "privacy_chain_length": len(privacy_chain) if privacy_chain else 0,
        "total_time_s": round(result.total_time, 3),
    }

    with open(RESULTS_DIR / "benchmark_results.json", "w") as f:
        json.dump(results_data, f, indent=2, default=str)

    with open(RESULTS_DIR / "benchmark_summary.txt", "w") as f:
        f.write(result.summary())
        f.write("\n\n--- 2-Morphism Chains ---\n")
        if marbury_chain:
            f.write(f"Marbury chain: {len(marbury_chain)} links\n")
        if privacy_chain:
            f.write(f"Privacy chain: {len(privacy_chain)} links\n")

    print(f"\nResults saved to {RESULTS_DIR}/")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="SCOTUS Citations benchmark")
    parser.add_argument("--data-dir", type=Path, default=Path(__file__).parent / "data")
    parser.add_argument("--use-landmark", action="store_true",
                        help="Use curated landmark dataset instead of SCDB bulk")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    run_benchmark(args.data_dir, args.use_landmark, args.limit)


if __name__ == "__main__":
    main()
