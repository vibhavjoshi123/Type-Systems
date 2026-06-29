# Type Systems for Legal and Regulatory Domains

## From Mathematical Provers to Regulatory Compliance Engines via Typed N-ary Relations

This document defines how a rich type system — built on TypeDB's PERA model (Polymorphic Entity-Relation-Attribute) with native N-ary relations, typed roles, and categorical morphisms — serves as the formal substrate for regulatory and legal reasoning. The core insight: mathematical theorem provers perform **deep, narrow** search over static axioms, while regulatory provers must perform **wide, shallow** search over mutable human definitions. A purpose-built type system with entity inheritance, relation polymorphism, and defeasible morphism chains is the architecture that bridges this gap.

---

## 1. Theoretical Foundation: Type Theory, Curry-Howard, and Proof Assistants

### 1.1 From Set Theory to Type Theory

Traditionally, mathematics is built on Set Theory and Logic. Mathematical objects are represented as sets, and logic is a separate system used to manipulate propositions about those sets. Theorems are proven by chaining axioms — but as Gödel's Incompleteness Theorem demonstrates, no consistent axiomatic system can prove its own consistency.

**Type Theory** is the alternative foundation. Instead of everything being a "set," every mathematical object has a specific **Type**:

- **Basic Types**: `Bool` (true, false), `String`, `Nat` (0, 1, 2, 3...)
- **Function Types**: `Nat → Nat` (e.g., a successor function that takes a number and returns the next)
- **Product Types**: `A × B` (pairs — requires both components)
- **Sum Types**: `A + B` (either — requires one component)

### 1.2 The Curry-Howard Correspondence: Types ARE Propositions

The power of Type Theory is that it unifies mathematical objects and logic into a single system:

| Type Theory | Logic | Our Regulatory Type System |
|-------------|-------|---------------------------|
| **Type `A`** | Proposition `A` | `RegulatoryDetermination` (a compliance claim) |
| **Element `a : A`** | Proof of `A` | A valid determination instance with all prongs satisfied |
| **Empty type `⊥`** | Unprovable statement | A determination where a required prong evaluates to `false` |
| **Function `A → B`** | Implication `A ⟹ B` | "If entity meets requirements, then exemption follows" |
| **Product `A × B`** | Conjunction `A ∧ B` | ABC Test: Prong A AND Prong B AND Prong C |
| **Sum `A + B`** | Disjunction `A ∨ B` | FLSA: Executive OR Administrative OR Computer exemption |

**Proofs as Elements**: If you can construct an element `a` of type `A` (`a : A`), that element serves as the definitive proof that proposition `A` is true. If a type has no elements (it is empty), the proposition is unprovable. This is exactly how our regulatory prover works:

- **A compliance determination is a type** (the claim that entity X is compliant with regulation Y)
- **A valid determination instance is the proof** (the concrete evidence — prong evaluations, entity data, timestamps)
- **If no valid instance can be constructed, compliance is unproven** (the type is uninhabited)

### 1.3 The Regulatory Prover as Proof Assistant

A **Proof Assistant** is a program that automatically verifies whether a mathematical proof is correct. Instead of a human checking logical steps, the proof assistant runs a **type checker** — if the proof compiles and outputs the correct type, it is mathematically guaranteed correct.

Our regulatory prover is exactly this:

```
Traditional Proof Assistant:
  Theorem: "For all n, n + 0 = n"
  Proof:   Induction on n, with base case and inductive step
  Type checker: Verifies each step produces the expected type

Regulatory Proof Assistant:
  Theorem: "Employee Jane Doe is FLSA-exempt"
  Proof:   Computer Employee branch: salary ≥ $684/week ∧ primary duty = systems design
  Type checker: GovernanceAgent verifies each prong evaluation produces Bool,
                the conjunction produces the expected ExemptionDetermination type,
                and the temporal/jurisdictional constraints hold
```

The GovernanceAgent's coherence check (`beta = alpha . gamma` for diagram commutativity) is literally a type-level verification: it ensures that the composition of 2-morphisms produces the expected type at every step.

### 1.4 Why This Matters for Regulatory Domains

Mathematical proof assistants operate over **static axioms** — the properties of natural numbers don't change. Regulatory proof assistants must handle:

- **Defeasible types**: A type (regulation) can be **uninhabited retroactively** when a court strikes it down
- **Temporal type signatures**: The function `f: LegalEntity × Regulation → Determination` has a hidden parameter — the point in time at which `Regulation` is evaluated
- **Hierarchical type priority**: Federal types preempt state types via 3-morphisms
- **Dynamic type constructors**: New regulations create new types at runtime (legislative amendments)

This is why traditional LLMs fail at compliance: they are statistical pattern matchers, not type checkers. They can generate text that *looks like* a compliance determination, but they cannot *prove* it — the output is not type-checked against the live regulatory schema.

---

## 1.5 Why Type Systems for Law

Traditional knowledge graphs decompose legal relationships into binary triples:

```
(Employee) --classifiedAs--> (Exempt)
(Employee) --underStatute--> (FLSA)
```

This loses the **atomicity** of a legal determination. A worker classification is not two independent facts — it is a single N-ary typed relation binding the worker, the statute, the exemption category, the approver, and the effective date into one indivisible structure, where each participant plays a typed role. Binary graphs cannot express this without reification hacks that destroy type safety.

A type system with **polymorphic N-ary relations** captures this natively: each legal determination is a first-class typed relation with role constraints, cardinality bounds, and attribute ownership — enforced at the schema level, not by application-layer convention.

### The Structural Divergence

| Feature | Mathematical Provers | Our Regulatory Prover |
|---------|---------------------|-----------------------|
| **Search Space** | Deep and narrow (long chains of logic) | Wide and shallow (thousands of interconnected definitions) |
| **Rule Stability** | Static (axioms are eternal) | Dynamic (rules amended constantly by human institutions) |
| **Evaluation Strategy** | Exhaustive exploration, deep backtracking | Structural short-circuiting via typed relation pruning and committing |
| **Knowledge Base** | Pre-trained on historical proofs; closed-world | Agnostic; reasons over live rule sets at inference time |
| **Epistemology** | Monotonic (new truths never invalidate old truths) | Defeasible/Non-monotonic (exceptions actively defeat general rules) |
| **Execution Outcome** | Absolute binary truth or falsity | Defeasible justification; burden-of-proof identification |
| **Error Cost** | Rejected paper, halted compilation | Regulatory fines, class-action lawsuits, constitutional rights suppression |

