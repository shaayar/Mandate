# Mandate FRIDAY Integration Plan

## 1. Integration Architecture

### 1.1 Thin Adapter Pattern
Mandate integrates with FRIDAY through a **thin adapter layer** that resides in FRIDAY's integration code (not in the Mandate library). The adapter's responsibilities:

1. **Translate FRIDAY context** to Mandate's evaluation API
2. **Invoke `guard.evaluate()`** before every tool execution
3. **Handle decisions**: 
   - `ALLOW` → proceed with tool execution
   - `DENY` → raise `PermissionError`, do not execute
   - `REQUIRE_APPROVAL` → request human approval, then re-evaluate
4. **Proxy audit events** from Mandate to FRIDAY's JSONL logging system
5. **Implement approval mechanism** callback that Mandate calls when `REQUIRE_APPROVAL` is decided

### 1.2 Integration Entry Point
The adapter hooks into FRIDAY's tool invocation pipeline at the `before_tool_execute` point:

```python
# FRIDAY adapter pseudo-code
def before_tool_execute(tool_name, parameters, context):
    # 1. Evaluate through Mandate guard
    result = mandate_guard.evaluate(
        tool_name=tool_name,
        parameters=parameters,
        context=context
    )
    
    # 2. Emit audit event for FRIDAY JSONL log
    emit_audit_event(result)
    
    # 3. Handle decision
    if result.decision == ALLOW:
        # Proceed with execution
        return True
    elif result.decision == DENY:
        # Block execution
        raise PermissionError(f"Denied: {result.reason}")
    elif result.decision == REQUIRE_APPROVAL:
        # Request approval, then re-evaluate
        return handle_approval_flow(result, mandate_guard)
```

---

## 2. Selected High-Risk Tools for First Integration

### 2.1 Priority Order (Highest to Lowest)

| Priority | Tool Category | Specific Tools | Risk Justification |
|---|---|---|---|
| **1** | **File system** | `file_read`, `file_write`, `file_delete` | Highest risk: unrestricted file access; path traversal potential; data exfiltration; core to many AI agent workflows |
| **2** | **Data export** | `data_export`, `scan_directory` | High risk: large data transfers; compliance implications; REQUIRE_APPROVAL use case demonstration |
| **3** | **Web request** | `http_get`, `http_post` | Medium-high risk: network operations; data exfiltration; CORS and origin validation needs; context-aware evaluation |
| **4** | **Database** | (deferred to post-MVP) | Requires connection string handling, credential management |
| **5** | **Process execution** | (deferred to post-MVP) | Highest risk; command injection; requires OS isolation |

### 2.2 Why These Three Categories?

| Category | MVP Justification |
|---|---|
| **File system** | Most common AI agent operation; clear parameter patterns (paths); demonstrates all three decision types; immediate value for FRIDAY's file-based workflows |
| **Data export** | Demonstrates REQUIRE_APPROVAL flow; critical for compliance/audit use case; parameter-driven conditions (size, destination) show policy power |
| **Web request** | Demonstrates context-aware evaluation (URL patterns, user agent, etc.); network boundary security; common in agent workflows for data retrieval |

---

## 3. Adapter Implementation Plan

### 3.1 Phase 1 - Base Integration (Sprint 1)

**Goal**: Integrate Mandate guard with FRIDAY's top-3 tool categories with basic ALLOW/DENY flow.

**Tasks**:
- [ ] Install Mandate as a dependency in FRIDAY
- [ ] Create FRIDAY adapter module: `friday/integration/mandate_adapter.py`
- [ ] Implement `before_tool_execute` hook that calls `guard.evaluate()`
- [ ] Handle ALLOW → proceed, DENY → raise PermissionError
- [ ] Emit audit events to FRIDAY's JSONL logger
- [ ] Write unit tests for the adapter with mock guard

**Deliverable**: FRIDAY can route `file_read`, `file_write`, `file_delete`, `data_export`, `http_get`, `http_post` through Mandate guard with ALLOW/DENY decisions.

