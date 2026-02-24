"""Executive Agent - reasoning and interpretation with iterative verification.

Operates on 2-morphisms: proposes arrows between arrows (meta-relations).
Types include PRECEDENT, EXCEPTION, GENERALIZATION.

Uses an iterative hypothesize → verify → refine loop:
1. Form an initial hypothesis about decision relationships
2. Verify the hypothesis against the graph data
3. Refine if verification reveals gaps or contradictions
4. Extract 2-morphism proposals from the verified reasoning

From Higher-Order Reasoning PDF Section 3:
The Hypothesizer proposes 2-cells - typed connections between decisions.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

from src.agents.base import AgentQuery, AgentResponse, BaseAgent
from src.llm.base import BaseLLMConnector

# Avoid circular import — ReplAgent is injected at runtime, not imported.
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.agents.repl import ReplAgent

logger = logging.getLogger(__name__)

# Maximum iterations for the hypothesize-verify-refine loop.
MAX_REASONING_ITERATIONS = 3

# Confidence threshold: stop iterating once we reach this.
CONFIDENCE_THRESHOLD = 0.85


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


class VerificationResult(BaseModel):
    """Result of verifying a reasoning hypothesis against graph data."""

    is_supported: bool = Field(description="Whether the hypothesis is supported by evidence")
    confidence: float = Field(default=0.0, ge=0, le=1)
    gaps: list[str] = Field(
        default_factory=list,
        description="Evidence gaps or contradictions found",
    )
    suggestions: list[str] = Field(
        default_factory=list,
        description="Suggestions for refining the hypothesis",
    )


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


_VERIFICATION_SYSTEM = (
    "You are a verification engine for enterprise decision reasoning. "
    "Given a hypothesis and the raw graph evidence, assess whether the "
    "hypothesis is supported. Identify gaps, contradictions, or missing "
    "connections. Be specific about what evidence supports or refutes "
    "each claim."
)

_VERIFICATION_PROMPT = """Evaluate whether the following reasoning hypothesis is supported
by the graph evidence.

Hypothesis:
{hypothesis}

Entities in graph:
{entities}

Decision hyperedges:
{hyperedges}

Graph traversal context:
{paths}

Respond ONLY with valid JSON:
```json
{{
  "is_supported": true/false,
  "confidence": 0.0-1.0,
  "gaps": ["list of evidence gaps or contradictions"],
  "suggestions": ["list of specific refinement suggestions"]
}}
```
"""

_REFINEMENT_PROMPT = """Refine your previous analysis based on verification feedback.

Original query: {query}
Previous reasoning: {previous_reasoning}

Verification found these issues:
- Gaps: {gaps}
- Suggestions: {suggestions}

Graph context:
{graph_summary}

Entities: {entities}
Hyperedges: {hyperedges}