---

## 2. Extended Entity Types

The base system defines 6 enterprise entities (customer, employee, deal, ticket, policy, metric). The regulatory extension adds 7 new entity types rooted in legal ontology.

### 2.1 New Entity Definitions (Pydantic)

```python
class Regulation(Entity):
    """A statute, rule, or regulatory framework."""
    entity_type: EntityType = EntityType.REGULATION
    jurisdiction: str              # "US-Federal", "EU", "CA-State"
    statute_citation: str          # "29 USC § 213(a)(1)", "GDPR Art. 46"
    effective_date: datetime       # When enacted / last amended
    expiry_date: datetime | None   # Sunset clause, if any
    regulatory_body: str           # "DOL", "EPA", "CJEU", "CPPA"
    rule_type: str                 # "conjunction", "disjunction", "totality"
    is_active: bool = True         # False after repeal / judicial strike-down

class Requirement(Entity):
    """An individual prong, condition, or test within a regulation."""
    entity_type: EntityType = EntityType.REQUIREMENT
    regulation_id: str             # Parent regulation
    prong_label: str               # "Prong A", "Salary Threshold", "Zone Check"
    condition_type: str            # "boolean", "threshold", "geographic", "temporal"
    evaluation_cost: float         # Estimated compute cost (for pruning order)
    is_conjunctive: bool           # True = AND (prune on first false)
    is_disjunctive: bool           # True = OR (commit on first true)

class Exemption(Entity):
    """A granted exception to a regulation or requirement."""
    entity_type: EntityType = EntityType.EXEMPTION
    requirement_id: str            # Which requirement is exempted
    beneficiary_id: str            # Who receives the exemption
    approval_id: str | None        # Decision hyperedge that granted it
    valid_from: datetime
    valid_to: datetime | None      # None = indefinite
    conditions: list[str]          # Conditions that must remain true

class Violation(Entity):
    """A detected breach of a regulatory requirement."""
    entity_type: EntityType = EntityType.VIOLATION
    requirement_id: str
    violating_entity_id: str
    severity: str                  # "minor", "material", "critical"
    detection_date: datetime
    remediation_deadline: datetime | None
    penalty_amount: float | None
    status: str                    # "open", "remediated", "escalated", "litigated"

class Jurisdiction(Entity):
    """A legal jurisdiction with authority over regulations."""
    entity_type: EntityType = EntityType.JURISDICTION
    jurisdiction_code: str         # "US-CA", "EU", "US-FED"
    parent_jurisdiction: str | None  # Federal > State > Municipal
    governing_body: str
    hierarchy_level: int           # 0=supranational, 1=federal, 2=state, 3=local

class LegalEntity(Entity):
    """A corporate or individual entity subject to regulations."""
    entity_type: EntityType = EntityType.LEGAL_ENTITY
    registration_id: str           # EIN, company number, SSN
    entity_class: str              # "corporation", "LLC", "individual", "trust"
    jurisdiction_id: str           # Where incorporated/domiciled
    naics_code: str | None         # Industry classification
    employee_count: int | None
    annual_revenue: float | None

class AuditRecord(Entity):
    """A compliance audit event."""
    entity_type: EntityType = EntityType.AUDIT_RECORD
    auditor_id: str
    scope: str                     # "FLSA overtime", "Title V emissions", "GDPR transfer"
    audit_date: datetime
    findings_count: int
    status: str                    # "scheduled", "in-progress", "completed", "remediation"
    next_audit_date: datetime | None
```

### 2.2 TypeQL Schema Extension

```typeql
define

# ============ REGULATORY ATTRIBUTES ============
attribute jurisdiction-code, value string;
attribute statute-citation, value string;
attribute regulatory-body, value string;
attribute rule-type, value string;
attribute prong-label, value string;
attribute condition-type, value string;
attribute evaluation-cost, value double;
attribute is-conjunctive, value boolean;
attribute is-disjunctive, value boolean;
attribute is-active, value boolean;
attribute valid-from, value datetime;
attribute valid-to, value datetime;
attribute recorded-at, value datetime;
attribute penalty-amount, value double;
attribute hierarchy-level, value long;
attribute naics-code, value string;
attribute employee-count, value long;
attribute annual-revenue, value double;
attribute registration-id, value string;
attribute entity-class, value string;
attribute findings-count, value long;
attribute remediation-deadline, value datetime;

# ============ REGULATORY ENTITIES ============
entity regulation, sub enterprise-entity,
    owns statute-citation,
    owns jurisdiction-code,
    owns effective-date,
    owns regulatory-body,
    owns rule-type,
    owns is-active,
    plays regulatory-determination:governing-regulation,
    plays amendment:original-regulation,
    plays amendment:amended-regulation;

entity requirement, sub enterprise-entity,
    owns prong-label,
    owns condition-type,
    owns evaluation-cost,
    owns is-conjunctive,
    owns is-disjunctive,
    plays regulatory-determination:applicable-requirement,
    plays prong-evaluation:evaluated-prong;

entity exemption, sub enterprise-entity,
    owns valid-from,
    owns valid-to,
    plays regulatory-determination:granted-exemption;

entity violation, sub enterprise-entity,
    owns severity,
    owns remediation-deadline,
    owns penalty-amount,
    plays regulatory-determination:detected-violation,
    plays enforcement-action:triggering-violation;

entity jurisdiction, sub enterprise-entity,
    owns jurisdiction-code,
    owns hierarchy-level,
    plays jurisdiction-hierarchy:parent-jurisdiction,
    plays jurisdiction-hierarchy:child-jurisdiction;

entity legal-entity, sub enterprise-entity,
    owns registration-id,
    owns entity-class,
    owns naics-code,
    owns employee-count,
    owns annual-revenue,
    plays regulatory-determination:subject-entity,
    plays enforcement-action:liable-entity;

entity audit-record, sub enterprise-entity,
    owns findings-count,
    plays regulatory-determination:audit-evidence;
```

---

## 3. Regulatory Relation Types (1-Morphisms)

Legal determinations are inherently N-ary. A single compliance evaluation binds a subject entity, a regulation, multiple requirements, an evaluator, evidence, and an outcome into one atomic typed relation.

### 3.1 Core Regulatory Relations

