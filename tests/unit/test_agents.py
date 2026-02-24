"""Tests for the multi-agent reasoning system.

Covers:
- BaseAgent delegation and fan-out
- ContextAgent graph traversal
- ExecutiveAgent iterative reasoning
- GovernanceAgent coherence verification
- OrchestratorAgent query routing
- SandboxedREPL execution and safety
- ReplAgent code execution and LLM-generated verification
"""

import pytest

from src.agents.base import (
    AgentQuery,
    AgentResponse,
    BaseAgent,
    DelegationRequest,
    MAX_DELEGATION_DEPTH,
)
from src.agents.context_agent import ContextAgent
from src.agents.executive_agent import ExecutiveAgent
from src.agents.governance_agent import GovernanceAgent
from src.agents.orchestrator import (
    OrchestratorAgent,
    QueryComplexity,
)
from src.agents.repl import ExecutionResult, ReplAgent, SandboxedREPL
from src.models.decisions import DecisionTrace, PrecedentChain
from src.models.hyperedges import Hyperedge, RoleAssignment
from src.typedb.traversal import HypergraphTraversal


def make_hyperedge(hid: str, entity_ids: list[str]) -> Hyperedge:
    return Hyperedge(
        hyperedge_id=hid,
        participants=[
            RoleAssignment(entity_id=eid, role="participant")
            for eid in entity_ids
        ],
    )


def _sample_hyperedges() -> list[Hyperedge]:
    return [
        make_hyperedge("h0", ["a", "b", "c"]),
        make_hyperedge("h1", ["b", "c", "d"]),
        make_hyperedge("h2", ["c", "d", "e"]),
        make_hyperedge("h3", ["x", "y", "z"]),  # disconnected
    ]


# ── BaseAgent Delegation ───────────────────────────────────────────


class EchoAgent(BaseAgent):
    """Minimal agent for testing delegation."""

    def __init__(self, agent_name: str = "echo") -> None:
        super().__init__()
        self._name = agent_name

    @property
    def name(self) -> str:
        return self._name

    async def process(self, query: AgentQuery) -> AgentResponse:
        return AgentResponse(
            answer=f"echo:{query.query}",
            confidence=0.5,
        )


class TestBaseAgentDelegation:
    def test_register_sub_agent(self):
        parent = EchoAgent("parent")
        child = EchoAgent("child")
        parent.register_sub_agent(child)

        assert "child" in parent._agent_registry
        assert child._delegation_depth == 1

    def test_can_delegate(self):
        agent = EchoAgent()
        assert agent.can_delegate is True

        # Push to the limit
        agent._delegation_depth = MAX_DELEGATION_DEPTH
        assert agent.can_delegate is False

    @pytest.mark.asyncio
    async def test_delegate_to_sub_agent(self):
        parent = EchoAgent("parent")
        child = EchoAgent("child")
        parent.register_sub_agent(child)

        query = AgentQuery(query="hello")
        response = await parent.delegate("child", query)

        assert response is not None
        assert response.answer == "echo:hello"
        assert response.delegated_from == "parent"

    @pytest.mark.asyncio
    async def test_delegate_unknown_agent_returns_none(self):
        parent = EchoAgent("parent")
        query = AgentQuery(query="hello")

        response = await parent.delegate("nonexistent", query)
        assert response is None

    @pytest.mark.asyncio
    async def test_delegate_depth_limit(self):
        parent = EchoAgent("parent")
        parent._delegation_depth = MAX_DELEGATION_DEPTH
        child = EchoAgent("child")
        parent.register_sub_agent(child)

        query = AgentQuery(query="hello")
        response = await parent.delegate("child", query)
        assert response is None  # Depth limit reached

    @pytest.mark.asyncio
    async def test_fan_out(self):
        parent = EchoAgent("parent")
        child = EchoAgent("child")
        parent.register_sub_agent(child)

        requests = [
            DelegationRequest(
                target_agent="child",
                sub_query=AgentQuery(query="task_1"),
                rationale="first sub-task",
            ),
            DelegationRequest(
                target_agent="child",
                sub_query=AgentQuery(query="task_2"),
                rationale="second sub-task",
            ),
        ]
        results = await parent.fan_out(requests)

        assert len(results) == 2
        assert results[0] is not None
        assert results[0].answer == "echo:task_1"
        assert results[1].answer == "echo:task_2"

    @pytest.mark.asyncio
    async def test_fan_out_mixed_results(self):
        parent = EchoAgent("parent")
        child = EchoAgent("child")
        parent.register_sub_agent(child)

        requests = [
            DelegationRequest(
                target_agent="child",
                sub_query=AgentQuery(query="ok"),
            ),
            DelegationRequest(
                target_agent="missing",
                sub_query=AgentQuery(query="fail"),
            ),
        ]
        results = await parent.fan_out(requests)

        assert len(results) == 2
        assert results[0] is not None
        assert results[1] is None  # Unknown agent

    def test_delegation_depth_propagates(self):
        """Sub-agents inherit incremented depth from parent."""
        a = EchoAgent("a")
        b = EchoAgent("b")
        c = EchoAgent("c")

        a.register_sub_agent(b)
        b.register_sub_agent(c)

        assert a._delegation_depth == 0
        assert b._delegation_depth == 1
        assert c._delegation_depth == 2


