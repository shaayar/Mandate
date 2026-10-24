# Mandate Public API Specification

## Overview
A small, intuitive Python API for authorization enforcement. All imports come from the `mandate` package.

## Core Imports

```python
from mandate import (
    Guard,
    ALLOW,
    DENY,
    REQUIRE_APPROVAL,
    Decision,
    Policy,
    PolicyRule,
    EvaluationContext,
    AuditEvent,
)
from mandate.core.types import (
    ComparisonOperator,
    Pattern,
)
from mandate.approval.request import ApprovalRequest
from mandate.audit.emitter import emit_audit_event
```

---

## 1. Creating a Guard Instance

```python
from mandate import Guard

# Minimal - no policies loaded yet
guard = Guard()

# With base policies
guard = Guard(policies=["policies/baseline.yaml"])

# With custom approval and audit configuration
guard = Guard(
    policies=["policies/airport_security.yaml"],
    approval_mechanism=my_approval_handler,
    logger=my_logger,
)
```

### `Guard` Constructor Parameters
| Parameter | Type | Default | Description |
|---|---|---|---|
| `policies` | `list[str]` | `[]` | Paths to policy YAML/JSON files to load initially |
| `approval_mechanism` | `callable` | `None` | Callback `f(approval_request) -> ApprovalResult` |
| `logger` | `logging.Logger` | `None` | Logger for audit events |
| `evaluation_timeout_ms` | `int` | `30000` | Timeout for policy evaluation |
| `approval_timeout_ms` | `int` | `60000` | Timeout for approval response |

---

## 2. Defining and Loading Policies

### 2.1 YAML Policy Format

```yaml
# policies/airport_security.yaml
rules:
  - name: "block_destructive_tools"
    action: deny
    condition:
      tool_name: "file_delete"

  - name: "allow_read_only_files"
    action: allow
    condition:
      tool_name: "file_read"
      parameters:
        path:
          pattern: "/data/%"
          operator: eq

  - name: "approve_large_exports"
    action: require_approval
    condition:
      tool_name: "data_export"
      parameters:
        size:
          operator: gt
          value: 100
          unit: MB
```

### 2.2 Loading a Policy

```python
from mandate import Policy

# From YAML file
policy = Policy.from_yaml("policies/airport_security.yaml")

# From JSON file
policy = Policy.from_json("policies/airport_security.json")

# From a string (YAML)
policy = Policy.from_yaml_string("tool_name: file_read\naction: allow\n")

# Load into guard
guard.load_policy(policy)
```

### 2.3 Policy Schema (internal)

A valid policy must have:
- `rules`: list of rule objects
- Each rule must have:
  - `name`: string (unique identifier)
  - `action`: one of `allow`, `deny`, `require_approval`
  - `condition`: condition object (see below)

### 2.4 Condition Object

```yaml
condition:
  tool_name: "file_delete"               # exact match or "*" wildcard
  parameters:
    path:
      operator: eq                       # comparison operator: eq, neq, gt, lt, gte, lte, contains, regex
    size:
      operator: gt
      value: 100
      unit: MB
```

Supported `parameter` condition structure (Python dict):

```python
{
    "tool_name": "file_read",              # string or "*"
    "parameters": {
        "key": {
            "operator": "eq",              # eq, neq, gt, lt, gte, lte, contains, regex
            "value": "some_value",         # value to compare against
        }
    }
}
```

---

## 3. Evaluating a Tool Call Before Execution

### 3.1 Basic Evaluation

```python
from mandate import ALLOW, DENY, REQUIRE_APPROVAL

result = guard.evaluate(
    tool_name="file_delete",
    parameters={"path": "/etc/passwd"},
    context={"user": "ai_agent", "session": "abc123"},
)

if result.decision == ALLOW:
    tool.execute()
elif result.decision == DENY:
    raise PermissionError(f"Denied: {result.reason}")
elif result.decision == REQUIRE_APPROVAL:
    # request human approval
    ...
```

### 3.2 `EvaluationResult` Attributes