Provide a refined analysis that addresses the identified gaps. Be concise and specific."""


class ExecutiveAgent(BaseAgent):
    """Agent for mechanistic interpretation and causal reasoning.

    Uses an iterative reasoning loop:
    1. Generate initial hypothesis (LLM reasoning over graph context)
    2. Verify the hypothesis against the actual graph data
    3. Refine if verification reveals gaps (up to MAX_REASONING_ITERATIONS)
    4. Extract 2-morphism proposals from the final verified reasoning

    Capabilities:
    - Causal chain construction from hypergraph paths
    - Decision rationale synthesis
    - 2-morphism proposal (precedent/exception identification)
    - Self-verification against graph evidence
    - Iterative refinement with feedback
    """

    def __init__(
        self,
        llm: BaseLLMConnector | None = None,
        repl_agent: ReplAgent | None = None,
    ) -> None:
        super().__init__()
        self._llm = llm
        self._repl_agent = repl_agent

    @property
    def name(self) -> str:
        return "executive_agent"

    async def process(self, query: AgentQuery) -> AgentResponse:
        """Synthesize reasoning from context paths with iterative verification.

        Takes paths found by the ContextAgent and produces mechanistic
        interpretations and decision rationale, verifying each iteration
        against the graph data before finalizing.
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

        # If LLM is available, use the iterative reasoning loop
        if self._llm:
            try:
                result = await self._iterative_reason(
                    query.query, paths, entities, hyperedges, graph_summary
                )
                return result
            except Exception as exc:
                logger.error(
                    "Iterative reasoning failed (%s): %s",
                    type(exc).__name__,
                    exc,
                )
                # Fall through to non-LLM response

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

    async def _iterative_reason(
        self,
        query: str,
        paths: list[object],
        entities: list[object],
        hyperedges: list[object],
        graph_summary: str,
    ) -> AgentResponse:
        """Run the hypothesize → verify → refine loop.

        Each iteration:
        1. Generate or refine a reasoning hypothesis
        2. Verify it against the graph evidence
        3. If confidence is high enough or iterations exhausted, finalize
        """
        assert self._llm is not None

        current_reasoning = ""
        best_confidence = 0.0
        best_reasoning = ""
        iteration_log: list[dict[str, Any]] = []

        for iteration in range(MAX_REASONING_ITERATIONS):
            # Step 1: Generate or refine hypothesis
            if iteration == 0:
                prompt = self._build_reasoning_prompt(
                    query, paths, entities, hyperedges, graph_summary
                )
                current_reasoning = await self._llm.complete(
                    prompt=prompt,
                    system_prompt=(
                        "You are an executive reasoning agent for an enterprise "
                        "hypergraph context graph. You analyze decision traces, "
                        "entity relationships, and hyperedge connections to "
                        "construct causal chains explaining how enterprise "
                        "decisions were made. Be concise and specific."
                    ),
                )
            else:
                # Refine based on verification feedback
                current_reasoning = await self._refine_reasoning(
                    query,
                    current_reasoning,
                    verification,
                    entities,
                    hyperedges,
                    graph_summary,
                )

            # Step 2: Verify the hypothesis against graph data
            verification = await self._verify_hypothesis(
                current_reasoning, entities, hyperedges, paths
            )

            # Step 2b: Code-based verification via REPL (if available)
            if self._repl_agent:
                code_result = await self._verify_with_code(
                    current_reasoning, entities, hyperedges, paths
                )
                if code_result is not None:
                    # Blend code verification with LLM verification
                    verification = self._blend_verification(
                        verification, code_result
                    )

            iteration_log.append({
                "iteration": iteration,
                "confidence": verification.confidence,
                "is_supported": verification.is_supported,
                "gaps_count": len(verification.gaps),
            })

            logger.info(
                "Iteration %d: confidence=%.2f, supported=%s, gaps=%d",
                iteration,
                verification.confidence,
                verification.is_supported,
                len(verification.gaps),
            )

            # Track best result
            if verification.confidence > best_confidence:
                best_confidence = verification.confidence
                best_reasoning = current_reasoning

            # Step 3: Check if we can stop
            if verification.is_supported and verification.confidence >= CONFIDENCE_THRESHOLD:
                logger.info(
                    "Reasoning converged at iteration %d (confidence=%.2f)",
                    iteration,
                    verification.confidence,
                )
                break

            if not verification.gaps and not verification.suggestions:
                # Nothing to improve on — stop even if below threshold
                break

        # Use the best reasoning we found across iterations
        final_reasoning = best_reasoning or current_reasoning

        # Extract 2-morphism proposals from the final reasoning
        proposals = await self._extract_2morphisms(final_reasoning, hyperedges)

        return AgentResponse(
            answer=final_reasoning,
            evidence=[{
                "paths": paths,
                "entities": entities,
                "hyperedges": hyperedges,
            }],
            paths_found=len(paths),
            confidence=best_confidence,
            metadata={
                "two_morphism_proposals": [p.model_dump() for p in proposals],
                "reasoning_iterations": len(iteration_log),
                "iteration_log": iteration_log,
                "verified": best_confidence >= CONFIDENCE_THRESHOLD,
            },
        )

    async def _verify_hypothesis(
        self,
        hypothesis: str,
        entities: list[object],
        hyperedges: list[object],
        paths: list[object],
    ) -> VerificationResult:
        """Verify a reasoning hypothesis against graph evidence.

        Asks the LLM to act as a critic: does the evidence actually
        support the claims in the hypothesis?
        """
        if not self._llm:
            return VerificationResult(is_supported=True, confidence=0.5)

        try:
            prompt = _VERIFICATION_PROMPT.format(
                hypothesis=hypothesis,
                entities=entities,
                hyperedges=hyperedges,
                paths=paths,
            )
            raw = await self._llm.complete(
                prompt=prompt,
                system_prompt=_VERIFICATION_SYSTEM,
            )

            text = raw.strip()
            if text.startswith("```"):
                lines = text.split("\n")
                text = "\n".join(lines[1:])
                if text.endswith("```"):
                    text = text[:-3].strip()

            return VerificationResult.model_validate_json(text)

        except Exception as exc:
            logger.warning("Verification failed: %s", exc)
            # If verification itself fails, assume moderate confidence
            return VerificationResult(is_supported=True, confidence=0.5)

    async def _refine_reasoning(
        self,
        query: str,
        previous_reasoning: str,
        verification: VerificationResult,
        entities: list[object],
        hyperedges: list[object],
        graph_summary: str,
    ) -> str:
        """Refine reasoning based on verification feedback."""
        assert self._llm is not None

        prompt = _REFINEMENT_PROMPT.format(
            query=query,
            previous_reasoning=previous_reasoning,
            gaps="; ".join(verification.gaps) if verification.gaps else "None",
            suggestions="; ".join(verification.suggestions) if verification.suggestions else "None",
            graph_summary=graph_summary,
            entities=entities,
            hyperedges=hyperedges,
        )
        return await self._llm.complete(
            prompt=prompt,
            system_prompt=(
                "You are an executive reasoning agent refining a previous "
                "analysis based on verification feedback. Address each gap "
                "and incorporate the suggestions. Be concise and specific."
            ),
        )

    async def _verify_with_code(
        self,
        hypothesis: str,
        entities: list[object],
        hyperedges: list[object],
        paths: list[object],
    ) -> VerificationResult | None:
        """Run code-based verification via the REPL agent.

        Delegates to the ReplAgent which generates and executes Python
        code to programmatically check whether the hypothesis is supported
        by the actual graph data.
        """
        if not self._repl_agent:
            return None

        try:
            repl_query = AgentQuery(
                query=f"Verify: {hypothesis}",
                context={
                    "hypothesis": hypothesis,
                    "entities": entities,
                    "hyperedges": hyperedges,
                    "paths": paths,
                },
            )
            response = await self._repl_agent.process(repl_query)

            # Parse the REPL result into a VerificationResult
            repl_result = response.metadata.get("success", False)
            evidence = response.evidence[0] if response.evidence else {}
            return_value = evidence.get("return_value")

            if isinstance(return_value, dict) and "supported" in return_value:
                return VerificationResult(
                    is_supported=bool(return_value["supported"]),
                    confidence=response.confidence,
                    gaps=return_value.get("checks", []),
                    suggestions=[return_value.get("findings", "")],
                )

            # Fallback: use the response confidence as a signal
            return VerificationResult(
                is_supported=response.confidence > 0.5,
                confidence=response.confidence,
                gaps=[],
                suggestions=[response.answer] if response.answer else [],
            )

        except Exception as exc:
            logger.warning("Code-based verification failed: %s", exc)
            return None

    @staticmethod
    def _blend_verification(
        llm_result: VerificationResult,
        code_result: VerificationResult,
    ) -> VerificationResult:
        """Combine LLM-based and code-based verification results.

        Code verification gets a slight edge since it's deterministic.
        """
        blended_confidence = (
            llm_result.confidence * 0.4 + code_result.confidence * 0.6
        )
        combined_gaps = list(llm_result.gaps) + list(code_result.gaps)
        combined_suggestions = list(llm_result.suggestions) + list(code_result.suggestions)

        return VerificationResult(
            is_supported=llm_result.is_supported and code_result.is_supported,
            confidence=round(blended_confidence, 3),
            gaps=combined_gaps,
            suggestions=combined_suggestions,
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