# ── ContextAgent ───────────────────────────────────────────────────


class TestContextAgent:
    @pytest.fixture
    def agent(self):
        traversal = HypergraphTraversal()
        traversal.add_hyperedges(_sample_hyperedges())
        return ContextAgent(traversal)

    @pytest.mark.asyncio
    async def test_process(self, agent):
        query = AgentQuery(query="Find context", intersection_size=2)
        response = await agent.process(query)
        assert isinstance(response, AgentResponse)
        assert response.paths_found >= 1
        assert "component" in response.answer.lower()

    @pytest.mark.asyncio
    async def test_find_paths(self, agent):
        paths = await agent.find_paths(0, 2, k=2, s=2)
        assert len(paths) >= 1


# ── GovernanceAgent ────────────────────────────────────────────────


class TestGovernanceAgent:
    @pytest.mark.asyncio
    async def test_coherent_trace(self):
        agent = GovernanceAgent()
        trace = DecisionTrace(
            trace_id="t1",
            decisions=["d1", "d2"],
            two_morphisms=[
                PrecedentChain(precedent_id="d1", derived_id="d2"),
            ],
            is_coherent=True,
        )
        query = AgentQuery(
            query="Check compliance",
            context={"traces": [trace.model_dump()]},
        )
        response = await agent.process(query)
        assert response.metadata.get("compliant") is True

    @pytest.mark.asyncio
    async def test_circular_precedent_detected(self):
        agent = GovernanceAgent()
        trace = DecisionTrace(
            trace_id="t2",
            decisions=["d1", "d2"],
            two_morphisms=[
                PrecedentChain(precedent_id="d1", derived_id="d2"),
                PrecedentChain(precedent_id="d2", derived_id="d1"),
            ],
        )
        query = AgentQuery(
            query="Check compliance",
            context={"traces": [trace.model_dump()]},
        )
        response = await agent.process(query)
        assert response.metadata.get("compliant") is False
        assert "circular" in response.answer.lower()

    @pytest.mark.asyncio
    async def test_no_traces(self):
        agent = GovernanceAgent()
        query = AgentQuery(query="Check compliance")
        response = await agent.process(query)
        assert response.confidence == 0.0


# ── ExecutiveAgent ─────────────────────────────────────────────────


class TestExecutiveAgent:
    @pytest.mark.asyncio
    async def test_no_context(self):
        agent = ExecutiveAgent()
        query = AgentQuery(query="Why was discount given?")
        response = await agent.process(query)
        assert response.confidence == 0.0

    @pytest.mark.asyncio
    async def test_with_context_no_llm(self):
        agent = ExecutiveAgent()
        query = AgentQuery(
            query="Why was discount given?",
            context={"paths": [["d1", "d2"]], "entities": ["cust_001"]},
        )
        response = await agent.process(query)
        assert response.paths_found == 1
        assert response.confidence == 0.3  # No LLM, lower confidence

    @pytest.mark.asyncio
    async def test_iterative_reasoning_with_mock_llm(self):
        """Verify the iterative loop runs when an LLM is available."""

        class MockLLM:
            call_count = 0

            async def complete(self, prompt: str, system_prompt: str | None = None, **kw) -> str:
                self.call_count += 1
                if "verification" in (system_prompt or "").lower():
                    return '{"is_supported": true, "confidence": 0.9, "gaps": [], "suggestions": []}'
                if "extraction" in (system_prompt or "").lower():
                    return '{"proposals": []}'
                return "The discount was approved because of strategic value."

        mock_llm = MockLLM()
        agent = ExecutiveAgent(llm=mock_llm)
        query = AgentQuery(
            query="Why was discount given?",
            context={
                "paths": [["d1", "d2"]],
                "entities": [{"name": "Acme"}],
                "hyperedges": [{"decision_type": "discount"}],
                "graph_summary": "2 entities, 1 hyperedge",
            },
        )
        response = await agent.process(query)

        assert response.confidence >= 0.5
        assert mock_llm.call_count >= 2  # At least reasoning + verification
        assert "reasoning_iterations" in response.metadata

    @pytest.mark.asyncio
    async def test_iterative_reasoning_refines_on_low_confidence(self):
        """Verify that the loop refines when verification gives low confidence."""

        class RefinementLLM:
            call_count = 0

            async def complete(self, prompt: str, system_prompt: str | None = None, **kw) -> str:
                self.call_count += 1
                sp = (system_prompt or "").lower()
                if "verification" in sp:
                    # First verification: low confidence with gaps
                    if self.call_count <= 3:
                        return (
                            '{"is_supported": false, "confidence": 0.4, '
                            '"gaps": ["Missing link between A and B"], '
                            '"suggestions": ["Check entity A direct connections"]}'
                        )
                    # Second verification: higher confidence
                    return '{"is_supported": true, "confidence": 0.9, "gaps": [], "suggestions": []}'
                if "extraction" in sp:
                    return '{"proposals": []}'
                if "refining" in sp:
                    return "Refined: A connects to B via decision D1."
                return "Initial analysis of the discount decision."

        mock_llm = RefinementLLM()
        agent = ExecutiveAgent(llm=mock_llm)
        query = AgentQuery(
            query="Why was discount given?",
            context={
                "paths": [["d1"]],
                "entities": [{"name": "Acme"}],
                "hyperedges": [{"decision_type": "discount"}],
            },
        )
        response = await agent.process(query)

        # Should have iterated at least twice (initial + refinement)
        assert response.metadata["reasoning_iterations"] >= 2
        assert mock_llm.call_count >= 4  # reason + verify + refine + verify


