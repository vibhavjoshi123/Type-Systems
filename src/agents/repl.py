"""Sandboxed REPL for agent code execution.

Provides a persistent Python execution environment that agents can use
to verify hypotheses, explore graph data, and run programmatic checks
against the hypergraph, interleaving reasoning with code execution.

Security model:
- Restricted builtins (no file I/O, no eval/exec, no subprocess)
- Allowlisted imports only (math, json, collections, etc.)
- Execution timeout (default 10s)
- Output size capping
"""

from __future__ import annotations

import asyncio
import io
import logging
import sys
import threading
import traceback
import time
from contextlib import redirect_stdout, redirect_stderr
from typing import Any

from pydantic import BaseModel, Field

from src.agents.base import AgentQuery, AgentResponse, BaseAgent
from src.llm.base import BaseLLMConnector

logger = logging.getLogger(__name__)

# Modules agents are allowed to import in the sandbox.
_ALLOWED_MODULES = frozenset({
    "math",
    "statistics",
    "collections",
    "itertools",
    "functools",
    "json",
    "re",
    "datetime",
    "copy",
    "operator",
    "typing",
})

# Builtins that are blocked for security.
_BLOCKED_BUILTINS = frozenset({
    "exec",
    "eval",
    "compile",
    "open",
    "breakpoint",
    "__import__",
    "exit",
    "quit",
    "input",
    "memoryview",
    "globals",
})

# Defaults
DEFAULT_TIMEOUT = 10  # seconds
MAX_OUTPUT_SIZE = 50_000  # characters


class ExecutionResult(BaseModel):
    """Result of executing code in the sandbox."""

    stdout: str = ""
    stderr: str = ""
    return_value: Any = None
    success: bool = True
    error: str | None = None
    duration_ms: float = 0.0


class SandboxedREPL:
    """Persistent sandboxed Python execution environment.

    Maintains state across executions (variables defined in one call
    are available in the next), but restricts dangerous operations.

    Usage::

        repl = SandboxedREPL()
        repl.inject("entities", [{"name": "Acme"}])
        result = await repl.execute("len(entities)")
        assert result.return_value == 1
    """

    def __init__(self, timeout: float = DEFAULT_TIMEOUT) -> None:
        self._timeout = timeout
        self._namespace: dict[str, Any] = {}
        self._history: list[ExecutionResult] = []
        self._setup_namespace()

    def _setup_namespace(self) -> None:
        """Populate the sandbox namespace with safe builtins."""
        safe_builtins = {
            k: v
            for k, v in __builtins__.items()  # type: ignore[union-attr]
            if k not in _BLOCKED_BUILTINS
        } if isinstance(__builtins__, dict) else {
            k: getattr(__builtins__, k)
            for k in dir(__builtins__)
            if k not in _BLOCKED_BUILTINS and not k.startswith("_")
        }

        # Replace __import__ with a restricted version
        safe_builtins["__import__"] = self._safe_import
        self._namespace["__builtins__"] = safe_builtins

    @staticmethod
    def _safe_import(
        name: str,
        globals: dict | None = None,
        locals: dict | None = None,
        fromlist: tuple = (),
        level: int = 0,
    ) -> Any:
        """Import function that only allows allowlisted modules."""
        top_level = name.split(".")[0]
        if top_level not in _ALLOWED_MODULES:
            raise ImportError(
                f"Import of '{name}' is not allowed. "
                f"Allowed modules: {sorted(_ALLOWED_MODULES)}"
            )
        return __import__(name, globals, locals, fromlist, level)

    def inject(self, name: str, obj: Any) -> None:
        """Inject an object into the REPL namespace.

        Args:
            name: Variable name accessible in code.
            obj: The Python object to inject.
        """
        self._namespace[name] = obj

    def inject_many(self, bindings: dict[str, Any]) -> None:
        """Inject multiple objects into the REPL namespace."""
        for name, obj in bindings.items():
            self.inject(name, obj)

    async def execute(self, code: str) -> ExecutionResult:
        """Execute code in the sandbox with timeout.

        The last expression in the code is captured as the return value
        (similar to a Jupyter cell).  Stdout and stderr are captured.

        Args:
            code: Python source code to execute.

        Returns:
            ExecutionResult with stdout, return_value, and error info.
        """
        try:
            result = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None, self._execute_sync, code
                ),
                timeout=self._timeout,
            )
        except asyncio.TimeoutError:
            result = ExecutionResult(
                success=False,
                error=f"Execution timed out after {self._timeout}s",
            )
        except Exception as exc:
            result = ExecutionResult(
                success=False,
                error=f"Execution error: {exc}",
            )

        self._history.append(result)
        return result

    def _execute_sync(self, code: str) -> ExecutionResult:
        """Synchronous code execution with output capture."""
        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()
        start = time.monotonic()
        return_value = None
        error = None
        success = True

        try:
            with redirect_stdout(stdout_buf), redirect_stderr(stderr_buf):
                # Try to capture the return value of the last expression.
                # Split into statements and last expression.
                try:
                    # Compile as exec first (multi-statement)
                    compiled = compile(code, "<repl>", "exec")
                    exec(compiled, self._namespace)  # noqa: S102

                    # If the code is a single expression, also eval it
                    # for the return value.
                    lines = code.strip().splitlines()
                    if lines:
                        last_line = lines[-1].strip()
                        if last_line and not last_line.startswith(
                            ("import ", "from ", "def ", "class ", "if ",
                             "for ", "while ", "with ", "try ", "raise ",
                             "return ", "del ", "assert ", "#")
                        ) and not last_line.endswith((":", "\\")) and "=" not in last_line.split("#")[0]:
                            try:
                                return_value = eval(  # noqa: S307
                                    last_line, self._namespace
                                )
                            except Exception:
                                pass  # Not an expression, that's fine
                except SyntaxError as exc:
                    success = False
                    error = f"SyntaxError: {exc}"
                except Exception as exc:
                    success = False
                    error = f"{type(exc).__name__}: {exc}"
                    stderr_buf.write(traceback.format_exc())

        except Exception as exc:
            success = False
            error = f"Sandbox error: {exc}"

        duration_ms = (time.monotonic() - start) * 1000

        stdout = stdout_buf.getvalue()[:MAX_OUTPUT_SIZE]
        stderr = stderr_buf.getvalue()[:MAX_OUTPUT_SIZE]

        return ExecutionResult(
            stdout=stdout,
            stderr=stderr,
            return_value=return_value if _is_serializable(return_value) else str(return_value),
            success=success,
            error=error,
            duration_ms=round(duration_ms, 2),
        )

    @property
    def history(self) -> list[ExecutionResult]:
        """Execution history for this session."""
        return list(self._history)

    @property
    def namespace_keys(self) -> list[str]:
        """List of user-visible names in the namespace."""
        return [k for k in self._namespace if k != "__builtins__"]

    def reset(self) -> None:
        """Clear all state and start fresh."""
        self._namespace.clear()
        self._history.clear()
        self._setup_namespace()