### 3.2 Phase 2 - Approval Workflow (Sprint 2)

**Goal**: Add REQUIRE_APPROVAL support for data_export with large sizes.

**Tasks**:
- [ ] Implement approval request flow in adapter
- [ ] Create simple CLI-based approval mechanism for demonstration
- [ ] Implement re-evaluation after approval
- [ ] Handle approval expiration and timeout
- [ ] Test approval flow end-to-end

**Deliverable**: FRIDAY can require human approval for large data exports, and the approval flow works correctly.

### 3.3 Phase 3 - Policy Management (Sprint 3)

**Goal**: Policy loading, validation, and hot-reload.

**Tasks**:
- [ ] Implement policy YAML loading from FRIDAY's policy storage
- [ ] Add policy validation on load
- [ ] Implement hot-reload mechanism
- [ ] Add base policies for file system tools

**Deliverable**: FRIDAY administrators can update policies without restarting, and base policies are in place for common tools.

### 3.4 Phase 4 - Hardening (Post-MVP)

**Tasks**:
- [ ] Add framework-specific integrations (LangChain, etc.)
- [ ] Implement persistent approval store
- [ ] Add advanced condition operators
- [ ] Multi-factor approval support
- [ ] Performance optimization and caching

---

## 4. Adapter Code Structure

### 4.1 Minimal Adapter Skeleton

