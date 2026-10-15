# Mandate MVP Design Document

## 1. Product Boundaries

### 1.1 Responsibilities
- **Enforce authorization policies** for AI agent tool calls before execution
- **Produce allow/deny/require-approval decisions** based on defined policies
- **Emit structured audit events** for every decision
- **Manage approval lifecycles** for actions requiring human approval
- **Be framework-agnostic** - no direct dependencies on FRIDAY's internals

### 1.2 Non-Goals
- Do NOT implement tool execution or scheduling
- Do NOT provide AI model inference or prompting
- Do NOT handle transport/communication protocols (HTTP, gRPC, etc.)
- Do NOT persist long-term policy state beyond what is loaded at evaluation time
- Do NOT provide a built-in approval UI (acceptable to start with a simple CLI/sync mechanism)

### 1.3 FRIDAY Integration
Mandate integrates with FRIDAY through a **thin adapter layer** that:
- Translates FRIDAY's tool invocation context into Mandate's evaluation API
- Maps Mandate decisions back to FRIDAY's enforcement points
- Proxies Mandate's audit events to FRIDAY's JSONL logging system
- Handles FRIDAY-specific state (approval UI, user sessions, etc.)

The adapter is **not** part of the Mandate library itself - it lives in FRIDAY's integration code.

### 1.4 Existing FRIDAY Security Controls That Must Remain
- FRIDAY's existing transport security (TLS, network boundaries)
- FRIDAY's process isolation and sandboxing
- FRIDAY's credential management and secret handling
- FRIDAY's existing rate limiting and DoS protections
- OS-level process isolation

---

## 2. Core Authorization Model

### 2.1 Decision Semantics
- **ALLOW**: The tool call is authorized to proceed. Execution may continue.
- **DENY**: The tool call is prohibited. The guard must raise a `PermissionError` or `AuthorizationError` in FRIDAY's adapter, and the tool must not execute.
- **REQUIRE_APPROVAL**: The tool call is conditionally authorized pending human approval. Execution must not proceed until an approval is obtained and validated.

### 2.2 Rule Conflict Resolution
Deterministic precedence algorithm:

1. **Explicit DENY takes absolute precedence**: If any policy rule across all loaded policies has `action: deny` and matches the tool call (tool_name + all parameter conditions), the decision is DENY. Multiple DENY rules are resolved by first-match within the earliest-precedence matching policy file.

2. **Within each policy file, first-match wins**: Rules are evaluated top-to-bottom within a single file. The first rule whose condition matches (tool_name and all parameters) determines that file's contribution to the result.

3. **Policy file precedence**: Policy files are loaded in definition order. Earlier files have lower precedence (their rules are checked first), and later files can override. When no matching explicit DENY exists across any file, the result from the highest-precedence matching policy file determines the outcome.

4. **ALLOW / REQUIRE_APPROVAL interaction across files**: If multiple files contain matching rules for the same tool call:
   - Any matching DENY rule (from any file, resolved by the algorithm above) takes absolute precedence over ALLOW or REQUIRE_APPROVAL.
   - If no DENY matches, the first matching REQUIRE_APPROVAL rule from the highest-precedence file yields REQUIRE_APPROVAL.
   - If no REQUIRE_APPROVAL matches but an ALLOW rule matches, the decision is ALLOW.
   - This means: DENY > REQUIRE_APPROVAL > ALLOW in the cross-file resolution order.

5. **Default-deny**: If no rule matches in any loaded policy, the decision is DENY (default-deny boundary).

### 2.3 Policy Evaluation Failure
When policy evaluation fails (e.g., policy file malformed, policy cannot be parsed):
- The guard must **DENY** the action by default
- Emit an `EVALUATION_ERROR` audit event
- Raise a `PolicyEvaluationError` exception to the caller
- Never silently allow an action when policy evaluation has failed

### 2.4 Unavailable Approval Mechanism
When the approval mechanism is unavailable (e.g., approval service down, timeout):
- Actions marked `REQUIRE_APPROVAL` must be **DENY**d
- Emit a `APPROVAL_UNAVAILABLE` audit event
- Raise an `ApprovalUnavailableError` exception
- Never treat unavailability as authorization

### 2.5 Default-Deny Boundary
- Actions **within** the integration boundary are covered by Mandate and default-deny applies
- Actions **outside** the integration boundary are not automatically protected - this requires integration discipline at the FRIDAY level

---

## 3. Public API