def _is_serializable(obj: Any) -> bool:
    """Check if an object can be serialized by Pydantic/JSON."""
    if obj is None:
        return True
    if isinstance(obj, (str, int, float, bool)):
        return True
    if isinstance(obj, (list, tuple)):
        return all(_is_serializable(item) for item in obj)
    if isinstance(obj, dict):
        return all(
            isinstance(k, str) and _is_serializable(v)
            for k, v in obj.items()
        )
    return False


# ── Code generation prompts ───────────────────────────────────────

_CODE_GEN_SYSTEM = (
    "You are a code generation engine for verifying hypotheses against "
    "enterprise hypergraph data. You write concise Python code that checks "
    "claims programmatically. Variables available in the sandbox:\n"
    "- `entities`: list[dict] — entity records with 'name', 'entity_id', etc.\n"
    "- `hyperedges`: list[dict] — decision events with 'decision_type', 'rationale', role players\n"
    "- `traversal`: HypergraphTraversal — call .find_s_connected_components(s), "
    ".hub_nodes(min_degree), .get_s_neighbors(idx, s), .bfs(start, target, s)\n"
    "- `paths`: list — context path data from graph traversal\n"
    "- `spawn_agent(task, **objects)` — delegate a focused subtask to a fresh sub-agent;\n"
    "  returns dict with 'answer' (str), 'confidence' (float), 'result' (any).\n"
    "  Example: r = spawn_agent('count decisions for Acme', entities=entities)\n\n"
    "Not all variables may be present — use only what exists in scope. "
    "Output ONLY valid Python code, no markdown fences, no explanation. "
    "Store your final answer in a variable called `result`."
)

# ── Routing/synthesis prompts (used by OrchestratorAgent) ─────────

