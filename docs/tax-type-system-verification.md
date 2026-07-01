# Tax Type System Verification

## Audit-Defensible Tax Optimization Through Formal Verification and Dependent Type Theory

Tax codes are not abstract principles of fairness — they are highly specific, interlocking algorithms for calculating liabilities, credits, exemptions, and phase-outs, drafted in prose by legislatures. This medium is woefully inadequate for specifying boundary conditions, variable dependencies, and logical consistency. The result: tax planning is a high-stakes optimization problem trapped inside a combinatorial explosion of conflicting rules.

This document defines how dependent type theory, domain-specific languages (Catala, L4), and theorem provers (Lean 4, Coq) transform tax compliance from probabilistic guesswork into mathematically proven, audit-defensible verification.

---

## 1. The Combinatorial Trap

Optimizing tax outcomes requires navigating a mathematical maze where utilizing one deduction may explicitly or implicitly invalidate another:

```
Allocate child as dependent to Parent A
  → Maximizes Child Tax Credit for Parent A
  → BUT alters Adjusted Gross Income (AGI)
    → Triggers phase-out of senior deduction
    → Reduces Qualified Business Income (QBI) deduction
    → Triggers Net Investment Income Tax (NIIT)
```

These tradeoffs form a combinatorial space where a potentially exponential number of scenarios must be evaluated to mathematically prove that a particular tax plan is optimal. Legacy software built on Python/C++ lacks formal guarantees of correctness — susceptible to silent failures, edge-case bugs, and statute misinterpretation.

---

## 2. Why LLMs Fail at Tax Optimization

LLMs are auto-regressive engines optimized to predict the next most statistically likely token. They lack an underlying engine for deterministic algebraic evaluation and constraint satisfaction. In tax optimization, "roughly correct" is legally invalid.

### 2.1 The Alice and Bob Scenario

An unmarried couple, Alice and Bob, share two qualifying children. The optimization objective: maximize combined Traditional-to-Roth IRA conversions while maintaining an average tax rate strictly below 25%.

Variables: differing baseline incomes ($60K W-2 for Bob, $22K for Alice), investment incomes, Social Security benefits, and S-corp pass-through income classified as Specified Service Trade or Business (SSTB). Interacting phase-outs: Child Tax Credit, age-65 senior deduction, NIIT, and QBI deduction.

### 2.2 Results: Formal Methods vs. Frontier LLMs

| Model | Combined Conversion | Avg Tax Rate | Compliance | Error vs. Optimum |
|-------|-------------------|-------------|------------|-------------------|
| **True Optimum (Lean 4)** | $187,149 | 24.9999% | Feasible, Axis-Tight | $0 |
| **GPT-class (High)** | $195,490 | 25.60% | **Infeasible (Illegal)** | +$8,341 (Overshoot) |
| **Claude-class (Max)** | $179,091 | 24.85% | Suboptimal (Loss) | -$8,058 (Undershoot) |

### 2.3 Failure Mode 1: Overshooting (Legal Infeasibility)

The SSTB classification allows QBI deductions up to 20%, but this benefit phases out as QBI exceeds a threshold while simultaneously colliding with a separate wage-limit phase-in. The intersection reduces the deductible amount **quadratically**. The LLM lacks a symbolic algebra engine and approximates this as linear — under-approximating tax liability, recommending $195,490 in conversions. If executed: average tax rate exceeds 25%, rendering the return non-compliant.

```
LLM's mental model (WRONG):
  QBI_deduction = QBI × 0.20                    # Linear approximation

Actual statutory logic:
  QBI_deduction = QBI × 0.20 × phase_out_factor  # Where:
  phase_out_factor = f(QBI_threshold, wage_limit) # Non-linear interaction
  # Two independent statutory rules collide quadratically
  # The LLM cannot discover this without symbolic evaluation
```

### 2.4 Failure Mode 2: Undershooting (Suboptimality)