```python
# friday/integration/mandate_adapter.py

from mandate import Guard, ALLOW, DENY, REQUIRE_APPROVAL
import logging

logger = logging.getLogger(__name__)

# Global guard instance (initialized once)
mandate_guard = Guard()

def init_mandate(policies_path=None):
    """Initialize the Mandate guard with policies."""
    global mandate_guard
    if policies_path:
        mandate_guard = Guard(policies=policies_path)
    else:
        mandate_guard = Guard()

def evaluate_tool_call(tool_name, parameters, context):
    """
    Core adapter function - called by FRIDAY before every tool execution.
    
    Returns:
        True if action is allowed to proceed
        Raises PermissionError if denied
    """
    # 1. Evaluate through Mandate guard
    result = mandate_guard.evaluate(
        tool_name=tool_name,
        parameters=parameters,
        context=context or {}
    )
    
    # 2. Emit audit event for FRIDAY JSONL
    # Fail-closed audit emission: if the audit write fails, block the action
    try:
        _emit_audit_event(result, tool_name, parameters, context)
    except Exception:
        # Audit emission failed; block the protected action
        raise PermissionError(
            f"Authorization decision could not be recorded; action blocked: {result.reason}"
        )
    
    # 3. Handle decision
    if result.decision == ALLOW:
        return True
    
    elif result.decision == DENY:
        raise PermissionError(f"Mandate denied: {result.reason}")
    
    elif result.decision == REQUIRE_APPROVAL:
        return _handle_approval_flow(result, tool_name, parameters, context)

def _handle_approval_flow(result, tool_name, parameters, context):
    """
    Handle REQUIRE_APPROVAL decision: request approval, wait for response,
    re-evaluate, and proceed or deny.
    """
    # Request approval from human
    approval = mandate_guard.request_approval(
        tool_name=tool_name,
        parameters=parameters,
        context=context
    )
    
    # Present to human via whatever mechanism (CLI, UI, etc.)
    # For demonstration, we'll use a simple callback
    human_approved = present_approval_to_human(approval)
    
    if human_approved:
        # Re-evaluate after approval
        result = mandate_guard.evaluate(
            tool_name=tool_name,
            parameters=parameters,
            context=context
        )
        
        if result.decision == ALLOW:
            return True
        else:
            # Something changed after approval; deny
            raise PermissionError(f"Denied after approval re-evaluation: {result.reason}")
    else:
        # Human denied the approval
        raise PermissionError(f"Approval denied by human: {result.reason}")

def _emit_audit_event(result, tool_name, parameters, context):
    """Emit structured audit event to FRIDAY's JSONL log."""
    import json
    from datetime import datetime, timezone
    
    event = {
        "event_type": "mandate_authorization_decision",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "guard_version": "0.1.0",
        "tool_name": result.tool_name,
        "parameters_sanitized": mandate_audit_sanitize(parameters),
        "decision": result.decision.value,
        "reason": result.reason,
        "approval_id": result.approval_id,
        "policy_ids": result.policy_ids,
        "evaluation_time_ms": result.evaluation_time_ms
    }
    
    # Write to FRIDAY's JSONL log (adapter controls what's logged)
    log_line = json.dumps(event, ensure_ascii=False)
    logger.info(log_line)  # FRIDAY's JSONL logger will capture this
    # OR: friday_jsonl_logger.write(log_line + "\n")

def mandate_audit_sanitize(parameters):
    """Sanitize parameters before logging - remove/redact secrets."""
    import re
    
    sanitized = dict(parameters)  # shallow copy
    
    # Redact common secret patterns
    secret_patterns = [
        (r'(?i)password', '<redacted>'),
        (r'(?i)api_key', '<redacted>'),
        (r'(?i)api_secret', '<redacted>'),
        (r'(?i)token', '<redacted>'),
        (r'(?i)secret', '<redacted>'),
    ]
    
    for key, value in sanitized.items():
        for pattern, replacement in secret_patterns:
            if isinstance(value, str) and re.search(pattern, key + value):
                sanitized[key] = replacement
    
    # Truncate large values
    for key, value in sanitized.items():
        if isinstance(value, str) and len(value) > 200:
            sanitized[key] = value[:200] + "...(truncated)"
    
    return sanitized

def present_approval_to_human(approval):
    """
    Present approval request to human and wait for response.
    This is adapter-specific - FRIDAY implements the UI.
    
    For MVP demo purposes only. In production, FRIDAY must implement a proper

# Single-use consumption enforcement
# The approval must be consumed before execution to enforce the single-use guarantee
consume_result = mandate_guard.consume_approval(approval.id)
if not consume_result:
    raise PermissionError(f"Approval {approval.id} was already consumed or is in an invalid state (expired, denied, invalidated); cannot authorize execution. Request a fresh approval.")


# Single-use consumption enforcement
# The approval must be consumed before execution to enforce the single-use guarantee
consume_result = mandate_guard.consume_approval(approval.id)
if not consume_result:
    raise PermissionError(f"Approval {approval.id} was already consumed or is in an invalid state (expired, denied, invalidated); cannot authorize execution. Request a fresh approval.")

    approval UI/mechanism. This function must not be used for production
    authorization decisions.
    """
    # Demo mechanism only - never use for production authorization
    # In production, FRIDAY must implement a proper UI/mechanism
    import os
    _ = os.environ.get("MANDATE_APPROVAL_APROVE", "")  # noqa: F841 - demo variable only
    return False  # demo: always deny in production flow
```

### 4.2 Audit Event Emission (No FRIDAY Dependency)

Mandate **does not depend** on FRIDAY's logging implementation. The adapter is responsible for:

1. Receiving the audit event from `guard.evaluate()`
2. Sanitizing any remaining sensitive data
3. Formatting as JSONL for FRIDAY's existing log infrastructure
4. Writing to the appropriate log file

```python
# Adapter - receives event data from Mandate, formats for FRIDAY
def on_mandate_audit_event(event_data):
    """
    Called by Mandate's audit emitter or called after evaluate().
    event_data contains sanitized fields from the EvaluationResult.
    """
    import json
    log_line = json.dumps(event_data, ensure_ascii=False)
    # Write to FRIDAY's JSONL log file
    friday_jsonl_path = "/var/log/friday/authorizations.jsonl"
    with open(friday_jsonl_path, "a") as f:
        f.write(log_line + "\n")
```