_ROUTING_SYSTEM = (
    "You are a routing and synthesis agent for an enterprise decision hypergraph. "
    "You have live graph data and can spawn focused sub-agents for subtasks.\n\n"
    "Available in scope:\n"
    "- `spawn_agent(task, **objects)` — spawn a sub-agent with live object access;\n"
    "  returns dict with 'answer' (str), 'confidence' (float), 'result' (any).\n"
    "- `entities` — list of all entity dicts\n"
    "- `hyperedges` — list of decision event dicts\n"
    "- `traversal` — HypergraphTraversal for graph operations\n\n"
    "Decompose the query, spawn sub-agents for each part, then synthesize.\n"
    "Example:\n"
    "  r1 = spawn_agent('Analyze decisions for Acme Corp', "
    "entities=entities, hyperedges=hyperedges)\n"
    "  r2 = spawn_agent('Find connections between Acme and Globex', "
    "traversal=traversal, hyperedges=hyperedges)\n"
    "  result = {'answer': r1['answer'] + '\\n' + r2['answer'], "
    "'confidence': (r1['confidence'] + r2['confidence']) / 2}\n\n"
    "Output ONLY valid Python code, no markdown fences, no explanation. "
    "Store the synthesized answer in `result` as: {'answer': str, 'confidence': float}."
)

_ROUTING_PROMPT = """Decompose and analyze this query by spawning focused sub-agents.

Query: {query}

Entity mentions detected: {entity_mentions}
Total entities available: {n_entities}
Total decision hyperedges: {n_hyperedges}

Use spawn_agent() to delegate focused subtasks to sub-agents that each receive only
the relevant data they need. Then synthesize their results into a final answer.
Store the final synthesized answer in `result` as a dict with 'answer' and 'confidence'.
"""

_CODE_GEN_PROMPT = """Write Python code to verify this hypothesis against the graph data.

Hypothesis: {hypothesis}

Available data summary:
- {n_entities} entities
- {n_hyperedges} hyperedges
- {n_paths} path components

Check whether the claims in the hypothesis are supported by the actual data.
Store a dict in `result` with keys: "supported" (bool), "findings" (str), "checks" (list of str).
"""