# ── OrchestratorAgent ──────────────────────────────────────────────


class TestOrchestratorAgent:
    @pytest.fixture
    def entities(self):
        return [
            {"name": "Acme Corp", "entity-name": "Acme Corp"},
            {"name": "Globex Inc", "entity-name": "Globex Inc"},
            {"name": "Initech Ltd", "entity-name": "Initech Ltd"},
        ]

    @pytest.fixture
    def orchestrator(self, entities):
        traversal = HypergraphTraversal(_sample_hyperedges())
        return OrchestratorAgent(
            traversal=traversal,
            llm=None,
            entities=entities,
            hyperedges=[],
        )

    def test_classify_simple_query(self, orchestrator):
        query = AgentQuery(query="List all entities")
        classification = orchestrator.classify_query(query)
        assert classification.complexity == QueryComplexity.SIMPLE

    def test_classify_standard_query(self, orchestrator):
        query = AgentQuery(query="Why was the discount approved?")
        classification = orchestrator.classify_query(query)
        assert classification.complexity == QueryComplexity.STANDARD

    def test_classify_complex_multi_entity(self, orchestrator):
        query = AgentQuery(
            query="How are Acme Corp, Globex Inc and Initech Ltd connected?"
        )
        classification = orchestrator.classify_query(query)
        assert classification.complexity == QueryComplexity.COMPLEX
        assert len(classification.entity_mentions) == 3

    def test_classify_governance_query(self, orchestrator):
        query = AgentQuery(query="Are there any compliance violations?")
        classification = orchestrator.classify_query(query)
        assert classification.needs_governance is True

    def test_classify_risk_with_entities(self, orchestrator):
        query = AgentQuery(
            query="What is the risk of Acme Corp and Globex Inc decisions?"
        )
        classification = orchestrator.classify_query(query)
        assert classification.needs_governance is True
        assert classification.complexity == QueryComplexity.COMPLEX

    @pytest.mark.asyncio
    async def test_simple_route_skips_llm(self, orchestrator):
        query = AgentQuery(query="Show all connections")
        response = await orchestrator.process(query)

        assert isinstance(response, AgentResponse)
        routing = response.metadata.get("routing", {})
        assert routing.get("strategy") == "simple"

    @pytest.mark.asyncio
    async def test_standard_route_no_llm(self, orchestrator):
        query = AgentQuery(query="Why was the discount approved?")
        response = await orchestrator.process(query)

        assert isinstance(response, AgentResponse)
        routing = response.metadata.get("routing", {})
        assert routing.get("strategy") == "standard"

    @pytest.mark.asyncio
    async def test_complex_route(self, orchestrator):
        query = AgentQuery(
            query="How are Acme Corp, Globex Inc and Initech Ltd connected?"
        )
        response = await orchestrator.process(query)

        assert isinstance(response, AgentResponse)
        routing = response.metadata.get("routing", {})
        assert routing.get("strategy") == "complex"

    @pytest.mark.asyncio
    async def test_sub_agents_registered(self, orchestrator):
        assert "context_agent" in orchestrator._agent_registry
        assert "executive_agent" in orchestrator._agent_registry
        assert "governance_agent" in orchestrator._agent_registry
        assert "repl_agent" in orchestrator._agent_registry