```typeql
# ============ REGULATORY RELATIONS (N-ARY TYPED) ============

# The central N-ary relation: a compliance determination
relation regulatory-determination, sub decision-event,
    relates governing-regulation as participant,
    relates applicable-requirement as participant @card(1..),
    relates subject-entity as participant,
    relates granted-exemption as participant @card(0..),
    relates detected-violation as participant @card(0..),
    relates audit-evidence as participant @card(0..),
    owns rule-type,           # "conjunction" | "disjunction" | "totality"
    owns is-active;           # Can be invalidated by judicial ruling

# Individual prong evaluation within a determination
relation prong-evaluation, sub context-hyperedge,
    relates evaluated-prong,
    relates evaluating-determination,
    owns status,              # "true" | "false" | "indeterminate"
    owns evaluation-cost;     # Actual compute cost (for adaptive reordering)

# Enforcement action following a violation
relation enforcement-action, sub decision-event,
    relates triggering-violation as participant,
    relates liable-entity as participant,
    relates enforcement-authority as participant,
    owns penalty-amount,
    owns status;              # "proposed" | "final" | "appealed" | "settled"

# Jurisdiction hierarchy (federal > state > municipal)
relation jurisdiction-hierarchy,
    relates parent-jurisdiction,
    relates child-jurisdiction,
    owns timestamp;

# Regulation amendment chain
relation amendment, sub context-hyperedge,
    relates original-regulation,
    relates amended-regulation,
    owns rationale,
    owns effective-date,
    owns timestamp;
```

### 3.2 Concrete Example: FLSA Overtime Exemption

A software developer's overtime exemption under the Computer Employee test, modeled as a single hyperedge:

```
regulatory-determination {
    governing-regulation:  reg_flsa_213a17    # 29 USC § 213(a)(17)
    applicable-requirement: req_salary_test    # Prong: salary >= $684/week
    applicable-requirement: req_primary_duty   # Prong: primary duty = systems analysis/design
    subject-entity:        le_acme_corp        # Employer
    subject-entity:        emp_jane_doe        # Employee being classified
    decision-maker:        emp_hr_director     # Person making determination
    decision-type:         "exemption-classification"
    rationale:             "Computer Employee exemption applies: salary $95K/yr
                            exceeds threshold; primary duty is software architecture.
                            Committed to this branch — Executive/Admin/Outside Sales
                            branches pruned."
    confidence-score:      0.98
    rule-type:             "disjunction"       # Only ONE exemption category needed
    timestamp:             2026-06-15T10:30:00
}
```

**Cardinality**: 5 entities. This is a true 5-ary typed relation — no binary decomposition preserves the atomicity of the determination.

### 3.3 Concrete Example: EPA Title V Permit — Pruned

A manufacturing facility's Title V permit evaluation where geographic pruning eliminates chemical analysis:

```
regulatory-determination {
    governing-regulation:  reg_caa_title_v     # Clean Air Act Title V
    applicable-requirement: req_industrial_src  # Prong: is industrial source?
    applicable-requirement: req_100_ton_yr     # Prong: >100 tons/yr criteria pollutant?
    applicable-requirement: req_nonattainment  # Prong: in non-attainment zone?
    subject-entity:        le_midwest_mfg      # Manufacturing facility
    decision-type:         "permit-determination"
    rationale:             "Facility is in Polk County (attainment zone for all criteria
                            pollutants). Prong C (non-attainment) = false. Conjunction
                            short-circuited — chemical analysis of VOC/NOx/PM2.5
                            emissions PRUNED. No Title V permit required."
    confidence-score:      0.99
    rule-type:             "conjunction"
    timestamp:             2026-06-15T14:00:00
}
```

Three prong-evaluation sub-relations record what happened:

```
prong-evaluation { evaluated-prong: req_nonattainment, status: "false", evaluation-cost: 0.01 }
prong-evaluation { evaluated-prong: req_industrial_src, status: "not-evaluated", evaluation-cost: 0.0 }
prong-evaluation { evaluated-prong: req_100_ton_yr,    status: "not-evaluated", evaluation-cost: 0.0 }
```

The prover tested the cheapest condition first and **pruned** the remaining tree.

### 3.4 Concrete Example: GDPR Cross-Border Transfer — Temporal Invalidation

```
regulatory-determination {
    governing-regulation:  reg_gdpr_art46       # GDPR Article 46
    applicable-requirement: req_adequacy_decision # Prong: adequate protection?
    applicable-requirement: req_transfer_mechanism # Prong: valid legal mechanism?
    subject-entity:        le_euro_analytics     # European data controller
    subject-entity:        le_us_cloud_inc       # US data processor
    detected-violation:    viol_schrems_ii       # Privacy Shield invalidated
    decision-type:         "cross-border-transfer"
    rationale:             "Privacy Shield mechanism struck down by CJEU (Schrems II,
                            July 2020). Transfer mechanism prong = false. Company
                            must use Standard Contractual Clauses or demonstrate
                            supplementary measures. Determination re-evaluated against
                            2023 Data Privacy Framework."
    confidence-score:      0.85
    rule-type:             "conjunction"
    is-active:             false                 # Superseded by DPF determination
    valid-from:            2020-07-16T00:00:00   # Schrems II ruling date
    valid-to:              2023-07-10T00:00:00   # DPF adoption date
    timestamp:             2020-07-16T12:00:00
}
```

This relation is **temporally bounded** — `is-active: false` after the Data Privacy Framework replaced it. The system never reasons over invalidated determinations without flagging them.

---

## 4. Regulatory 2-Morphisms (Meta-Relations)

The existing 2-morphism types (SEQUENCE, PRECEDENT, OVERRIDE, GENERALIZATION, EXCEPTION, JUSTIFICATION) extend naturally to legal reasoning. We add three domain-specific types.

### 4.1 Extended MorphismType Enum

```python
class MorphismType(StrEnum):
    # Existing types
    SEQUENCE = "sequence"
    PRECEDENT = "precedent"
    OVERRIDE = "override"
    GENERALIZATION = "generalization"
    EXCEPTION = "exception"
    JUSTIFICATION = "justification"
    # New regulatory types
    JUDICIAL_INVALIDATION = "judicial-invalidation"   # Court strikes down rule
    LEGISLATIVE_AMENDMENT = "legislative-amendment"   # Statute amended
    REGULATORY_PREEMPTION = "regulatory-preemption"   # Federal preempts state
```