---

## 5. FRIDAY Integration Checklist

### 5.1 Pre-Integration

- [ ] Mandate library is packaged and installed (or imported from source)
- [ ] FRIDAY adapter team reviews design documents (design, API, scope, threat model)
- [ ] Approval questions decisions are resolved (see open-questions.md)
- [ ] Policy YAML files are defined for the 3 tool categories
- [ ] Test environment is set up with Mandate as a dependency

### 5.2 Integration Tasks

- [ ] Create `friday/integration/mandate_adapter.py`
- [ ] Hook `before_tool_execute` into FRIDAY's tool invocation pipeline
- [ ] Implement ALLOW/DENY flow for all 3 tool categories
- [ ] Implement REQUIRE_APPROVAL flow for `data_export` with size conditions
- [ ] Wire audit events to FRIDAY JSONL logger
- [ ] Test end-to-end: tool call → guard evaluate → decision → execution/prohibition
- [ ] Test approval flow: REQUIRE_APPROVAL → human response → re-evaluate → proceed/deny
- [ ] Test policy loading and hot-reload
- [ ] Test error cases: malformed policy, evaluation failure, unavailable approval

### 5.3 Post-Integration Validation

- [ ] All 42 acceptance criteria pass with FRIDAY adapter
- [ ] All security test matrix tests pass in FRIDAY context
- [ ] No secrets leaked in FRIDAY JSONL logs
- [ ] Approval flow works correctly (approve/deny/invalidate)
- [ ] Default-deny applies to uncovered actions
- [ ] Audit events are structured and JSONL-compatible
- [ ] FRIDAY team signs off on integration

---

## 6. Integration Risks and Mitigations

| Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|
| **Adapter bypasses guard** | No security value | High | Code review mandate; static analysis; integration tests that verify every tool call goes through guard |
| **Secrets leak in audit events** | Data breach | Medium | Mandate library redacts known patterns; adapter performs additional sanitization; regex scan of 100+ events before release |
| **Approval flow not implemented correctly** | REQUIRE_APPROVAL bypassed | Medium | Integration tests for all approval lifecycle states; approval invalidation on parameter change; timeout handling |
| **Policy conflicts cause unexpected behavior** | Mis-authorization | Low | Documentation of precedence; tests for conflict scenarios; first-match wins is deterministic |
| **Performance impact** | Slow tool execution | Low | Evaluation timeout (30s); benchmark; caching considered for post-MVP |
| **Policy YAML schema drift** | Policies break | Low | Schema validation on load; CI test that policies validate; version pinning |

---

## 7. Integration Boundary

### What the Adapter Does (In Scope)
- Translates FRIDAY context to Mandate API
- Calls `guard.evaluate()` before every tool execution
- Handles ALLOW/DENY/REQUIRE_APPROVAL decisions
- Emits audit events to JSONL
- Implements approval mechanism callback
- Sanitizes parameters before logging

### What the Adapter Does NOT Do (Out of Scope)
- Modifies Mandate's core logic
- Depend on FRIDAY's logging implementation
- Bypasses the guard for any reason
- Implements custom approval UI (just provides the API for it)
- Handles OS-level sandboxing or process isolation
- Manages credentials or secrets beyond redaction

---

## 8. Migration Path from FRIDAY's Existing Security Controls

FRIDAY currently has existing security controls. The integration plan:

1. **Existing controls REMAIN in place** - Mandate does not replace FRIDAY's transport security, process isolation, credential management, or rate limiting
2. **Mandate adds authorization policy enforcement** at the tool-call boundary
3. **Adapter proxies audit events** to FRIDAY's existing JSONL logs without depending on FRIDAY's logging implementation
4. **FRIDAY's adapter** is the single point of integration; if the adapter is removed, Mandate has no effect (by design - framework-agnostic)
5. **Transition**: New tool calls go through Mandate guard; existing controls continue to operate in parallel during transition period