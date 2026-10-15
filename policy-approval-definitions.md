# Mandate Policy and Approval Lifecycle Definitions

## 1. Policy Definitions

### 1.1 Rule Actions

| Action Value | Semantics | Execution Behavior |
|---|---|---|
| `allow` | The tool call is authorized to proceed without restrictions. | Execution may continue immediately. |
| `deny` | The tool call is prohibited. | Execution must not proceed; raise `PermissionError`. |
| `require_approval` | The tool call is conditionally authorized pending human approval. | Execution must not proceed until approval is obtained and re-evaluation yields `ALLOW`. |

### 1.2 Condition Structure

A condition specifies when a rule matches. It consists of:

- `tool_name`: String or `"*"` wildcard. If `"*"`, matches any tool name.
- `parameters`: Optional map of parameter_name → condition_sub-object.

Each parameter condition supports:

| Field | Type | Description |
|---|---|---|
| `operator` | `str` | Comparison operator: `eq`, `neq`, `gt`, `lt`, `gte`, `lte`, `contains`, `regex` |
| `value` | `any` | The value to compare against |

There is no `pattern` field in MVP conditions. The eight comparison operators are evaluated as documented in Section 1.3.

### 1.3 Operator Semantics

| Operator | Description | Example |
|---|---|---|
| `eq` | Equal | `{"operator": "eq", "value": "file_read"}` matches `tool_name: "file_read"` |
| `neq` | Not equal | `{"operator": "neq", "value": "file_delete"}` matches any tool except `file_delete` |
| `gt` | Greater than | `{"operator": "gt", "value": 100}` matches `size: 150` but not `size: 50` |
| `lt` | Less than | `{"operator": "lt", "value": 10}` matches `size: 5` but not `size: 20` |
| `gte` | Greater than or equal | `{"operator": "gte", "value": 10}` matches `size: 10` and above |
| `lte` | Less than or equal | `{"operator": "lte", "value": 100}` matches `size: 100` and below |
| `contains` | String contains | `{"operator": "contains", "value": "/tmp"}` matches `path: "/tmp/foo.txt"` |
| `regex` | Regular expression match | `{"operator": "regex", "value": "^/data/"}` matches `path: "/data/report.txt"` |

### 1.4 Condition Evaluation

```
For each parameter in the condition:
1. Retrieve the corresponding value from the tool's actual parameters
2. If the parameter is absent from the tool call:
   - If the rule requires the parameter to be present (AND logic), the rule does NOT match
   - If the parameter is optional, the rule may still match based on other parameters
3. Apply the operator:
   - eq/neq: equality comparison (string or numeric)
   - gt/lt/gte/lte: numeric comparison; also works for sortable strings
   - contains: substring check (Python `in` operator)
   - regex: Python `re.search(value, string)` match
4. All parameter conditions must match for the rule to match (AND semantics)
5. If tool_name matches AND all parameter conditions match → rule matches
```

### 1.5 Policy Precedence

The precedence algorithm is as follows, consistent with the full algorithm documented in Section 2.2 of the design:

- **Explicit DENY takes absolute precedence**: If any matching explicit DENY rule exists across all loaded policies, the decision is DENY. This is independent of ALLOW or REQUIRE_APPROVAL rules in any file.

- **Within each policy file, first-match wins**: Rules are evaluated top-to-bottom within a single file. The first rule whose condition matches (tool_name + all parameters) determines that file's contribution.

- **Policy file precedence**: Files are loaded in definition order. Earlier files have lower precedence (their rules are checked first), and later files can override. When no matching explicit DENY exists:
  1. Check for matching REQUIRE_APPROVAL rules, starting from the lowest-precedence (earliest-loaded) file and moving to higher-precedence files. The first matching REQUIRE_APPROVAL rule's file determines the result.
  2. If no REQUIRE_APPROVAL matches, check for matching ALLOW rules, starting from the lowest-precedence file. The first matching ALLOW rule's file determines the result.
  3. If no rule matches in any file, the decision is default-deny.

- **Cross-file ALLOW/REQUIRE_APPROVAL order**: DENY > REQUIRE_APPROVAL > ALLOW. That is:
  - If any file has a matching DENY (per the absolute DENY precedence), the decision is DENY.
  - Otherwise, if any file has a matching REQUIRE_APPROVAL, the decision is REQUIRE_APPROVAL.
  - Otherwise, if any file has a matching ALLOW, the decision is ALLOW.