# ── SandboxedREPL ─────────────────────────────────────────────────


class TestSandboxedREPL:
    @pytest.mark.asyncio
    async def test_basic_execution(self):
        repl = SandboxedREPL()
        result = await repl.execute("x = 2 + 3")
        assert result.success is True

    @pytest.mark.asyncio
    async def test_return_value(self):
        repl = SandboxedREPL()
        result = await repl.execute("2 + 3")
        assert result.success is True
        assert result.return_value == 5

    @pytest.mark.asyncio
    async def test_state_persists(self):
        """Variables defined in one execution are available in the next."""
        repl = SandboxedREPL()
        await repl.execute("counter = 10")
        result = await repl.execute("counter + 5")
        assert result.return_value == 15

    @pytest.mark.asyncio
    async def test_inject_object(self):
        repl = SandboxedREPL()
        repl.inject("data", [1, 2, 3, 4, 5])
        result = await repl.execute("sum(data)")
        assert result.return_value == 15

    @pytest.mark.asyncio
    async def test_inject_live_object(self):
        """Injected objects are live references, not copies — like Agentica."""
        repl = SandboxedREPL()
        entities = [{"name": "Acme"}, {"name": "Globex"}]
        repl.inject("entities", entities)
        result = await repl.execute("len(entities)")
        assert result.return_value == 2

        # Mutate from outside — REPL sees the change (live reference)
        entities.append({"name": "Initech"})
        result = await repl.execute("len(entities)")
        assert result.return_value == 3

    @pytest.mark.asyncio
    async def test_inject_traversal_object(self):
        """HypergraphTraversal can be injected and called from sandbox."""
        traversal = HypergraphTraversal(_sample_hyperedges())
        repl = SandboxedREPL()
        repl.inject("traversal", traversal)
        result = await repl.execute(
            "components = traversal.find_s_connected_components(2)\n"
            "len(components)"
        )
        assert result.success is True
        assert result.return_value >= 1

    @pytest.mark.asyncio
    async def test_stdout_capture(self):
        repl = SandboxedREPL()
        result = await repl.execute('print("hello from sandbox")')
        assert "hello from sandbox" in result.stdout

    @pytest.mark.asyncio
    async def test_blocked_import(self):
        repl = SandboxedREPL()
        result = await repl.execute("import os")
        assert result.success is False
        assert "not allowed" in (result.error or "")

    @pytest.mark.asyncio
    async def test_allowed_import(self):
        repl = SandboxedREPL()
        result = await repl.execute("import math\nmath.sqrt(16)")
        assert result.success is True
        assert result.return_value == 4.0

    @pytest.mark.asyncio
    async def test_blocked_builtins(self):
        repl = SandboxedREPL()
        result = await repl.execute('open("/etc/passwd")')
        assert result.success is False

    @pytest.mark.asyncio
    async def test_timeout(self):
        repl = SandboxedREPL(timeout=0.5)
        result = await repl.execute("while True: pass")
        assert result.success is False
        assert "timed out" in (result.error or "").lower()

    @pytest.mark.asyncio
    async def test_reset(self):
        repl = SandboxedREPL()
        await repl.execute("x = 42")
        repl.reset()
        result = await repl.execute("x")
        assert result.success is False  # x no longer defined

    @pytest.mark.asyncio
    async def test_history_tracking(self):
        repl = SandboxedREPL()
        await repl.execute("1 + 1")
        await repl.execute("2 + 2")
        assert len(repl.history) == 2

    @pytest.mark.asyncio
    async def test_namespace_keys(self):
        repl = SandboxedREPL()
        repl.inject("foo", 1)
        repl.inject("bar", 2)
        assert "foo" in repl.namespace_keys
        assert "bar" in repl.namespace_keys
        assert "__builtins__" not in repl.namespace_keys

    @pytest.mark.asyncio
    async def test_multiline_code(self):
        repl = SandboxedREPL()
        code = """
results = []
for i in range(5):
    results.append(i * 2)
len(results)
"""
        result = await repl.execute(code)
        assert result.success is True
        assert result.return_value == 5


# ── ReplAgent ─────────────────────────────────────────────────────


