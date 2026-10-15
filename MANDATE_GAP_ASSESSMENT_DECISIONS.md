# Mandate: Gap Assessment and Planning Decisions

**Status:** Proposed validation plan\
**Date:** 15 October 2026\
**Project phase:** Phase 1, Design Finalization\
**Purpose:** Preserve the current decisions and guide the next review
without silently changing the approved project scope.

------------------------------------------------------------------------

## 1. Executive decision

**Keep Mandate. Do not restart the project or pivot to a separate
product at this stage.**

Mandate remains a standalone, framework-agnostic Python library for
authorization of AI-agent tool calls. FRIDAY remains its first
integration and proving ground, not the whole product.

The change is to the **validation process**: before implementation,
verify that Mandate's security guarantees are testable, identify gaps in
its existing design and acceptance criteria, and investigate whether its
proposed capabilities meaningfully differ from existing tools.

The goal is not to make Mandate larger. The goal is to establish that
its design is secure, coherent, useful, and appropriately scoped.

## 2. Decisions that remain unchanged

1.  **Project name:** Mandate.
2.  **Architecture:** A standalone, framework-agnostic Python library
    with its own codebase and public API.
3.  **Initial integration:** FRIDAY is the first integration and
    practical proving ground.
4.  **Core decisions:** `ALLOW`, `DENY`, and `REQUIRE_APPROVAL`.
5.  **Core responsibilities:** Authorization-policy evaluation,
    enforcement at the tool-call boundary through the integrating
    application, approval lifecycle support, and structured audit
    events.
6.  **Security posture:** Default-deny within the integration boundary;
    policy-evaluation or approval failures must never silently authorize
    an action.
7.  **Design-first workflow:** No implementation or source-code changes
    until the design and relevant changes are explicitly reviewed and
    approved.
8.  **Existing FRIDAY controls:** Mandate does not replace OS/process
    isolation, network controls, credential management, or other
    independent security controls.

## 3. What changes now

The immediate next milestone is a **Mandate Gap Assessment**, not
implementation and not a new product pivot.

The assessment should: - Compare Mandate's actual guarantees and
integration approach with relevant existing authorization tools. -
Review the existing threat model and acceptance criteria against
concrete adversarial test cases. - Distinguish library-level decision
correctness from enforcement at the real tool-execution boundary. -
Identify missing tests, incorrect or overstated guarantees, design
inconsistencies, potential differentiators, and out-of-scope concerns. -
Recommend only evidence-backed changes to the design documents and
acceptance criteria. - Preserve all previously approved decisions unless
a specific change is proposed and explicitly approved.

## 4. Candidate gaps to investigate

These are **hypotheses to validate**, not confirmed vulnerabilities.

### 4.1 Enforcement boundary and bypass resistance

**Question:** Does a `DENY` decision actually prevent the underlying
tool from executing?

A standalone library cannot prevent arbitrary direct calls that bypass
its integration boundary. The library's decision tests and the
integrating application's enforcement tests must therefore be distinct.

**Suggested test:** Use a fake tool with an observable execution
counter. Test allowed, denied, approval-pending, and error cases. Verify
that the tool executes only when the integration has established
authorization.

**Expected output:** Clear documentation of what Mandate guarantees
itself and what requires correct integration.

### 4.2 Approval binding, expiry, and replay

**Question:** Is an approval bound to the exact action and parameters
that a person reviewed?

**Suggested tests:** Change parameters after approval, reuse an
approval, submit duplicate approval responses, test expiry, and exercise
concurrent requests. Define the expected outcome for each case before
implementing the test.

**Expected output:** A precise approval lifecycle and testable rules for
stale, reused, expired, or mismatched approvals.

### 4.3 Policy conflicts and evaluation failures

**Question:** Do malformed policies, unexpected evaluation exceptions,
conflicting rules, or problematic matching operations fail safely and
deterministically?

**Suggested tests:** Inject evaluation failures, malformed policy input,
and conflicting rules. Verify the exception contract, fail-closed
enforcement, and audit behavior.

**Expected output:** One consistent policy-precedence algorithm and a
clear distinction between ordinary `DENY` decisions, policy validation
failures, and policy evaluation failures.

### 4.4 Audit safety and reliability

**Question:** Can audit events explain authorization decisions without
exposing secrets or making authorization behavior unsafe when logging
fails?

**Suggested tests:** Include nested dictionaries and lists, secret-like
values under unusual keys, oversized values, and values that cannot be
serialized. Verify recursive sanitization where supported, secret
minimization, and explicitly documented behavior when audit emission
fails.

**Expected output:** A defined audit schema, redaction contract, and
failure policy. Do not claim that simple pattern-based redaction can
guarantee removal of every possible secret.

### 4.5 Differentiation and existing alternatives

**Question:** What specific, useful capability or integration advantage
would make Mandate worth using when similar authorization and
security-testing tools already exist?

Research should compare concrete guarantees, APIs, integration
requirements, limitations, and test coverage. Feature-name overlap alone
does not prove Mandate is unnecessary; a proposed feature list alone
does not prove Mandate is differentiated.

The Open Agent Security Benchmark (OASB) is a candidate source of
reusable attack scenarios and testing ideas. Review its actual scope and
adapter interface before building a separate conformance suite. Do not
assume a broad agent-security benchmark fully covers authorization
enforcement at the tool-execution boundary.