### 4.2 TypeQL 2-Morphism Extensions

```typeql
# Court ruling invalidates a prior regulatory determination
relation judicial-invalidation, sub precedent-chain,
    relates invalidated-determination as precedent-decision,
    relates invalidating-ruling as derived-decision,
    owns statute-citation,        # Case citation (e.g., "Schrems II, C-311/18")
    owns jurisdiction-code;

# Legislative amendment supersedes prior determination
relation legislative-amendment, sub precedent-chain,
    relates superseded-determination as precedent-decision,
    relates amended-determination as derived-decision,
    owns effective-date;

# Federal regulation preempts conflicting state regulation
relation regulatory-preemption, sub precedent-chain,
    relates state-determination as precedent-decision,
    relates federal-determination as derived-decision,
    owns jurisdiction-code;
```

### 4.3 Precedent Chains in Practice

The Schrems II → Data Privacy Framework transition as a 2-morphism chain:

```
2-morphism chain:
  [det_privacy_shield_2019]
       |
       | judicial-invalidation (Schrems II, C-311/18, 2020-07-16)
       v
  [det_no_valid_mechanism_2020]
       |
       | legislative-amendment (EU-US DPF, 2023-07-10)
       v
  [det_dpf_transfer_2023]
```

Each arrow is a 2-morphism (a relation between relations). The governance agent verifies coherence: the chain must be temporally monotonic (each amendment's `effective_date` > predecessor's) and jurisdictionally valid (CJEU has authority over GDPR determinations).

### 4.4 Exception Overrides with Catalyst-Approver Pattern

The existing `ExceptionOverride` model maps directly to regulatory exemptions. The "catalyst" from the Chemical Reaction Networks isomorphism is the approving authority:

```python
# Employee classified as exempt despite edge-case ambiguity
ExceptionOverride(
    base_decision_id="det_flsa_nonexempt_default",     # Default: employee
    exception_decision_id="det_computer_exemption",     # Exception: exempt
    override_rationale="Computer Employee exemption under 29 USC § 213(a)(17). "
                       "Primary duty test satisfied: >50% time on systems design.",
    approver_id="emp_hr_director",                      # Catalyst/approver
    timestamp=datetime(2026, 6, 15, 10, 30)
)
```

---

## 5. Short-Circuiting via Typed Relation Traversal

The type system's s-adjacency constraint (two relations are s-adjacent if they share ≥ s typed entities) is the computational mechanism for **structural short-circuiting** — the regulatory prover's alternative to exhaustive backtracking.

### 5.1 Pruning Strategy (Conjunctions)

For conjunctive regulations (all prongs must be true), the prover:

1. **Orders prongs by `evaluation_cost`** (cheapest first)
2. **Evaluates sequentially** — each prong is a sub-relation
3. **On first `false`**: halts evaluation, marks remaining prongs as `not-evaluated`
4. **Records the pruning** in the determination's rationale

```python
async def evaluate_conjunction(
    self,
    requirements: list[Requirement],
    context: dict,
) -> tuple[bool, list[ProngResult]]:
    """Short-circuit conjunction: prune on first false.
    
    Orders by evaluation_cost to minimize wasted compute.
    From EPA Title V example: geographic check ($0.01) before
    chemical stoichiometry ($50.00).
    """
    ordered = sorted(requirements, key=lambda r: r.evaluation_cost)
    results = []
    for req in ordered:
        result = await self._evaluate_prong(req, context)
        results.append(result)
        if not result.value:
            # PRUNE: remaining prongs are irrelevant
            for remaining in ordered[len(results):]:
                results.append(ProngResult(
                    requirement_id=remaining.entity_id,
                    value=None,
                    status="pruned",
                    evaluation_cost=0.0,
                ))
            return False, results
    return True, results
```

### 5.2 Committing Strategy (Disjunctions)

For disjunctive regulations (any prong sufficient), the prover:

1. **Orders branches by likelihood** (highest first, using learned priors from π_rel)
2. **Evaluates in parallel** (fan out via `asyncio.gather`)
3. **On first `true`**: cancels remaining branches, commits to this path
4. **Records the commitment** and which branches were abandoned

```python
async def evaluate_disjunction(
    self,
    exemption_branches: list[ExemptionBranch],
    context: dict,
) -> tuple[bool, str, list[BranchResult]]:
    """Short-circuit disjunction: commit on first true.
    
    From FLSA example: Computer Employee exemption committed,
    Executive/Administrative/Professional/Outside Sales abandoned.
    """
    ordered = sorted(exemption_branches, key=lambda b: -b.prior_probability)
    results = []
    for branch in ordered:
        result = await self._evaluate_branch(branch, context)
        results.append(result)
        if result.value:
            # COMMIT: this branch is sufficient
            for remaining in ordered[len(results):]:
                results.append(BranchResult(
                    branch_id=remaining.branch_id,
                    value=None,
                    status="abandoned",
                ))
            return True, branch.branch_id, results
    return False, None, results
```

### 5.3 S-Adjacency for Regulatory Clustering

Two regulatory determinations are **s-adjacent** if they share ≥ s entities. At s=2 (our default), this naturally clusters related compliance events:

```
det_flsa_exemption:     {emp_jane_doe, le_acme_corp, reg_flsa, req_salary}
det_abc_test_ca:        {emp_jane_doe, le_acme_corp, reg_ab5_ca, req_prong_b}
                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                         IS = 2 (emp_jane_doe, le_acme_corp) → s-adjacent
```

These two determinations — federal FLSA exemption and California ABC test — are s-adjacent because they concern the same worker at the same company. The traversal engine discovers this automatically, enabling cross-jurisdictional conflict detection.

---

## 6. TypeDB 3.x Functions for Regulatory Inference

TypeDB 3.x replaces 2.x rules with **explicit functions** — computed values evaluated on demand, not materialized. This maps perfectly to regulatory inference where rules change and results must reflect the live state.

### 6.1 Transitive Jurisdiction Hierarchy

```typeql
fun jurisdiction_ancestors($j: jurisdiction) -> { jurisdiction }:
match
  {
    (child-jurisdiction: $j, parent-jurisdiction: $parent)
      isa jurisdiction-hierarchy;
    let $ancestor = $parent;
  } or {
    (child-jurisdiction: $j, parent-jurisdiction: $parent)
      isa jurisdiction-hierarchy;
    let $ancestor in jurisdiction_ancestors($parent);
  };
return { $ancestor };
```

