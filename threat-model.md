# Mandate Threat Model and Security Test Matrix

## 1. Threat Model Overview

### 1.1 Attack Surface

| Threat Vector | Description | Mitigation |
|---|---|---|
| **Unauthorized tool execution** | Agent calls tool without guard evaluation | Guard must be called first for every tool invocation; adapter enforces this |
| **Parameter manipulation** | Parameters changed between evaluation and execution | Re-evaluate before execution; approval invalidated on parameter change |
| **Policy conflicts** | Conflicting rules (ALLOW + DENY) | First-match precedence; documented behavior |
| **Approval bypass** | Skipping approval flow for REQUIRE_APPROVAL actions | Guard enforces approval; adapter must not bypass |
| **Stale approval** | Using old approval after action changes | Approval invalidated on parameter/context change; re-evaluate |
| **Audit logging leakage** | Sensitive data in audit events | Library redacts secrets; adapter controls final log output |
| **Bypass through unwrapped tools** | Agent calls underlying tool without going through guard | Requires integration discipline at FRIDAY level; all calls must route through guard |
| **Evaluation failure** | Malformed policy causes evaluation to fail | Failure → DENY; never silently allow |
| **Unavailable approval mechanism** | Approval service down or timed out | Actions requiring approval are DENYd; never treat as authorization |

### 1.2 Security Guarantees Provided by Mandate

| Guarantee | What It Means |
|---|---|
| **All-or-nothing evaluation** | Every tool call is evaluated; there is no "bypass" mode |
| **Deterministic precedence** | Rule conflict resolution is defined and consistent |
| **Default-deny by default** | Actions not covered by any ALLOW rule are denied |
| **Sanitized audit events** | Secrets and credentials are never recorded |
| **Approval binding** | Approvals are bound to specific action/parameter combinations |
| **Evaluation failure → DENY** | Never allow an action when policy evaluation fails |
| **Approval unavailability → DENY** | Never treat missing approval as authorization |



### Single-Use Approval Consumption

- **Atomic consumption**: Only one consumer may consume each approval.
- **Single-use guarantee**: After consumption, an approval cannot authorize another execution, even with identical tool_name, parameters, and context.
- **Concurrent prevention**: Double consumption is prevented by the library.
- **Post-consumption state**: Consumed approvals are marked and rejected by `is_approval_valid()`.
- **Prohibited states**: Expired, denied, invalidated, or already-consumed approvals must never authorize execution.

| Guarantee | Description |
|---|---|
| **Atomic consumption** | Only one consumer may consume each approval |
| **Single-use guarantee** | After consumption, approval cannot authorize another execution |
| **Concurrent prevention** | Double consumption is prevented by the library |
| **Post-consumption state** | Consumed approvals are marked and rejected by `is_approval_valid()` |
| **Prohibited states** | Expired, denied, invalidated, or already-consumed approvals must never authorize execution.

### 1.3 What Requires Integration Discipline

| Area | Responsibility |
|---|---|
| **All tool calls routed through guard** | FRIDAY adapter must ensure no tool bypasses the guard |
| **OS-level process isolation** | Not Mandate's responsibility; FRIDAY/OSS must provide sandboxes |
| **Transport security (TLS, etc.)** | Not Mandate's responsibility; standard infrastructure |
| **Credential and secret management** | Not Mandate's responsibility; FRIDAY manages its own secrets |
| **Network boundaries and firewall rules** | Not Mandate's responsibility |
| **Human approval UI/UX** | FRIDAY's responsibility; Mandate provides the approval request/response API |
| **Persisting approval state across restarts** | FRIDAY's responsibility; MVP uses in-memory store |
| **Rate limiting and DoS protection** | FRIDAY's responsibility; Mandate has no timeout-based DoS protections beyond evaluation timeout |

---

## 2. Security Test Matrix

### 2.1 Unauthorized Tool Execution

| Test | Description | Expected Outcome |
|---|---|---|
| `UTX-001` | Tool called without prior `guard.evaluate()` | `PermissionError` raised; tool does not execute |
| `UTX-002` | `guard.enforce()` called for DENY decision | `PermissionError` raised |
| `UTX-003` | `guard.enforce()` called for ALLOW decision | Returns normally; caller proceeds |

### 2.2 Path Traversal and Parameter Manipulation

| Test | Description | Expected Outcome |
|---|---|---|
| `PTM-001` | `file_delete` with `path: "/etc/passwd"` → DENY if policy blocks it | DENY decision |
| `PTM-002` | `file_read` with `path: "/data/report.txt"` → ALLOW if policy allows it | ALLOW decision |
| `PTM-003` | Parameter value changed between evaluation and execution | Approval invalidated; re-evaluation required |
| `PTM-004` | `*` wildcard matches any tool | `guard.evaluate(tool_name="http_get", parameters={}, condition={"tool_name": "*"})` matches `http_get`, and `guard.evaluate(tool_name="file_read", parameters={}, condition={"tool_name": "*"})` matches `file_read` | Correct `*` wildcard matching |

### 2.3 Policy Conflicts and Evaluation Failures

