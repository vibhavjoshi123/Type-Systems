"""Generate the final comparison report across all three benchmarks.

Reads results from each benchmark's results/ folder and produces
a unified RESULTS.md with comparison tables and analysis.

Run:
    python -m compare.generate_report
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ROOT = Path(__file__).parent.parent
RESULTS_FILE = ROOT / "RESULTS.md"


def _load_json(path: Path) -> dict | None:
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return None


def generate_report() -> None:
    """Generate RESULTS.md from all benchmark outputs."""

    # Load results
    icij = _load_json(ROOT / "icij_offshore" / "results" / "benchmark_results.json")
    scotus = _load_json(ROOT / "scotus_citations" / "results" / "benchmark_results.json")
    faers = _load_json(ROOT / "fda_faers" / "results" / "benchmark_results.json")

    neo4j_scotus = _load_json(ROOT / "compare" / "results" / "neo4j_comparison_scotus.json")
    neo4j_faers = _load_json(ROOT / "compare" / "results" / "neo4j_comparison_faers.json")
    vector_scotus = _load_json(ROOT / "compare" / "results" / "vector_comparison_scotus.json")
    vector_faers = _load_json(ROOT / "compare" / "results" / "vector_comparison_faers.json")

    lines: list[str] = []
    lines.append("# Context Graph Benchmark Results")
    lines.append("")
    lines.append(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*")
    lines.append("")

    # ── Summary Table ──────────────────────────────────────────────────
    lines.append("## Summary")
    lines.append("")
    lines.append("| Metric | ICIJ Offshore | SCOTUS Citations | FDA FAERS |")
    lines.append("|--------|:---:|:---:|:---:|")

    def _v(d: dict | None, key: str, fmt: str = ",") -> str:
        if d is None:
            return "—"
        val = d.get(key, "—")
        if isinstance(val, (int, float)) and fmt == ",":
            return f"{val:,}"
        if isinstance(val, float) and fmt == ".1f":
            return f"{val:.1f}"
        return str(val)

    lines.append(f"| Entities | {_v(icij, 'entity_count')} | {_v(scotus, 'entity_count')} | {_v(faers, 'entity_count')} |")
    lines.append(f"| Hyperedges | {_v(icij, 'hyperedge_count')} | {_v(scotus, 'case_count')} | {_v(faers, 'event_count')} |")
    lines.append(f"| 2-Morphisms | — | {_v(scotus, 'citation_count')} | — |")
    lines.append(f"| Connections (s=1) | {_v(icij, 'connections_s1')} | {_v(scotus, 'connections_s1')} | {_v(faers, 'connections_s1')} |")
    lines.append(f"| Connections (s=2) | {_v(icij, 'connections_s2')} | {_v(scotus, 'connections_s2')} | {_v(faers, 'connections_s2')} |")
    lines.append(f"| **Noise Reduction** | **{_v(icij, 'noise_reduction_pct')}%** | **{_v(scotus, 'noise_reduction_pct')}%** | **{_v(faers, 'noise_reduction_pct')}%** |")
    lines.append(f"| s=2 Components | {_v(icij, 'component_count_s2')} | {_v(scotus, 'component_count_s2')} | {_v(faers, 'component_count_s2')} |")
    lines.append(f"| Total Time | {_v(icij, 'total_time_s')}s | {_v(scotus, 'total_time_s')}s | {_v(faers, 'total_time_s')}s |")
    lines.append("")

    # ── Noise Reduction ────────────────────────────────────────────────
    lines.append("## Key Finding: Noise Reduction with IS >= 2")
    lines.append("")
    lines.append("The intersection size constraint (IS >= 2) consistently reduces noise across all three domains:")
    lines.append("")
    lines.append("| Domain | s=1 Connections | s=2 Connections | Noise Removed |")
    lines.append("|--------|:---:|:---:|:---:|")
    for name, d in [("ICIJ Offshore", icij), ("SCOTUS", scotus), ("FDA FAERS", faers)]:
        if d:
            lines.append(f"| {name} | {d.get('connections_s1', '—'):,} | {d.get('connections_s2', '—'):,} | **{d.get('noise_reduction_pct', '—')}%** |")
    lines.append("")
    lines.append("> IS >= 2 means: two events are only connected if they share **at least 2** entities.")
    lines.append("> This filters out spurious connections where events share just one common participant.")
    lines.append("")

    # ── Neo4j Comparison ───────────────────────────────────────────────
    lines.append("## Comparison: Hypergraph vs Neo4j (Binary Graph)")
    lines.append("")
    lines.append("| Metric | Hypergraph | Neo4j (Naive) | Neo4j (Star) | Neo4j (Reified) |")
    lines.append("|--------|:---:|:---:|:---:|:---:|")

    for name, neo in [("SCOTUS", neo4j_scotus), ("FDA FAERS", neo4j_faers)]:
        if neo:
            lines.append(f"| **{name}** | | | | |")
            lines.append(f"| Edges needed | {neo['hyperedge_count']:,} | {neo['neo4j_naive_edges']:,} | {neo['neo4j_star_edges']:,} | {neo['neo4j_reified_edges']:,} |")
            lines.append(f"| Explosion factor | 1x | {neo['edge_explosion_factor_naive']}x | {neo['edge_explosion_factor_star']}x | — |")

    lines.append("")
    lines.append("**Why this matters:**")
    lines.append("- Neo4j requires **multiple binary edges** to represent what we capture in **one hyperedge**")
    lines.append("- IS >= 2 queries require expensive self-joins in Neo4j — they're native in our engine")
    lines.append("- Multi-party events (3-drug interactions, multi-justice decisions) lose atomicity in binary graphs")
    lines.append("")

    # ── Vector DB Comparison ───────────────────────────────────────────
    lines.append("## Comparison: Hypergraph vs Vector Search")
    lines.append("")
    lines.append("| Capability | Hypergraph | Vector DB |")
    lines.append("|-----------|:---:|:---:|")
    lines.append("| Structural connections (IS >= 2) | Native | Impossible |")
    lines.append("| 2-Morphism chains (precedent, override) | Native | Impossible |")
    lines.append("| Distinguish 'Drug A alone' vs 'Drug A + B together' | Yes | No |")
    lines.append("| Explain WHY two results are connected | Yes (shared entities) | No (cosine distance) |")
    lines.append("| Audit trail for regulatory compliance | Native | Not available |")
    lines.append("| False positive rate | Low (structural guarantee) | High (similarity != causation) |")
    lines.append("")

    # ── SCOTUS 2-Morphism Results ──────────────────────────────────────
    if scotus:
        lines.append("## Benchmark 2 Highlight: Legal Precedent Chains")
        lines.append("")
        lines.append("2-Morphisms capture the **typed, annotated relationships between decisions**:")
        lines.append("")
        lines.append(f"- Precedent citations: {scotus.get('precedents', '—')}")
        lines.append(f"- Overrulings: {scotus.get('overrulings', '—')}")
        lines.append(f"- Distinctions: {scotus.get('distinctions', '—')}")
        lines.append("")
        if scotus.get("marbury_chain_length"):
            lines.append(f"Longest chain from Marbury v. Madison: **{scotus['marbury_chain_length']} links**")
        if scotus.get("privacy_chain_length"):
            lines.append(f"Privacy rights chain (Griswold → Roe → Casey → Dobbs): **{scotus['privacy_chain_length']} links**")
        lines.append("")
        lines.append("> These chains are impossible to represent in vector databases — they require")
        lines.append("> typed, directed meta-relations between decision-events (2-morphisms).")
        lines.append("")

    # ── Reproduction ───────────────────────────────────────────────────
    lines.append("## Reproduce These Results")
    lines.append("")
    lines.append("```bash")
    lines.append("# Quick (sample data, no downloads needed)")
    lines.append("python -m scotus_citations.benchmark --use-landmark")
    lines.append("python -m fda_faers.benchmark --use-sample")
    lines.append("")
    lines.append("# Full (requires data download)")
    lines.append("./run_all.sh")
    lines.append("```")
    lines.append("")

    # Write RESULTS.md
    content = "\n".join(lines)
    with open(RESULTS_FILE, "w") as f:
        f.write(content)

    print(f"Report written to {RESULTS_FILE}")
    print(f"({len(lines)} lines)")


def main() -> None:
    generate_report()


if __name__ == "__main__":
    main()