Usage — find all regulations that apply to a California entity (CA → US-Federal → Supranational):

```typeql
match
  $entity isa legal-entity, has jurisdiction-code "US-CA";
  $j isa jurisdiction, has jurisdiction-code "US-CA";
  let $ancestor in jurisdiction_ancestors($j);
  $ancestor has jurisdiction-code $code;
  $reg isa regulation, has jurisdiction-code $code, has is-active true;
```

### 6.2 Regulatory Applicability Check

```typeql
fun active_regulations_for($entity: legal-entity) -> { regulation }:
match
  {
    ($entity, $reg) isa regulatory-determination;
    $reg isa regulation, has is-active true;
  };
return { $reg };
```

### 6.3 Precedent Chain Reachability (Defeasible)

```typeql
fun precedent_reachable($det: regulatory-determination) -> { regulatory-determination }:
match
  {
    (precedent-decision: $det, derived-decision: $derived)
      isa precedent-chain;
    let $target = $derived;
  } or {
    (precedent-decision: $det, derived-decision: $mid)
      isa precedent-chain;
    let $target in precedent_reachable($mid);
  };
return { $target };
```

This is evaluated **on demand** — not materialized — so invalidated precedents (judicial-invalidation 2-morphisms) are automatically excluded when the underlying data changes. No stale cache. No hallucinated legal validity.

### 6.4 Defeasible Override Resolution

```typeql
fun effective_determination($entity: legal-entity, $reg: regulation)
    -> { regulatory-determination }:
match
  (subject-entity: $entity, governing-regulation: $reg) isa regulatory-determination,
    has timestamp $t, has is-active true;
  not {
    (base-decision: $det, exception-decision: $override) isa exception-override;
    $override has timestamp $t2;
    $t2 > $t;
  };
return { $det };
```

This function returns only the **latest undefeated determination** — if an exception override exists with a later timestamp, the base determination is excluded. This is defeasible reasoning in TypeQL: the general rule holds until defeated by a specific exception.

---

## 7. Bi-Temporal Model for Regulatory Versioning

Legal facts have two independent time axes. A regulation enacted in 2020 but recorded in our system in 2024 has different `valid_from` and `recorded_at` timestamps. This matters for audit trails and retroactive analysis.

### 7.1 Temporal Attributes

| Attribute | Meaning | Example |
|-----------|---------|---------|
| `valid_from` | When the legal fact becomes true in the real world | Privacy Shield struck down: 2020-07-16 |
| `valid_to` | When the legal fact ceases to be true | Privacy Shield validity ends: 2020-07-16 |
| `recorded_at` | When our system ingested this fact | System updated: 2020-07-20 |
| `effective_date` | When a regulation/amendment takes effect | DPF adopted: 2023-07-10 |
| `timestamp` | When the determination was made | Compliance check run: 2026-06-15 |

### 7.2 Temporal Queries

**"What was our compliance status as of 2021-01-01?"**

```typeql
match
  $det isa regulatory-determination,
    has valid-from $vf,
    has is-active $active,
    has timestamp $t;
  $vf <= 2021-01-01T00:00:00;
  { $active == true; } or {
    $det has valid-to $vt;
    $vt > 2021-01-01T00:00:00;
  };
```

This returns determinations that were valid at that point-in-time — even if they've since been invalidated. Essential for retroactive audits.

---

## 8. Agent Architecture for Regulatory Reasoning

The existing 4-agent architecture (Context → Executive → Governance → Orchestrator) maps directly to the neuro-symbolic separation required for legal compliance.

### 8.1 Agent Role Mapping

| Agent | Regulatory Role | Mathematical Analogy | Layer |
|-------|----------------|---------------------|-------|
| **ContextAgent** | Finds s-adjacent regulatory clusters; identifies which regulations apply to an entity | 1-morphism traversal | **Symbolic** — graph traversal only |
| **ExecutiveAgent** | Proposes exemption/violation determinations; generates 2-morphism chains | 2-morphism proposal via LLM | **Neural** — intent parsing |
| **GovernanceAgent** | Verifies coherence of determination chains; checks temporal validity, jurisdictional authority | Diagram commutativity | **Symbolic** — deterministic verification |
| **OrchestratorAgent** | Routes compliance queries; triggers governance checks on keywords | Dynamic routing | **Control plane** |

### 8.2 The Glass Box Audit Trail

This architecture implements the **neuro-symbolic separation** described in the Veriprajna tax engine pattern:

```
┌─────────────────────────────────────────────────────┐
│  1. INTENT PARSER (Neural Layer — ExecutiveAgent)    │
│     LLM ingests: "Is Jane Doe exempt from overtime?" │
│     Outputs: structured JSON → entity IDs, statute   │
│     references, exemption category hypothesis        │
├─────────────────────────────────────────────────────┤
│  2. TRUTH ANCHOR (Symbolic Layer — ContextAgent +    │
│     GovernanceAgent)                                 │
│     • ContextAgent: BFS/Yen's over regulation graph  │
│     • Prong evaluation: conjunction/disjunction       │
│       short-circuiting                                │
│     • GovernanceAgent: coherence verification,        │
│       temporal validity, jurisdiction authority        │
│     Output: deterministic boolean + audit trace       │
├─────────────────────────────────────────────────────┤
│  3. RESPONSE GENERATOR (Neural Layer — Executive)    │
│     LLM translates audit trace into human-readable   │
│     explanation. CONSTRAINED to the symbolic output — │
│     no freedom to hallucinate legal conclusions.      │
└─────────────────────────────────────────────────────┘
```

Every determination links back to specific graph paths, prong evaluations, and statute citations. If an auditor asks "why was this worker classified as exempt?", the system returns the exact nodes traversed, branches committed to, and branches pruned — not a probabilistic guess.

---

## 9. Worked Examples with Seed Data

### 9.1 Employment Law: FLSA Disjunction (Commit)

**Scenario**: Classify Sarah Chen (employee `emp_001`) for overtime exemption at Acme Corp.