The Claude-class model correctly recognized that crossing $200K AGI triggers NIIT and begins CTC phase-out. But it stopped evaluating further conversions at exactly $200K — a safe heuristic from training data. It failed to perform exhaustive search to verify whether pushing past $200K might still yield an average rate below 25%. Result: $8,058 of optimal tax-advantaged conversion space left on the table.

```
LLM's reasoning (INCOMPLETE):
  if AGI > 200_000:
      stop()  # "Crossing this threshold is dangerous"
      # HEURISTIC — not a proof

Formal prover's reasoning (EXHAUSTIVE):
  for conversion in range(179_091, 200_000):
      plan = evaluate(conversion)
      if plan.avg_tax_rate < 0.25:
          optimum = conversion  # Keep pushing
  # Discovers: $187,149 is feasible at 24.9999%
  # The $200K heuristic left $8,058 on the table
```

### 2.5 The Unverifiability Problem

LLMs either produce answers with no trace (un-auditable black box) or generate pages of pseudo-reasoning filled with backtracks, hallucinations, and restarted sub-procedures. Verifying a massive natural language reasoning chain is as costly as computing the plan from scratch. Audit defensibility requires formal mathematical guarantees — each step a formally correct logical transition, each output mathematically guaranteed to be the input of the next.

---

## 3. Structural Non-Monotonicity: Hidden Math Traps in Tax Policy

Human intuition assumes tax codes are monotonic — an increase in gross income should never decrease net take-home pay. Because laws are drafted in prose, subjected to political compromise, and layered with decades of amendments, tax systems frequently violate this assumption. These "cliffs" bypass human lawmakers, policy analysts, and LLMs — but they are instantly flagged by formal theorem proving.

### 3.1 The 50-Lakh Cliff in Indian Tax Logic

During formalization of the Indian ITR-2 form using Lean 4, the system was tasked to verify monotonicity across the entire income tax domain. The assumption: India's "Marginal Relief" provision would guarantee monotonicity.

Lean 4 returned a definitive mathematical counterexample:

| Taxable Income (INR) | Tax Liability (INR) | Net Take-Home (INR) | Marginal Change |
|---------------------|--------------------|--------------------|----------------|
| 5,000,000 | 1,123,200 | 3,876,800 | N/A |
| 5,100,000 | 1,227,200 | 3,872,800 | **-4,000** |

Despite earning 100,000 INR more, the taxpayer **loses** 4,000 INR in net pay.

**Root cause** — an order-of-operations conflict between two statutory variables:

```
Statutory Algorithm (as written):
  Step 1: Compute base_tax + primary_surcharge
  Step 2: Apply marginal_relief (caps the penalty)
  Step 3: Compute cess = (base_tax + surcharge) × 0.04
           ↑ Cess is computed on UNMITIGATED base amounts
           ↑ NOT on the post-relief amount
  Step 4: total_tax = (base_tax + surcharge - relief) + cess

The 4% Cess BYPASSES the marginal relief cap.
It eats directly into the taxpayer's net pay.
```

**The formal fix**: When the code was amended to move Cess computation inside the Marginal Relief block, Lean 4 confirmed perfect monotonicity across all infinite permutations of income. Formalization allows lawmakers to mathematically guarantee fixes before enactment.

At the 2 Crore (20,000,000 INR) threshold, this same flaw penalizes a taxpayer by **36,416 INR** for crossing the boundary.

### 3.2 California Phase-Out Micro-Cliffs

California's personal exemption credits (dependents, blind, seniors) phase out at specific AGI levels. The statute mandates a step-function: reduce credits by $6 for every $2,500, **"or fraction thereof,"** that AGI exceeds $237,035.

| Federal AGI | Phase-Out Trigger | Credit Reduction | Marginal Effect |
|------------|-------------------|-----------------|-----------------|
| $237,035.00 | 0 fractions over threshold | $0.00 | Standard |
| $237,035.01 | 1 fraction over threshold | $6.00 | **Disproportionate** |
| $239,535.01 | 2 fractions over threshold | $12.00 | **Disproportionate** |

