"""Orchestrator Agent - unified REPL-based query routing.

All queries go through the same REPL-based routing path: the LLM writes
code that can optionally call spawn_agent() to delegate subtasks, then
synthesises results. No pre-classification into simple/standard/complex.

Falls back to a ContextAgent → ExecutiveAgent pipeline if REPL routing
fails or produces a low-confidence answer.
"""

from __future__ import annotations

import logging
from typing import Any

from src.agents.base import AgentQuery, AgentResponse, BaseAgent
from src.agents.context_agent import ContextAgent
from src.agents.executive_agent import ExecutiveAgent
from src.agents.governance_agent import GovernanceAgent
from src.agents.repl import AgentSpawner, ReplAgent, _ROUTING_PROMPT
from src.typedb.traversal import HypergraphTraversal

logger = logging.getLogger(__name__)

# Keywords that signal governance/compliance review is needed.
_GOVERNANCE_KEYWORDS = frozenset({
    "compliance", "compliant", "violation", "audit", "coherent",
    "coherence", "policy", "override", "exception", "risk",
})


class OrchestratorAgent(BaseAgent):
    """Routes every query through REPL-based emergent reasoning.

    The LLM writes code that inspects the live graph data and decides
    autonomously how to answer — directly, or by spawning focused
    sub-agents via spawn_agent(). This replaces pre-programmed
    routing logic with LLM-driven decomposition.

    GovernanceAgent is triggered when compliance-related keywords are
    detected or when decision traces are present in the context.
    """

    def __init__(
        self,
        traversal: HypergraphTraversal,
        llm: Any = None,
        entities: list[dict[str, Any]] | None = None,
        hyperedges: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__()
        self._traversal = traversal
        self._llm = llm
        self._entities = entities or []
        self._hyperedges = hyperedges or []

        # Create the REPL agent with live graph objects injected
        self._repl_agent = ReplAgent(llm=llm)
        self._repl_agent.load_graph_context(
            traversal=traversal,
            entities=self._entities,
            hyperedges=self._hyperedges,
        )

        # Sub-agents used in the fallback pipeline
        self._context_agent = ContextAgent(traversal)
        self._executive_agent = ExecutiveAgent(llm=llm, repl_agent=self._repl_agent)
        self._governance_agent = GovernanceAgent()

        self.register_sub_agents([
            self._context_agent,
            self._executive_agent,
            self._governance_agent,
            self._repl_agent,
        ])

    @property
    def name(self) -> str:
        return "orchestrator"

    async def process(self, query: AgentQuery) -> AgentResponse:
        """Route query through REPL-based reasoning with optional governance."""
        needs_governance = any(
            kw in query.query.lower() for kw in _GOVERNANCE_KEYWORDS
        )

        # Inject a fresh spawner so LLM code can delegate subtasks
        spawner = AgentSpawner(llm=self._llm, depth=self._delegation_depth)
        self._repl_agent.repl.inject("spawn_agent", spawner)

        # Build the routing task prompt
        routing_task = _ROUTING_PROMPT.format(
            query=query.query,
            n_entities=len(self._entities),
            n_hyperedges=len(self._hyperedges),
        )

        repl_response: AgentResponse | None = None
        if self._llm:
            try:
                repl_response = await self._repl_agent.route_with_code(routing_task)
                logger.info(
                    "REPL routing completed: confidence=%.2f, sub-agents spawned=%d",
                    repl_response.confidence,
                    len(spawner.spawn_log),
                )
            except Exception as exc:
                logger.warning("REPL routing failed, falling back: %s", exc)

        # Use REPL result if it produced a meaningful answer
        if repl_response and repl_response.confidence > 0.1:
            governance_response = None
            if needs_governance:
                governance_response = await self._run_governance(repl_response)

            metadata = dict(repl_response.metadata)
            metadata["routing"] = {
                "strategy": "repl",
                "sub_agents_spawned": len(spawner.spawn_log),
                "spawn_log": spawner.spawn_log,
            }
            if governance_response:
                metadata["governance"] = {
                    "compliant": governance_response.metadata.get("compliant"),
                    "answer": governance_response.answer,
                }

            answer = repl_response.answer
            if governance_response and governance_response.metadata.get("compliant") is False:
                answer += f"\n\n[Governance Warning] {governance_response.answer}"

            return AgentResponse(
                answer=answer,
                evidence=repl_response.evidence,
                paths_found=repl_response.paths_found,
                confidence=repl_response.confidence,
                metadata=metadata,
            )

        # Fallback: ContextAgent → ExecutiveAgent pipeline
        logger.info("REPL routing produced low confidence, falling back to pipeline")
        context_response = await self._context_agent.process(query)
        exec_query = AgentQuery(
            query=query.query,
            context={
                "paths": context_response.evidence,
                "entities": self._entities,
                "hyperedges": self._hyperedges,
                "graph_summary": context_response.answer,
            },
            intersection_size=query.intersection_size,
            max_depth=query.max_depth,
        )
        exec_response = await self._executive_agent.process(exec_query)

        governance_response = None
        if needs_governance:
            governance_response = await self._run_governance(exec_response)

        return self._build_response(
            exec_response,
            context_response,
            governance_response,
            strategy="fallback",
        )

    async def _run_governance(
        self,
        exec_response: AgentResponse,
    ) -> AgentResponse | None:
        """Run governance verification on executive reasoning output."""
        proposals = exec_response.metadata.get("two_morphism_proposals", [])
        if not proposals:
            return None

        from src.models.decisions import DecisionTrace, PrecedentChain

        trace = DecisionTrace(
            trace_id="runtime_check",
            decisions=[p.get("source_description", "") for p in proposals],
            two_morphisms=[
                PrecedentChain(
                    precedent_id=p.get("source_description", ""),
                    derived_id=p.get("target_description", ""),
                )
                for p in proposals
                if p.get("morphism_type") in ("precedent", "sequence")
            ],
        )

        gov_query = AgentQuery(
            query="Verify coherence of proposed decision traces",
            context={"traces": [trace.model_dump()]},
        )

        return await self.delegate(
            "governance_agent",
            gov_query,
            rationale="Compliance check on proposed 2-morphisms",
        )

    @staticmethod
    def _build_response(
        exec_response: AgentResponse,
        context_response: AgentResponse | None,
        governance_response: AgentResponse | None,
        strategy: str,
    ) -> AgentResponse:
        """Combine fallback pipeline responses into a single response."""
        answer = exec_response.answer

        if governance_response and governance_response.metadata.get("compliant") is False:
            answer += f"\n\n[Governance Warning] {governance_response.answer}"

        metadata = dict(exec_response.metadata)
        metadata["routing"] = {"strategy": strategy}

        if governance_response:
            metadata["governance"] = {
                "compliant": governance_response.metadata.get("compliant"),
                "answer": governance_response.answer,
            }

        paths_found = exec_response.paths_found
        if context_response and context_response.paths_found > paths_found:
            paths_found = context_response.paths_found

        return AgentResponse(
            answer=answer,
            evidence=exec_response.evidence,
            paths_found=paths_found,
            confidence=exec_response.confidence,
            metadata=metadata,
        )
