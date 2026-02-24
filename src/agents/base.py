"""Base agent interface for the multi-agent reasoning system.

Supports recursive delegation: any agent can spawn focused sub-agents
with isolated context to avoid context rot and enable dynamic depth/width
exploration strategies.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Global limit on recursive delegation depth to prevent runaway chains.
MAX_DELEGATION_DEPTH = 5


class AgentQuery(BaseModel):
    """Input query for an agent."""

    query: str = Field(..., description="Natural language query")
    context: dict[str, Any] = Field(default_factory=dict)
    max_depth: int = Field(default=5, ge=1)
    intersection_size: int = Field(default=2, ge=1)


class AgentResponse(BaseModel):
    """Response from an agent."""

    answer: str
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    paths_found: int = 0
    confidence: float = Field(default=0.0, ge=0, le=1)
    metadata: dict[str, Any] = Field(default_factory=dict)
    delegated_from: str | None = Field(
        default=None, description="Name of the parent agent that delegated this task"
    )


class DelegationRequest(BaseModel):
    """A request for a parent agent to delegate work to a sub-agent."""

    target_agent: str = Field(..., description="Name/type of the sub-agent to spawn")
    sub_query: AgentQuery = Field(..., description="Focused query for the sub-agent")
    rationale: str = Field(
        default="", description="Why this sub-task is being delegated"
    )


class BaseAgent(ABC):
    """Abstract base class for reasoning agents.

    Supports recursive delegation: agents can spawn sub-agents with
    focused context slices via ``delegate()``. Each sub-agent gets a
    fresh invocation (clean context), avoiding the degraded reasoning
    that comes from long accumulated conversation state.

    Delegation depth is capped at ``MAX_DELEGATION_DEPTH`` to prevent
    runaway recursion.
    """

    def __init__(self) -> None:
        self._delegation_depth: int = 0
        self._agent_registry: dict[str, BaseAgent] = {}

    @property
    @abstractmethod
    def name(self) -> str:
        """Agent name identifier."""
        ...

    @abstractmethod
    async def process(self, query: AgentQuery) -> AgentResponse:
        """Process a query and return a response.

        Args:
            query: The agent query with parameters.

        Returns:
            AgentResponse with answer, evidence, and metadata.
        """
        ...

    # ── Delegation ──────────────────────────────────────────────────

    def register_sub_agent(self, agent: BaseAgent) -> None:
        """Register an agent that can be delegated to by name."""
        agent._delegation_depth = self._delegation_depth + 1
        agent._agent_registry = self._agent_registry
        self._agent_registry[agent.name] = agent

    def register_sub_agents(self, agents: list[BaseAgent]) -> None:
        """Register multiple sub-agents."""
        for agent in agents:
            self.register_sub_agent(agent)

    @property
    def can_delegate(self) -> bool:
        """Whether this agent can still delegate (depth limit not reached)."""
        return self._delegation_depth < MAX_DELEGATION_DEPTH

    async def delegate(
        self,
        target_name: str,
        sub_query: AgentQuery,
        rationale: str = "",
    ) -> AgentResponse | None:
        """Delegate a focused sub-task to a registered sub-agent.

        The sub-agent receives only the ``sub_query`` — a focused context
        slice — rather than inheriting the parent's full accumulated state.
        This combats context rot and lets each sub-agent reason cleanly.

        Args:
            target_name: Name of the registered sub-agent.
            sub_query: Focused query with only the relevant context.
            rationale: Why this delegation is happening (for logging).

        Returns:
            The sub-agent's response, or None if delegation failed.
        """
        if not self.can_delegate:
            logger.warning(
                "%s: delegation depth %d reached limit %d — running locally",
                self.name,
                self._delegation_depth,
                MAX_DELEGATION_DEPTH,
            )
            return None

        target = self._agent_registry.get(target_name)
        if target is None:
            logger.warning(
                "%s: no sub-agent registered as '%s' — available: %s",
                self.name,
                target_name,
                list(self._agent_registry.keys()),
            )
            return None

        logger.info(
            "%s → delegating to %s (depth %d): %s",
            self.name,
            target_name,
            self._delegation_depth + 1,
            rationale or sub_query.query[:80],
        )

        response = await target.process(sub_query)
        response.delegated_from = self.name
        return response

    async def fan_out(
        self,
        requests: list[DelegationRequest],
    ) -> list[AgentResponse | None]:
        """Delegate multiple sub-tasks in sequence and collect results.

        Useful when a complex query can be decomposed into independent
        pieces — e.g., one sub-agent per entity or per decision trace.

        Args:
            requests: List of delegation requests.

        Returns:
            List of responses (None for any that failed).
        """
        results: list[AgentResponse | None] = []
        for req in requests:
            result = await self.delegate(
                req.target_agent, req.sub_query, req.rationale
            )
            results.append(result)
        return results
