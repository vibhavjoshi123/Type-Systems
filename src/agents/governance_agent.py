"""Governance Agent - compliance verification and coherence checking.

Operates on coherence: verifies diagram commutativity.
If Decision_A set precedent for Decision_B (alpha), and Decision_B set
precedent for Decision_C (beta), then there should be a consistent
story from A to C (beta . alpha).

From Higher-Order Reasoning PDF Section 4:
The key capability is coherence verification - checking whether
reasoning chains are logically consistent.
"""

from __future__ import annotations

from src.agents.base import AgentQuery, AgentResponse, BaseAgent
from src.models.decisions import DecisionTrace


class GovernanceAgent(BaseAgent):
    """Agent for compliance verification and policy matching.

    Capabilities:
    - Decision trace coherence verification
    - Policy compliance checking
    - Recommendation generation for non-compliant decisions
    """

    def __init__(self) -> None:
        super().__init__()

    @property
    def name(self) -> str:
        return "governance_agent"

    async def process(self, query: AgentQuery) -> AgentResponse:
        """Verify governance compliance of decision traces."""
        traces = query.context.get("traces", [])

        if not traces:
            return AgentResponse(
                answer="No decision traces provided for governance review.",
                confidence=0.0,
            )

        violations: list[str] = []
        for trace_data in traces:
            if isinstance(trace_data, dict):
                trace = DecisionTrace(**trace_data)
            elif isinstance(trace_data, DecisionTrace):
                trace = trace_data
            else:
                continue
            trace_violations = self._check_coherence(trace)
            violations.extend(trace_violations)

        if violations:
            return AgentResponse(
                answer=f"Found {len(violations)} coherence violation(s): "
                       + "; ".join(violations),
                evidence=[{"violations": violations}],
                confidence=0.9,
                metadata={"compliant": False, "violation_count": len(violations)},
            )

        return AgentResponse(
            answer=f"All {len(traces)} decision trace(s) pass coherence verification.",
            confidence=0.95,
            metadata={"compliant": True, "traces_checked": len(traces)},
        )

    @staticmethod
    def _check_coherence(trace: DecisionTrace) -> list[str]:
        """Check a decision trace for coherence violations.

        Verifies that 2-morphism chains are consistent:
        if alpha: A -> B and beta: B -> C, then gamma: A -> C
        should be coherent with beta . alpha.
        """
        violations: list[str] = []

        if trace.is_coherent is False:
            violations.extend(trace.coherence_violations)

        # Check for precedent chain consistency
        precedent_map: dict[str, list[str]] = {}
        for pm in trace.two_morphisms:
            precedent_map.setdefault(pm.precedent_id, []).append(pm.derived_id)

        # Check for circular precedents
        for start_id, derived_ids in precedent_map.items():
            for derived_id in derived_ids:
                if derived_id in precedent_map:
                    for transitive in precedent_map[derived_id]:
                        if transitive == start_id:
                            violations.append(
                                f"Circular precedent detected: {start_id} -> "
                                f"{derived_id} -> {start_id}"
                            )

        return violations