| Attribute | Type | Description |
|---|---|---|
| `decision` | `Decision` | `ALLOW`, `DENY`, or `REQUIRE_APPROVAL` |
| `reason` | `str` | Human-readable reason for the decision |
| `policy_ids` | `list[str]` | IDs of policies/rules consulted |
| `approval_id` | `str | None` | If `REQUIRE_APPROVAL`, the approval request ID |
| `evaluation_time_ms` | `int` | How long the evaluation took |

### 3.3 Example: ALLOW Decision

```python
result = guard.evaluate(
    tool_name="file_read",
    parameters={"path": "/data/report.txt"},
    context={"user": "ai_agent"},
)

result.decision  # ALLOW
result.reason    # "rule_match: allow_read_only_files"
result.policy_ids  # ["airport_security.yaml:0"]
result.approval_id  # None
result.evaluation_time_ms  # 5
```

### 3.4 Example: DENY Decision

```python
result = guard.evaluate(
    tool_name="file_delete",
    parameters={"path": "/etc/passwd"},
    context={"user": "ai_agent"},
)

result.decision  # DENY
result.reason    # "explicit_deny: block_destructive_tools"
result.policy_ids  # ["airport_security.yaml:0"]
result.approval_id  # None
```

### 3.5 Example: REQUIRE_APPROVAL Decision

```python
result = guard.evaluate(
    tool_name="data_export",
    parameters={"size": "500", "unit": "MB", "destination": "/backups/"},
    context={"user": "ai_agent"},
)

result.decision  # REQUIRE_APPROVAL
result.reason    # "rule_match: approve_large_exports"
result.policy_ids  # ["airport_security.yaml:2"]
result.approval_id  # "req_abc123"  -- request ID for human approval
result.evaluation_time_ms  # 3
```

---

## 4. Enforcing Decisions at the Execution Boundary

### 4.1 `enforce()` - Throw if Not Allowed

```python
from mandate import ALLOW, DENY

try:
    guard.enforce(
        tool_name="file_write",
        parameters={"path": "/tmp/output.txt"},
        context={"user": "ai_agent"},
    )
    # If we get here, the decision was ALLOW
    tool.execute()
except PermissionError:
    # Decision was DENY - tool must not execute
    log_denial()
```

### 4.2 `enforce()` Behavior
- **ALLOW**: Returns normally, caller proceeds with tool execution
- **DENY**: Raises `PermissionError` (or `MandateError` subclass)
- **REQUIRE_APPROVAL**: Raises `ApprovalRequiredError` (subclass of `PermissionError`)
- Never silently allows a REQUIRE_APPROVAL action

---

## 5. Requesting and Resolving Human Approval

### 5.1 Request Approval

```python
approval = guard.request_approval(
    tool_name="data_export",
    parameters={"size": "500", "unit": "MB", "destination": "/backups/"},
    context={"user": "ai_agent"},
)

# `approval` is an ApprovalRequest object
approval.id           # "req_xyz789"
approval.tool_name    # "data_export"
approval.parameters   # {"size": "500", "unit": "MB", "destination": "/backups/"}
approval.context      # {"user": "ai_agent"}
approval.state        # "pending"
approval.created_at   # datetime timestamp
```

### 5.2 Approval Lifecycle Methods

```python
# Check if approval is still valid for current action
valid = guard.is_approval_valid(approval.id, tool_name, parameters)

# Approve the request
guard.approve(approval.id)

# Deny the request
guard.deny(approval.id)
```

### 5.3 After Approval - Re-evaluate

```python
# After human approves via whatever UI
guard.approve(approval.id)

# Re-evaluate the action after approval
result = guard.evaluate(
    tool_name="data_export",
    parameters={"size": "500", "unit": "MB", "destination": "/backups/"},
    context={"user": "ai_agent"},
)

if result.decision == ALLOW:
    tool.execute()
elif result.decision == DENY:
    # Something changed; execution must not proceed
    raise PermissionError("Denied after approval re-evaluation")
```

### 5.4 Approval Invalidated on Action Change

If the tool name or parameters change, the existing approval is automatically invalidated:
### 5.5 Consume Approval