### 3.1 Core Types

```python
from mandate import (
    Guard, Policy, PolicyRule, Decision, ApprovalRequest,
    ALLOW, DENY, REQUIRE_APPROVAL
)
```

### 3.2 Creating a Guard Instance

```python
# Minimal setup
guard = Guard()

# With custom configuration
guard = Guard(
    policies=["policies/airport_security.yaml"],
    approval_mechanism=my_approval_handler,
    logger=my_logger
)
```

### 3.3 Defining and Loading Policies

```yaml
# policies/airport_security.yaml
rules:
  - name: "block_destructive_tools"
    action: DENY
    condition:
      tool_name: "file_delete"
      parameters:
        path:
          pattern: "/etc/*"

  - name: "allow_read_only"
    action: ALLOW
    condition:
      tool_name: "file_read"
      parameters:
        path:
          pattern: "/data/*"

  - name: "approve_data_export"
    action: REQUIRE_APPROVAL
    condition:
      tool_name: "data_export"
      parameters:
        size:
          gt: 100MB
```

```python
# Loading policies
guard = Guard(policies=["policies/airport_security.yaml"])
# Or dynamically:
policy = Policy.from_yaml("policies/airport_security.yaml")
guard.load_policy(policy)
```

### 3.4 Evaluating a Tool Call Before Execution

```python
from mandate import Decision

result = guard.evaluate(
    tool_name="file_delete",
    parameters={"path": "/etc/passwd"},
    context={"user": "ai_agent", "session": "abc123"}
)

if result.decision == ALLOW:
    # proceed with tool execution
    tool.execute()
elif result.decision == DENY:
    # raise permission error, do not execute
    raise PermissionError(f"Denied: {result.reason}")
elif result.decision == REQUIRE_APPROVAL:
    # request human approval before proceeding
    approval = request_approval(result.approval_id)
    if approval.is_approved:
        # re-evaluate after approval
        result = guard.evaluate(...)
        if result.decision == ALLOW:
            tool.execute()
    else:
        raise PermissionError("Approval denied")
```

### 3.5 Enforcing Decisions at the Execution Boundary

```python
# The enforce method throws if not allowed
guard.enforce(
    tool_name="file_write",
    parameters={"path": "/tmp/output.txt"},
    context={"user": "ai_agent"}
)
# If we get here, the action is ALLOWed
tool.execute()
```

### 3.6 Requesting and Resolving Human Approval

```python
approval = guard.request_approval(
    tool_name="data_export",
    parameters={"size": "500MB", "destination": "/backups/"},
    context={"user": "ai_agent"}
)

# Present approval to human via whatever UI mechanism
human_responds(approval.id, approved=True)

# After approval, re-evaluate
result = guard.evaluate_after_approval(approval.id)
if result.decision == ALLOW:
    tool.execute()
```

### 3.7 Emitting Structured Authorization Audit Events

```python
# Every evaluation emits an audit event
event = guard.last_audit_event

# Event structure:
{
    "event_type": "authorization_decision",
    "timestamp": "2026-01-15T10:30:00Z",
    "tool_name": "file_delete",
    "parameters": {"path": "/etc/passwd"},  # sanitized - no secrets
    "decision": "deny",
    "reason": "explicit_deny_rule_matched",
    "approval_id": None,
    "guard_version": "0.1.0"
}
```

---

## 4. Policy Design

### 4.1 Declarative JSON/YAML Policies

Mandate MVP uses **JSON and YAML** policies exclusively. No Python predicates, `eval`, or arbitrary code execution are supported in this release.

- **YAML** is the primary human-authored format. Policies are written in YAML and loaded via `yaml.safe_load()` (no arbitrary code execution).
- **JSON** provides equivalent policy capabilities and is supported as an alternative format.
- Both formats express the same authorization semantics: `tool_name`, `action` (allow/deny/require_approval), and parameter conditions with the eight comparison operators (`eq`, `neq`, `gt`, `lt`, `gte`, `lte`, `contains`, `regex`).

**Python predicates are not supported in MVP.** They are deferred to v2. The library never uses `eval` or executes arbitrary policy expressions.

### 4.2 Policy Representation