```
Entities in typed relation:
  emp_001     (Sarah Chen, VP Sales, department=sales)
  le_acme     (Acme Corp, 500 employees, $50M revenue)
  reg_flsa    (FLSA 29 USC § 213(a)(1))
  req_exec_a  (Manages 2+ employees)
  req_exec_b  (Management is primary duty)
  req_exec_c  (Authority to hire/fire)
  req_salary  (Salary >= $684/week)

Prover execution:
  1. Root: DISJUNCTION over {Executive, Administrative, Professional,
           Computer, Outside Sales}
  2. Evaluate Executive branch (highest π_rel for VP Sales role):
     a. req_salary: $95K/yr ÷ 52 = $1,827/week >= $684 → TRUE
     b. req_exec_a: Sarah manages 4 account executives → TRUE
     c. req_exec_b: Primary duty is department management → TRUE
     d. req_exec_c: Has hire/fire authority per HR records → TRUE
  3. COMMIT to Executive Exemption.
  4. ABANDON: Administrative, Professional, Computer, Outside Sales branches.

Result: EXEMPT (Executive)
Confidence: 0.97
Branches evaluated: 1 of 5
Prongs evaluated: 4 of 4 (conjunction within committed branch)
Computational savings: ~80% (4 branches × ~4 prongs each = 16 prongs skipped)
```

### 9.2 Environmental: Title V Conjunction (Prune)

**Scenario**: New backup generator at Acme Corp's Iowa facility.

```
Entities in typed relation:
  le_acme_iowa  (Acme Corp Iowa facility, Polk County)
  reg_caa_v     (Clean Air Act Title V)
  req_ind_src   (Is industrial source? eval_cost=0.05)
  req_100_ton   (>100 tons/yr criteria pollutant? eval_cost=15.0)
  req_nonattn   (In non-attainment zone? eval_cost=0.01)

Prover execution (ordered by evaluation_cost):
  1. Root: CONJUNCTION (all three must be true)
  2. req_nonattn (cost=0.01): Polk County, Iowa → ATTAINMENT zone
     → FALSE
  3. PRUNE: req_ind_src and req_100_ton not evaluated.
     Chemical stoichiometry of VOC/NOx/PM2.5 entirely bypassed.

Result: NO PERMIT REQUIRED
Confidence: 0.99
Prongs evaluated: 1 of 3
Computational savings: ~99% (chemical analysis at cost=15.0 pruned)
```

### 9.3 Data Privacy: GDPR Temporal Invalidation

**Scenario**: Euro Analytics transfers user data to US Cloud Inc.

```
Timeline of determinations:

[2019] det_privacy_shield
  Entities: {le_euro_analytics, le_us_cloud, reg_gdpr_46, req_adequacy}
  Result: TRANSFER PERMITTED (Privacy Shield valid)
  valid_from: 2016-07-12, valid_to: 2020-07-16

  ↓ judicial-invalidation (Schrems II, C-311/18)

[2020] det_schrems_ii_block
  Entities: {le_euro_analytics, le_us_cloud, reg_gdpr_46, viol_no_mechanism}
  Result: TRANSFER BLOCKED (no valid mechanism)
  valid_from: 2020-07-16, valid_to: 2023-07-10

  ↓ legislative-amendment (EU-US DPF)

[2023] det_dpf_transfer
  Entities: {le_euro_analytics, le_us_cloud, reg_gdpr_46, req_dpf_adequacy}
  Result: TRANSFER PERMITTED (DPF valid)
  valid_from: 2023-07-10, valid_to: null (current)

Query: "Can we transfer data to US Cloud Inc today?"
  → GovernanceAgent traverses 2-morphism chain
  → Finds det_dpf_transfer is latest, is_active=true, valid_to=null
  → Verifies DPF adequacy requirement still holds
  → Result: PERMITTED under DPF
  → Audit trail includes full temporal chain of invalidations
```

---

## 10. Defeasible Logic in the Type System

### 10.1 Mapping Defeasibility to 2-Morphisms

In defeasible logic, a rule holds until a **defeater** overrides it. Our 2-morphism architecture encodes this natively:

| Defeasible Concept | Type System Encoding |
|-------------------|---------------------|
| **General rule** | Base `regulatory-determination` typed relation |
| **Strict defeater** | `judicial-invalidation` 2-morphism (sets `is_active=false`) |
| **Defeasible defeater** | `exception-override` 2-morphism (higher-priority exception) |
| **Burden of proof** | `rule_type` on regulation ("conjunction" = burden on challenger, "disjunction" = burden on claimant) |
| **Priority ordering** | `hierarchy_level` on jurisdiction (federal > state > local) |

### 10.2 The ABC Test as Defeasible Logic

Under California AB5, the **default** is employment. The hiring entity bears the burden of defeating all three prongs:

```
Default:     worker IS employee          (base determination)
Defeater A:  free from control           (exception-override, prong A)
Defeater B:  outside usual business      (exception-override, prong B)
Defeater C:  independently established   (exception-override, prong C)

Classification = employee UNLESS (A ∧ B ∧ C)
  → If ANY defeater fails, default holds
  → Prune on first false defeater
```

This is a strict conjunction of defeaters — the exact structure our `evaluate_conjunction` handles with cost-ordered pruning.

### 10.3 Federal Preemption as Higher-Order Morphism

When federal regulation preempts state regulation, this is a **3-morphism** — a relation between 2-morphisms:

```
Level 0: Entities (worker, company)
Level 1: Hyperedges (state determination, federal determination)
Level 2: 2-morphisms (state precedent chain, federal precedent chain)
Level 3: 3-morphism (federal-preemption relation between the two chains)
```

Our n-morphism architecture handles this via the self-referential `n-morphism` relation where `source-morphism` and `target-morphism` roles are played by other morphisms at any level.

---

## 11. Integration with Existing Memory System

### 11.1 Skill Store for Regulatory Patterns

The self-evolving memory's `skill_store.py` learns regulatory evaluation patterns:

```python
# After repeated FLSA exemption checks, the system learns:
Skill(
    skill_id="skill_flsa_computer_exempt",
    domain="employment-law",
    description="Computer Employee exemption classification",
    trigger_patterns=["overtime exempt", "computer employee", "FLSA 213(a)(17)"],
    learned_prior=0.82,  # π_rel: 82% of software workers qualify
)
```

### 11.2 Intent Resolution for Legal Queries

The `intent_resolver.py` maps natural language to regulatory entities:

