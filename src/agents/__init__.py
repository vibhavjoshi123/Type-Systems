"""Multi-agent reasoning system for the hypergraph context graph.

From Higher-Order Reasoning PDF Section 3, each agent implements
a well-defined categorical operation:

- ContextAgent: 1-morphism composition (path finding via IS constraints)
- ExecutiveAgent: 2-morphism proposal (iterative reasoning with verification)
- GovernanceAgent: Coherence verification (diagram commutativity checking)
- OrchestratorAgent: Dynamic query routing and sub-agent delegation
- ReplAgent: Sandboxed code execution for hypothesis verification
- AgentSpawner: Live sub-agent delegation from within REPL code
"""

from src.agents.base import BaseAgent
from src.agents.context_agent import ContextAgent
from src.agents.executive_agent import ExecutiveAgent
from src.agents.governance_agent import GovernanceAgent
from src.agents.orchestrator import OrchestratorAgent
from src.agents.repl import AgentSpawner, ReplAgent, SandboxedREPL
from src.agents.tools import HypergraphTools

__all__ = [
    "AgentSpawner",
    "BaseAgent",
    "ContextAgent",
    "ExecutiveAgent",
    "GovernanceAgent",
    "HypergraphTools",
    "OrchestratorAgent",
    "ReplAgent",
    "SandboxedREPL",
]
