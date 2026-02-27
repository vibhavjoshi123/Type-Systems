"""Orchestrator Agent - dynamic query routing and decomposition.

Instead of running every query through the same fixed pipeline
(ContextAgent → ExecutiveAgent → store), the orchestrator inspects
the query and graph state to decide the execution strategy:

- Simple lookups skip the LLM entirely
- Multi-entity queries fan out to per-entity sub-agents
- Deep analysis queries iterate with verification
- Governance checks are triggered when decision traces are involved

This replaces the rigid 3-step pipeline with adaptive routing.
"""

from __future__ import annotations

import logging
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from src.agents.base import AgentQuery, AgentResponse, BaseAgent, DelegationRequest
from src.agents.context_agent import ContextAgent
from src.agents.executive_agent import ExecutiveAgent
from src.agents.governance_agent import GovernanceAgent
from src.agents.repl import AgentSpawner, ReplAgent, _ROUTING_PROMPT
from src.typedb.traversal import HypergraphTraversal

logger = logging.getLogger(__name__)


class QueryComplexity(StrEnum):
    """Classified complexity of an incoming query."""

    SIMPLE = "simple"       # Direct lookup, no LLM needed
    STANDARD = "standard"   # Single-pass reasoning
    COMPLEX = "complex"     # Multi-entity or deep analysis, benefits from delegation


class QueryClassification(BaseModel):
    """Result of classifying a query's complexity and routing needs."""

    complexity: QueryComplexity
    entity_mentions: list[str] = Field(default_factory=list)
    needs_governance: bool = False
    reason: str = ""


# Keywords that signal governance/compliance review is needed.
_GOVERNANCE_KEYWORDS = frozenset({
    "compliance", "compliant", "violation", "audit", "coherent",
    "coherence", "policy", "override", "exception", "risk",
})

# Keywords that signal a simple lookup rather than deep analysis.
_LOOKUP_KEYWORDS = frozenset({
    "list", "show", "get", "what is", "who is", "how many", "count",
})