```python
# Atomically consume an approval. Has three mutually exclusive outcomes:

# Returns True: A valid approval is successfully consumed for the first time.
# The approval is now marked as consumed and cannot authorize another execution.

# Returns False: The approval is in an unusable state, including when it has already been consumed.
# Re-consumption does not raise an exception; it simply returns False.

# Raises ApprovalAlreadyConsumedError: The supplied approval ID is unknown.
result = guard.consume_approval(approval.id)
if result is True:
    # Approval was consumed successfully
    pass
elif result is False:
    # Approval is in an unusable state (already-consumed, expired, denied, invalidated,
    # or pending). Consumption was not performed; no exception is raised.
    pass
else:
    # Approval ID is unknown
    raise ApprovalAlreadyConsumedError(
        f"Approval {approval.id} was not found"
    )
```
```
**Consume Approval**
- **Returns `True`**: A valid approval is successfully consumed for the first time. The approval is now marked as consumed and cannot authorize another execution.
- **Returns `False`**: The approval is in an unusable state, including when it has already been consumed. Re-consumption does not raise an exception.
- **Raises `ApprovalAlreadyConsumedError`**: The supplied approval ID is unknown.

**Atomic single-use consumption**: Concurrent attempts to consume the same approval must not allow more than one successful consumption. The method enforces this guarantee atomically.
```

**Consume Approval**
- **Atomic consumption**: The `consume_approval()` method atomically attempts to consume an approval.
- **Return `True`**: The approval was consumed successfully (fresh consumption, approval was in consumable state).
- **Return `False`**: The approval is in an unusable state (pending, expired, denied, invalidated,
  or already-consumed). Consumption was not performed; no exception is raised.
- **Raise `ApprovalAlreadyConsumedError`**: The approval ID is unknown, or an already-consumed
  approval is being re-consumed. This is a distinct outcome from returning `False`.
- **Single-use guarantee**: This method enforces the single-use consumption guarantee. Once consumed,
  the approval is bound to the exact approved action only once.

**Consumption state after use**:
- **Consumed**: Approval has been consumed via `guard.consume_approval()`. Cannot be reused.
- **Already-consumed**: Attempting to consume an already-consumed approval returns `False` and
  raises `ApprovalAlreadyConsumedError` (if the approval was previously consumed).
- **Expired**: Expired approvals cannot be consumed; `consume_approval()` returns `False`.
- **Denied**: Denied approvals cannot be consumed; `consume_approval()` returns `False`.
- **Invalidated**: Invalidated approvals (due to parameter/context change) cannot be consumed;
  `consume_approval()` returns `False`.

```python
# First approval request
approval = guard.request_approval(
    tool_name="file_read",
    parameters={"path": "/data/old.txt"},
    context={"user": "ai_agent"},
)

# Later, agent tries file_read with different parameters
# The old approval is invalidated - re-evaluate or request new approval
result = guard.evaluate(
    tool_name="file_read",
    parameters={"path": "/data/new.txt"},
    context={"user": "ai_agent"},
)

# If you try to approve the old ID with new parameters, it will fail:
guard.is_approval_valid(approval.id, "file_read", {"path": "/data/new.txt"})
# Returns False - approval was for old parameters
```

### 5.5 ApprovalResult

```python
# From the approval mechanism callback
result = approval_mechanism(approval)

result.is_approved    # True or False
result.approval_id    # The approval request ID
result.decision       # ALLOW (if approved) or DENY (if rejected)
reason              # Human-readable reason
```

---

## 6. Emitting Structured Authorization Audit Events

### 6.1 Every Evaluation Emits an Event

```python
result = guard.evaluate(...)

# The guard emits an audit event automatically
# Access the last event via:
last_event = guard.last_audit_event

# Or use the emitter directly
from mandate.audit.emitter import emit_audit_event
event = emit_audit_event(
    decision=result.decision,
    tool_name=tool_name,
    parameters=sanitized_parameters,
    reason=result.reason,
    approval_id=result.approval_id,
    policy_ids=result.policy_ids,
    evaluation_time_ms=result.evaluation_time_ms,
)
```

**Fail-closed audit emission**: If a required audit event cannot be emitted successfully, the protected action must not execute. The adapter must establish successful required audit emission before allowing the protected action to execute. If required audit emission fails, the adapter blocks the action. A failed audit write must not be represented as a successful audit record. Fallback logging, if available, must not be treated as proof that the required audit event was successfully emitted.

