# Arcgentica & Recursive REPL Agents — Architecture Reference

> **Source:** [Symbolica AI Blog — SotA ARC-AGI-2 Results with REPL Agents](https://www.symbolica.ai/blog/arcgentica)
> **Code:** [github.com/symbolica-ai/arcgentica](https://github.com/symbolica-ai/arcgentica)

## Why This Matters For Context Graphs

Arcgentica achieved **85.28% on ARC-AGI-2** (state-of-the-art) with ~350 lines of Python.
The architecture maps directly to our multi-agent reasoning layer:

| Arcgentica Concept | Context Graph Equivalent |
|---|---|
| REPL Agent with live Python objects | ExecutiveAgent reasoning over TypeDB objects |
| Recursive delegation (`call_agent()`) | ContextAgent → ExecutiveAgent → GovernanceAgent pipeline |
| Scope = objects with methods, not flat tool lists | Agent scope = hyperedge graph with traversal methods |
| `soft_accuracy()` feedback loop | 2-morphism feedback loop (query → extract → store → richer graph) |
| FinalSolution constraint (structured return) | QueryResponse constraint (answer + evidence + confidence) |
| Sandboxed code execution | Schema-enforced reasoning (TypeDB rejects invalid actions) |

The key insight: **the agent doesn't just "think" — it writes code, runs it, sees results, and iterates.**
Our equivalent: the agent doesn't just answer — it traverses the graph, finds structural evidence,
and the GovernanceAgent validates against curated constraints.

---

## What Arcgentica Is

An open-source ARC-AGI-2 solver by Symbolica AI. ARC-AGI tests **fluid intelligence** —
the ability to reason about novel visual puzzles you've never seen before.

**Score:** 85.28% with Claude Opus 4.6 (previous SotA: ~79%)

**Core:** ~350 lines of Python. No domain-specific heuristics.

---

## How It Works

### 1. Code-Mode Agents with Persistent REPL

Instead of asking the model to "think and output an answer," the agent gets a **live Python
environment** where it can:

```
hypothesize → write code → execute → compare → revise
```

For ARC tasks:
1. Agent inspects training input/output grid pairs
2. Forms a hypothesis about the transformation rule
3. Writes a Python function implementing it
4. Runs it against training examples, checks accuracy
5. If wrong: sees exactly which pixels mismatch, revises
6. Once passing: applies to test inputs

**Why this matters:** The tight feedback loop means the agent self-corrects from concrete
evidence, not just re-prompting. Same principle as our feedback loop where each query
extracts 2-morphisms that enrich the next query.

### 2. Objects as the Interface (Not JSON Tools)

Most agent frameworks give models flat JSON-schema tools: `search()`, `calculate()`.
Agentica gives agents **real Python objects with methods**.

```python
# Flat tool approach (most frameworks):
result = call_tool("database.get_user", {"name": "alice"})

# Agentica approach:
user = database.get_user("alice")
posts = user.get_posts()          # ← methods on the returned object
recent = [p for p in posts if p.date > cutoff]  # ← Python expressiveness
```

**Context Graph parallel:** Our agents don't call flat `search_graph()` tools. They get a
`HypergraphTraversal` object with `.bfs()`, `.get_s_neighbors()`, `.find_s_connected_components()`
methods. The agent discovers capabilities by exploring the object graph — just like a developer.

### 3. Recursive Delegation — The Key Innovation

The agent has `call_agent()` in its scope, which spawns **child agents** with:
- Fresh REPL (clean context window)
- Only the specific state the parent passes in
- Their own return type constraint

```python
# Parent agent is stuck on a complex task
# Instead of struggling with a polluted 100k token context:
insight = call_agent(
    "Analyze just this one training example and tell me what pattern you see",
    scope={"example": training_examples[2]},
    return_type=PatternAnalysis,
)
# Now parent incorporates the focused insight
```

**Why it's powerful:**

| Problem | Solution |
|---|---|
| Context rot (long conversations degrade reasoning) | Fresh context per sub-agent |
| One approach might be wrong | Fan out: 3 sub-agents try different hypotheses |
| Some sub-problems need deep focus | Delegate with only relevant state |
| Hard to know complexity upfront | Agent decides at runtime: go deep or go wide |

**Context Graph parallel:** Our pipeline already does this:
- ContextAgent focuses only on graph traversal (clean scope)
- ExecutiveAgent focuses only on LLM reasoning (separate scope)
- GovernanceAgent focuses only on validation (separate scope)

Arcgentica shows this should be **recursive** — an agent should be able to spawn
sub-agents when it encounters unexpected complexity. Our ExecutiveAgent could
spawn a sub-agent to deeply analyze one specific 2-morphism chain before
synthesizing the final answer.

---

## Results

| Setup | Score | Cost/task |
|---|---|---|
| Agentica + Opus 4.6 (120k) High | **85.28%** | $6.94 |
| Opus 4.6 (120k) High (CoT only) | 79.03% | $3.81 |
| Agentica + GPT 5.2 (XHigh) | 70.27% | $5.03 |
| GPT 5.2 (XHigh) (CoT only) | 59.81% | $2.05 |
| Agentica + Opus 4.5 | 49.58% | $10.40 |
| Opus 4.5 (CoT only) | 28.15% | $1.37 |

**Key takeaway:** The agentic wrapper boosts every model by **6–21 percentage points**.
The model doesn't get smarter — it gets a better environment in which to think.

The Opus 4.5 result is striking: base model 28%, with agent scaffold **50%** — nearly doubled.

---

## Execution Details

- **Pass@2:** Each task gets 2 independent attempts. Diversity helps.
- **Concurrency:** Up to 60 problems concurrently, 1200 concurrent agent invocations.
- **Average agents per task:** 2.6 (most tasks don't need heavy delegation).
- **Max depth:** 10 agents per attempt (9 sub-agents + initial).
- **Prompt caching:** 85% cache hit rate on input tokens — critical for cost.
- **Code timeout:** 5 seconds per execution (catches infinite loops).

---

## Security Model

Since agents run arbitrary Python:

1. **Remote object proxying** — Objects in scope don't exist inside the agent's sandbox.
   They live on the user's side. Agent method calls trigger remote procedure calls.
2. **Nested sandboxes** — WASM inside microVMs. Agent can't access host filesystem.
3. **Type-constrained returns** — Agent MUST return a `FinalSolution` object. Can't
   just output free text.

**Context Graph parallel:** Our TypeDB schema acts as the sandbox. The agent can't
propose relationships that violate the schema — "hallucination is structurally impossible"
because invalid types/roles are rejected at the database level.

---

## What We Should Take From This

### Already doing well:
- Multi-agent pipeline with separated concerns (Context/Executive/Governance)
- Feedback loop (2-morphism extraction enriches future queries)
- Structured returns (QueryResponse with evidence + confidence)
- Schema enforcement as constraint system

### Should adopt:
1. **REPL-style iteration in the agent layer.** Instead of one-shot LLM calls,
   let the ExecutiveAgent write and test hypotheses against the graph before
   committing to an answer.
2. **Recursive delegation.** When a query involves complex multi-hop reasoning,
   the ExecutiveAgent should be able to spawn a focused sub-agent for each
   hop of the path, then synthesize.
3. **Object scope instead of tool lists.** Give agents the `HypergraphTraversal`
   object directly, not flat tool descriptions. Let them call `.bfs()`,
   `.get_s_neighbors()`, `.hub_nodes()` as methods.
4. **Pass@K scoring.** Run K independent query attempts and take the best.
   Cheap with caching, significant accuracy boost.

---

## References

- [SotA ARC-AGI-2 Results with REPL Agents](https://www.symbolica.ai/blog/arcgentica) — Symbolica AI, 2026
- [Beyond Code Mode: Agentica](https://www.symbolica.ai/blog/beyond-code-mode) — Symbolica AI, 2026
- [ARC Prize — What is ARC-AGI?](https://arcprize.org) — François Chollet
- [github.com/symbolica-ai/arcgentica](https://github.com/symbolica-ai/arcgentica) — Open source, ~350 lines