Earning one cent over the threshold immediately strips $6 of credit. The phrase "or fraction thereof" creates a step-function, not a continuous decay — the effective marginal tax rate on that specific cent is astronomically high.

### 3.3 The EITC Welfare Cliff

The Earned Income Tax Credit phases out at a fixed percentage per additional dollar earned. When intersecting with simultaneous loss of nutritional assistance, housing subsidies, and payroll taxes, the effective marginal rate on low-income workers can exceed 100%. A minor promotion or additional hours **actively harms** financial survival.

Formal verification maps the exact multi-dimensional intersections of these phase-outs, rendering the true marginal rate visible and computable — something no LLM or human practitioner can reliably do across the full state space.

---

## 4. Foundations: Curry-Howard Isomorphism for Tax Law

### 4.1 From Set Theory to Dependent Types

Standard axiomatic set theory (Zermelo-Fraenkel) suffers from foundational limits — Godel's Incompleteness Theorems show no consistent system can prove its own consistency. Type Theory (specifically the Calculus of Inductive Constructions used by Lean 4 and Coq) assigns every object a strict, computationally verifiable Type. Lean employs an infinite hierarchy of Type Universes (`Type 0`, `Type 1`, `Type 2`...) to prevent Russell's Paradox.

### 4.2 The Core Mapping

| Logic | Type Theory | Tax Domain |
|-------|------------|------------|
| **Proposition** | Type | A tax constraint or statutory requirement |
| **Proof** | Element inhabiting the Type | A valid tax return satisfying all constraints |
| **Implication (A → B)** | Function Type | "If income > threshold, then surcharge applies" |
| **AND (A ∧ B)** | Product Type (tuple) | ABC Test: Prong A AND Prong B AND Prong C |
| **OR (A ∨ B)** | Sum Type (variant) | FLSA: Executive OR Administrative OR Computer |
| **Truth** | Unit Type (uniquely inhabited) | A constraint that always holds |
| **Falsehood** | Empty Type (uninhabited) | A constraint that can never be satisfied |

### 4.3 Constructive Mathematics = Fearless Optimization

Lean defaults to **Constructive Mathematics** — proving existence requires an explicit algorithm, example, or numeric instantiation. Code either compiles definitively or fails instantly.

This enables **fearless optimization**: an automated agent can recursively push financial values higher — increasing Roth conversions dollar by dollar — until the type-checker explicitly rejects the input due to a compliance boundary violation. That boundary IS the absolute, provable mathematical optimum.

```
-- Lean 4 pseudocode for fearless optimization:
def find_optimum (taxpayer : TaxpayerState) : OptimalPlan :=
  let mut conversion := 0
  while is_valid (plan_with_conversion taxpayer (conversion + 1)) do
    conversion := conversion + 1
  -- Type-checker rejected (conversion + 1)
  -- Therefore `conversion` is the proven optimum
  return { conversion := conversion
         , proof := validity_proof taxpayer conversion }
```

---

## 5. Formalizing the Tax Code with Lean 4

### 5.1 Cell-for-Cell Form 1040 Encoding

Each cell on Form 1040 is a dedicated mathematical function deriving its value strictly from raw taxpayer inputs or from deterministically proven outputs of preceding cells:

```
-- Every Form 1040 cell is a pure function:
def total_income (inputs : TaxpayerInputs) : Money :=
  inputs.wages
  + inputs.household_employment
  + inputs.tip_income
  + inputs.medicaid_waivers
  + inputs.dependent_care_benefits
  + inputs.social_security_taxable
  + inputs.capital_gains
  + inputs.business_income

-- Hundreds of cells, dozens of computation chains deep
-- Each cell's output is the proven input to the next
```

### 5.2 Constraint Encoding

The constraint "average tax rate on conversions must not exceed 25%" becomes a logical proposition:

