# Mandate Project Context

## Purpose of this file
This is the handoff context for a separate ChatGPT conversation dedicated to **Mandate**. Read it before giving advice or proposing next steps. Treat the current state and constraints below as binding unless the user explicitly changes them.

## 1. What Mandate is
**Mandate** is a planned standalone, reusable Python library for authorization and policy enforcement around AI-agent tool calls.

Working tagline: **Policy enforcement for AI agents.**

Core idea: give AI agents the authority they need, not unrestricted power. Mandate evaluates whether an action should proceed before the protected tool executes.

Mandate is an independent project with its own codebase, repository, and public identity. It is intended to be usable by other developers without adopting FRIDAY or a particular agent framework. The intended direction is open source, but don't claim publishing/licensing decisions are finalized unless the user confirms them.

**FRIDAY is Mandate's first integration and proving ground, not the limit of the product.**

The name “Mandate” has been selected. Do not rename it. Before public naming claims, verify availability across existing projects, package registries, GitHub, domains, and trademarks.

## 2. Current status
- The initial read-only investigation of FRIDAY and the agent-security landscape has been completed.
- The user approved proceeding with Mandate as a project in principle.
- The user chose **staged integration**: build the reusable library, integrate FRIDAY's highest-risk tools first, validate it, and expand later. Do not start by migrating every tool at once.
- The user has created a separate Mandate repository.
- A Phase 1B design-finalization prompt has been pasted into the Mandate repository's coding agent. The prompt explicitly requires investigation/design only, no source-code changes, no dependency installs, no migrations, and no roadmap/documentation changes.
- The next step in this chat is to review the coding agent's design output when the user shares it. Do not assume the output has been completed or approved unless it is provided.
- No implementation has been approved yet. The user wants to review and agree on major design decisions before implementation.
- FRIDAY should not be stopped entirely. Work on independent FRIDAY roadmap items may continue, but avoid overlapping authorization/security-boundary changes until Mandate's design is approved. FRIDAY integration planning can be documented without changing code.

## 3. Agreed product direction
- Standalone Python package, separate from FRIDAY.
- Framework-agnostic core, with thin framework/product adapters.
- Authorization decisions:
  - `ALLOW`
  - `DENY`
  - `REQUIRE_APPROVAL`
- Default-deny behavior for actions that are actually covered by Mandate.
- Decisions must be enforced before protected tool execution.
- Structured authorization audit events.
- Adversarial security tests from the beginning.
- Initial integration targets selected high-risk FRIDAY tools, then expand based on validation.
- Keep the first release small enough for one developer to build, test, document, and demonstrate.
- Design first, explicit approval second, implementation only after approval.

These are design goals, not proof that a proposed implementation will enforce them correctly. Be precise about trust boundaries and limits.

## 4. Investigation findings from FRIDAY
The initial investigation report identified these existing components and gaps. Treat these as findings from that report, and re-check code before making implementation claims.

### Existing controls
- `friday/filesystem/policy.py:51-76` contains `PathPolicy` authorization checks that resolve paths and check whether they fall within the workspace or a registered project grant.
- `FileSystemManager` wraps filesystem operations with limits on bytes, entries, and depth, and authorizes before operations.
- FRIDAY has JSONL logs at `logs/sessions/<session_id>/friday.log`, including rotation, secret redaction, and correlation.
- `safe_eval()` uses an AST allowlist and empty builtins; the report says it blocks `__import__`, `open()`, lambdas, comprehensions, and subscripts.

### Reported security gaps
- **Hermes filesystem I/O:** the investigation says Hermes uses CLI-level file operations that bypass `PathPolicy` and `FileSystemManager`. The report classifies this as a high-priority security gap.
- **Web redirect validation / SSRF:** the investigation says URL validation checks scheme and IP policy, but fetch clients follow redirects without revalidating redirect destinations. The report classifies this as a high-priority SSRF gap.
- **Authorization boundary:** no cohesive deterministic authorization layer sits below the LLM level across all tool calls. Tool results may enter history without sanitization or authorization checks.
- **Audit gap:** existing logs do not provide a consistent authorization-decision audit trail.