```python
# "Is our Iowa plant exempt from Title V?"
domain_hints = ["environmental", "emissions", "Title V"]
entity_hints = ["le_acme_iowa", "reg_caa_v"]
# → Routes to ContextAgent with regulatory-determination traversal
```

### 11.3 Progressive Loading for Large Regulatory Graphs

The `context_loader.py` 3-tier JIT loading prevents loading the entire regulatory corpus:

```
Tier 1 (Metadata): Load regulation IDs, jurisdiction codes, active status
Tier 2 (Skills):   Load applicable regulatory skills for this entity type
Tier 3 (Entities): Load only the specific prongs and requirements needed
                    for the determination being evaluated
```

---

## 12. The Rules-as-Code Interface

The architecture is designed to consume **Rules as Code** (RaC) APIs — regulations published as executable code by governing bodies.

### 12.1 External Rule Source Integration

```python
class RulesAsCodeConnector:
    """Fetches live regulatory rules from government APIs.
    
    When legislation is published as an executable API,
    the system makes an API call to the official rule-set
    rather than maintaining a stale local copy.
    """
    
    async def fetch_rule(
        self, statute_citation: str, jurisdiction: str
    ) -> RegulationGraph:
        """Fetch the current regulatory graph for a statute.
        
        Returns a subgraph of requirements, thresholds, and
        exemptions reflecting the LIVE state of the law.
        """
        ...
    
    async def evaluate_against_live_rules(
        self, entity: LegalEntity, regulation: Regulation
    ) -> RegulatoryDetermination:
        """Submit entity metadata to the official rule API.
        
        The government's published prover returns a
        mathematically proven classification — no
        interpretation ambiguity.
        """
        ...
```

### 12.2 Catala / s(CASP) Integration Points

The symbolic layer can delegate to external provers:

| Prover | Language | Strength | Integration Point |
|--------|----------|----------|-------------------|
| **Catala** | Default calculus DSL | Exception-as-syntax; mirrors statute structure | `GovernanceAgent._evaluate_statutory_rule()` |
| **Blawx / s(CASP)** | Constraint ASP | Proof trees; defeasible rules; explanation generation | `ExecutiveAgent._extract_2morphisms()` |
| **Datalog** | Declarative logic | DOM verification; consent auditing; taint tracking | `ContextAgent._evaluate_privacy_constraints()` |

---

## 13. Strongly-Typed Tool Registry — Fixing MCP Shortcomings

The CategoryScienceClaw architecture demonstrates the same Curry-Howard mechanism applied to scientific discovery: artifacts have types, tools are morphisms between types, and the type system rejects invalid compositions before compute spends a cycle.

### 13.1 Skills as Typed Morphisms

Every skill is a strict morphism `f: A → B`. The type system rejects invalid tool application before execution.

**CategoryScienceClaw (Chemistry Domain):**

```
# Typed skills in materials science:
Skill: extract_features
  Type: Protein → FeatureVector
  
Skill: compute_stiffness
  Type: FeatureVector → StiffnessTensor

Skill: fit_surrogate
  Type: (FeatureVector, StiffnessTensor) → SurrogateModel

# REJECTED at type-check: cannot feed a Protein directly to fit_surrogate
# fit_surrogate expects (FeatureVector, StiffnessTensor), not Protein
# The category theory engine blocks this BEFORE any compute happens
```

**Our Regulatory Domain — Same Pattern, Different Type Alphabet:**

```python
# Typed skills for regulatory compliance:

# Skill 1: Classification (disjunction — commit on first true)
SkillMorphism(
    skill_id="skill_flsa_exemption_check",
    input_types=["LegalEntity", "Regulation"],
    output_type="RegulatoryDetermination",
    effect_type="CLASSIFY",
    constraints={"regulation.rule_type": "disjunction"},
)

# Skill 2: Threshold evaluation (conjunction — prune on first false)
SkillMorphism(
    skill_id="skill_title_v_check",
    input_types=["LegalEntity", "Regulation"],
    output_type="RegulatoryDetermination",
    effect_type="THRESHOLD_CHECK",
    constraints={"regulation.regulatory_body": "EPA"},
)

# Skill 3: Penalty calculation (requires a violation as input)
SkillMorphism(
    skill_id="skill_penalty_calculator",
    input_types=["Violation", "Regulation"],
    output_type="EnforcementAction",
    effect_type="PENALTY_CALCULATE",
)

# TYPE REJECTION EXAMPLES:
#
# ✗ skill_penalty_calculator(le_acme_corp, reg_flsa)
#   REJECTED: input_types expect [Violation, Regulation]
#   but received [LegalEntity, Regulation]
#   → "Cannot calculate penalty without a Violation"
#
# ✗ skill_flsa_exemption_check(viol_emissions, reg_caa_v)
#   REJECTED: CLASSIFY skill expects LegalEntity, not Violation
#   → "Cannot classify a violation for exemption"
#
# ✓ skill_flsa_exemption_check(le_acme_corp, reg_flsa)
#   ACCEPTED: types match, proceeds to execution
```

The TypeDB schema enforces this at insert time — a `CLASSIFY` skill cannot inhabit a `PENALTY_CALCULATE` proposition. The `proves` relation's typed roles reject the composition before any LLM call or prong evaluation fires.

### 13.2 Append-Only Provenance Graph for Regulatory Determinations

Every exploration branch is preserved as an immutable DAG. Every artifact links to its parents + the skill that created it. Nothing is overwritten — if a determination is later invalidated, the invalidation is a new node, not a deletion.

**Regulatory Provenance Graph:**