**Expected output:** A concise comparison, identified gaps in existing
coverage, and an evidence-based differentiation hypothesis. Avoid
unsupported claims that Mandate is first, unique, or categorically
better.

## 5. Existing documentation issues to verify

These are review findings to confirm against the current repository
documents before changing them.

### 5.1 Acceptance criterion AC-038

The current wording reportedly says that calling a tool without
`guard.evaluate()` raises `PermissionError` and prevents execution.

**Concern:** A library cannot guarantee that an arbitrary unwrapped tool
call will raise an exception. That guarantee must be implemented and
tested at the actual guarded wrapper or framework dispatch boundary.

**Action:** Review AC-038 and separate: - library behavior when
authorization denies a request; - wrapper/adapter behavior when
execution is attempted without successful authorization; and -
end-to-end proof that denied or unauthorized actions produce no tool
side effects.

### 5.2 Policy-precedence wording

The current documents reportedly state both that later-loaded policy
files take precedence and that `DENY` has absolute precedence across
files, followed by `REQUIRE_APPROVAL`, then `ALLOW`.

**Concern:** These rules need a single, explicit algorithm. File
ordering and action precedence must not be described in a way that makes
the result ambiguous.

**Action:** Reconcile `mvp-design.md`, `policy-approval-definitions.md`,
`acceptance-criteria.md`, and related documents. Add table-driven tests
for conflicting rules and ensure all documents describe the same
behavior. Do not change the accepted algorithm silently.

## 6. Proposed validation workflow

### Step 1: Establish the baseline

Review these existing documents: - `mvp-design.md` -
`package-structure.md` - `public-api.md` -
`policy-approval-definitions.md` - `threat-model.md` - `mvp-scope.md` -
`acceptance-criteria.md` - `friday-integration-plan.md` -
`open-questions.md`

For each security guarantee, record the responsible component, the
relevant acceptance criterion, and whether it has a deterministic test.

### Step 2: Compare relevant existing work

Inspect relevant authorization libraries and OASB's attack
catalog/adapter interface. Record: - verified overlapping
capabilities; - relevant tests or attack scenarios that can be reused; -
features or guarantees that are genuinely different; - limitations and
untested areas; and - claims that remain unverified.

Do not build a separate benchmark merely because it is an interesting
idea.

### Step 3: Prototype a small conformance test set

Begin with approximately **10--15 high-value, deterministic tests**
covering enforcement, approval binding, policy conflicts, evaluation
failures, and audit leakage.

Use: - a deliberately broken guard to verify that the tests detect
failures; and - a correct reference implementation to verify that the
tests do not simply reject every implementation.

This is a validation experiment, not an approved expansion of Mandate's
product scope. Reuse or contribute tests to an existing project if that
is the better outcome.

### Step 4: Classify findings

Label every finding as one of the following:

-   **Required fix:** A documented guarantee is incorrect, unsafe, or
    unenforceable as written.
-   **Missing test:** The design may be sound, but the behavior has not
    been proven.
-   **Potential differentiator:** A meaningful user need or technical
    gap may justify a design change.
-   **Out of scope:** The concern requires another layer, such as OS
    sandboxing or network enforcement.
-   **No change needed:** Existing design and tests adequately address
    the issue.

Each proposed change should cite the affected document/section, the
evidence, the security or user impact, and the acceptance criterion that
will verify the fix.

### Step 5: Review and approve changes

Produce a change proposal that lists: - decisions that remain
unchanged; - proposed document edits; - new or revised acceptance
criteria; - tests to add; - scope implications and trade-offs; and -
unresolved questions requiring the user's decision.

**Do not implement the proposed changes until they are explicitly
approved.**

## 7. Completion criteria for the assessment

The assessment is complete when:

-   The existing design and requirements have been reviewed for
    consistency.
-   AC-038 and policy-precedence wording have been checked against the
    current repository.
-   Important guarantees are mapped to tests at the correct layer.
-   The most relevant alternatives and reusable security-test resources
    have been compared.
-   Candidate gaps are classified as confirmed, unconfirmed, or out of
    scope.
-   Each recommended change is evidence-backed and has a measurable
    acceptance criterion.
-   The user has reviewed and approved any design or scope changes
    before implementation.

## 8. Guardrails for future work

-   Do not rewrite the project or expand scope without evidence.
-   Do not confuse a decision result with enforcement of that decision.
-   Do not claim protection for tool paths that bypass the integration
    boundary.
-   Do not treat pattern-based secret redaction as a perfect guarantee.
-   Do not duplicate an existing benchmark without identifying a
    specific uncovered need.
-   Do not silently alter approved policy semantics or other decisions.
-   Keep FRIDAY integration narrow and test high-risk tool paths first.
-   Keep Mandate's guarantees distinct from the security guarantees
    provided by the host application, operating system, network, and
    deployment environment.

## 9. Immediate next action

Review the current Mandate repository documents and produce the
**Mandate Gap Assessment**. Return a findings report and proposed
documentation changes for review. Remain in Phase 1; do not modify
source code, install dependencies, or begin implementation during this
assessment.

------------------------------------------------------------------------

**Decision summary:** Keep Mandate. Keep its current core concept and
framework-agnostic architecture. Change the next milestone to
evidence-based gap validation. Review enforcement-boundary guarantees,
approval binding, failure behavior, audit safety, policy-precedence
consistency, and differentiation before approving implementation.