| Test | Description | Expected Outcome |
|---|---|---|
| `PCF-001` | Two DENY rules for same tool → first match wins | First rule's action takes effect |
| `PCF-002` | MALFORMED policy → evaluation fails → DENY | `PolicyEvaluationError` raised; action DENYd |
| `PCF-003` | Invalid action in policy rule → policy rejected on load | `PolicyValidationError` raised; policy not loaded |
| `PCF-004` | Policy file not found → guard startup error | `FileNotFoundError` or appropriate error |

### 2.4 Approval Bypasses and Stale Approvals

| Test | Description | Expected Outcome |
|---|---|---|
| `ABC-001` | REQUIRE_APPROVAL action without requesting approval → DENY | DENY decision, not ALLOW |
| `ABC-002` | Using expired approval → DENY | `ApprovalExpiredError` or DENY decision |
| `ABC-003` | Using approval for different parameters → invalidated, new approval needed | `is_approval_valid()` returns False |
| `ABC-004` | Approval mechanism times out → action DENYd | `ApprovalUnavailableError` raised |

### 2.5 Audit Logging and Sensitive-Data Leakage

| Test | Description | Expected Outcome |
|---|---|---|
| `ALL-001` | Audit event for `file_read` with `path: "/home/user/secret.txt"` | Path sanitized; no raw secrets in event |
| `ALL-002` | Audit event for `http_post` with JSON body containing `api_key` | `api_key` value redacted in event |
| `ALL-003` | Audit event for `data_export` with large parameters | Parameters truncated; `"truncated": true` flag set |
| `ALL-004` | No secrets (passwords, tokens, API keys) in any audit event | Verified by inspection |

### 2.6 Bypass Through Unwrapped Tools

| Test | Description | Expected Outcome |
|---|---|---|
| `BUT-001` | Agent calls underlying tool function directly | Must go through guard; if not, no protection applied |
| `BUT-002` | FRIDAY adapter shortcuts guard evaluation | Should raise error; integration violation |

### 2.7 Evaluation Failure and Edge Cases

| Test | Description | Expected Outcome |
|---|---|---|
| `EFC-001` | Empty policy file (no rules) → default-deny | All actions DENYd |
| `EFC-002` | Policy with `tool_name: "*"` → matches all tools | Universal rule applies |
| `EFC-003` | Parameter condition with missing parameter | Depends on operator; `eq` with missing → no match; `gt` with missing → defined behavior |
| `EFC-004` | Evaluation timeout exceeded | `PolicyEvaluationError`; action DENYd |

---

## 3. Test Classification

| Classification | Description |
|---|---|
| **Unit tests** | Test individual modules (evaluator, policy loader, approval store) in isolation |
| **Integration tests** | Test guard + policy + approval flow end-to-end |
| **Property tests** | Verify invariants (e.g., "evaluation failure always → DENY", "secrets never in audit events") |
| **Fuzz tests** | Send random policy/parameter combinations to find edge cases |
| **Safety tests** | Verify that denied actions truly do not execute (hard to test, requires sandbox) |

---

## 4. Mandate Guarantees vs. Integration Requirements

| Area | Mandate Guarantee | Integration/External Requirement |
|---|---|---|
| Tool evaluation | Every call evaluated | Adapter must ensure all calls go through guard |
| Policy decisions | Based on defined rules only | Developer writes correct policies |
| Default-deny | Actions not covered are denied | Must define policies for protected actions |
| Audit events | Structured, sanitized | Adapter writes to log correctly |
| Approval lifecycle | Bound to action/parameters | Adapter handles UI/response |
| Policy validation | Schemas enforced on load | Policy authors write valid YAML/JSON |
| Evaluation failure | → DENY | Must not catch and suppress errors |
| OS isolation | Not provided | FRIDAY/OSS must provide sandboxing |
| Network security | Not provided | Standard infrastructure |
| Human approval | API provided | FRIDAY provides UI/mechanism |
| All tool calls routed | Depends on adapter design | Adapter design decision |

---

## 5. Success Criteria for Security Tests

All of the following must pass for MVP to be considered secure:

1. [ ] `UTX-001`: Unauthorized execution is blocked
2. [ ] `PTM-001`: Path/parameter patterns work correctly
3. [ ] `PCF-002`: Malformed policy → DENY, not allow
4. [ ] `ABC-001`: REQUIRE_APPROVAL without approval → DENY
5. [ ] `ALL-002`: No secrets in audit events
6. [ ] `ABC-003`: Stale approval → invalidated, new request needed
7. [ ] `BUT-001`: All tool calls must route through guard (integration test)

Failed any of these → MVP does not meet security baseline.

### Single-Use Approval Consumption

Each approval authorizes the exact approved action exactly once. Consumption is atomic; concurrent attempts cannot both succeed. Once consumed, an approval cannot authorize another execution, even with identical tool_name, parameters, and context. Single-use consumption is enforced by the Mandate library; replay or double consumption is prevented.

| Guarantee | Description |
|---|---|
| **Atomic consumption** | Only one consumer may consume each approval |
| **Single-use guarantee** | After consumption, approval cannot authorize another execution |
| **Concurrent prevention** | Double consumption is prevented by the library |
| **Post-consumption state** | Consumed approvals are marked and rejected by `is_approval_valid()` |

