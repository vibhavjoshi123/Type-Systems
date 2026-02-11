"""Executive Agent - reasoning and interpretation.

Operates on 2-morphisms: proposes arrows between arrows (meta-relations).
Types include PRECEDENT, EXCEPTION, GENERALIZATION.

From Higher-Order Reasoning PDF Section 3:
The Hypothesizer proposes 2-cells - typed connections between decisions.
"""

from __future__ import annotations

from src.agents.base import AgentQuery, AgentResponse, BaseAgent
from src.llm.base import BaseLLMConnector


class ExecutiveAgent(BaseAgent):
    """Agent for mechanistic interpretation and causal reasoning.

    Capabilities:
    - Causal chain construction from hypergraph paths
    - Decision rationale synthesis
    - 2-morphism proposal (precedent/exception identification)
    """

    def __init__(self, llm: BaseLLMConnector | None = None) -> None:
        self._llm = llm

    @property
    def name(self) -> str:
        return "executive_agent"

    async def process(self, query: AgentQuery) -> AgentResponse:
        """Synthesize reasoning from context paths.

        Takes paths found by the ContextAgent and produces
        mechanistic interpretations and decision rationale.
        """
        paths = query.context.get("paths", [])
        entities = query.context.get("entities", [])
        hyperedges = query.context.get("hyperedges", [])
        graph_summary = query.context.get("graph_summary", "")

        if not paths and not entities and not hyperedges:
            return AgentResponse(
                answer="No context paths or entities provided for reasoning.",
                confidence=0.0,
            )

        # If LLM is available, use it for reasoning
        if self._llm:
            prompt = self._build_reasoning_prompt(
                query.query, paths, entities, hyperedges, graph_summary
            )
            answer = await self._llm.complete(
                prompt=prompt,
                system_prompt=(
                    "You are an executive reasoning agent for an enterprise "
                    "hypergraph context graph. You analyze decision traces, "
                    "entity relationships, and hyperedge connections to "
                    "construct causal chains explaining how enterprise "
                    "decisions were made. Be concise and specific."
                ),
            )
            return AgentResponse(
                answer=answer,
                evidence=[{
                    "paths": paths,
                    "entities": entities,
                    "hyperedges": hyperedges,
                }],
                paths_found=len(paths),
                confidence=0.8,
            )

        # Without LLM, return structured summary
        return AgentResponse(
            answer=f"Graph context: {len(entities)} entities, "
                   f"{len(hyperedges)} hyperedge(s), "
                   f"{len(paths)} path component(s). "
                   f"{graph_summary} "
                   f"Configure LLM_ANTHROPIC_API_KEY for full reasoning.",
            evidence=[{
                "paths": paths,
                "entities": entities,
                "hyperedges": hyperedges,
            }],
            paths_found=len(paths),
            confidence=0.3,
        )

    @staticmethod
    def _build_reasoning_prompt(
        query: str,
        paths: list[object],
        entities: list[object],
        hyperedges: list[object] | None = None,
        graph_summary: str = "",
    ) -> str:
        """Build the reasoning prompt for the LLM."""
        hyperedges = hyperedges or []
        return f"""Analyze the following enterprise decision context and answer the query.

Query: {query}

Graph Summary: {graph_summary}

Entities in the graph ({len(entities)}):
{entities}

Decision hyperedges ({len(hyperedges)}):
{hyperedges}

Context paths / components ({len(paths)}):
{paths}

Based on the above context, provide:
1. A direct answer to the query
2. The causal chain showing how entities and decisions are connected
3. Any precedents or exceptions identified in the decision patterns
4. Your confidence assessment
"""