class OrchestratorAgent(BaseAgent):
    """Dynamically routes queries based on complexity analysis.

    Execution strategies:
    - SIMPLE: ContextAgent only — return graph structure data directly
    - STANDARD: ContextAgent → ExecutiveAgent (iterative reasoning)
    - COMPLEX: Fan out to per-entity sub-agents, then synthesize

    Also triggers GovernanceAgent when compliance-related keywords
    are detected or when decision traces are present in the context.
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

        # Create and register the sub-agents
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

    def classify_query(self, query: AgentQuery) -> QueryClassification:
        """Analyze the query to determine routing strategy.

        Inspects the query text and available context to decide between
        simple lookup, standard reasoning, or complex fan-out.
        """
        q_lower = query.query.lower()

        # Check for governance keywords
        needs_governance = any(kw in q_lower for kw in _GOVERNANCE_KEYWORDS)

        # Count entity mentions by checking which known entity names appear
        entity_mentions: list[str] = []
        for entity in self._entities:
            ename = ""
            # Handle different entity dict formats
            for key in ("name", "entity-name", "entity_name", "ename"):
                if key in entity:
                    ename = str(entity[key])
                    break
            if ename and ename.lower() in q_lower:
                entity_mentions.append(ename)

        # Classify complexity
        if any(kw in q_lower for kw in _LOOKUP_KEYWORDS) and not entity_mentions:
            complexity = QueryComplexity.SIMPLE
            reason = "Query matches lookup pattern with no specific entity references"
        elif len(entity_mentions) >= 3:
            complexity = QueryComplexity.COMPLEX
            reason = f"Query mentions {len(entity_mentions)} entities: {entity_mentions}"
        elif needs_governance and len(entity_mentions) >= 2:
            complexity = QueryComplexity.COMPLEX
            reason = f"Governance query spanning {len(entity_mentions)} entities"
        else:
            complexity = QueryComplexity.STANDARD
            reason = "Standard single-pass reasoning"

        return QueryClassification(
            complexity=complexity,
            entity_mentions=entity_mentions,
            needs_governance=needs_governance,
            reason=reason,
        )

    async def process(self, query: AgentQuery) -> AgentResponse:
        """Route and execute the query based on complexity classification."""
        classification = self.classify_query(query)

        logger.info(
            "Query classified as %s: %s",
            classification.complexity,
            classification.reason,
        )

        if classification.complexity == QueryComplexity.SIMPLE:
            return await self._handle_simple(query, classification)
        elif classification.complexity == QueryComplexity.COMPLEX:
            return await self._handle_complex(query, classification)
        else:
            return await self._handle_standard(query, classification)

    async def _handle_simple(
        self,
        query: AgentQuery,
        classification: QueryClassification,
    ) -> AgentResponse:
        """Simple lookup: just run the ContextAgent, skip LLM."""
        response = await self.delegate(
            "context_agent",
            query,
            rationale="Simple lookup — graph traversal only",
        )

        if response is None:
            # Fallback: run directly
            response = await self._context_agent.process(query)

        response.metadata["routing"] = {
            "strategy": "simple",
            "reason": classification.reason,
        }
        return response

    async def _handle_standard(
        self,
        query: AgentQuery,
        classification: QueryClassification,
    ) -> AgentResponse:
        """Standard pipeline: ContextAgent → ExecutiveAgent, with optional governance."""
        # Step 1: Get graph context
        context_response = await self._context_agent.process(query)

        # Step 2: Run executive reasoning with the context
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
        exec_response = await self.delegate(
            "executive_agent",
            exec_query,
            rationale="Standard reasoning over graph context",
        )

        if exec_response is None:
            exec_response = await self._executive_agent.process(exec_query)

        # Step 3: Optional governance check
        governance_response = None
        if classification.needs_governance:
            governance_response = await self._run_governance(exec_response)

        return self._build_response(
            exec_response,
            context_response,
            governance_response,
            strategy="standard",
            reason=classification.reason,
        )

    async def _handle_complex(
        self,
        query: AgentQuery,
        classification: QueryClassification,
    ) -> AgentResponse:
        """Complex query: LLM decides how to decompose via REPL + spawn_agent.

        Rather than pre-programming which sub-agents to call and in what order,
        we inject a ``spawn_agent`` callable into the REPL and let the LLM write
        code that decides decomposition autonomously — it can fan out (width),
        go deep (sequential spawns), or mix both.

        Falls back to a single traversal pass if REPL routing fails.
        """
        # Inject spawner so the LLM's code can delegate subtasks
        spawner = AgentSpawner(llm=self._llm, depth=self._delegation_depth)
        self._repl_agent.repl.inject("spawn_agent", spawner)

        # Build the routing task and attempt REPL-based decomposition
        routing_task = _ROUTING_PROMPT.format(
            query=query.query,
            entity_mentions=classification.entity_mentions or "none detected",
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

        # If REPL routing produced a meaningful answer, use it
        if repl_response and repl_response.confidence > 0.1:
            governance_response = None
            if classification.needs_governance:
                governance_response = await self._run_governance(repl_response)

            metadata = dict(repl_response.metadata)
            metadata["routing"] = {
                "strategy": "complex",
                "reason": classification.reason,
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

        # Fallback: single traversal pass through executive agent
        logger.info("Falling back to single traversal for complex query")
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
        if classification.needs_governance:
            governance_response = await self._run_governance(exec_response)

        return self._build_response(
            exec_response,
            context_response,
            governance_response,
            strategy="complex",
            reason=classification.reason + " (fallback)",
            fan_out_count=len(classification.entity_mentions),
        )

    async def _run_governance(
        self,
        exec_response: AgentResponse,
    ) -> AgentResponse | None:
        """Run governance verification on executive reasoning output."""
        proposals = exec_response.metadata.get("two_morphism_proposals", [])
        if not proposals:
            return None

        # Build traces from proposals for governance checking
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
        reason: str,
        fan_out_count: int = 0,
    ) -> AgentResponse:
        """Combine agent responses into a single orchestrated response."""
        answer = exec_response.answer

        # Append governance findings if relevant
        if governance_response and governance_response.metadata.get("compliant") is False:
            answer += (
                f"\n\n[Governance Warning] {governance_response.answer}"
            )

        metadata = dict(exec_response.metadata)
        metadata["routing"] = {
            "strategy": strategy,
            "reason": reason,
            "fan_out_count": fan_out_count,
        }

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