class TestReplAgent:
    @pytest.mark.asyncio
    async def test_direct_code_execution(self):
        agent = ReplAgent()
        query = AgentQuery(
            query="Run code",
            context={"code": "2 ** 10"},
        )
        response = await agent.process(query)
        assert response.confidence > 0
        assert "1024" in response.answer

    @pytest.mark.asyncio
    async def test_direct_code_with_injected_data(self):
        agent = ReplAgent()
        agent.load_graph_context(
            entities=[{"name": "Acme"}, {"name": "Globex"}],
        )
        query = AgentQuery(
            query="Count entities",
            context={"code": "len(entities)"},
        )
        response = await agent.process(query)
        assert "2" in response.answer

    @pytest.mark.asyncio
    async def test_traversal_from_repl(self):
        """ReplAgent can execute code against a live traversal object."""
        traversal = HypergraphTraversal(_sample_hyperedges())
        agent = ReplAgent()
        agent.load_graph_context(traversal=traversal)
        query = AgentQuery(
            query="Find components",
            context={
                "code": (
                    "comps = traversal.find_s_connected_components(2)\n"
                    "result = {'supported': True, 'findings': f'{len(comps)} components', 'checks': []}"
                ),
            },
        )
        response = await agent.process(query)
        assert response.success is not False  # metadata check
        assert response.confidence >= 0.6

    @pytest.mark.asyncio
    async def test_llm_generated_verification(self):
        """ReplAgent generates and executes verification code with a mock LLM."""

        class CodeGenLLM:
            async def complete(self, prompt: str, system_prompt: str | None = None, **kw) -> str:
                return (
                    "entity_names = [e.get('name', '') for e in entities]\n"
                    "result = {'supported': len(entity_names) > 0, "
                    "'findings': f'Found {len(entity_names)} entities', "
                    "'checks': entity_names}"
                )

        agent = ReplAgent(llm=CodeGenLLM())
        agent.load_graph_context(
            entities=[{"name": "Acme"}, {"name": "Globex"}],
            hyperedges=[],
        )
        query = AgentQuery(
            query="Verify entity presence",
            context={"hypothesis": "Acme and Globex are in the graph"},
        )
        response = await agent.process(query)
        assert response.confidence >= 0.6
        assert response.metadata.get("mode") == "generated"

    @pytest.mark.asyncio
    async def test_no_llm_no_code_returns_empty(self):
        agent = ReplAgent()
        query = AgentQuery(query="Do something")
        response = await agent.process(query)
        assert response.confidence == 0.0

    @pytest.mark.asyncio
    async def test_failed_code_low_confidence(self):
        agent = ReplAgent()
        query = AgentQuery(
            query="Bad code",
            context={"code": "undefined_variable + 1"},
        )
        response = await agent.process(query)
        assert response.confidence <= 0.2

    @pytest.mark.asyncio
    async def test_repl_state_persists_across_calls(self):
        """Like Agentica: state accumulates across agent invocations."""
        agent = ReplAgent()
        await agent.process(AgentQuery(
            query="Set state",
            context={"code": "analysis_count = 0"},
        ))
        response = await agent.process(AgentQuery(
            query="Increment",
            context={"code": "analysis_count += 1\nanalysis_count"},
        ))
        assert "1" in response.answer


# ── ExecutiveAgent + REPL Integration ─────────────────────────────


class TestExecutiveAgentWithREPL:
    @pytest.mark.asyncio
    async def test_repl_enhances_verification(self):
        """ExecutiveAgent uses ReplAgent for code-based verification."""

        class MockLLM:
            call_count = 0

            async def complete(self, prompt: str, system_prompt: str | None = None, **kw) -> str:
                self.call_count += 1
                sp = (system_prompt or "").lower()
                if "verification" in sp:
                    return '{"is_supported": true, "confidence": 0.9, "gaps": [], "suggestions": []}'
                if "extraction" in sp:
                    return '{"proposals": []}'
                if "code generation" in sp:
                    return (
                        "result = {'supported': True, "
                        "'findings': 'Entities match', 'checks': []}"
                    )
                return "The discount was approved based on strategic value."

        mock_llm = MockLLM()
        repl_agent = ReplAgent(llm=mock_llm)
        repl_agent.load_graph_context(
            entities=[{"name": "Acme"}],
            hyperedges=[{"decision_type": "discount"}],
        )

        agent = ExecutiveAgent(llm=mock_llm, repl_agent=repl_agent)
        query = AgentQuery(
            query="Why was discount given?",
            context={
                "paths": [["d1", "d2"]],
                "entities": [{"name": "Acme"}],
                "hyperedges": [{"decision_type": "discount"}],
                "graph_summary": "1 entity, 1 hyperedge",
            },
        )
        response = await agent.process(query)
        assert response.confidence >= 0.5
        assert "reasoning_iterations" in response.metadata
