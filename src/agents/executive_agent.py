"""Executive Agent - reasoning and interpretation.

Operates on 2-morphisms: proposes arrows between arrows (meta-relations).
Types include PRECEDENT, EXCEPTION, GENERALIZATION.

From Higher-Order Reasoning PDF Section 3:
The Hypothesizer proposes 2-cells - typed connections between decisions.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

from src.agents.base import AgentQuery, AgentResponse, BaseAgent
from src.llm.base import BaseLLMConnector

logger = logging.getLogger(__name__)


class TwoMorphismProposal(BaseModel):
    """A 2-morphism proposed by the LLM from its reasoning."""

    morphism_type: str = Field(
        description="One of: precedent, exception, override, generalization, sequence"
    )
    source_description: str = Field(description="Description of the source decision/event")
    target_description: str = Field(description="Description of the target decision/event")
    rationale: str = Field(description="Why this relationship exists")


class TwoMorphismExtractionResult(BaseModel):
    """Structured output from the 2-morphism extraction call."""

    proposals: list[TwoMorphismProposal] = Field(default_factory=list)


_EXTRACTION_SYSTEM = (
    "You are a 2-morphism extraction engine for an enterprise hypergraph. "
    "Given a reasoning analysis, identify relationships BETWEEN decisions or events. "
    "A 2-morphism is a typed link between two hyperedges (decision events). "
    "Types: precedent (B follows from A), exception (B overrides A), "
    "generalization (B abstracts A), justification (A justifies B), "
    "sequence (B follows A in time)."
)

_EXTRACTION_PROMPT = """From the reasoning below, extract any 2-morphism relationships
(relationships BETWEEN decisions/events, not between entities).

Reasoning:
{reasoning}

Hyperedges available:
{hyperedges}

Respond ONLY with valid JSON matching this schema:
```json
{{
  "proposals": [
    {{
      "morphism_type": "precedent|exception|override|generalization|sequence|justification",
      "source_description": "description of the source decision/event",
      "target_description": "description of the target decision/event",
      "rationale": "why this relationship exists"
    }}
  ]
}}
```

If no 2-morphism relationships are found, return {{"proposals": []}}.
Only propose relationships that are clearly supported by the evidence."""


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
            try:
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

                # Extract 2-morphism proposals from the reasoning
                proposals = await self._extract_2morphisms(answer, hyperedges)

                return AgentResponse(
                    answer=answer,
                    evidence=[{
                        "paths": paths,
                        "entities": entities,
                        "hyperedges": hyperedges,
                    }],
                    paths_found=len(paths),
                    confidence=0.8,
                    metadata={
                        "two_morphism_proposals": [
                            p.model_dump() for p in proposals
                        ],
                    },
                )
            except Exception as exc:
                logger.error(
                    "LLM call failed (%s): %s",
                    type(exc).__name__,
                    exc,
                )
                # Fall through to non-LLM response (confidence=0.3)

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

    async def _extract_2morphisms(
        self,
        reasoning: str,
        hyperedges: list[Any],
    ) -> list[TwoMorphismProposal]:
        """Extract 2-morphism proposals from the LLM's reasoning output."""
        if not self._llm:
            return []

        try:
            prompt = _EXTRACTION_PROMPT.format(
                reasoning=reasoning,
                hyperedges=hyperedges,
            )
            raw = await self._llm.complete(
                prompt=prompt,
                system_prompt=_EXTRACTION_SYSTEM,
            )

            # Parse the JSON response
            text = raw.strip()
            if text.startswith("```"):
                lines = text.split("\n")
                text = "\n".join(lines[1:])
                if text.endswith("```"):
                    text = text[:-3].strip()

            result = TwoMorphismExtractionResult.model_validate_json(text)
            logger.info(
                "Extracted %d 2-morphism proposal(s) from reasoning",
                len(result.proposals),
            )
            return result.proposals

        except Exception as exc:
            logger.warning("2-morphism extraction failed: %s", exc)
            return []

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