```
-- The constraint IS a Type:
def valid_plan (plan : TaxPlan) : Prop :=
  plan.total_tax_on_conversion / plan.total_conversion < 0.25
  ∧ plan.total_conversion ≥ 0
  ∧ all_statutory_limits_satisfied plan

-- A valid plan IS a proof:
-- If we can construct an element of type (valid_plan p),
-- then p is mathematically proven to be compliant.
```

### 5.3 Proof of Optimality

An optimal plan is proven when adding a single dollar to any variable causes the validity proposition to evaluate to `False`:

```
-- Optimality IS a Type:
def is_optimal (plan : TaxPlan) : Prop :=
  valid_plan plan
  ∧ ¬ valid_plan (plan.with_conversion (plan.conversion + 1))
  -- ^ Adding $1 violates the constraint
  -- Therefore this IS the boundary — proven by the kernel

-- The Lean 4 kernel (minimal, highly audited trusted codebase)
-- verifies every derivation step traces back to the tax code.
-- Result: strictly audit-defensible.
```

---

## 6. Catala: Domain-Specific Language for Socio-Fiscal Logic

### 6.1 The Structural Misalignment Problem

Standard programming makes linear, forward progress. Statutory law uses a base-case and exceptions model — a broad rule in one paragraph, a specific exception in the next, an exception to the exception pages later. Flattening this into nested if-then-else is unreadable, unmaintainable, and error-prone.

### 6.2 Prioritized Default Logic

Catala is built on **Prioritized Default Logic**. Multiple definitions for the same variable can be active simultaneously. At runtime:

1. Evaluate applicability of all rules based on factual inputs
2. If multiple conflicting definitions apply, check priority
3. If one is labeled as a legislative exception to the other, it overrides
4. If two exceptions of equal priority are simultaneously met, **intentionally crash** with a "conflicting definitions" error

```catala
# Base rule: standard deduction applies
scope TaxDeduction:
  definition deduction_amount equals $14,600

# Exception: itemized deductions if higher
scope TaxDeduction:
  exception
  definition deduction_amount under condition
    itemized_total > $14,600
  consequence equals itemized_total

# Exception to exception: AMT disallows certain itemized deductions
scope TaxDeduction:
  exception  
  definition deduction_amount under condition
    subject_to_amt AND itemized_total > $14,600
  consequence equals itemized_total - amt_disallowed_items

# If TWO equal-priority exceptions fire simultaneously
# with no precedence declared → Catala CRASHES with:
# "Error: conflicting definitions for deduction_amount"
# This forces the statutory ambiguity to be resolved by humans,
# not silently resolved by arbitrary code.
```

This deterministic fail-safe prevents software from quietly executing arbitrary interpretations of ambiguous law.

### 6.3 Type Safety for Legal Constructs

Standard languages treat decimals and integers interchangeably, or rely on floating-point arithmetic — notorious for silent precision loss. In tax computation, a rounding error across millions of returns invalidates compliance.

Catala enforces strict, mutually exclusive algebraic data types:

```
Type: Money
  ✓ Money + Money = Money          (add tax amounts)
  ✓ Money - Money = Money          (subtract credits)
  ✓ Money × Decimal = Money        (apply tax rate)
  ✗ Money × Money = ???            (COMPILER ERROR — no legal meaning)
  Rounding: deterministic, to nearest cent, per fiscal rules

Type: Date
  ✓ Date - Date = Duration         (time between events)
  ✓ Date + Duration = Date         (deadline calculation)

Type: Duration
  ✗ Duration(days) > Duration(months)  (RUNTIME ERROR)
  # Months have variable days — comparing is inherently ambiguous
  # Catala forces explicit cast per statutory intent

Type: Decimal  
  ✓ Decimal × Decimal = Decimal    (compound rates)
  ✓ Money / Money = Decimal        (effective tax rate)
```

### 6.4 F* Verified Compiler