- **tool_name**: Exact string match or the universal wildcard `*`. A condition `{"tool_name": "*"}` matches any tool name; an exact string `{"tool_name": "file_read"}` matches only the tool named `file_read`. Prefix or glob matching such as `file_*` is not supported in MVP unless explicitly approved in a future version.
- **parameters**: Nested key-value conditions with support for comparison operators (`eq`, `neq`, `gt`, `lt`, `gte`, `lte`, `contains`, `regex`). Each parameter condition has an `operator` field and a `value` field.
- **execution_context**: Optional fields like `user_id`, `session_id`, `environment`
- **constraints**: Time-based, rate-based, or resource-based limitations (deferred to v2)

### 4.3 Policy Validation

Every loaded policy is validated against a schema:
- Required fields present
- Valid action values (`ALLOW`, `DENY`, `REQUIRE_APPROVAL`)
- Valid comparison operators in conditions
- Well-formed pattern syntax
- Invalid policies are **rejected** with a `PolicyValidationError`, not silently ignored

### 4.4 Policy Precedence

The precedence algorithm is fully defined in Section 2.2 Rule Conflict Resolution. The key points from the policy design perspective are:

- **Within a single policy file**: Rules are evaluated top-to-first-match. The first matching rule's action wins.
- **Across multiple policy files**: Files are loaded in definition order. Earlier files have lower precedence (their rules are checked first), and later files can override specific rules. This allows FRIDAY integrations to declare base policies in one file and override them in a later file.
- **Explicit DENY precedence**: Any matching explicit DENY rule across all loaded policies takes absolute precedence over ALLOW or REQUIRE_APPROVAL.
- **ALLOW / REQUIRE_APPROVAL interaction**: If no DENY matches, the result from the highest-precedence matching policy file determines the outcome. The cross-file order is: DENY > REQUIRE_APPROVAL > ALLOW (i.e., if any file has a matching DENY, the decision is DENY; otherwise, if any file has a matching REQUIRE_APPROVAL, the decision is REQUIRE_APPROVAL; otherwise, if any file has a matching ALLOW, the decision is ALLOW).
- **Default-deny**: If no rule matches in any loaded policy, the decision is DENY.

### 4.5 Policy Reload Behavior

- **Hot reload**: `guard.reload_policies()` re-reads all policy files
- **Change detection**: Files modified since last load trigger reload on next evaluation
- **Atomic swap**: New policies are validated before replacing old ones; if validation fails, old policies are retained
- **Reload does not affect** in-progress evaluations

### 4.6 Essential MVP Policy Capabilities

| Capability | Status |
|---|---|
| tool_name matching | Essential |
| parameter condition with operators | Essential |
| ALLOW/DENY/REQUIRE_APPROVAL actions | Essential |
| Wildcard `*` for tool_name | Essential |
| Pattern matching on paths/strings | Essential |
| Python predicate callbacks | Deferred to v2 |
| Policy chaining/composition | Deferred to v2 |
| Version-aware policy loading | Deferred to v2 |

---

## 5. Approval Workflow

### 5.1 Minimum Approval Lifecycle States

| State | Description |
|---|---|
| **pending** | Approval request issued, awaiting human response |
| **approved** | Human confirmed approval |
| **denied** | Human rejected approval |
| **expired** | Timeout reached without response |
| **failed** | System error during approval process |

### 5.2 Approval Binding

Each approval is **bound** to:
- The specific `tool_name` and `parameters` at the time of request
- The `context` (user, session, environment) at the time of request

If the action changes (different tool, different parameters, different context), the existing approval is **invalidated** and a new approval must be requested.

```python
# Example of invalidation
approval = guard.request_approval(tool_name="file_read", parameters={"path": "/data/old"})
# ... later, agent tries file_read with new parameters ...
# The old approval is automatically invalidated
new_approval = guard.request_approval(tool_name="file_read", parameters={"path": "/data/new"})
```

### 5.3 Re-evaluation After Approval

After an approval is obtained, the guard re-evaluates the action:
- If the re-evaluation produces `ALLOW`, proceed
- If `DENY`, something changed and execution must not proceed
- If `REQUIRE_APPROVAL`, another approval cycle may be needed



### 5.4 Single-Use Consumption

Each approval authorizes the exact approved action exactly once. Consumption is atomic so that concurrent attempts cannot both succeed. Once consumed, an approval cannot authorize another execution, even with identical tool_name, parameters, and context. After an approval is consumed (re-evaluation completes with a result), it is marked as consumed and cannot authorize another execution, even if a subsequent request uses the identical tool_name, parameters, and context. A retry after execution failure requires fresh authorization. Where applicable (REQUIRE_APPROVAL), a new approval must be requested. Expired, denied, invalidated, or already-consumed approvals must never authorize execution.