### 1.6 Policy Validation

Every policy is validated on load. Validation errors raise `PolicyValidationError`. Validation checks:

- Required fields present (`name`, `action`, `condition`)
- `action` is one of `allow`, `deny`, `require_approval`
- `condition.tool_name` is a string or `"*"`
- Parameter conditions have valid `operator` and `value`
- Pattern syntax is well-formed
- No duplicate rule names within a policy
- If validation fails, the policy is rejected and **not** loaded; an error is raised

### 1.7 Policy Reload

- `guard.reload_policies()` re-reads all policy files
- Files modified since last load trigger a reload
- New policies are validated before replacing existing ones
- If validation of new policies fails, old policies are retained (atomic swap)
- Reload does not affect in-progress evaluations (current evaluation completes with current policies)

---

## 2. Approval Lifecycle

### 2.1 States

| State | Description | Transitions |
|---|---|---|
| `pending` | Approval request issued, awaiting human response | → `approved`, → `denied`, → `expired` |
| `approved` | Human confirmed the approval | → `invalidated` (if action changes) |
| `denied` | Human rejected the approval | terminal |
| `expired` | Timeout reached without response | terminal |
| `invalidated` | Approval invalidated because action changed | → `pending` (new request required) |

### 2.2 Approval Lifecycle Diagram

```
         +-------+
         |pending|
         +-------+
          /      \
         /        \
    +---------+  +----------+
    |  approved|  |   denied   |
    +---------+  +----------+
         |           |
         |           +→ (terminal)
         |
         +→ expired (timeout)
              (terminal)
```

### 2.3 Approval Request Lifecycle

```python
# 1. Request approval
approval = guard.request_approval(
    tool_name="data_export",
    parameters={"size": "500MB", "destination": "/backups/"},
    context={"user": "ai_agent"},
)

# approval.state == "pending"
# approval.id == "req_xyz789"

# 2. Human responds (via UI, CLI, etc.)
#    - If approved:
guard.approve(approval.id)
#    - If denied:
guard.deny(approval.id)

# 3. After approval, re-evaluate
result = guard.evaluate(
    tool_name="data_export",
    parameters={"size": "500MB", "destination": "/backups/"},
    context={"user": "ai_agent"},
)

# 4. If result.decision == ALLOW, proceed with execution
if result.decision == ALLOW:
    tool.execute()
```

### 2.4 Approval Invalidated on Action Change

If the tool name or parameters change, the existing approval is invalidated:

```python
# Original approval
approval = guard.request_approval(
    tool_name="file_read",
    parameters={"path": "/data/old.txt"},
    context={"user": "ai_agent"},
)

# Agent changes the action parameters
# The old approval is now invalidated
guard.is_approval_valid(approval.id, "file_read", {"path": "/data/new.txt"})
# Returns False - approval was for old parameters

# Must request new approval
new_approval = guard.request_approval(
    tool_name="file_read",
    parameters={"path": "/data/new.txt"},
    context={"user": "ai_agent"},
)
```

### 2.5 Timeout Handling

- Each approval request has a configurable timeout (default: 60000ms / 60 seconds)
- If no human response before timeout, the approval automatically transitions to `expired` state
- After expiration, the action is `DENY`d
- The adapter is responsible for clearing timed-out approvals

### 2.6 Approval Unavailability

When the approval mechanism is unavailable (callback not callable, timeout, service error):

- Actions marked `REQUIRE_APPROVAL` are `DENY`d
- An `ApprovalUnavailableError` is raised
- An audit event with `reason: "approval_unavailable"` is emitted
- Never treat unavailability as authorization

### 2.7 Minimum Approval Workflow (MVP)

The MVP approval workflow does NOT require a production UI. It starts with:

1. `guard.request_approval()` creates a pending approval with an ID
2. The adapter presents the approval ID to a human via whatever mechanism (CLI prompt, environment variable, test hook)
3. The adapter calls `guard.approve(approval.id)` or `guard.deny(approval.id)`
4. The guard re-evaluates and the caller proceeds or is denied

For testing and demonstration, the adapter can use a simple CLI prompt or environment variable-based approval.

**Gap documentation: approval single-use consumption**:
The documentation specifies that approvals are bound to the exact action (tool_name, parameters, context) at the time of request and are invalidated when the action changes (AC-018, AC-019, AC-020, AC-021, AC-042). After an approval is consumed (i.e., re-evaluation completes with a result), the approval is effectively used.