Catala's compiler has core compilation steps mathematically proven correct using **F* (F-star)**, Microsoft Research's proof-oriented language combining dependent types with SMT solving. This guarantees the transition from human-readable legal logic to executable machine code preserves absolute semantic equivalence — the compiler itself cannot introduce deviations from the legal text.

### 6.5 Real-World Validation

During formalization of the French family benefits code, Catala's compiler uncovered logical bugs in the French administration's official, decades-old software — demonstrating the danger of relying on legacy code without formal verification. It has also formalized Section 121 of the US IRC (exclusion of gain from principal residence sale, $250K cap with conditioned timelines).

---

## 7. L4: Executable Semantics and Deontic Logic

While Catala excels at socio-fiscal arithmetic, contracts and regulations regulate **behavior over time**. L4 (Singapore Management University, Centre for Computational Law) treats legal contracts as **deterministic finite automata augmented with Deontic Logic**.

### 7.1 Deontic Operators

| Operator | Meaning | Example |
|----------|---------|---------|
| **Obligation** | Party MUST perform action | Lender must disburse funds |
| **Permission** | Party MAY perform action | Lender may seize collateral after default |
| **Prohibition** | Party MUST NOT perform action | Borrower must not transfer collateral |

### 7.2 Contracts as State Machines

```
State: CONTRACT_EXECUTED
  → Obligation(lender, disburse_funds, deadline=30_days)

Event: funds_disbursed
  → Extinguish(Obligation, lender)
  → Create(Obligation, borrower, repay_principal, deadline=12_months)

State: REPAYMENT_DUE
  → if deadline_passed AND NOT repaid:
      → State: VIOLATION
      → Create(Obligation, borrower, pay_late_fee)
      → Create(Permission, lender, seize_collateral)

State: VIOLATION
  → if late_fee_paid AND principal_repaid:
      → State: RESOLVED
  → if 90_days_past_violation:
      → State: DEFAULT
      → Create(Permission, lender, initiate_foreclosure)
```

### 7.3 Static Analysis Before Signature

L4 integrates with **s(CASP)** (Constraint Answer Set Programming) to perform exhaustive analysis on contracts before execution:

- Detect **under-specification**: states with no defined transitions
- Detect **infinite loops**: cyclic obligation chains with no exit
- Detect **logical dead ends**: states from which no party can act
- Generate **Natural Language**: translate executable code back to human-readable Controlled Natural Language for non-technical stakeholders

---

## 8. TypeDB: Symbolic Reasoning Database for Tax Law

### 8.1 Why Not SQL

Relational databases (SQL) are built on Set Theory and Relational Algebra. Modeling tax compliance in SQL requires extensive schema hacks, denormalization, and expensive JOINs that degrade performance and obscure logical intent. A tax regulation linking a taxpayer, their filing status, income sources, deductions, credits, and phase-out thresholds is inherently an N-ary relation — not a chain of binary JOINs.

### 8.2 TypeDB's PERA Model

TypeDB's Polymorphic Entity-Relation-Attribute model is rooted in Type Theory:

```typeql
define

# ============ TAX ENTITIES ============
entity taxpayer, sub enterprise-entity,
    owns filing-status,          # single, married-joint, married-separate, hoh
    owns federal-agi,
    owns state-agi,
    owns total-income,
    plays tax-determination:subject-taxpayer;

entity tax-provision, sub enterprise-entity,
    owns statute-citation,       # "26 USC § 199A", "IRC § 121"
    owns provision-type,         # credit, deduction, exclusion, surcharge
    owns phase-out-threshold,
    owns phase-out-rate,
    owns is-active,
    plays tax-determination:governing-provision,
    plays provision-interaction:interacting-provision;

entity tax-form-cell, sub enterprise-entity,
    owns cell-reference,         # "1040.Line8b", "Schedule1.Line3"
    owns cell-value,
    owns computation-chain-depth,
    plays cell-dependency:source-cell,
    plays cell-dependency:derived-cell;

# ============ TAX RELATIONS ============

# N-ary determination: taxpayer + provision + inputs → result
relation tax-determination, sub decision-event,
    relates subject-taxpayer as participant,
    relates governing-provision as participant @card(1..),
    relates input-cell as participant @card(1..),
    owns determination-result,   # "eligible", "phased-out", "disqualified"
    owns computed-amount,
    owns is-optimal;

# Provision interactions (where phase-outs collide)
relation provision-interaction,
    relates interacting-provision @card(2..),
    owns interaction-type,       # "phase-out-collision", "mutual-exclusion", "cascade"
    owns non-monotonic;          # true if interaction creates a cliff

# Cell dependency chain (Form 1040 computation graph)
relation cell-dependency,
    relates source-cell,
    relates derived-cell,
    owns dependency-type;        # "direct", "conditional", "phase-out-trigger"
```