**Single-use contract**: This guarantee is enforced through the public API method `guard.consume_approval(approval.id)`. The method atomically consumes the approval and returns `True` if successful, or `False` if the approval was already consumed, expired, denied, or invalidated.

**Affected documents**: This single-use consumption guarantee is enforceable through the public API and aligned across all Mandate documentation. It is an MVP requirement that integrators must adhere to.

### 5.4 Unavailable Approval Response

A missing or timed-out approval response is **never** treated as authorization:
- `timeout` → DENY the action
- `no_response` → DENY the action
- `system_error` → DENY the action, emit audit event

---

## 6. Auditability

### 6.1 Structured Decision Event

Minimum fields in every audit event:

```json
{
    "event_type": "authorization_decision",
    "timestamp": "ISO8601",
    "guard_version": "0.1.0",
    "tool_name": "string",
    "parameters": "object",  // sanitized - no secrets/credentials
    "decision": "ALLOW|DENY|REQUIRE_APPROVAL",
    "reason": "string enum [explicit_deny, rule_match, default_deny, approval_granted, approval_denied, evaluation_error, approval_unavailable]",
    "approval_id": "string | null",
    "policy_ids": "array of policy identifiers that were consulted",
    "evaluation_time_ms": "integer"
}
```

### 6.2 Data Sanitization

- **Secrets/credentials** in parameters are redacted before logging
- **Large parameters** are truncated (with `"truncated": true` flag)
- **Path parameters** have sensitive directory components masked
- The library **never** records passwords, API keys, or token values

### 6.3 FRIDAY JSONL Integration

Mandate integrates with FRIDAY's existing JSONL logs through the adapter:

```python
# Adapter code (in FRIDAY, not Mandate)
def on_audit_event(event):
    log_line = json.dumps(event)  # event already sanitized
    friday_jsonl_logger.write(log_line)
```

Mandate **does not depend** on FRIDAY's logging implementation. The adapter is responsible for:
1. Receiving the audit event from Mandate
2. Sanitizing any remaining sensitive data
3. Formatting as JSONL for FRIDAY's existing log infrastructure
4. Writing to the appropriate log file

---

## 7. MVP Scope

### 7.1 Smallest Useful Release

The MVP focuses on **3 representative tool categories**:

1. **File system tools** (`file_read`, `file_write`, `file_delete`)
   - High-risk, common in AI agent workflows
   - Clear ALLOW/DENY/REQUIRE_APPROVAL use cases
   - Parameter patterns (paths) are easy to express and test

2. **Data export tools** (`data_export`, `scan_directory`)
   - REQUIRE_APPROVAL use case for large data transfers
   - Audit logging critical for compliance
   - Parameter-driven conditions (size, destination)

3. **Web request tools** (`http_get`, `http_post`)
   - Network operation with clear security boundary
   - Can enforce ALLOW/DENY based on URL patterns
   - Demonstrates context-aware evaluation

### 7.2 Why These Categories
- Cover the most common AI agent tooling patterns
- Provide clear demonstration of all three decision types
- Enable immediate value for FRIDAY integration
- Relatively simple policy expression yet non-trivial security value

### 7.3 Reusable Library vs. FRIDAY Adapters

| Mandate (reusable) | FRIDAY Adapters (integration) |
|---|---|
| Core guard, policy engine, evaluation | Tool invocation proxy |
| Policy YAML/JSON loading and validation | FRIDAY-specific policy paths |
| Approval lifecycle management | FRIDAY approval UI integration |
| Audit event emission | FRIDAY JSONL log proxy |
| Decision enforcement at boundary | FRIDAY's `before_tool_execute` hook |

---

## 8. Threat Model and Security Test Matrix

### 8.1 Security Tests