Important: Mandate alone will not automatically fix Hermes bypasses, SSRF redirect validation, OS-level security, or any tool that is not routed through its enforcement boundary. Treat the reported SSRF and Hermes issues as separate FRIDAY security fixes as well as potential integration targets.

## 5. Existing alternatives and differentiation
The investigation compared multiple existing agent-security and authorization projects, including Doberman-Core, hexgate, agentlock, secondsign-core, capfence, eunomia, mcp-agent-security-gateway, agent-scan, saf-mcp, agentseal, llm-agent-audit, and several Python packages.

The intended product hypothesis is to combine runtime enforcement, explicit allow/deny/approval decisions, parameter-level constraints, and structured audit events in a framework-agnostic package that is straightforward to integrate.

Do not claim Mandate is the first, unique, or categorically better solution without current external verification and careful comparison. Its differentiation is a hypothesis to test.

## 6. Design questions Phase 1 must settle
The design proposal should cover:
1. Product boundaries and non-goals.
2. Package/module structure and public API.
3. How policies are represented, validated, prioritized, and reloaded.
4. How `ALLOW`, `DENY`, and `REQUIRE_APPROVAL` behave, including conflicts and policy-evaluation failures.
5. A safe declarative policy model. Do not evaluate arbitrary expressions or use `eval`. Trusted Python predicates may be considered only as explicit trusted code, not as untrusted policy text.
6. Approval lifecycle, including pending, approved, denied, expired, and failed states where appropriate.
7. Approval binding to the exact action and parameters. Changed actions must require fresh evaluation/approval; a missing or failed approval must never authorize execution.
8. Structured audit events, including redaction of secrets and minimization of sensitive parameters.
9. Integration with FRIDAY's existing JSONL logs without coupling the core package to FRIDAY.
10. Minimal first-release tool categories and a justified MVP scope.
11. Threat model, adversarial tests, measurable acceptance criteria, and known limitations.
12. FRIDAY integration plan starting with selected high-risk tools.
13. Open questions and explicit decisions the user must approve before implementation.

The initial investigation suggested an approximately eight-person-day MVP, but this estimate has not been approved and should be critically reviewed rather than accepted by default. The initial candidate scope mentioned policy storage, a guard API/decorator, approval workflow, logging, and policies for read/write/list/search/fetch/calculate. Don't assume all of these belong in the first release; justify the smallest useful MVP.

## 7. Threat model topics
At minimum, consider:
- Unauthorized tool execution and fail-open behavior.
- Path traversal and parameter manipulation.
- Policy conflicts, malformed policies, and policy-evaluation failures.
- Approval bypass, expiry, replay, and stale approval after parameter changes.
- Audit tampering, missing events, secret leakage, and over-logging.
- Calls through tools or code paths not wrapped by Mandate.
- Integration errors and the difference between library guarantees and OS/process/network isolation.

Explicitly distinguish what the library can guarantee from what requires correct integration, operating-system sandboxing, network controls, or other defenses.

## 8. Collaboration and working rules
- Keep responses concise and practical unless a deeper design review is needed.
- Discuss architecture and trade-offs before implementation.
- Do not silently resolve major trade-offs; present the options, recommend one, and explain why.
- Do not modify source code, FRIDAY's roadmap, or project documentation unless the user explicitly approves that phase of work.
- In the current phase, do design/review only. No code changes or dependency installation.
- When reviewing the agent's output, identify unsupported claims, unnecessary complexity, unsafe assumptions, gaps in the threat model, and acceptance criteria that cannot be objectively tested.
- Separate confirmed investigation findings from assumptions and recommendations.
- Do not make the user repeat decisions already recorded in this file.

## 9. Immediate next action
Ask the user to share the design output produced by the coding agent in the Mandate repository, then review it against the requirements above. If the agent has not finished, the user can return with its output when ready.

Do not begin implementation until the design and the relevant decisions have been explicitly approved by the user.