### 8.3 TypeDB 3.x Functions for Tax Inference

```typeql
# Find all non-monotonic cliffs for a given taxpayer:
fun non_monotonic_cliffs($tp: taxpayer) -> { provision-interaction }:
match
  (subject-taxpayer: $tp, governing-provision: $prov)
    isa tax-determination;
  (interacting-provision: $prov, interacting-provision: $prov2)
    isa provision-interaction, has non-monotonic true;
return { $interaction };

# Trace the full computation chain from a Form 1040 cell:
fun cell_chain($cell: tax-form-cell) -> { tax-form-cell }:
match
  {
    (derived-cell: $cell, source-cell: $source) isa cell-dependency;
    let $ancestor = $source;
  } or {
    (derived-cell: $cell, source-cell: $mid) isa cell-dependency;
    let $ancestor in cell_chain($mid);
  };
return { $ancestor };

# Find all provisions whose phase-outs interact with a given provision:
fun interacting_provisions($prov: tax-provision) -> { tax-provision }:
match
  (interacting-provision: $prov, interacting-provision: $other)
    isa provision-interaction;
return { $other };
```

### 8.4 Inference at Query Time

TypeDB functions evaluate on demand — not materialized. When a tax provision is amended (new phase-out threshold, changed rate), the function re-evaluates against the live schema. No stale cache. No hallucinated compliance status based on last year's rules.

---

## 9. Typed Skills for Tax Optimization

Applying the strongly-typed tool registry to tax domains:

```python
# ──── TAX COMPUTATION SKILLS ────

skill_form_1040 = SkillMorphism(
    skill_id="skill_1040_total_income",
    input_types=["Taxpayer", "TaxYear"],
    output_type="Form1040Result",
    effect_type=EffectType.COMPUTE,
    evaluation_strategy="sequential",
    # Pure function: raw inputs → cell-by-cell computation
    # Every cell output is the proven input to the next
)

skill_qbi_deduction = SkillMorphism(
    skill_id="skill_qbi_199a",
    input_types=["Taxpayer", "BusinessIncome", "TaxProvision"],
    output_type="DeductionResult",
    effect_type=EffectType.THRESHOLD_CHECK,
    constraints={
        "provision.statute_citation": "26 USC § 199A",
        "business.classification": "SSTB",
    },
    evaluation_strategy="conjunction",
    # Phase-out + wage-limit collision = quadratic interaction
    # Must evaluate BOTH thresholds jointly, not independently
)

skill_roth_optimizer = SkillMorphism(
    skill_id="skill_roth_conversion_optimize",
    input_types=["Form1040Result", "TaxConstraint"],
    output_type="OptimalPlan",
    effect_type=EffectType.OPTIMIZE,
    constraints={
        "constraint.type": "max_avg_rate",
    },
    evaluation_strategy="exhaustive",
    # Fearless optimization: push conversion dollar-by-dollar
    # until type-checker rejects → that IS the optimum
)

skill_monotonicity_check = SkillMorphism(
    skill_id="skill_monotonicity_verify",
    input_types=["TaxProvision", "IncomeRange"],
    output_type="MonotonicityResult",
    effect_type=EffectType.VERIFY,
    evaluation_strategy="exhaustive",
    # Scan entire income range for dTakeHome/dIncome < 0
    # Returns counterexample if non-monotonic cliff found
)

# ──── TYPE REJECTION EXAMPLES ────

# ✗ skill_roth_optimizer(taxpayer_inputs, tax_year)
#   REJECTED: expects [Form1040Result, TaxConstraint]
#            received [Taxpayer, TaxYear]
#   Reason: "Must compute Form 1040 first. Cannot optimize
#            without a complete tax computation as input."
#   Fix: Chain skill_form_1040 → skill_roth_optimizer

# ✗ skill_qbi_deduction(taxpayer, w2_income, reg_flsa)
#   REJECTED: expects [Taxpayer, BusinessIncome, TaxProvision]
#            W2 income is not BusinessIncome type
#   Reason: "QBI deduction applies to pass-through business
#            income only, not W-2 wages."

# ✗ skill_monotonicity_check(taxpayer, income_range)
#   REJECTED: expects [TaxProvision, IncomeRange]
#            received [Taxpayer, IncomeRange]  
#   Reason: "Monotonicity is verified per provision, not per
#            taxpayer. Specify which provision to check."

# ──── VALID COMPOSITION CHAIN ────

# Step 1: skill_form_1040(alice, 2025) → Form1040Result
# Step 2: skill_qbi_deduction(alice, alice.s_corp, irc_199a) → DeductionResult
# Step 3: skill_roth_optimizer(form_result, max_rate_25pct) → OptimalPlan
# Step 4: skill_monotonicity_check(irc_199a, 0..500_000) → MonotonicityResult
#
# Each step's output type matches the next step's input type.
# The type-checker verifies the entire chain at composition time.
```

---

## 10. The Neuro-Symbolic Tax Engine

### 10.1 Architecture

The same neuro-symbolic separation as regulatory compliance, adapted for tax:

```
┌──────────────────────────────────────────────────────┐
│  1. INTENT PARSER (Neural Layer)                      │
│     LLM ingests: "Maximize Alice and Bob's Roth       │
│     conversions while keeping tax rate under 25%"     │
│     Outputs: structured JSON →                        │
│       { taxpayers: [alice, bob],                      │
│         objective: "maximize_roth_conversion",        │
│         constraint: { avg_tax_rate: { lt: 0.25 } },  │
│         variables: ["conversion_alice", "conv_bob"],  │
│         provisions: ["CTC", "NIIT", "QBI", "senior"] │
│       }                                               │
├──────────────────────────────────────────────────────┤
│  2. TRUTH ANCHOR (Symbolic Layer — Lean 4 / Catala)   │
│     • Encode all relevant Form 1040 cells as pure fns │
│     • Define validity proposition: avg_rate < 0.25    │
│     • Fearless optimization: push dollar-by-dollar    │
│     • Type-checker rejects at $187,150 → boundary     │
│     • Output: proven optimum + audit-defensible trace  │
│     • Side-check: monotonicity verification on each   │
│       interacting provision                           │
├──────────────────────────────────────────────────────┤
│  3. RESPONSE GENERATOR (Neural Layer)                 │
│     LLM translates formal proof into:                 │
│     "Alice should convert $X, Bob should convert $Y.  │
│      This hits 24.9999% — adding $1 more would        │
│      push over 25% due to QBI/SSTB phase-out          │
│      interaction. Here's the cell-by-cell trace..."   │
│     CONSTRAINED to the symbolic output — no freedom   │
│     to hallucinate different numbers.                 │
└──────────────────────────────────────────────────────┘
```

### 10.2 Glass Box Audit Trail

Every optimization links back to:

- The exact Form 1040 cells traversed
- The exact phase-out thresholds that constrained the result
- The exact dollar amount where the type-checker rejected
- The formal proof that no higher conversion is feasible
- Any non-monotonic cliffs detected during verification