| Test Category | Description | Mandate Guarantee | Integration Discipline Required |
|---|---|---|---|
| **Unauthorized tool execution** | Tool called without guard evaluation | **Guaranteed** - guard must be called first | N/A |
| **Path traversal** | `../` in path parameters to access forbidden areas | **Partially** - Mandate can pattern-match known paths; full path traversal requires OS isolation | OS-level sandboxing, FRIDAY must not pass unvalidated paths |
| **Parameter manipulation** | Changing parameters between evaluation and execution | **Guaranteed** - re-evaluate before execution; approval invalidated on parameter change | FRIDAY must not skip re-evaluation |
| **Policy conflicts** | Two rules conflict (ALLOW + DENY for same action) | **Guaranteed** - conflict resolved by precedence order; first match wins | Developer must understand precedence; documented in API |
| **Approval bypass** | Skipping approval flow for REQUIRE_APPROVAL actions | **Guaranteed** - guard enforces approval; adapter must not bypass | FRIDAY adapter must not shortcut the guard |
| **Stale approval** | Using old approval after action changes | **Guaranteed** - approval invalidated on parameter/context change | FRIDAY must request new approval when action changes |
| **Audit logging leakage** | Sensitive data in audit events | **Guaranteed** - library redacts secrets; adapter controls what's logged | Adapter must implement redaction; library provides sanitized view |
| **Bypass through unwrapped tools** | Agent calls underlying tool without going through guard | **Not guaranteed** - requires integration discipline | FRIDAY must route all tool calls through the Mandate guard |
| **Evaluation failure** | Malformed policy causes evaluation to fail | **Guaranteed** - failure → DENY, never allow | N/A |

### 8.2 What Mandate Can Guarantee
- All tool calls go through the guard evaluation
- Policy decisions are based on defined rules only (no external factors)
- Audit events are structured and sanitized
- Approval lifecycle is enforced
- Default-deny when no rule matches or on failure

### 8.3 What Requires External Controls
- OS isolation and process sandboxing
- Network boundaries and transport security
- Credential management and secret storage
- FRIDAY's responsibility to route all tool calls through the guard
- Integration discipline to re-evaluate before execution

---

## 9. Existing Alternatives and Naming

The project name **Mandate** is retained as selected. The investigation identified existing authorization and agent-security projects (e.g., PyPI packages, research prototypes). Mandate's intended differentiation is a hypothesis to validate:

- **Focus on AI agent tool authorization** rather than general RBAC
- **Built-from-ground-up for LLM agent workflows** with parameter-level conditions
- **Default-deny with ALLOW/DENY/REQUIRE_APPROVAL** three-valued semantics
- **Explicit approval workflow** bound to specific actions/parameters
- **Framework-agnostic design** with thin adapter pattern

These differentiators should be validated through actual use with FRIDAY rather than claimed as novel in the existing literature.

---

## 10. Open Questions and Decisions Requiring Approval

1. **Policy format for MVP**: JSON/YAML only vs. adding Python predicate support? 
   - *Recommendation*: JSON/YAML only for MVP. Python predicates deferred to v2.

2. **Wildcard/tool_name matching**: Exact string vs. `*` vs. prefix vs. regex?
   - *Recommendation*: Support exact matches and the universal wildcard `*` (i.e., `{"tool_name": "*"}` matches any tool). Do not introduce prefix matching such as `file_*` unless explicitly approved in a future version. Ensure policy examples, schema documentation, and tests use the same matching rules.

3. **Comparison operators in parameters**: Which operators are essential?
   - *Recommendation*: `eq`, `neq`, `gt`, `lt`, `gte`, `lte` for numeric/comparison; `contains`, `regex` for string matching.

4. **Approval mechanism implementation**: 
   - *Options*: CLI prompt, environment variable mock, HTTP endpoint, FRIDAY-native UI
   - *Recommendation*: Start with a callback-based mechanism the adapter implements; MVP can use a simple CLI prompt.

5. **Policy precedence across files**: Earlier/later files?
   - *Recommendation*: Earlier files checked first (lower precedence), allowing overrides by later files.

6. **Audit event sandboxing scope**: What parameters get redacted?
   - *Recommendation*: Library redacts anything matching secret patterns (env-style, key=value, token, password). Adapter controls final log output.

7. **Default policy set for MVP**: Should Mandate ship with any base policies?
   - *Recommendation*: No base policies shipped. Empty by user loads their own. This keeps the library truly framework-agnostic.

8. **Evaluation error handling**: Exception type and propagation?
   - *Recommendation*: `PolicyEvaluationError` (subclass of `Exception`). Adapter catches and translates to FRIDAY's error type.

9. **Context fields**: Which context fields are mandatory vs optional?
   - *Recommendation*: `tool_name` and `parameters` are mandatory. `user_id`, `session_id`, `environment` are optional with sensible defaults.

10. **Version 0.1.0 scope boundary**: What explicitly is IN vs OUT?
    - *See Section 7 for full scope definition*

---