**Single-use consumption guarantee**: Each approval authorizes the exact approved action exactly once. The approval is bound to the exact tool name, parameters, and relevant context at the time of request. Mandate enforces single-use consumption:

1. **After consumption**: Once an approval has been consumed (re-evaluation completes with a result), it cannot authorize another execution. Even if a subsequent request uses the identical tool_name, parameters, and context, the approval is invalidated and a new approval must be requested.

2. **Concurrent prevention**: Mandate ensures that concurrent attempts to consume the same approval cannot both succeed. Only one consumer may consume the approval.

3. **Post-consumption invalidation**: After an approval is consumed, it is marked as consumed and any further attempts to use it (via `guard.approve()`, `guard.is_approval_valid()`, or direct re-evaluation) result in the approval being rejected as already consumed.

4. **Retry after failure**: A retry after execution failure requires fresh authorization. Where applicable (REQUIRE_APPROVAL), a new approval must be requested.

5. **Prohibited states**: Expired, denied, invalidated, or already-consumed approvals must never authorize execution. Any attempt to do so results in a DENY decision and an `approval_consumed` or `approval_invalidated` reason code.

**Single-use contract**: This guarantee is enforceable through the public API. The `guard.consume_approval(approval.id)` method atomically consumes an approval and returns `True` if successful, or `False` if the approval was already consumed or in an invalid state (expired, denied, invalidated).

**User review**: This single-use consumption guarantee is an MVP requirement. The Mandate library enforces it. Integrators must not assume approvals can be reused.

---

## 3. Decision Event and Reason Codes

### 3.1 Decision Reason Enum

| Reason Code | Meaning |
|---|---|
| `explicit_deny` | An explicit DENY rule matched |
| `rule_match` | A rule matched (could be ALLOW, DENY, or REQUIRE_APPROVAL) |
| `default_deny` | No rule matched; default-deny applied |
| `approval_granted` | Action allowed after approval was obtained |
| `approval_denied` | Action denied because approval was rejected |
| `evaluation_error` | Policy evaluation failed; default-deny applied |
| `approval_unavailable` | Approval mechanism unavailable; default-deny applied |
| `stale_approval` | Approval was invalidated because action changed |

### 3.2 Decision Flow with Reasons

```text
START: evaluate(tool_name, parameters, context)
    |
    v
Check for explicit DENY rules (first match wins)
    |
    +-- YES → decision: DENY, reason: "explicit_deny"
    |
    v
Check for REQUIRE_APPROVAL rules (first match wins)
    |
    +-- YES → decision: REQUIRE_APPROVAL, reason: "rule_match", approval_id set
    |
    v
Check for ALLOW rules (first match wins)
    |
    +-- YES → decision: ALLOW, reason: "rule_match"
    |
    v
No rules matched
    |
    v → decision: DENY, reason: "default_deny"
```

---

## 4. Re-evaluation After Approval

After an approval is obtained, the guard re-evaluates the action. This is critical because:

1. The action may have changed between the initial evaluation and the approval
2. The approval itself may have been invalidated (if parameters changed)
3. New policies may have been loaded

```python
# Post-approval re-evaluation
result = guard.evaluate_after_approval(approval_id)

if result.decision == ALLOW:
    # Safe to proceed
    tool.execute()
elif result.decision == DENY:
    # Action changed or something else occurred; must NOT proceed
    raise PermissionError("Denied after approval re-evaluation")
elif result.decision == REQUIRE_APPROVAL:
    # Another approval cycle may be needed
    # (Should not normally happen in MVP, but handled)
    raise PermissionError("Still requires approval after approval cycle")
```

---

## 5. Summary of Policy and Approval Guarantees

| Guarantee | Scope |
|---|---|
| All tool calls evaluated against defined policies | Mandate core |
| First-match rule precedence is deterministic | Mandate core |
| Default-deny when no rule matches | Mandate core |
| Policy evaluation failure → DENY | Mandate core |
| Approval invalidated when action changes | Mandate core |
| Missing/timed approval → DENY | Mandate core |
| Audit events emitted for every evaluation | Mandate core |
| Secrets redacted from audit events | Mandate core |
| Policy validation on load | Mandate core |
| FRIDAY routing discipline required | Integration layer |
| OS isolation required | Operating system |