If an auditor asks "why $187,149 and not $190,000?", the system returns the exact computation chain — not a probabilistic guess.

---

## 11. Rules as Code: Levels of Legislative Digitization

| Level | Description | Example | Problem |
|-------|------------|---------|---------|
| **Level 0** | Paper-based legislation | Printed tax code | No machine processing |
| **Level 1** | Digitized text (XML, Akoma Ntoso) | Statute PDFs, HTML | Searchable, not executable |
| **Level 2** | Rules hardcoded in application software | TurboTax, H&R Block | Software developer = unappointed legal interpreter |
| **Level 3** | Declarative rules with separate engine | OpenFisca, Catala APIs | **Goal**: legal logic fully decoupled from application |

### 11.1 Level 3: The Target

When legislation is published as an executable API using Catala or OpenFisca:

```
# Company's payroll software makes an API call:
response = government_api.evaluate(
    statute="26 USC § 213(a)(17)",
    inputs={
        "employee_salary": 95_000,
        "primary_duty": "software_architecture",
        "employer_ein": "XX-XXXXXXX",
    }
)

# Returns a mathematically proven classification:
{
    "determination": "EXEMPT",
    "exemption_category": "Computer Employee",
    "proof_hash": "sha256:abc123...",  # Verifiable proof certificate
    "provisions_evaluated": ["salary_test", "primary_duty_test"],
    "provisions_pruned": ["executive", "administrative", "outside_sales"],
    "timestamp": "2026-07-01T10:30:00Z"
}

# No interpretation ambiguity.
# No proprietary software acting as legal interpreter.
# The government's own prover returns the answer.
```

---

## 12. The Verification Stack

The complete stack from natural language statute to proven tax plan:

```
┌─────────────────────────────────────────┐
│  NATURAL LANGUAGE STATUTE               │
│  "26 USC § 199A: QBI deduction..."      │
└──────────────────┬──────────────────────┘
                   │
          Catala (literate programming)
          Statute text embedded alongside code
                   │
┌──────────────────▼──────────────────────┐
│  CATALA SOURCE                          │
│  Prioritized Default Logic              │
│  Strict Money/Date/Duration types       │
│  Exceptions as native syntax            │
└──────────────────┬──────────────────────┘
                   │
          F*-verified compiler
          Proven semantic preservation
                   │
┌──────────────────▼──────────────────────┐
│  EXECUTABLE CODE (OCaml / Python)       │
│  Cell-by-cell Form 1040 computation     │
└──────────────────┬──────────────────────┘
                   │
          Lean 4 optimization layer
          Fearless dollar-by-dollar search
                   │
┌──────────────────▼──────────────────────┐
│  PROVEN OPTIMAL PLAN                    │
│  $187,149 conversion @ 24.9999%         │
│  Audit-defensible proof certificate     │
│  Non-monotonicity warnings attached     │
└──────────────────┬──────────────────────┘
                   │
          TypeDB provenance graph
          Every cell, every provision,
          every phase-out interaction stored
                   │
┌──────────────────▼──────────────────────┐
│  AUDIT RESPONSE                         │
│  "Here is the exact computation chain   │
│   from raw inputs to final result.      │
│   Every step is a formally correct      │
│   logical transition. The proof          │
│   certificate is machine-verifiable."   │
└─────────────────────────────────────────┘
```

---

## Summary

The future of tax compliance is not statistical approximation — it is formal verification. LLMs hallucinate linear phase-outs, fail to explore non-linear boundaries, and generate unverifiable reasoning chains. By encoding statutory law in dependent type theory, the law ceases to be an ambiguous string of prose and becomes a deterministic mathematical environment where code either compiles or it doesn't — and the boundary where it stops compiling is the proven optimum.

The cost of being wrong in mathematics is a failed paper. The cost of being wrong in tax compliance is an illegal return, a massive fine, or $8,058 left on the table. The type-checker doesn't approximate. It proves.