class ReplAgent(BaseAgent):
    """Agent with sandboxed code execution for hypothesis verification.

    Can operate in two modes:
    1. Direct execution: code provided in query.context["code"]
    2. LLM-generated: LLM generates verification code from a hypothesis

    The REPL maintains persistent state, so objects created in one
    execution are available in subsequent calls (within the same session).
    """

    def __init__(
        self,
        llm: BaseLLMConnector | None = None,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        super().__init__()
        self._llm = llm
        self._repl = SandboxedREPL(timeout=timeout)

    @property
    def name(self) -> str:
        return "repl_agent"

    @property
    def repl(self) -> SandboxedREPL:
        """Access the underlying REPL (e.g. to inject objects)."""
        return self._repl

    def load_graph_context(
        self,
        traversal: Any = None,
        entities: list[dict[str, Any]] | None = None,
        hyperedges: list[dict[str, Any]] | None = None,
    ) -> None:
        """Inject graph data into the REPL namespace for code to use."""
        if traversal is not None:
            self._repl.inject("traversal", traversal)
        if entities is not None:
            self._repl.inject("entities", entities)
        if hyperedges is not None:
            self._repl.inject("hyperedges", hyperedges)

    async def process(self, query: AgentQuery) -> AgentResponse:
        """Execute code or generate + execute verification code.

        Context keys:
        - code (str): Direct Python code to execute.
        - hypothesis (str): Hypothesis for LLM to generate verification code.
        - paths (list): Graph path data to inject.
        """
        # Inject any path context provided
        paths = query.context.get("paths", [])
        if paths:
            self._repl.inject("paths", paths)

        # Mode 1: Direct code execution
        code = query.context.get("code")
        if code:
            return await self._execute_and_respond(code, mode="direct")

        # Mode 2: LLM-generated verification code
        hypothesis = query.context.get("hypothesis", query.query)
        if self._llm:
            return await self._verify_with_code(hypothesis, query)

        # No LLM, no code — nothing to execute
        return AgentResponse(
            answer="ReplAgent requires either code in context or an LLM for code generation.",
            confidence=0.0,
        )

    async def _verify_with_code(
        self, hypothesis: str, query: AgentQuery
    ) -> AgentResponse:
        """Generate verification code from hypothesis, then execute it."""
        assert self._llm is not None

        entities = query.context.get("entities", [])
        hyperedges = query.context.get("hyperedges", [])
        paths = query.context.get("paths", [])

        # Ask LLM to generate verification code
        prompt = _CODE_GEN_PROMPT.format(
            hypothesis=hypothesis,
            n_entities=len(entities),
            n_hyperedges=len(hyperedges),
            n_paths=len(paths),
        )

        try:
            generated_code = await self._llm.complete(
                prompt=prompt,
                system_prompt=_CODE_GEN_SYSTEM,
            )
        except Exception as exc:
            logger.warning("Code generation failed: %s", exc)
            return AgentResponse(
                answer=f"Failed to generate verification code: {exc}",
                confidence=0.0,
                metadata={"mode": "code_gen_failed", "error": str(exc)},
            )

        # Strip markdown fences if the LLM included them
        code = generated_code.strip()
        if code.startswith("```"):
            lines = code.split("\n")
            code = "\n".join(lines[1:])
            if code.endswith("```"):
                code = code[:-3].strip()

        return await self._execute_and_respond(
            code, mode="generated", generated_code=code
        )

    async def route_with_code(self, routing_task: str) -> AgentResponse:
        """Generate routing/synthesis code and execute it.

        Used by the orchestrator for complex queries where the LLM decides
        how to decompose the problem and which sub-agents to spawn.
        The sandbox must already have ``spawn_agent`` injected before calling.

        Args:
            routing_task: Natural language description of the routing/synthesis task.

        Returns:
            AgentResponse with the synthesized result.
        """
        if not self._llm:
            return AgentResponse(
                answer="No LLM configured for routing.",
                confidence=0.0,
            )

        try:
            generated_code = await self._llm.complete(
                prompt=routing_task,
                system_prompt=_ROUTING_SYSTEM,
            )
        except Exception as exc:
            logger.warning("Routing code generation failed: %s", exc)
            return AgentResponse(
                answer=f"Routing code generation failed: {exc}",
                confidence=0.0,
                metadata={"mode": "routing_failed", "error": str(exc)},
            )

        code = generated_code.strip()
        if code.startswith("```"):
            lines = code.split("\n")
            code = "\n".join(lines[1:])
            if code.endswith("```"):
                code = code[:-3].strip()

        return await self._execute_and_respond(code, mode="routing", generated_code=code)

    async def _execute_and_respond(
        self,
        code: str,
        mode: str = "direct",
        generated_code: str | None = None,
    ) -> AgentResponse:
        """Execute code and build an AgentResponse from the result."""
        result = await self._repl.execute(code)

        if not result.success:
            return AgentResponse(
                answer=f"Code execution failed: {result.error}",
                confidence=0.1,
                metadata={
                    "mode": mode,
                    "execution": result.model_dump(),
                    "generated_code": generated_code,
                },
            )

        # Build answer from output and return value
        parts: list[str] = []
        if result.stdout.strip():
            parts.append(f"Output:\n{result.stdout.strip()}")
        if result.return_value is not None:
            parts.append(f"Result: {result.return_value}")
        answer = "\n".join(parts) if parts else "Code executed successfully (no output)."

        # Try to extract structured verification result
        repl_result = self._repl._namespace.get("result")
        confidence = 0.6  # Base confidence for executed code
        if isinstance(repl_result, dict):
            if "supported" in repl_result:
                confidence = 0.8 if repl_result["supported"] else 0.3

        # Lift answer and confidence from `result` dict if routing mode set it
        repl_dict = self._repl._namespace.get("result")
        if isinstance(repl_dict, dict) and "answer" in repl_dict:
            answer = str(repl_dict["answer"])
            confidence = float(repl_dict.get("confidence", confidence))

        return AgentResponse(
            answer=answer,
            evidence=[{
                "code": generated_code or code,
                "stdout": result.stdout,
                "return_value": result.return_value,
                "duration_ms": result.duration_ms,
            }],
            confidence=confidence,
            metadata={
                "mode": mode,
                "success": result.success,
                "duration_ms": result.duration_ms,
                "generated_code": generated_code,
                "namespace_keys": self._repl.namespace_keys,
            },
        )


# ── AgentSpawner ──────────────────────────────────────────────────


class AgentSpawner:
    """Callable that spawns focused sub-agents from within REPL code.

    Injected into the REPL namespace so LLM-generated code can autonomously
    delegate subtasks with live object passing — no serialization required.

    Sub-agents get their own fresh REPL with only the objects explicitly
    passed, preventing context rot. Each spawned agent also receives a child
    spawner so true recursive delegation is possible.

    Usage inside REPL code::

        r = spawn_agent(
            "find all decisions involving Acme Corp",
            entities=entities,
            hyperedges=hyperedges,
        )
        print(r["answer"], r["confidence"])

        # Fan-out (width): spawn multiple in a loop
        results = [
            spawn_agent(f"analyse {e['name']}", entity=e, hyperedges=hyperedges)
            for e in entities[:3]
        ]

        # Deep dive (depth): pass a spawner result into another spawn
        summary = spawn_agent("summarise findings", raw=results)
    """

    MAX_SPAWN_DEPTH = 4

    def __init__(self, llm: Any = None, depth: int = 0) -> None:
        self._llm = llm
        # Store config (not the connector instance) so child threads can create
        # their own fresh connectors — an AsyncAnthropic client is bound to the
        # event loop where it was first used and cannot be shared across loops.
        self._llm_config = getattr(llm, "config", None)
        self._depth = depth
        self.spawn_log: list[dict[str, Any]] = []

    def __call__(self, task: str, **objects: Any) -> dict[str, Any]:
        """Spawn a sub-agent synchronously from REPL code.

        Creates a new thread with its own event loop so async spawning
        can be called from synchronous REPL execution without nesting loops.

        Args:
            task: Natural language description of the subtask.
            **objects: Live Python objects injected into the sub-agent's REPL
                       by reference — no serialization.

        Returns:
            dict with keys: answer (str), confidence (float),
            result (value stored in sub-agent's ``result`` variable),
            spawn_log (list of any further spawns the sub-agent made).
        """
        if self._depth >= self.MAX_SPAWN_DEPTH:
            logger.warning(
                "AgentSpawner: max depth %d reached, skipping spawn for: %s",
                self.MAX_SPAWN_DEPTH,
                task[:80],
            )
            return {"answer": "Max spawn depth reached.", "confidence": 0.0, "result": None}

        outcome: dict[str, Any] = {}
        exc_bucket: list[Exception] = []

        def _run() -> None:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                outcome["value"] = loop.run_until_complete(
                    self._spawn_async(task, objects)
                )
            except Exception as exc:
                exc_bucket.append(exc)
            finally:
                loop.close()

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
        thread.join(timeout=30)

        if exc_bucket:
            logger.warning("Sub-agent '%s' raised: %s", task[:60], exc_bucket[0])
            return {"answer": f"Sub-agent error: {exc_bucket[0]}", "confidence": 0.0, "result": None}

        result = outcome.get(
            "value",
            {"answer": "Sub-agent timed out.", "confidence": 0.0, "result": None},
        )
        self.spawn_log.append({
            "task": task,
            "objects_passed": list(objects.keys()),
            "confidence": result.get("confidence", 0.0),
        })
        logger.info(
            "AgentSpawner (depth=%d): spawned '%s' → confidence=%.2f",
            self._depth,
            task[:60],
            result.get("confidence", 0.0),
        )
        return result

    async def _spawn_async(self, task: str, objects: dict[str, Any]) -> dict[str, Any]:
        """Create and run a fresh sub-agent with the given live objects."""
        # Fresh sandbox — sub-agent only sees what's explicitly passed
        child_sandbox = SandboxedREPL()

        # Inject live Python objects by reference (no serialization)
        for name, obj in objects.items():
            child_sandbox.inject(name, obj)

        # Inject a child spawner so the sub-agent can spawn further agents.
        # Pass self._llm so the child spawner can also extract config.
        child_spawner = AgentSpawner(llm=self._llm, depth=self._depth + 1)
        child_sandbox.inject("spawn_agent", child_spawner)

        # Create a FRESH LLM connector for the child agent.
        # We must NOT reuse the parent's connector: its AsyncAnthropic client
        # is bound to the parent event loop and cannot run in this child loop.
        child_llm = None
        if self._llm_config is not None:
            try:
                from src.llm.anthropic import AnthropicConnector
                child_llm = AnthropicConnector(config=self._llm_config)
            except Exception as exc:
                logger.warning("Could not create child LLM connector: %s", exc)

        # Build and wire the child agent with its own fresh sandbox + connector
        child_agent = ReplAgent(llm=child_llm)
        child_agent._repl = child_sandbox

        child_query = AgentQuery(
            query=task,
            context={"injected_objects": list(objects.keys())},
        )
        response = await child_agent.process(child_query)

        # Sub-agent may store a primary result in the `result` variable
        sub_result = child_sandbox._namespace.get("result")

        return {
            "answer": response.answer,
            "confidence": response.confidence,
            "result": sub_result,
            "metadata": response.metadata,
            "spawn_log": child_spawner.spawn_log,
        }