### 6.2 Event Structure (JSON)

### 6.2 Event Structure (JSON)

```json
{
    "event_type": "authorization_decision",
    "timestamp": "2026-01-15T10:30:00Z",
    "guard_version": "0.1.0",
    "tool_name": "file_delete",
    "parameters": {"path": "/etc/passwd"},
    "decision": "deny",
    "reason": "explicit_deny_rule_matched",
    "approval_id": null,
    "policy_ids": ["airport_security.yaml:0"],
    "evaluation_time_ms": 3,
    "sanitized": true
}
```

### 6.3 Sanitization Rules

Parameters are sanitized before emission:
- Any value matching secret patterns (`password`, `secret`, `key`, `token`) is replaced with `"<redacted>"`
- Large objects are truncated with `"truncated": true` flag
- Paths have sensitive components masked (e.g., `/etc/secrets/passwd` → `<redacted>`)
- The library never records raw passwords, API keys, or token values

### 6.4 Integration with FRIDAY JSONL

```python
# In the FRIDAY adapter (not in Mandate itself)
def on_guard_evaluation(guard, tool_name, parameters, context):
    result = guard.evaluate(tool_name, parameters, context)
    
    # Emit structured event for FRIDAY's JSONL logger
    event = {
        "event_type": "mandate_authorization_decision",
        "timestamp": result.timestamp.isoformat(),
        "tool_name": result.tool_name,
        "parameters_sanitized": result.sanitized_parameters,
        "decision": result.decision.value,
        "reason": result.reason,
        "approval_id": result.approval_id,
        "policy_ids": result.policy_ids,
    }
    
    # Fail-closed audit emission: if the audit write fails, block the action
    try:
        friday_jsonl_logger.write(json.dumps(event) + "\n")
    except Exception:
        # Audit emission failed; block the protected action
        raise PermissionError(
            f"Authorization decision could not be recorded; action blocked: {result.reason}"
        )
    
    # Write to FRIDAY's existing JSONL log
```

---

## 7. Illustrative Usage Example - Complete Flow

```python
from mandate import Guard, ALLOW, DENY, REQUIRE_APPROVAL
import json

# 1. Create guard with policies
guard = Guard(policies=["policies/airport_security.yaml"])

# 2. Agent intends to delete a file
tool_name = "file_delete"
parameters = {"path": "/etc/passwd"}
context = {"user": "ai_agent", "session": "sess_abc"}

# 3. Evaluate before execution
result = guard.evaluate(tool_name, parameters, context)

print(f"Decision: {result.decision}")
print(f"Reason: {result.reason}")

# 4. Handle the decision
if result.decision == ALLOW:
    # Proceed with execution
    tool.delete_file(parameters["path"])
    
elif result.decision == DENY:
    # Raise error, do NOT execute
    raise PermissionError(f"Authorization denied: {result.reason}")
    
elif result.decision == REQUIRE_APPROVAL:
    # Request human approval
    approval = guard.request_approval(tool_name, parameters, context)
    
    # Present to human (via CLI, UI, etc.)
    human_approves(approval.id)  # returns True/False
    
    if human_approves:
        # Re-evaluate after approval
        result = guard.evaluate(tool_name, parameters, context)
        if result.decision == ALLOW:
            tool.delete_file(parameters["path"])
        else:
            raise PermissionError("Denied after approval re-evaluation")
    else:
        raise PermissionError("Approval denied by human")

# 5. Audit event is automatically emitted and accessible
event = guard.last_audit_event
print(json.dumps(event.to_dict(), indent=2))
```

---

## 6. Error Classes

```python
from mandate import (
    MandateError,
    PolicyEvaluationError,
    PolicyValidationError,
    ApprovalUnavailableError,
    PermissionError,
)

# Policy evaluation failure
try:
    guard.evaluate(...)
except PolicyEvaluationError as e:
    # Policy was malformed or evaluation failed
    # Decision was automatically DENY
    pass

# Approval unavailable
try:
    guard.request_approval(...)
except ApprovalUnavailableError as e:
    # Approval mechanism is down or timed out
    pass

# Permission denied
try:
    guard.enforce(...)
except PermissionError as e:
    # Action was DENYed
    pass
```