```
                    ┌─────────────────────┐
                    │ le_acme_corp        │  Type: LegalEntity
                    │ emp_jane_doe        │  Type: Employee
                    │ reg_flsa            │  Type: Regulation
                    └────┬───────────┬────┘
                         │           │
  skill_executive_check  │           │  skill_computer_check
  (LegalEntity,Employee, │           │  (LegalEntity,Employee,
   Regulation) →         │           │   Regulation) →
  RegulatoryDetermination│           │  RegulatoryDetermination
                         │           │
              ┌──────────▼──┐  ┌─────▼─────────────┐
              │ det_exec    │  │ det_computer       │
              │ branch      │  │ branch             │
              └──────┬──────┘  └──────┬─────────────┘
                     │                │
              Evaluating...           │ salary ≥ $684/wk ✓
              req_exec_a: manages     │ primary duty =
              2+ employees?           │ systems design ✓
              Result: TRUE            │ Result: TRUE
              req_exec_b: primary     │
              duty = management?      │
              Result: FALSE           │
              (VP Sales, but primary  │
               duty is client         │
               relationships)         │
                     │                │
              ┌──────▼──────┐  ┌──────▼─────────────┐
              │ PRUNED      │  │ COMMITTED           │
              │ Prong B     │  │ Computer Employee   │
              │ failed →    │  │ Exemption           │
              │ conjunction │  │                     │
              │ short-      │  │ proves(skill_       │
              │ circuited   │  │  computer_check)    │
              └─────────────┘  └──────┬─────────────┘
                                      │
              ┌───────────────────────▼─────────────────┐
              │ FINAL: det_flsa_exempt_2026             │
              │ Type: RegulatoryDetermination            │
              │ Result: EXEMPT (Computer Employee)       │
              │ Provenance: skill_computer_check         │
              │ Pruned: [Executive, Admin, Professional, │
              │          Outside Sales]                  │
              │ FailureArchive: det_exec (Prong B fail)  │
              └─────────────────────────────────────────┘
              
              # Next query about Jane Doe:
              # FailureArchive biases away from Executive branch
              # π_rel for Computer Employee increases
              # Progressive disclosure surfaces Computer first
```

The provenance graph is the **audit trail**. Every determination links to the exact skill that produced it, the exact inputs, and the exact branches that were pruned. The FailureArchive records *why* branches failed, biasing future skill selection (the Introspective MCTS pattern — learn from failures, don't repeat them).

### 13.3 Cross-Domain Transfer via Proof Graph Traversal

The provenance graph enables cross-regulation transfer. A TypeQL function traverses the proof graph to find patterns:

```typeql
# Find all entities with conflicting determinations across jurisdictions:
fun cross_jurisdiction_conflicts($entity: legal-entity) -> { regulatory-determination, regulatory-determination }:
match
  (subject-entity: $entity, governing-regulation: $reg1) isa regulatory-determination,
    has jurisdiction-code $j1, has decision-type "exemption-classification",
    has is-active true;
  (subject-entity: $entity, governing-regulation: $reg2) isa regulatory-determination,
    has jurisdiction-code $j2, has decision-type "exemption-classification",
    has is-active true;
  not { $j1 == $j2; };
return { $det1, $det2 };

# Result: det_flsa_exempt (federal: exempt) vs det_abc_test_ca (state: employee)
# → Flag for human review: federal and state classifications conflict
```

### 13.4 The Runtime Split: TypeDB Verifier + Python Compute

The KCG pattern executes typed skills during graph traversal — the database is the runtime. We deliberately diverge:

| Layer | Scientific Discovery | Regulatory Prover |
|-------|---------------------|-------------------|
| **Type checking** | Category theory engine | TypeDB schema + typed roles |
| **Structural query** | KCG traversal | TypeQL functions (recursive) |
| **Compute** | KCG-internal execution | Python (LLM calls, prong evaluation, threshold math) |
| **Why split** | Chemical artifacts are small | LLM calls + document parsing too expensive to route through DB |

TypeDB is the **verifier**. Python is the **compute**. The type system is the **immune system** — it catches logical hallucinations at "compile-time" (schema validation) rather than "run-time" (post-hoc audit).

### 13.5 Progressive Skill Disclosure (Solving MCP Context Bloat)

MCP's failure mode: dump all available tools into context, overwhelming the LLM with irrelevant options. The typed skill registry solves this with progressive disclosure — only skills whose input types match the current artifact are surfaced.

```
Query: "Is our Iowa plant Title V exempt?"

Tier 1 — Domain routing (intent_resolver.py):
    Keywords → domain = "environmental"
    → Filter: only skills with input_type containing "Regulation" 
      where regulation.regulatory_body = "EPA"
    → 3 skills surfaced (not 200)

Tier 2 — Type-compatible skills:
    Current artifacts: [le_acme_iowa: LegalEntity, reg_caa_v: Regulation]
    → skill_title_v_check: (LegalEntity, Regulation) → RegulatoryDetermination ✓
    → skill_neshap_check: (LegalEntity, Regulation) → RegulatoryDetermination ✓
    → skill_nsps_check: (LegalEntity, Regulation) → RegulatoryDetermination ✓

Tier 3 — Prong-level (only load what the chosen skill needs):
    skill_title_v_check needs: [req_industrial_src, req_100_ton, req_nonattainment]
    → Load 3 requirement entities (not the entire EPA regulatory corpus)
```

The type system acts as an automatic relevance filter — same mechanism, different domain. No heuristic prompt engineering. No context bloat. The verifier is primary, the proposer is secondary.

---

## Summary

The type system maps to regulatory reasoning with zero architectural contortion:

| Type System Concept | Regulatory Application |
|---------------------|----------------------|
| **N-ary typed relation** | Atomic compliance determination (3-7 entities with typed roles) |
| **S-adjacency (IS ≥ 2)** | Cross-jurisdictional conflict detection |
| **2-morphisms** | Precedent chains, judicial invalidations, legislative amendments |
| **N-morphisms** | Federal preemption (3-morphisms between 2-morphism chains) |
| **Conjunction pruning** | Short-circuit on first false prong (EPA Title V) |
| **Disjunction committing** | Short-circuit on first true branch (FLSA exemptions) |
| **Bi-temporal model** | `valid_from`/`valid_to` for regulation versioning |
| **TypeDB 3.x functions** | On-demand inference over live rules (no stale materialization) |
| **Governance agent** | Coherence verification (diagram commutativity for decision traces) |
| **Typed skill registry** | Curry-Howard morphisms: skills as `f: A → B` with type-safe composition |
| **Append-only DAG** | Immutable provenance chain for every determination (Copresheaf pattern) |
| **Progressive disclosure** | Type-filtered skill surfacing eliminates MCP context bloat |
| **Skill memory** | Learned regulatory priors (π_rel) for adaptive prong ordering |

The system is not a mathematical prover repurposed for law. It is a purpose-built regulatory reasoning engine where typed N-ary relations capture the atomicity of legal determinations, type-safe traversal implements structural short-circuiting, the categorical 2-morphism layer encodes defeasible logic, and the strongly-typed skill registry (the CategoryScienceClaw pattern) ensures that the verifier is primary, the proposer is secondary — all evaluated on demand against the live state of the law.
